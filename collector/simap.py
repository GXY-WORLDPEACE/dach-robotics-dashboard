"""SIMAP official public search + details with rolling pagination."""
import datetime as dt
import time
from urllib.parse import urlencode
from .public_sources import request,multilingual,relevant,record
BASE='https://www.simap.ch/api/publications'
SUPPLY_TERMS=['automatisierung','automation','automatisation','automazione']
TERMS=['robot','cobot','manipulator','manipulateur','manipolatore','humanoid','umanoide',*SUPPLY_TERMS]

def parse(p,d,now):
    info=d.get('project-info',{});proc=d.get('procurement',{})
    title=multilingual(info.get('title') or p.get('title'));desc=multilingual(proc.get('orderDescription'))
    if not relevant(title,desc):return None
    kind=d.get('type') or p.get('pubType')
    stage='result' if kind in ('award','direct_award','revocation','abandonment') else 'planned' if kind in ('advance_notice','request_for_information') else 'notice'
    dates=d.get('dates',{});buyer=multilingual(info.get('procOfficeAddress',{}).get('name') or p.get('procOfficeName'))
    end=dates.get('offerDeadline') or dates.get('participationDeadline')
    x=record('SIMAP',p['publicationId'],title,buyer,'CH',desc,p.get('publicationDate') or d.get('base',{}).get('publicationDate'),f"https://www.simap.ch/de/project-detail/{p['id']}",now,end=end,stage=stage,procedure_id='SIMAP:'+p['id']+(':lot:'+str(p['_lot_key']) if p.get('_lot_key') else ''),reference=p.get('projectNumber'))
    if x:
        x['publication_type']=kind;x['lot_key']=p.get('_lot_key');x['canton']=(p.get('orderAddress') or {}).get('cantonId')
        x['final_user']=multilingual(info.get('procurementRecipientAddress',{}).get('name')) or None
        if x['final_user'] and not x['education_research']:
            from .institutions import classify
            x.update(classify({**x,'description':desc+' '+x['final_user']}))
    return x

def collect(now):
    since=(now.date()-dt.timedelta(days=90)).isoformat();projects={};scanned=0
    for term in TERMS:
        params={'search':term,'newestPublicationFrom':since};seen=set()
        if term in SUPPLY_TERMS:params['projectSubTypes']='supply'
        for page in range(100):
            d=request(BASE+'/v2/project/project-search?'+urlencode(params))
            rows=d.get('projects')
            if not isinstance(rows,list):raise RuntimeError('SIMAP search schema changed')
            scanned+=len(rows)
            print(f'SIMAP: {term} page {page+1}, {len(rows)} hits',flush=True)
            for p in rows:
                # Projects with lots expose publication IDs at lot level.
                lots=[lot for lot in p.get('lots',[]) if lot.get('publicationId')]
                if p.get('publicationId') and not lots:projects[p['publicationId']]=p
                for lot in lots:
                    lot_key=lot.get('id') or lot.get('lotId') or lot.get('lotNumber') or lot['publicationId']
                    projects[lot['publicationId']]={**p,**lot,'id':p['id'],'_lot_key':lot_key}
            token=d.get('pagination',{}).get('lastItem')
            if not rows or not token:break
            if token in seen:raise RuntimeError('SIMAP pagination repeated')
            seen.add(token);params['lastItem']=token;time.sleep(.2)
        else:raise RuntimeError('SIMAP pagination limit exceeded')
    items=[];detail_errors=[];detail_started=time.monotonic()
    for index,p in enumerate(projects.values(),1):
        try:
            if time.monotonic()-detail_started>600:raise TimeoutError('本轮详情核验时间预算已用完；保留官方索引，截止待核实')
            d=request(f"{BASE}/v1/project/{p['id']}/publication-details/{p['publicationId']}",timeout=15,attempts=2)
            x=parse(p,d,now)
        except Exception as e:
            detail_errors.append({'publication_id':p['publicationId'],'error':type(e).__name__})
            x=parse(p,{},now)
            if x:x.update(detail_unavailable=True,verification_status='SIMAP 官方索引；详情访问失败，截止待核实')
        if x:items.append(x)
        if index%10==0 or index==len(projects):
            print(f'SIMAP: {index}/{len(projects)} detail pages processed',flush=True)
        time.sleep(.15)
    return items,{'endpoint':BASE+'/v2/project/project-search','window_start':since,'search_terms':TERMS,'scanned_hits':scanned,'unique_publications':len(projects),'accepted_notices':len(items),'detail_errors':detail_errors,'status':'partial' if detail_errors else 'connected','scope':'SIMAP 公开公告，覆盖申报的联邦／州／市项目；不含未公开采购','detail_time_budget_seconds':600,'reuse':'遵循 SIMAP 使用条件；不保存联系人及投标文件'}
