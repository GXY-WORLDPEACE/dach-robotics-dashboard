"""RSS/Atom ingestion for user-configured official feeds. Only items matching robotics keywords are kept."""
import json,datetime,sys,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
from .core import ROOT,normalize,merge,save,score

def fetch_feed(feed):
    req=urllib.request.Request(feed['url'],headers={'User-Agent':'DACH-Robotics-Tender-Monitor/1.0 (public procurement research)'})
    with urllib.request.urlopen(req,timeout=25) as resp: data=resp.read(3_000_000)
    root=ET.fromstring(data)
    def value(node,name):
        for c in node.iter():
            if c.tag.rsplit('}',1)[-1]==name and c.text:return c.text.strip()
        return ''
    nodes=[x for x in root.iter() if x.tag.rsplit('}',1)[-1] in ('item','entry')]
    out=[]
    for n in nodes:
        title=value(n,'title');desc=value(n,'description') or value(n,'summary') or value(n,'content')
        if score(title,desc)[0]<15:continue
        link=value(n,'link')
        if not link:
            for c in n.iter():
                if c.tag.rsplit('}',1)[-1]=='link' and c.get('href'):link=c.get('href');break
        obj=normalize({'title':title,'description':desc,'source_url':link,'notice_id':value(n,'guid') or value(n,'id') or None,'country':feed.get('country'),'publication_date':value(n,'pubDate') or value(n,'published') or None,'verification_status':'公告摘要待核实','status':'截止日期待核实'})
        if obj:out.append(obj)
    return out

def main():
    conf=json.loads((ROOT/'collector'/'sources.json').read_text(encoding='utf-8'))
    target=ROOT/'data'/'tenders.json'; old=json.loads(target.read_text(encoding='utf-8')).get('tenders',[]) if target.exists() else []
    fresh=[];errors=[]
    for feed in conf.get('rss_feeds',[]):
        if not feed.get('enabled'):continue
        try:fresh+=fetch_feed(feed)
        except Exception as e:errors.append(f"{feed.get('name')}: {type(e).__name__}: {e}")
    save(merge(old,fresh))
    (ROOT/'data'/'scan_status.json').write_text(json.dumps({'scanned_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new_items_fetched':len(fresh),'feeds_enabled':sum(bool(x.get('enabled')) for x in conf.get('rss_feeds',[])),'errors':errors,'note':'Only configured RSS/Atom feeds are collected. No full DACH coverage is implied.'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Fetched {len(fresh)} candidates; errors: {len(errors)}')

if __name__=='__main__':main()
