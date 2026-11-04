"""German official Bekanntmachungsservice Open Data (CC0), original eForms.
Two calendar months, including all notice types; never infer a deadline from a CSV
validity period or from a public opening date.
"""
import csv
import datetime as dt
import io
import os
from pathlib import Path
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from zoneinfo import ZoneInfo
from .core import normalize
from .institutions import classify
from .ted import match

API='https://oeffentlichevergabe.de/api/notice-exports'
NS={'a':'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'b':'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'e':'http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1'}

def val(node,path):
    if node is None:return ''
    e=node.find(path,NS)
    return ''.join(e.itertext()).strip() if e is not None else ''

def relevant(title,description):
    s=(title+' '+description).lower()
    if any(t in title.lower() for t in ['robotic process','rpa','kanal','kanalsanierung','mähroboter','rasenmäh','wartungsvertrag','geräteschulung']):return False
    if any(t in title.lower() for t in ['gebäudeautomation','gebaeudeautomation','gebäudeleittechnik','heizungs','softwarelizenz']):return False
    return bool(re.search(r'robot|cobot|manipulator|humanoid|teleoperation|quadruped',s) or re.search(r'automat',title,re.I))

def fetch_archive(month,format):
    # Cache files are untracked intermediate data, keyed by export date because
    # even a previous month can receive delayed official publications.
    today=dt.datetime.now(ZoneInfo('Europe/Berlin')).date().isoformat()
    root=Path(os.environ.get('BKMS_CACHE_DIR','.cache/bkms'));root.mkdir(parents=True,exist_ok=True)
    p=root/f'{today}-{month}-{format}'
    if not p.exists():
        url=f'{API}?pubMonth={month}&format={format}'
        for attempt in range(3):
            try:
                req=urllib.request.Request(url,headers={'User-Agent':'DACH-Robotics-Dashboard/3.0'})
                tmp=p.with_suffix('.part')
                with urllib.request.urlopen(req,timeout=60) as r,tmp.open('wb') as f:
                    size=0
                    while chunk:=r.read(1024*1024):
                        size+=len(chunk)
                        if size>400_000_000:raise RuntimeError('BKMS archive exceeds size limit')
                        f.write(chunk)
                with zipfile.ZipFile(tmp) as z:
                    if z.testzip():raise RuntimeError('Invalid BKMS ZIP')
                tmp.replace(p);break
            except Exception:
                if attempt==2:raise
                time.sleep(2**attempt)
    return zipfile.ZipFile(p)

def csv_rows(z,name):
    with z.open(name) as f:return list(csv.DictReader(io.TextIOWrapper(f,encoding='utf-8-sig')))

