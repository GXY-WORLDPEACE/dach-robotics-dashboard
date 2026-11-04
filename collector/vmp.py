"""Official regional cosinex/VMP ZIP exports, discovered in GovData."""
import datetime as dt
import io
from pathlib import Path
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from urllib.parse import urlsplit
from .bkms import parse_xml,val,NS
from .public_sources import relevant,record
from zoneinfo import ZoneInfo

def collect_source(source,now):
    source_id=source['id'];url=source['endpoint']
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Robotics-Education-Procurement-Monitor/4.0'}),timeout=60) as r:
        raw=r.read(150_000_001)
    if len(raw)>150_000_000:raise RuntimeError('Regional ZIP exceeds limit')
    items=[];scanned=0;unsupported=0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for filename in archive.namelist():
            if not filename.endswith('.xml'):continue
            if archive.getinfo(filename).file_size>20_000_000:raise RuntimeError('Regional XML exceeds limit')
            root=ET.fromstring(archive.read(filename))
            if root.tag=='NOTICES':
                continue
            scanned+=1
            if root.tag=='NOTICE_NAT':
                x=parse_legacy(root,source,Path(filename).stem,now)
                if x:items.append(x)
                continue
            if not root.tag.endswith(('ContractNotice','ContractAwardNotice','PriorInformationNotice')):
                unsupported+=1;continue
            project=root.find('a:ProcurementProject',NS)
            if not relevant(val(project,'b:Name'),val(project,'b:Description')):continue
            uuid=val(root,'b:ID')
            if not uuid:raise RuntimeError('Regional notice identifier missing')
            pub=val(root,'b:IssueDate')[:10] or val(root,'b:RequestedPublicationDate')[:10]
            meta={'noticeIdentifier':uuid,'noticeVersion':val(root,'b:VersionID') or '1','procedureIdentifier':val(root,'b:ContractFolderID'),'publicationDate':pub}
            x=parse_xml(ET.tostring(root),meta,now)
            if not x:continue
            portal_id=Path(filename).stem
            base=url.split('/opendata',1)[0]
            x.update(id=source_id+':'+uuid+':'+meta['noticeVersion'],source=source_id,notice_uuid=uuid,
               source_url=base+'/notice/'+portal_id,deadline_source=base+'/notice/'+portal_id,
               portal_notice_id=portal_id,source_label=source['name'])
            items.append(x)
    if scanned and unsupported==scanned:raise RuntimeError('Regional XML schema unsupported')
    return items,{'endpoint':url,'scanned_notices':scanned,'accepted_notices':len(items),'unsupported_schema_notices':unsupported,'scope':source['scope'],'documentation':source['documentation']}


def parse_legacy(root,source,portal_id,now):
    def text(path):
        e=root.find(path)
        return ' '.join(' '.join(e.itertext()).split()) if e is not None else ''
    title=text('OBJECT_CONTRACT/TITLE');desc=text('OBJECT_CONTRACT/SHORT_DESC')
    if not relevant(title,desc):return None
    buyer=text('CONTRACTING_BODY/ADDRESS_CONTRACTING_BODY/OFFICIALNAME')
    procedure=text('PROCEDURE/PROCEDURE_TYPE_LABEL').lower()
    stage='result' if any(t in procedure for t in ['ex post','vergeben','vergabebekanntmachung']) else 'planned' if 'ex ante' in procedure or 'vorinformation' in procedure else 'notice'
    end=None;receipt=root.find('PROCEDURE/RECEIPT_TENDER')
    if receipt is not None:
        try:
            day=dt.date(int(receipt.findtext('YEAR')),int(receipt.findtext('MONTH')),int(receipt.findtext('DAY')))
            hour=receipt.findtext('HOUR');minute=receipt.findtext('MIN')
            end=dt.datetime.combine(day,dt.time(int(hour),int(minute)),ZoneInfo('Europe/Berlin')).isoformat() if hour and minute else day.isoformat()
        except (TypeError,ValueError):pass
    base=source['endpoint'].split('/opendata',1)[0]
    x=record(source['id'],portal_id,title,buyer,'DE',desc,None,base+'/notice/'+portal_id,now,end=end,stage=stage,reference=text('OBJECT_CONTRACT/REFERENCE_NUMBER') or None)
    if x:
        x.update(portal_notice_id=portal_id,source_label=source['name'],procedure_type=procedure,publication_date=None)
        final_user=text('OBJECT_CONTRACT/PLACE_OF_FULLFILMENT/MAINPLACE/OFFICIALNAME')
        if final_user and not x['education_research']:
            from .institutions import classify
            x.update(classify({**x,'description':desc+' '+final_user}))
    return x
