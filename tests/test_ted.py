import datetime as dt
import unittest
from unittest.mock import patch
from collector.ted import parse,collect,query
from collector.core import merge
NOW=dt.datetime(2026,11,4,12,tzinfo=dt.timezone.utc)
def notice(**kw):
 n={'publication-number':'test-fixture','notice-title':{'deu':'Kollaborativer Roboterarm'},'buyer-name':{'deu':['Test buyer']},'buyer-country':['DEU'],'form-type':'competition','deadline-receipt-tender-date-lot':['2026-11-05+01:00'],'deadline-receipt-tender-time-lot':['10:00:00+01:00']};n.update(kw);return n
class TedTests(unittest.TestCase):
 def test_mapping(self):
  x=parse(notice(),NOW);self.assertEqual(x['priority'],'P1');self.assertIsNone(x['budget_amount']);self.assertEqual(x['deadline'],'2026-11-05T10:00:00+01:00')
 def test_expired(self):self.assertIsNone(parse(notice(**{'deadline-receipt-tender-date-lot':['2026-11-03+01:00']}),NOW))
 def test_award(self):self.assertIsNone(parse(notice(**{'form-type':'result'}),NOW))
 def test_country(self):self.assertIsNone(parse(notice(**{'buyer-country':['FRA']}),NOW))
 def test_software(self):self.assertIsNone(parse(notice(**{'notice-title':{'deu':'Automation Software Lizenz'}}),NOW))
 def test_history(self):
  x=parse(notice(),NOW);x['first_seen']='2020-01-01';x['status']='expired'
  y=merge([x],[parse(notice(),NOW)])[0];self.assertEqual(y['first_seen'],'2020-01-01');self.assertEqual(y['status'],'投标中')
 @patch('collector.ted.request')
 def test_pagination(self,r):
  r.side_effect=[{'notices':[notice()], 'totalNoticeCount':2},{'notices':[notice(**{'publication-number':'second'})], 'totalNoticeCount':2}]
  items,meta=collect(NOW);self.assertEqual(len(items),2);self.assertEqual(r.call_count,2)
 @patch('collector.ted.request')
 def test_incomplete_fails(self,r):
  r.return_value={'notices':[],'totalNoticeCount':1}
  with self.assertRaises(RuntimeError):collect(NOW)
