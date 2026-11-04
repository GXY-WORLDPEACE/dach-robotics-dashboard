"""Visible coverage ledger. A regional inventory is not a completeness claim."""
import json
from collections import Counter
from .core import ROOT
COUNTRY_NAMES={'DE':'德国','AT':'奥地利','CH':'瑞士','NL':'荷兰','BE':'比利时'}
REGIONS={
'DE':['Baden-Württemberg','Bayern','Berlin','Brandenburg','Bremen','Hamburg','Hessen','Mecklenburg-Vorpommern','Niedersachsen','Nordrhein-Westfalen','Rheinland-Pfalz','Saarland','Sachsen','Sachsen-Anhalt','Schleswig-Holstein','Thüringen'],
'AT':['Burgenland','Kärnten','Niederösterreich','Oberösterreich','Salzburg','Steiermark','Tirol','Vorarlberg','Wien'],
'CH':['Zürich','Bern','Luzern','Uri','Schwyz','Obwalden','Nidwalden','Glarus','Zug','Fribourg','Solothurn','Basel-Stadt','Basel-Landschaft','Schaffhausen','Appenzell Ausserrhoden','Appenzell Innerrhoden','St. Gallen','Graubünden','Aargau','Thurgau','Ticino','Vaud','Valais','Neuchâtel','Genève','Jura'],
'NL':['Drenthe','Flevoland','Friesland','Gelderland','Groningen','Limburg','Noord-Brabant','Noord-Holland','Overijssel','Utrecht','Zeeland','Zuid-Holland'],
'BE':['Vlaanderen','Wallonie','Bruxelles-Capitale']}

def registry():return json.loads((ROOT/'collector'/'source_registry.json').read_text())

def report(status,board,now):
    reg=registry();sources=[]
    for s in reg['sources']:
        runtime=status['sources'].get(s['id'],{})
        sources.append({**s,**runtime,'status':runtime.get('status') or s.get('status') or ('not_verified' if s.get('enabled') else 'not_connected')})
    countries=[]
    for code,name in COUNTRY_NAMES.items():
        ss=[s for s in sources if s.get('country')==code or code in s.get('country_codes',[])]
        active=[x for x in board if x.get('country')==code and x.get('phase')=='active']
        countries.append({'code':code,'name':name,'active_count':len(active),'education_active_count':sum(bool(x.get('education_research')) for x in active),'connected_sources':[s['id'] for s in ss if s['status'] in ('connected','partial')],
           'gaps':['未保证全部地方平台、全部历史或未公开采购覆盖']+(['BOSA 本地接口暂未接入；当前仅 TED'] if code=='BE' else [])})
    regions=[]
    for code,names in REGIONS.items():
        for name in names:
            regions.append({'country':code,'region':name,'coverage':'national_aggregation_partial',
                'direct_local_status':'partial_NRW_platforms' if code=='DE' and name=='Nordrhein-Westfalen' else 'not_individually_verified',
                'note':'仅纳入已接入国家级／区域平台上报的公开公告；不代表该地区全部地方平台已接入'})
    return {'checked_at':now,'coverage_complete':False,'coverage_claim':reg['coverage_claim'],'countries':countries,'sources':sources,'jurisdictions':regions,'jurisdiction_note':'66 个州／省／大区是检查清单，不是已接入平台数量；每个地区仍可能存在独立城市、学校和机构平台。','refresh':'每日 Europe/Berlin 08:00 自动重采集并记录来源健康；新增接口须验证后启用。'}
