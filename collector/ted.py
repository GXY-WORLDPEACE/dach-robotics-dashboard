"""Keyless official TED Search API. No estimated or generated notice content."""
import datetime as dt
import json
import time
import urllib.request
from zoneinfo import ZoneInfo
from .core import normalize
from .institutions import classify

API = 'https://api.ted.europa.eu/v3/notices/search'
FIELDS = ['publication-number','notice-title','buyer-name','buyer-country','publication-date',
          'deadline-receipt-tender-date-lot','deadline-receipt-tender-time-lot',
          'description-proc','estimated-value-proc','estimated-value-cur-proc','form-type',
          'procedure-identifier','internal-identifier-proc','notice-identifier']

def values(v):
    if isinstance(v, dict):
        v = v.get('deu', v.get('eng', next(iter(v.values()), [])))
    if isinstance(v, list):
        return [str(x) for x in v if x is not None]
    return [] if v is None else [str(v)]

def text(v):
    return ' / '.join(dict.fromkeys(values(v)))

def query(today):
    terms = ['robot*','cobot*','manipulator*','humanoid*','automatisierung*','automation*']
    keywords = ' OR '.join(f'{field} ~ {term}' for field in ['title-proc','description-proc'] for term in terms)
    return (f'buyer-country IN (DEU AUT) AND form-type = competition AND '
            f'deadline-receipt-tender-date-lot >= {today:%Y%m%d} AND ({keywords})')

def request(payload):
    for attempt in range(3):
        try:
            req = urllib.request.Request(API, data=json.dumps(payload).encode(),
                headers={'Content-Type':'application/json','User-Agent':'DACH-Robotics-Dashboard/2.0'})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            if data.get('timedOut'):
                raise RuntimeError('TED search timed out; refusing partial update')
            return data
        except Exception:
            if attempt == 2: raise
            time.sleep(2 ** attempt)

def parse(n, now):
    countries=values(n.get('buyer-country'))
    country=next(({'DEU':'DE','AUT':'AT'}[c] for c in countries if c in ('DEU','AUT')),None)
    if not country or text(n.get('form-type')) != 'competition': return None
    title=text(n.get('notice-title')).lower()
    training_service='berufsausbildung' in title and not any(term in title for term in ['robot','cobot','manipulator','lernstation','lernfabrik'])
    if training_service: return None
    if any(term in title for term in ['software','lizenz','bauarbeiten','bauinstallations','planungsleistungen','consulting','marketing','elektroinstall','gebäudeautomation','gebaeudeautomation','gebäudeleittechnik','heizungs','netzausrüstung','chirurgische eingriffe','installation von','schaltanlagen']): return None
    dates=values(n.get('deadline-receipt-tender-date-lot'))
    times=values(n.get('deadline-receipt-tender-time-lot'))
    deadlines=[]
    for i, date in enumerate(dates):
        try:
            day=dt.date.fromisoformat(date[:10])
            # Keep the timezone published by TED. Missing time is explicitly date-only.
            clock=times[i] if len(times)==len(dates) else None
            instant=dt.datetime.fromisoformat(day.isoformat()+'T'+clock) if clock else dt.datetime.combine(day,dt.time.max,ZoneInfo('Europe/Berlin'))
            if instant.tzinfo is None: instant=instant.replace(tzinfo=ZoneInfo('Europe/Berlin'))
            if instant>now: deadlines.append((instant,day.isoformat() if not clock else instant.isoformat()))
        except ValueError: continue
    if not deadlines: return None
    deadline=min(deadlines)[1]
    notice=text(n.get('publication-number'))
    if not notice: return None
    item=normalize({'notice_id':'TED:'+notice,'title':text(n.get('notice-title')),
        'description':text(n.get('description-proc')),'buyer':text(n.get('buyer-name')),
        'country':country,'publication_date':text(n.get('publication-date'))[:10],
        'deadline':deadline,'source_url':f'https://ted.europa.eu/en/notice/-/detail/{notice}',
        'verification_status':'TED 官方公告；技术规格待复核','status':'投标中'})
    if not item: return None
    item.update(source='TED',collected_at=now.isoformat(),notice_id=notice,
        procedure_id=text(n.get('procedure-identifier')) or None,
        procurement_reference=text(n.get('internal-identifier-proc')) or None,
        notice_uuid=text(n.get('notice-identifier')) or None,notice_stage='notice',
        deadlines=sorted(set(x[1] for x in deadlines)),
        budget_amount=text(n.get('estimated-value-proc')) or None,
        budget_currency=text(n.get('estimated-value-cur-proc')) or None,
        budget_basis='公告程序级预估金额；非单台设备预算',
        match_reasons=match(item)[2])
    item['priority'],item['matched_products'],_=match(item)
    item['match_score']={'P1':85,'P2':55,'P3':20}[item['priority']]
    item.update(classify({**item,'description':text(n.get('description-proc'))}))
    if item['institution_type'] in ('vocational','training','chamber') and any(t in (item['title']+' '+item['description']).lower() for t in ['robot','cobot','manipulator']):
        if 'DOBOT Magician / E6' not in item['matched_products']: item['matched_products'].append('DOBOT Magician / E6')
        item['match_reasons'].append('职业教育／培训场景：可核实 Magician、E6 或 CR/CRA 教学实训配置；不代表满足技术要求')
    return item

