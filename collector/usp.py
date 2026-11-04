"""Austrian official USP public list and server-rendered notice details."""
import datetime as dt
from html.parser import HTMLParser
import re
import time
import urllib.request
from urllib.parse import urlencode
from .public_sources import request,record,relevant,deadline
BASE='https://ausschreibungen.usp.gv.at/at.gv.bmdw.eproc-p/public/'
TERMS=['robot','cobot','manipulator','automatisierung','automation']
class Fields(HTMLParser):
    def __init__(self):super().__init__();self.mode=None;self.buf=[];self.label='';self.fields={}
    def handle_starttag(self,tag,attrs):
        if tag in ('dt','dd'):self.mode=tag;self.buf=[]
    def handle_data(self,text):
        if self.mode:self.buf.append(text)
    def handle_endtag(self,tag):
        if tag==self.mode:
            text=' '.join(' '.join(self.buf).split()).strip().rstrip(':')
            if tag=='dt':self.label=text
            elif self.label:self.fields.setdefault(self.label,[]).append(text)
            self.mode=None;self.buf=[]

def parse(row,html,now):
    f=Fields();f.feed(html);fields=f.fields
    def first(k):return next((v for v in fields.get(k,[]) if v),'')
    title=first('Titel') or row[0];desc=first('Beschreibung')
    if not relevant(title,desc):return None
    if 'berufsausbildung nach bag' in title.lower():return None
    form=first('Formulartyp');kind=first('Art der Bekanntmachung')
    s=(form+' '+kind).lower()
    stage='result' if any(t in s for t in ['ergebnis','zuschlagsbekannt','auftragsvergabe','vergebene']) else 'planned' if any(t in s for t in ['vorankündigung','ex-ante','ex ante','markterkundung']) else 'notice'
    candidates=fields.get('Frist für den Eingang der Angebote',[])+fields.get('Frist für den Eingang der Teilnahmeanträge',[])
    # USP list provides date-only deadlines. Keep date-only if no full official
    # timestamp is available instead of inventing a submission time.
    end=next((deadline(v) for v in candidates if deadline(v)),None) or row[6] or row[7] or row[3]
    url=BASE+('notice' if row[5] else 'tender')+'-detail?'+urlencode({'object':row[4]})
    x=record('USP',row[4],title,row[1],'AT',desc,row[2],url,now,end=end,stage=stage,
       procedure_id=first('Kennung des Verfahrens') or None,reference=first('Interne Kennung') or None)
    if x:
        x['publication_type']=form or kind
        x['notice_version']=first('Version der Bekanntmachung') or '1'
        urls=[]
        for k,values in fields.items():
            if 'unterlagen' in k.lower() or 'internetadresse' in k.lower():
                urls.extend(v for v in values if v.startswith('https://'))
        x['official_links']=list(dict.fromkeys(urls))[:5]
    return x

def collect(now):
    since=(now.date()-dt.timedelta(days=90)).isoformat();rows={};scanned=0
    for term in TERMS:
        for start in range(0,20000,100):
            params={'q':term,'start':start,'length':100,'orderColumn':2,'orderDir':'desc','draw':1}
            d=request(BASE+'api/tenderlist?'+urlencode(params))
            page=d.get('data')
            if not isinstance(page,list):raise RuntimeError('USP public list schema changed')
            for r in page:
                if len(r)<8:raise RuntimeError('USP columns changed')
                if not r[2]:continue
                if r[2]>=since:
                    scanned+=1
                    if relevant(r[0]):rows[r[4]]=r
            if not page or start+len(page)>=d.get('recordsFiltered',0) or min(r[2] or '0000' for r in page)<since:break
            time.sleep(.6)
        else:raise RuntimeError('USP pagination limit exceeded')
        time.sleep(1)
    items=[];detail_errors=[]
    for r in rows.values():
        url=BASE+('notice' if r[5] else 'tender')+'-detail?'+urlencode({'object':r[4]})
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Robotics-Education-Procurement-Monitor/4.0'}),timeout=25) as response:html=response.read(5_000_000).decode('utf-8')
            x=parse(r,html,now)
        except Exception as e:
            detail_errors.append({'notice_id':r[4],'error':type(e).__name__})
            x=parse(r,'',now)
            if x:x.update(detail_unavailable=True,verification_status='USP 官方列表；详情访问失败，内容待核实')
        if x:items.append(x)
        print(f'USP: {len(items)}/{len(rows)} detail pages',flush=True) if len(items)%10==0 else None
        time.sleep(.6)
    return items,{'endpoint':BASE+'tenderlist','search_terms':TERMS,'window_start':since,'scanned_hits':scanned,'unique_detail_pages':len(rows),'accepted_notices':len(items),'detail_errors':detail_errors,'status':'partial' if detail_errors else 'connected','scope':'USP 公开汇总最近 90 天；以各发布单位申报内容为准，非未公开采购'}
