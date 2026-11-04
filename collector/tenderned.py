"""TenderNed public TNS JSON service (CC0). No private XML API credentials."""
import datetime as dt
import time
from .public_sources import request,relevant,record
API='https://www.tenderned.nl/papi/tenderned-rs-tns/v2/publicaties'

def parse(n,now):
    title=n.get('aanbestedingNaam','');desc=n.get('opdrachtBeschrijving','')
    if not relevant(title,desc):return None
    code=n.get('typePublicatie',{}).get('code')
    sub=n.get('publicatiecode',{}).get('code')
    stage='result' if code in ('AGO','VBE','AAW') else 'planned' if code in ('VAK','MAC') and sub not in ('EF10','EF11','EF12','EF13') else 'notice'
    item=record('TENDERNED',n['publicatieId'],title,n.get('opdrachtgeverNaam'),'NL',desc,n.get('publicatieDatum'),n.get('link',{}).get('href') or f"https://www.tenderned.nl/aankondigingen/overzicht/{n['publicatieId']}",now,
        end=n.get('sluitingsDatum'),stage=stage,procedure_id='TenderNed:'+str(n['kenmerk']) if n.get('kenmerk') else None)
    if item:item['publication_type']=n.get('typePublicatie',{}).get('omschrijving')
    return item

def collect(now):
    since=(now.date()-dt.timedelta(days=90)).isoformat();items=[];scanned=0;last_day=None
    for page in range(200):
        d=request(f'{API}?page={page}&size=100')
        rows=d.get('content')
        if page%10==0:print(f'TenderNed: page {page+1}',flush=True)
        if not isinstance(rows,list):raise RuntimeError('TenderNed schema changed')
        for n in rows:
            pub=n.get('publicatieDatum')
            if not pub:raise RuntimeError('TenderNed publication date missing')
            if last_day and pub>last_day:raise RuntimeError('TenderNed publication sort changed; refusing truncated coverage')
            last_day=pub
            if pub<since:continue
            scanned+=1;x=parse(n,now)
            if x:items.append(x)
        if d.get('last') or not rows or min(x['publicatieDatum'] for x in rows)<since:break
        time.sleep(.25)
    else:raise RuntimeError('TenderNed 90-day pagination limit exceeded')
    return items,{'endpoint':API,'window_start':since,'scanned_notices':scanned,'accepted_notices':len(items),'license':'CC0','scope':'公开 TNS 最近 90 天；不等于所有未公开或历史采购'}
