import unittest
from collector.core import score,normalize,merge
class CoreTests(unittest.TestCase):
 def test_score(self):
  n,p,m=score('Robotik Cobot Automatisierung','Roboterarm für Ausbildung');self.assertGreater(n,0);self.assertTrue(m)
 def test_invalid(self):self.assertIsNone(normalize({'title':'x','source_url':'javascript:alert(1)'}))
 def test_merge(self):
  a=normalize({'title':'Cobot robot','source_url':'https://example.org/notice'});self.assertEqual(len(merge([a],[a])),1)
if __name__=='__main__':unittest.main()
