import datetime as dt
import unittest
import xml.etree.ElementTree as ET
from collector.ted import parse as ted_parse,query
from collector.tenderned import parse as nl_parse
from collector.simap import parse as ch_parse
from collector.usp import parse as at_parse
from collector.vmp import parse_legacy
from collector.public_sources import multilingual,deadline,relevant
from collector.institutions import classify
from collector.opportunities import phase,coalesce
from collector.coverage import report
from test_ted import notice,NOW
class FiveCountryTests(unittest.TestCase):
 def test_ted_countries(self):
  for iso,code in [('DEU','DE'),('AUT','AT'),('CHE','CH'),('NLD','NL'),('BEL','BE')]:
   with self.subTest(code=code):self.assertEqual(ted_parse(notice(**{'buyer-country':[iso]}),NOW)['country'],code)
  self.assertIn('CHE NLD BEL',query(NOW.date()))
 def test_dutch_award_is_not_active(self):
  n={'publicatieId':'fixture','aanbestedingNaam':'Robotarm','opdrachtgeverNaam':'Universiteit Gent','typePublicatie':{'code':'AGO'},'sluitingsDatum':'2027-01-01T12:00:00','publicatieDatum':'2026-11-01'}
  x=nl_parse(n,NOW);self.assertEqual(phase(x,NOW)[0],'history');self.assertIsNone(x['budget_amount'])
 def test_dutch_notice_datetime(self):
  n={'publicatieId':'fixture','aanbestedingNaam':'Onderwijsrobot','opdrachtgeverNaam':'Hogeschool','typePublicatie':{'code':'AAO'},'sluitingsDatum':'2026-11-06T10:00:00','publicatieDatum':'2026-11-01'}
  x=nl_parse(n,NOW);self.assertEqual(x['deadline'],'2026-11-06T10:00:00+01:00');self.assertTrue(x['education_research'])
 def test_swiss_deadline_not_questions_or_award_value(self):
  p={'id':'project','publicationId':'pub','publicationDate':'2026-11-01','title':{'de':'Roboterarm'},'procOfficeName':{'de':'ETH Zürich'}}
  d={'type':'tender','procurement':{'orderDescription':{'de':'Robotik für Forschung'}},'dates':{'offerDeadline':'2026-11-12T12:00:00+01:00','qnas':[{'date':'2026-11-05'}]},'decision':{'totalPrice':250000}}
  x=ch_parse(p,d,NOW);self.assertEqual(x['deadline'],'2026-11-12T12:00:00+01:00');self.assertEqual(x['country'],'CH');self.assertIsNone(x['budget_amount'])
  d['type']='direct_award';self.assertEqual(phase(ch_parse(p,d,NOW),NOW)[0],'history')
 def test_date_with_offset_is_still_date_only(self):self.assertEqual(deadline('2026-11-16+01:00'),'2026-11-16')
 def test_staffing_not_robot_hardware(self):self.assertFalse(relevant('Technisch wetenschappelijk personeel','robotica'))
 def test_multilingual_skips_nulls(self):self.assertEqual(multilingual({'de':None,'fr':'Robot industriel'}),'Robot industriel')
 def test_usp_date_only_is_preserved(self):
  row=['Cobot','TU Wien','2026-11-01','2026-11-12','fixture',True,'2026-11-12',None]
  html='<dl><dt>Titel:</dt><dd>Cobot</dd><dt>Beschreibung:</dt><dd>Robotik Lehre</dd><dt>Formulartyp:</dt><dd>Wettbewerb</dd><dt>Interne Kennung:</dt><dd>REF-1</dd></dl>'
  x=at_parse(row,html,NOW);self.assertEqual(x['country'],'AT');self.assertEqual(x['deadline'],'2026-11-12');self.assertEqual(x['procurement_reference'],'REF-1')
 def test_legacy_expost_does_not_use_delivery_date(self):
  root=ET.fromstring('<NOTICE_NAT><CONTRACTING_BODY><ADDRESS_CONTRACTING_BODY><OFFICIALNAME>Hochschule</OFFICIALNAME></ADDRESS_CONTRACTING_BODY></CONTRACTING_BODY><OBJECT_CONTRACT><TITLE>Roboterarm</TITLE><TIME_FRAME><DATE>2027-01-01</DATE></TIME_FRAME></OBJECT_CONTRACT><PROCEDURE><PROCEDURE_TYPE_LABEL>Ex post Veröffentlichung</PROCEDURE_TYPE_LABEL></PROCEDURE></NOTICE_NAT>')
  x=parse_legacy(root,{'id':'DE_NRW','name':'NRW','endpoint':'https://www.evergabe.nrw.de/VMPSatellite/opendata?id=fixture'},'CXFIXTURE',NOW)
  self.assertEqual(phase(x,NOW)[0],'history');self.assertIsNone(x['deadline']);self.assertIsNone(x['publication_date'])
 def test_target_institutions_across_countries(self):
  for buyer in ['KU Leuven','Universiteit Twente','Hogeschool Rotterdam','ZHAW','EPFL','Université de Liège']:
   with self.subTest(buyer=buyer):self.assertEqual(classify({'buyer':buyer})['institution_type'],'university')
 def test_coverage_ledger_is_not_completeness_claim(self):
  d=report({'sources':{'TED':{'status':'connected'}}},[],NOW.isoformat());self.assertEqual(len(d['jurisdictions']),66);self.assertFalse(d['coverage_complete']);self.assertEqual(len(d['countries']),5)
 def test_exact_tenderned_cross_source_link(self):
  x=nl_parse({'publicatieId':'123','aanbestedingNaam':'Robotarm','typePublicatie':{'code':'AAO'}},NOW)
  y=dict(x,id='TED:fixture',source='TED',notice_id='fixture',official_links=['https://www.tenderned.nl/aankondigingen/overzicht/123'])
  self.assertEqual(len(coalesce([x,y],NOW)),1)
if __name__=='__main__':unittest.main()
