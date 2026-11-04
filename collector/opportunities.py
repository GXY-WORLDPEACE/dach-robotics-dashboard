"""Cross-source identity and explicit procurement phases."""
import copy
import datetime as dt
import re
import unicodedata
from zoneinfo import ZoneInfo

def normalized(s):return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',str(s or '')).casefold())

def identity_keys(x):
    keys=[];country=x.get('country') or 'DE'
    if x.get('procedure_id'):keys.append(('procedure',country,x['procedure_id']))
    if x.get('procurement_reference') and x.get('buyer') and not x.get('lot_key'):
        keys.append(('buyer-reference',country,normalized(x['buyer']),normalized(x['procurement_reference'])))
    if x.get('source')=='BKMS':keys.append(('notice-uuid',x.get('notice_id')))
    if x.get('notice_uuid'):keys.append(('notice-uuid',x['notice_uuid']))
    if x.get('source')=='TENDERNED':keys.append(('tenderned-publication',str(x['notice_id'])))
    if x.get('source')=='SIMAP' and x.get('procedure_id') and not x.get('lot_key'):keys.append(('simap-project',x['procedure_id'].removeprefix('SIMAP:')))
    if x.get('portal_notice_id'):keys.append(('vmp-notice',x['portal_notice_id']))
    for url in x.get('official_links',[]):
        nl=re.search(r'tenderned\.nl/(?:[^?]*/)?aankondigingen/(?:overzicht/)?(\d+)',url)
        if nl:keys.append(('tenderned-publication',nl[1]))
        ch=re.search(r'simap\.ch/(?:[a-z]{2}/)?project-detail/([a-f0-9-]+)',url)
        if ch:keys.append(('simap-project',ch[1]))
        portal=re.search(r'/notice/(CX[A-Z0-9]+)',url)
        if portal:keys.append(('vmp-notice',portal[1]))
        m=re.search(r'https://(?:www\.)?subreport(?:-elvis)?\.de/.*?\b(E\d{8})\b',url)
        if m:keys.append(('subreport',m[1],normalized(x.get('buyer'))))
    return keys or [('id',x['id'])]

def as_time(v):
    if not v:return None
    try:
        t=dt.datetime.fromisoformat(v)
        if len(v)==10:t=dt.datetime.combine(t.date(),dt.time.max)
        return t if t.tzinfo else t.replace(tzinfo=ZoneInfo('Europe/Berlin'))
    except ValueError:return None

def phase(x,now):
    if x.get('notice_stage')=='result':return 'history','已公布结果／授标'
    if x.get('notice_stage')=='planned':return 'planned','采购预告／意向；参与期限需核实'
    deadline=as_time(x.get('deadline'))
    if deadline and deadline<=now:return 'history','截止日期已过'
    if x.get('source_unavailable'):return 'unknown','本次未在原查询中找到，状态待核实'
    if deadline:return 'active','投标中'
    return 'unknown','未公开可验证截止日期，不能确认仍可投标'

def publication_order(x):
    t=as_time(x.get('publication_timestamp') or x.get('publication_date') or x.get('source_snapshot_at'))
    # A date-only TED publication represents the start of the day here.
    if t and len(x.get('publication_date') or '')==10 and not x.get('publication_timestamp'):t=t.replace(hour=0,minute=0,second=0,microsecond=0)
    return (t.timestamp() if t else 0,int(x.get('notice_version') or 0),x.get('source')=='BKMS')

def coalesce(items,now,dfg_live=None):
    parent=list(range(len(items)));keys={}
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i,x in enumerate(items):
        for key in identity_keys(x):
            if key in keys:parent[find(i)]=find(keys[key])
            else:keys[key]=i
    groups={}
    for i,x in enumerate(items):groups.setdefault(find(i),[]).append(x)
    out=[];live={x['id'] for x in (dfg_live or [])}
    for group in groups.values():
        base=copy.deepcopy(max(group,key=publication_order))
        # All source publication IDs remain in history; dashboard groups exact IDs,
        # procedure UUIDs, buyer+reference or a specific official platform identifier.
        base['related_notice_ids']=sorted({x['id'] for x in group})
        base['source_links']=list(dict.fromkeys(x['source_url'] for x in group))
        portal=next((x for x in group if x.get('source')=='DFG' and x['id'] in live),None)
        if portal and base.get('notice_stage')!='result':
            before=base.get('deadline')
            base['deadline']=portal['deadline'];base['deadlines']=[portal['deadline']]
            base['deadline_source']=portal['source_url'];base['source_unavailable']=False
            base['deadline_note']='DFG 官方当前列表核验截止日期'+(f'；原公告字段：{before}' if before and before!=portal['deadline'] else '')
        base['phase'],base['status']=phase(base,now)
        out.append(base)
    return sorted(out,key=lambda x:(not x.get('education_research'),x.get('lead_priority','C'),x.get('priority','P3'),x.get('deadline') or '9999',x['title']))
