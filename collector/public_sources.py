"""Small helpers for public, unauthenticated official sources."""
import datetime as dt
import json
import hashlib
import os
from pathlib import Path
import re
import time
import urllib.request
from zoneinfo import ZoneInfo
from .core import normalize
from .institutions import classify
from .ted import match
COUNTRIES={'DEU':'DE','AUT':'AT','CHE':'CH','NLD':'NL','BEL':'BE'}

def request(url,payload=None,limit=12_000_000):
    cache_root=os.environ.get('PUBLIC_SOURCE_CACHE_DIR')
    cache_file=None
    if cache_root:
        key=hashlib.sha256((url+json.dumps(payload,sort_keys=True)).encode()).hexdigest()
        cache_file=Path(cache_root)/(key+'.json')
        if cache_file.exists():return json.loads(cache_file.read_text())
    req=urllib.request.Request(url,data=json.dumps(payload).encode() if payload is not None else None,
        headers={'User-Agent':'Robotics-Education-Procurement-Monitor/4.0','Accept':'application/json','Content-Type':'application/json'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=40) as r:
                raw=r.read(limit+1)
                if len(raw)>limit:raise RuntimeError('Response exceeds size limit')
                data=json.loads(raw)
                if cache_file:
                    cache_file.parent.mkdir(parents=True,exist_ok=True);cache_file.write_text(json.dumps(data))
                return data
        except Exception as e:
            if getattr(e,'code',None) in (401,403,404) or attempt==2:raise
            time.sleep(2**attempt)

def multilingual(v):
    if isinstance(v,dict):
        for lang in ['de','en','nl','fr','it','deu','eng','nld','fra']:
            if v.get(lang):return multilingual(v[lang])
        return next((multilingual(x) for x in v.values() if x),'')
    if isinstance(v,list):return ' / '.join(multilingual(x) for x in v if x)
    return str(v or '')

def relevant(title,description=''):
    title=title or '';s=(title+' '+(description or '')).casefold()
    if any(x in title.casefold() for x in ['ebook','e-book','e book','robotic process','rpa','kanalsanierung','mähroboter','rasenmäher','reinigungsdienst','softwarelizenz','gebäudeautomation','gebaeudeautomation']):return False
    return bool(re.search(r'robot|cobot|manipulator|humanoid|teleoper|quadrup',s) or re.search(r'automat',title,re.I))

def deadline(v,zone='Europe/Berlin'):
    if not v:return None
    v=str(v).strip()
    try:
        if len(v)==10:return dt.date.fromisoformat(v).isoformat()
        t=dt.datetime.fromisoformat(v)
        return (t if t.tzinfo else t.replace(tzinfo=ZoneInfo(zone))).isoformat()
    except ValueError:return None

def record(source,notice_id,title,buyer,country,description,publication_date,url,now,
           end=None,stage='notice',procedure_id=None,reference=None,links=None):
    if country not in ('DE','AT','CH','NL','BE') or not title or not url:return None
    x=normalize({'notice_id':source+':'+str(notice_id),'title':title,'buyer':buyer,'country':country,
       'description':description,'publication_date':publication_date,'deadline':deadline(end),
       'source_url':url,'verification_status':'官方公开来源；技术规格待复核'})
    if x is None:return None
    x.update(source=source,notice_id=str(notice_id),procedure_id=procedure_id,procurement_reference=reference,
       notice_stage=stage,collected_at=now.isoformat(),official_links=links or [],
       deadline_source=url if end else None,budget_amount=None,budget_currency=None)
    x['priority'],x['matched_products'],x['match_reasons']=match(x)
    x['match_score']={'P1':85,'P2':55,'P3':20}[x['priority']]
    x.update(classify({**x,'description':description}))
    return x
