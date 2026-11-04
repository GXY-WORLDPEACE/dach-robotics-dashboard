"""Collect independently verified official sources; publish active and other phases."""
import datetime as dt
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
from functools import partial
from .core import ROOT,merge
from .institutions import classify
from . import ted,bkms,dfg,simap,tenderned,usp,vmp
from .coverage import registry,report
from .public_sources import relevant
from .opportunities import coalesce,normalized
from .audit import audit

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)

def main():
    now=dt.datetime.now(dt.timezone.utc);previous=ROOT/'data'/'history.json'
    old=json.loads(previous.read_text()).get('tenders',[]) if previous.exists() else []
    status={'scanned_at':now.isoformat(),'sources':{},'errors':[]}
    config=registry()
    for source in config['sources']:
        if not source.get('enabled'):status['sources'][source['id']]={'status':source.get('status','not_connected'),'note':source.get('reason','暂未接入')}
    fresh=[];success={};dfg_live=[]
    collectors=[('TED',ted.collect),('BKMS',bkms.collect),('DFG',dfg.collect),('SIMAP',simap.collect),('USP',usp.collect),('TENDERNED',tenderned.collect)]
    collectors += [(s['id'],partial(vmp.collect_source,s)) for s in config['sources'] if s.get('kind')=='vmp_zip' and s.get('enabled')]
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs={pool.submit(collect,now):name for name,collect in collectors}
        for job in as_completed(jobs):
            name=jobs[job]
            try:
                items,details=job.result()
                details.pop('current_ids',None)
                status['sources'][name]={'status':'connected',**details}
                success[name]={x['id'] for x in items};fresh+=items
                if name=='DFG':dfg_live=items
                print(f'{name}: {len(items)} source notices',flush=True)
            except Exception as e:
                error=f'{name}: {type(e).__name__}: {e}'
                status['sources'][name]={'status':'error','note':'保留上次成功数据，可能陈旧'};status['errors'].append(error)
                print(error,file=sys.stderr,flush=True)
    # Attach a portal reference only for an unambiguous exact buyer+title match.
    for portal in dfg_live:
        matching=[x for x in fresh if x.get('source')=='BKMS' and normalized(x.get('buyer'))==normalized(portal.get('buyer')) and normalized(x.get('title'))==normalized(portal.get('title'))]
        identities={x.get('procedure_id') or x.get('notice_id') for x in matching}
        if len(identities)==1:
            for x in matching:
                if not x.get('procurement_reference'):x['procurement_reference']=portal['procurement_reference']
    history=merge(old,fresh)
    for item in history:
        if 'institution_type' not in item:item.update(classify(item))
        if item.get('source') not in ('BKMS',) and item.get('source') in success:
            item['source_unavailable']=bool(item.get('detail_unavailable')) or item['id'] not in success[item['source']]
    board=coalesce([x for x in history if x.get('source') not in ('TENDERNED','USP','SIMAP') or relevant(x.get('title',''),x.get('description',''))],now,dfg_live)
    active=[x for x in board if x['phase']=='active']
    timestamp=now.isoformat()
    write(ROOT/'data'/'history.json',{'updated_at':timestamp,'tenders':history})
    write(ROOT/'data'/'tenders.json',{'updated_at':timestamp,'tenders':active})
    write(ROOT/'data'/'opportunities.json',{'updated_at':timestamp,'tenders':board})
    write(ROOT/'data'/'coverage_audit.json',audit(board,timestamp))
    status.update(new_items_fetched=len(fresh),active_count=len(active),history_count=len(history),
       project_count=len(board),phase_counts=dict(Counter(x['phase'] for x in board)),
       education_active_count=sum(bool(x.get('education_research')) for x in active),
       feeds_enabled=sum(x.get('status') in ('connected','partial') for x in status['sources'].values()),
       country_counts=dict(Counter(x['country'] for x in active)))
    write(ROOT/'data'/'source_coverage.json',report(status,board,timestamp))
    write(ROOT/'data'/'scan_status.json',status)
    print(json.dumps({k:v for k,v in status.items() if k!='sources'},ensure_ascii=False),flush=True)
    return 1 if status['errors'] else 0
if __name__=='__main__':sys.exit(main())
