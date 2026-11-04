import copy
import datetime as dt
import pathlib
import unittest
from collector.bkms import parse_xml,relevant
from collector.dfg import parse as parse_dfg
from collector.opportunities import coalesce,phase
from collector.institutions import classify
NOW=dt.datetime(2026,11,4,20,tzinfo=dt.timezone.utc)
FIX=pathlib.Path(__file__).parent/'fixtures'
def sample(name):
 meta={'bam':{'noticeIdentifier':'d5ac23cd-3a48-4fa8-87eb-1b17e694c480','noticeVersion':'1','procedureIdentifier':'BAM-PROC','publicationDate':'2026-10-15T08:06:04Z'},'magdeburg-update':{'noticeIdentifier':'e6c7549e-f612-4265-9731-8b04db662c65','noticeVersion':'2','procedureIdentifier':'MAG-PROC','publicationDate':'2026-11-03T09:35:44Z'},'wildau-plan':{'noticeIdentifier':'25946758','noticeVersion':'1','publicationDate':'2026-10-20T07:00:00Z'}}[name]
 return parse_xml((FIX/(name+'.xml')).read_bytes(),meta,NOW)
class CoverageTests(unittest.TestCase):
 def test_bam_tender_not_question_deadline(self):
  x=sample('bam');self.assertEqual(x['deadline'],'2026-11-11T11:00:00+01:00');self.assertEqual(x['institution_type'],'research');self.assertIsNone(x['budget_amount'])
 def test_latest_magdeburg_version(self):
  new=sample('magdeburg-update');old=copy.deepcopy(new);old.update(id='old',publication_timestamp='2026-10-07T00:00:00Z',deadline='2026-11-04T10:00:00+01:00',notice_version='1')
  rows=coalesce([old,new],NOW);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['phase'],'active');self.assertEqual(rows[0]['deadline'],'2026-11-06T10:00:00+01:00')
 def test_plan_not_open_tender(self):
  x=sample('wildau-plan');self.assertEqual(x['notice_stage'],'planned');self.assertIsNone(x['deadline']);self.assertEqual(phase(x,NOW)[0],'planned')
 def test_missing_deadline_not_invented(self):
  x=sample('bam');x['deadline']=None;self.assertEqual(phase(x,NOW)[0],'unknown')
 def test_results_not_open_even_with_future_deadline(self):
  x=sample('bam');x['notice_stage']='result';self.assertEqual(phase(x,NOW)[0],'history')
 def test_dfg_live_extension(self):
  live,_=parse_dfg((FIX/'dfg-list.html').read_text(),NOW);self.assertEqual(len(live),1);portal=live[0];self.assertEqual(portal['deadline'],'2026-11-13T12:00:00+01:00');self.assertIsNone(portal['publication_date'])
  old=copy.deepcopy(portal);old.update(id='BKMS:old',source='BKMS',deadline='2026-11-02T12:00:00+01:00',publication_date='2026-10-03')
  rows=coalesce([old,portal],NOW,live);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['phase'],'active');self.assertIn('2026-11-02',rows[0]['deadline_note'])
 def test_exact_cross_source_procedure(self):
  a=sample('bam');b=copy.deepcopy(a);b.update(id='TED:other',source='TED');self.assertEqual(len(coalesce([a,b],NOW)),1)
 def test_subreport_alias_dedup(self):
  a=sample('bam');a.update(procedure_id=None,procurement_reference=None,official_links=['https://www.subreport-elvis.de/download/bund/E53258633/123/bekanntmachung.pdf']);b=copy.deepcopy(a);b.update(id='BKMS:second',notice_id='second',official_links=['https://www.subreport-elvis.de/download/bund/E53258633/456/bekanntmachung.pdf']);self.assertEqual(len(coalesce([a,b],NOW)),1)
  b['official_links']=['https://www.subreport-elvis.de/download/bund/E35321422/123/bekanntmachung.pdf'];self.assertEqual(len(coalesce([a,b],NOW)),2)
 def test_chamber_registry_not_final_user(self):
  self.assertFalse(classify({'buyer':'Stadt Beispiel','description':'Elektrotechnik. Nachweis der Eintragung bei IHK oder HWK.'})['education_research'])
 def test_no_rpa_or_building_noise(self):
  self.assertFalse(relevant('Robotic Process Automation','RPA'));self.assertFalse(relevant('Gebäudeautomation','automation'));self.assertTrue(relevant('Flexible Automation','Handling- und Palettiersystem'))
if __name__=='__main__':unittest.main()