def match(item):
    s=(item['title']+' '+item['description']).lower()
    groups=[('DOBOT CR / CRA',['cobot','kollaborativ','roboterarm','robot arm','industrieroboter']),
      ('DOBOT Magician / E6',['lernroboter','lehrroboter','bildungsroboter','education robot','ausbildungsroboter']),
      ('DOBOT ATOM / X-Trainer',['humanoid','dual-arm','dual arm','zweiar','teleoperation','imitation learning']),
      ('DOBOT Mobile Manipulation',['mobile robot','mobile roboter','mobiler roboter','fahrerlos','autonomer mobiler']),
      ('DOBOT Quadruped',['quadruped','vierbein','roboterhund','boston dynamics spot'])]
    products=[];reasons=[]
    for product,terms in groups:
        hits=[t for t in terms if t in s]
        if hits:products.append(product);reasons.append(product+'：公告包含 '+', '.join(hits))
    if any(t in s for t in ['operationstechnik','endoprothetik','pipettier','chirurg','reinigungsrobot','rasenmäh','kanalinspek','da vinci']):
        return 'P3',products,['专用医疗/清洁/检查应用，DOBOT 直接适配度低；需人工复核']
    if 'boston dynamics' in s or '„spot“' in s:
        return 'P3',products,['Fremdfabrikat SPOT ausdrücklich genannt；先核实是否允许等效产品，不能视为 DOBOT 直接替代']
    if products:return 'P1',products,reasons+['关键词匹配；负载、臂展、安全与接口尚未核实']
    if 'robot' in s or 'manipulator' in s:return 'P2',['DOBOT CR / CRA / E6 / ATOM（待确认）'],['明确涉及机器人，平台类型及技术规格待确认']
    return 'P3',[],['仅涉及自动化，需先确认是否包含机器人采购']

def collect(now):
    q=query(now.astimezone(ZoneInfo('Europe/Berlin')).date())
    payload={'query':q,'fields':FIELDS,'limit':200,'paginationMode':'PAGE_NUMBER','page':1,'scope':'ACTIVE','checkQuerySyntax':False}
    items=[];count=0;seen=set()
    for page in range(1000):
        data=request(payload)
        notices=data.get('notices')
        if not isinstance(notices,list): raise RuntimeError('Invalid TED response')
        count+=len(notices)
        for n in notices:
            item=parse(n,now)
            if item: items.append(item)
        total=data.get('totalNoticeCount')
        if total is None: raise RuntimeError('TED omitted total count')
        if total>15000: raise RuntimeError('TED result exceeds pagination limit; narrow query')
        if count>=total: break
        if not notices: raise RuntimeError('TED returned incomplete page')
        payload['page']+=1
        time.sleep(.3)
    else:raise RuntimeError('TED pagination safety limit exceeded')
    latest={}
    for item in items:
        key=item.get('procedure_id') or item['id']
        if key not in latest or (item['publication_date'],int(item['notice_id'].split('-')[0])) > (latest[key]['publication_date'],int(latest[key]['notice_id'].split('-')[0])): latest[key]=item
    return items,{'current_ids':[x['id'] for x in latest.values()],'query':q,'api_results':count,'accepted':len(items),'endpoint':API}
