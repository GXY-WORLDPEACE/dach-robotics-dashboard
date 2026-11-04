"""Collect real TED notices and retain an auditable, deduplicated history."""
import datetime as dt
import json
import sys
from .core import ROOT, merge
from .ted import collect

def write(path, data):
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(path)

def main():
    now=dt.datetime.now(dt.timezone.utc)
    target=ROOT/'data'/'tenders.json'
    archive=ROOT/'data'/'history.json'
    previous=archive if archive.exists() else target
    old=json.loads(previous.read_text()).get('tenders',[]) if previous.exists() else []
    status={'scanned_at':now.isoformat(),'sources':{'TED':{'status':'error'},'SIMAP':{'status':'not_connected','note':'官方 OpenAPI 已确认；搜索及详情映射与稳定性尚未验证，暂未接入。'}},'errors':[]}
    try:
        fresh,details=collect(now)
        history=merge(old,fresh)
        active_ids=set(details.pop('current_ids'))
        for item in history:
            if item.get('source')=='TED' and item['id'] not in active_ids:
                item['status']='已过期或不再出现在当前 TED 查询中'
        active=[x for x in history if x['id'] in active_ids]
        write(ROOT/'data'/'history.json',{'updated_at':now.isoformat(),'tenders':history})
        write(target,{'updated_at':now.isoformat(),'tenders':active})
        status.update(new_items_fetched=len(fresh),active_count=len(active),history_count=len(history),feeds_enabled=1)
        status['sources']['TED']={'status':'connected',**details}
        print(json.dumps(status,ensure_ascii=False))
    except Exception as e:
        status['errors']=[f'{type(e).__name__}: {e}'];status['feeds_enabled']=0
        print(status['errors'][0],file=sys.stderr)
    write(ROOT/'data'/'scan_status.json',status)
    return 1 if status['errors'] else 0

if __name__=='__main__':sys.exit(main())
