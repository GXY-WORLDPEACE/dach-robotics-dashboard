import json,re,hashlib,datetime,html
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
KEYWORDS={'robot':18,'robotik':18,'robotics':18,'cobot':22,'kollaborativ':12,'manipulator':20,'greifer':15,'gripper':15,'humanoid':18,'quadruped':18,'vierbeiner':18,'automatisierung':9,'automation':9,'mobile robot':18,'roboterarm':20,'robot arm':20,'teleoperation':18,'ros2':15,'pick and place':12,'machine vision':12,'bildverarbeitung':10}
NEGATIVE={'reinigungsroboter':-35,'saugroboter':-35,'rasenmäher':-35,'chirurg':-25,'da vinci':-25}
PRODUCTS=[('DOBOT CR / CRA','cobot kollaborativ roboterarm robot arm pick and place automatisierung'),('DOBOT Magician / E6','education ausbildung lehre schule training robotik'),('DOBOT ATOM / X-Trainer','humanoid zweiarmsystem dual arm embodied ai teleoperation imitation learning'),('DOBOT Quadruped','quadruped vierbeiner roboterhund'),('DOBOT Mobile Manipulation','mobile robot navigation manipulation logistics')]

def score(title,description):
    s=(title+' '+description).lower(); raw=sum(w for k,w in KEYWORDS.items() if k in s)+sum(w for k,w in NEGATIVE.items() if k in s)
    matches=[name for name,keys in PRODUCTS if any(k in s for k in keys.split(' ') if len(k)>4)]
    val=max(0,min(100,round(raw*1.5)))
    return val,('P1' if val>=65 else 'P2' if val>=30 else 'P3'),matches

def normalize(item):
    title=str(item.get('title') or '').strip(); url=str(item.get('source_url') or '').strip()
    if not title or not url or urlparse(url).scheme not in ('https','http'): return None
    desc=re.sub('<[^>]+>',' ',html.unescape(str(item.get('description') or '')))
    pts,priority,products=score(title,desc)
    identifier=str(item.get('notice_id') or hashlib.sha256(url.encode()).hexdigest()[:16])
    return {'id':identifier,'title':title,'buyer':item.get('buyer') or None,'country':item.get('country') or None,'region':item.get('region') or None,'description':desc[:1400], 'publication_date':item.get('publication_date') or None,'deadline':item.get('deadline') or None,'budget_amount':item.get('budget_amount') or None,'budget_currency':item.get('budget_currency') or None,'source_url':url,'priority':priority,'match_score':pts,'matched_products':products,'verification_status':item.get('verification_status') or '待核实','first_seen':item.get('first_seen') or datetime.date.today().isoformat(),'last_seen':datetime.date.today().isoformat(),'status':item.get('status') or '待核实'}

def merge(old,new):
    entries={x['id']:x for x in old if 'id' in x}
    for item in new:
        if item['id'] in entries:
            before=entries[item['id']]; item['first_seen']=before.get('first_seen',item['first_seen']); item['status']=before.get('status',item['status'])
        entries[item['id']]=item
    return sorted(entries.values(),key=lambda x:(x['priority'],x.get('deadline') or '9999',x['title']))

def save(items):
    p=ROOT/'data'/'tenders.json'; p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps({'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tenders':items},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
