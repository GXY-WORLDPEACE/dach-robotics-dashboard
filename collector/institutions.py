"""Evidence-based institution targeting, separate from product suitability."""
import re

RULES = [
 ('chamber', '工商会／手工业协会', r'\b(?:ihk|hwk)\b|handwerkskammer|industrie[-\s]und[-\s]handelskammer|chambre de métiers|chambre de commerce|wirtschaftskammer'),
 ('vocational', '职业学校／技术学校', r'\bbbs\b|gewerbeschul\w*|berufsschul\w*|berufskolleg\w*|berufsfachschul\w*|beruflich\w* schul\w*|fachschul\w*|technikerschul\w*|berufsbildend\w* schul\w*|berufsbildungswerk\w*|berufliches schulzentrum|höhere technische (?:bundes)?lehranstalt|\bhtl\b|berufsfachschule|école professionnelle|scuola professionale'),
 ('training', '职业培训中心', r'berufsbildungsstätt\w*|training cent(?:er|re)\w*|berufsbildungszentr\w*|bildungszentr\w*|ausbildungszentr\w*|lehrwerkstatt\w*|überbetrieblich\w* (?:bildungs|ausbildungs)stätt\w*|überbetrieblich\w* (?:ausbildungs|bildungs)zentr\w*|centre de formation professionnelle'),
 ('research', '研究所', r'deutsche forschungsgemeinschaft|fraunhofer|helmholtz|leibniz|max[-\s]planck|forschungszentr\w*|forschungsinstitut\w*|\bdlr\b|\bdesy\b|\bkit\b|bundesanstalt für materialforschung|\bempa\b|\beawag\b|\bpsi\b|\bcern\b|\bait\b|institut de recherche'),
 ('university', '高校／应用科技大学', r'\buniversität\b|\buniversitaet\b|\buniversit[yé]\b|\bhochschule\b|\bfachhochschule\b|\b(?:tu|fh|haw|eth|epfl)\b|technische universiteit|haute école'),
]
PUBLIC = r'\bstadt\b|landkreis|kreisverwaltung|landratsamt|schulträger|schultraeger|gemeinde|kanton|magistrat|senatsverwaltung'
ROBOT = r'robot|cobot|manipulator|humanoid|teleoperation|greifer|gripper|quadruped'

def hit(text):
    for key, label, pattern in RULES:
        m=re.search(pattern,text,re.I)
        if m:return key,label,m.group(0)
    return None

def classify(item):
    buyer=str(item.get('buyer') or '')
    title=str(item.get('title') or '')
    desc=str(item.get('description') or '')
    # A hospital's name is not evidence for a university teaching lab.
    buyer_hit=None if re.search(r'klinikum|hospital|krankenhaus',buyer,re.I) else hit(buyer)
    title_hit=hit(title)
    body_hit=hit(desc)
    if body_hit and body_hit[0]=='chamber':
        # Membership / registry requirements are not evidence of a chamber as user.
        m=re.search(RULES[0][2],desc,re.I)
        context=desc[max(0,m.start()-150):m.end()+150] if m else ''
        if not re.search(r'bildungszentr|ausbildungszentr|berufsbildung|lehrwerkstatt|überbetrieblich|fortbildung|weiterbildung',context,re.I):
            body_hit=None
            for key,label,pattern in RULES[1:]:
                m=re.search(pattern,desc,re.I)
                if m:body_hit=(key,label,m.group(0));break
    found=buyer_hit or title_hit or body_hit
    if not found:
        return {'institution_type':'other','institution_label':'其他／待确认',
          'education_research':False,'institution_evidence':[],
          'procurement_for_education':False,'institution_relation':'未发现明确教育科研机构线索',
          'lead_priority':'C','lead_reason':'暂未识别目标机构；不代表没有采购能力'}
    key,label,word=found
    location='采购机构' if buyer_hit else '项目名称' if title_hit else '公告正文'
    delegated=not buyer_hit and bool(re.search(PUBLIC,buyer,re.I))
    relation=('市县／公共机构代采线索，最终使用单位待核实' if delegated else
              '采购机构名称匹配' if buyer_hit else '项目涉及目标机构，具体关系待核实')
    robotic=bool(re.search(ROBOT,title+' '+desc,re.I))
    lead='A' if buyer_hit and robotic else 'B'
    reason=('目标机构直接采购，且公告明确涉及机器人，建议优先核实需求' if lead=='A' else
            '存在教育科研／培训机构线索，需核实最终用户及机器人需求')
    return {'institution_type':key,'institution_label':label,'education_research':True,
      'institution_evidence':[f'{location}关键词：{word}'],'procurement_for_education':delegated,
      'institution_relation':relation,'lead_priority':lead,'lead_reason':reason}
