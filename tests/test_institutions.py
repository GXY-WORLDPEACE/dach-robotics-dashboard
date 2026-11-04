import unittest
from collector.institutions import classify
from collector.ted import parse
from test_ted import notice,NOW

class InstitutionTests(unittest.TestCase):
 def test_target_types(self):
  for buyer,kind in [('Technische Universität München','university'),('FH Aachen','university'),('Fraunhofer IPA','research'),('Helmholtz-Zentrum Hereon','research'),('Staatliche Berufsschule München','vocational'),('Berufskolleg Köln','vocational'),('HTL Mödling','vocational'),('Berufsbildungszentrum Augsburg','training'),('Unternehmens-Ausbildungszentrum','training'),('Handwerkskammer München','chamber'),('IHK Bildungszentrum','chamber')]:
   with self.subTest(buyer=buyer):self.assertEqual(classify({'buyer':buyer})['institution_type'],kind)
 def test_city_proxy(self):
  x=classify({'buyer':'Landratsamt München','title':'Roboter für die Berufsschule','description':''})
  self.assertTrue(x['procurement_for_education']);self.assertTrue(x['education_research']);self.assertEqual(x['lead_priority'],'B');self.assertIn('待核实',x['institution_relation'])
 def test_body_proxy(self):
  x=classify({'buyer':'Stadt Essen','title':'Roboterausstattung','description':'Lieferung für das Berufskolleg Essen'})
  self.assertEqual(x['institution_type'],'vocational');self.assertTrue(x['procurement_for_education'])
 def test_no_invented_school(self):
  x=classify({'buyer':'Landratsamt München','title':'Roboter'})
  self.assertFalse(x['education_research']);self.assertFalse(x['procurement_for_education'])
 def test_hospital_not_university(self):
  self.assertFalse(classify({'buyer':'Universitätsklinikum Freiburg','description':'Wäscheautomation'})['education_research'])
 def test_training_not_just_instruction(self):
  self.assertFalse(classify({'buyer':'Industrie GmbH','description':'Roboter mit Einweisung und Schulung'})['education_research'])
 def test_brand_restriction_independent_of_institution(self):
  x=parse(notice(**{'buyer-name':{'deu':['Technische Universität München']},'notice-title':{'deu':'Roboterplattform Boston Dynamics Spot'}}),NOW)
  self.assertEqual(x['lead_priority'],'A');self.assertEqual(x['priority'],'P3')
 def test_vocational_robot_not_excluded(self):
  x=parse(notice(**{'buyer-name':{'deu':['Berufsschule München']},'notice-title':{'deu':'Roboter für die Berufsausbildung'}}),NOW)
  self.assertIsNotNone(x);self.assertEqual(x['institution_type'],'vocational');self.assertIn('DOBOT Magician / E6',x['matched_products'])
 def test_training_service_excluded(self):
  self.assertIsNone(parse(notice(**{'notice-title':{'deu':'Berufsausbildung nach BAG 30b'}}),NOW))
 def test_full_description(self):
  x=parse(notice(**{'buyer-name':{'deu':['Stadt Essen']},'description-proc':{'deu':('x '*1000)+'für das Berufskolleg Essen'}}),NOW)
  self.assertEqual(x['institution_type'],'vocational');self.assertTrue(x['procurement_for_education'])
