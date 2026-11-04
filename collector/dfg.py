"""Public DFG procurement list: live deadline verification, no login required."""
import datetime as dt
from html.parser import HTMLParser
import urllib.request
from zoneinfo import ZoneInfo
from .core import normalize
from .institutions import classify
from .ted import match
from .bkms import relevant
URL='https://bieterportal.dfg.de/?l=1'

class Rows(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.row=None;self.col=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='tr' and a.get('data-tendersid'):self.row={};self.col=None
        if tag=='td' and self.row is not None:
            self.col=a.get('data-column-index')
            if self.col:self.row[self.col]=a.get('data-sort-value','')
    def handle_endtag(self,tag):
        if tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None;self.col=None
        if tag=='td':self.col=None

def parse(html,now):
    p=Rows();p.feed(html)
    if not p.rows:raise RuntimeError('DFG table structure changed or no tender rows')
    items=[]
    for r in p.rows:
        ref,title,buyer=r.get('1',''),r.get('2',''),r.get('6','')
        if not relevant(title,''):continue
        deadline=dt.datetime.fromisoformat(r['4']).replace(tzinfo=ZoneInfo('Europe/Berlin')).isoformat()
        item=normalize({'notice_id':'DFG:'+ref,'title':title,'buyer':buyer,'description':title,
            'country':'DE','deadline':deadline,'source_url':URL,
            'verification_status':'DFG 官方门户实时截止日期；技术规格待复核'})
        if not item:continue
        item.update(source='DFG',procurement_reference=ref,notice_stage='notice',collected_at=now.isoformat(),publication_date=None,deadline_source=URL)
        item['priority'],item['matched_products'],item['match_reasons']=match(item)
        item['match_score']={'P1':85,'P2':55,'P3':20}[item['priority']]
        item.update(classify(item));items.append(item)
    return items,{'endpoint':URL,'scanned_rows':len(p.rows),'accepted_notices':len(items),'note':'当前公开列表；发布时间如未公开则留空'}

def collect(now):
    with urllib.request.urlopen(urllib.request.Request(URL,headers={'User-Agent':'DACH-Robotics-Dashboard/3.0'}),timeout=40) as r:html=r.read(5_000_000).decode('utf-8')
    return parse(html,now)