def parse_xml(raw,meta,now):
    root=ET.fromstring(raw)
    project=root.find('a:ProcurementProject',NS)
    title=val(project,'b:Name');description=val(project,'b:Description')
    if not title:return None
    if not relevant(title,description):return None
    parties=[]
    for cp in root.findall('a:ContractingParty/a:Party',NS):
        name=val(cp,'a:PartyName/b:Name')
        if not name:
            ident=val(cp,'a:PartyIdentification/b:ID')
            for company in root.findall('.//e:Organization/e:Company',NS):
                if ident and val(company,'a:PartyIdentification/b:ID')==ident:
                    name=val(company,'a:PartyName/b:Name');break
        if name:parties.append(name)
    identifier=meta.get('noticeIdentifier') or val(root,'b:ID')
    if not identifier:return None
    urls=[e.text.strip() for e in root.findall('.//a:CallForTendersDocumentReference//b:URI',NS) if e.text and e.text.startswith('http')]
    deadlines=[]
    for period in root.findall('.//a:TenderSubmissionDeadlinePeriod',NS)+root.findall('.//a:ParticipationRequestReceptionPeriod',NS):
        date=val(period,'b:EndDate');clock=val(period,'b:EndTime')
        if not date:continue
        try:
            if clock:
                t=dt.datetime.fromisoformat(date[:10]+'T'+clock)
                if t.tzinfo is None:t=t.replace(tzinfo=ZoneInfo('Europe/Berlin'))
                deadlines.append(t.isoformat())
            else:deadlines.append(date[:10])
        except ValueError:continue
    code=val(root,'b:NoticeTypeCode');procedure=val(root,'a:TenderingProcess/b:ProcedureCode')
    form=meta.get('formType','')
    stage='result' if root.tag.endswith('ContractAwardNotice') or form=='result' else 'notice'
    if root.tag.endswith('PriorInformationNotice') or form=='planning' or 'beabsichtig' in procedure.lower() or 'ex ante' in title.lower():stage='planned'
    item=normalize({'notice_id':'BKMS:'+identifier+':'+meta.get('noticeVersion','1'),'title':title,
       'description':description,'buyer':' / '.join(dict.fromkeys(parties)),
       'country':'DE','publication_date':meta.get('publicationDate','')[:10] or val(root,'b:RequestedPublicationDate')[:10] or None,
       'deadline':min(deadlines) if deadlines else None,
       'source_url':f'https://oeffentlichevergabe.de/ui/de/notices/{identifier}',
       'verification_status':'德国官方 Open Data；技术规格待复核'})
    if not item:return None
    money=project.find('a:RequestedTenderTotal/b:EstimatedOverallContractAmount',NS) if project is not None else None
    item.update(source='BKMS',notice_id=identifier,notice_version=meta.get('noticeVersion','1'),
       procedure_id=meta.get('procedureIdentifier') or val(root,'b:ContractFolderID') or None,
       procurement_reference=val(project,'b:ID') or None,
       collected_at=now.isoformat(),deadlines=sorted(set(deadlines)),
       publication_timestamp=meta.get('publicationDate') or None,
       official_links=list(dict.fromkeys(urls)),notice_stage=stage,
       procedure_type=procedure,form_type=form,deadline_source=f'https://oeffentlichevergabe.de/ui/de/notices/{identifier}',
       budget_amount=money.text if money is not None else None,
       budget_currency=money.get('currencyID') if money is not None else None,
       budget_basis='公告程序级预估金额；非单台设备预算')
    item['priority'],item['matched_products'],item['match_reasons']=match(item)
    item['match_score']={'P1':85,'P2':55,'P3':20}[item['priority']]
    # Full purpose text and lot names can reveal the educational final user.
    context=' '.join(val(e,'b:Name')+' '+val(e,'b:Description') for e in root.findall('.//a:ProcurementProject',NS))
    item.update(classify({**item,'description':context}))
    return item

def collect(now):
    local=now.astimezone(ZoneInfo('Europe/Berlin')).date()
    first=local.replace(day=1);previous=first-dt.timedelta(days=1)
    months=[previous.strftime('%Y-%m'),local.strftime('%Y-%m')]
    items=[];scanned=0
    for month in months:
        with fetch_archive(month,'csv.zip') as tablezip:
            notices=csv_rows(tablezip,'notice.csv');purposes=csv_rows(tablezip,'purpose.csv')
            candidates={(p['noticeIdentifier'],p['noticeVersion']) for p in purposes if relevant(p.get('title',''),p.get('description',''))}
        scanned+=len(notices)
        selected=[n for n in notices if (n['noticeIdentifier'],n['noticeVersion']) in candidates]
        with fetch_archive(month,'eforms.zip') as xmlzip:
            filenames=set(xmlzip.namelist())
            for n in selected:
                filename=f"{n['noticeIdentifier']}-{n['noticeVersion']}.xml"
                if filename not in filenames:raise RuntimeError('BKMS XML missing for selected notice '+filename)
                if xmlzip.getinfo(filename).file_size>20_000_000:raise RuntimeError('BKMS XML exceeds size limit')
                item=parse_xml(xmlzip.read(filename),n,now)
                if item:items.append(item)
    return items,{'endpoint':API,'months':months,'scanned_notices':scanned,'accepted_notices':len(items),'license':'CC0','export_available_through':'previous day Europe/Berlin'}
