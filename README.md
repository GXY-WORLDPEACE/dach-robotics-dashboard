# DACH Robotics Tender Intelligence

Live public tender dashboard: https://gxy-worldpeace.github.io/dach-robotics-dashboard/

## Sources and scope
- **TED connected**: official keyless `POST https://api.ted.europa.eu/v3/notices/search`, Germany/Austria buyers, competition notices, future submission deadlines. Queries robot/cobot/manipulator/humanoid/automation terms in procedure title and description. Software licences, construction and consulting titles are excluded. This is a targeted search, not complete DACH coverage.
- **SIMAP not connected**: official Swagger https://www.simap.ch/api-doc/ and OpenAPI https://www.simap.ch/api/specifications/simap.yaml verified. The specification exposes `/publications/v2/project/project-search` and publication detail endpoints. Search/detail field mapping, pagination and operational reliability remain unverified; no Swiss records are fabricated or imported.
- National below-threshold platforms are not connected.

## Run and validate
Python 3.12+, standard library only. No API key required.

```
python -m unittest discover -s tests -v
python -m collector.fetch
```

`data/tenders.json` contains current active notices; `data/history.json` retains previously collected records. IDs are TED publication numbers with a source prefix; repeated scans update the same notice and retain first_seen. Distinct official publications/corrections retain separate IDs in history; the dashboard displays the latest publication per procedure_id when available. Last successful data survives API errors, with error status published and workflow failure. Partial/pagination failures fail closed. Missing budgets stay null; amounts are procedure-level estimates, not device prices. Multiple future lot deadlines are stored, the earliest is displayed. A missing time is date-only (assumed valid until that local day's end), and must be checked manually. Removed notices are marked unavailable in history; this is not proof of cancellation.

P1: explicit product-family keywords; P2: generic robotics; P3: broad automation or specialist medical/cleaning/lab applications. Reasons and candidate DOBOT families appear on cards. This is preliminary matching, not technical qualification. Verify payload, reach, interfaces, safety, lots and deadlines in official documents. No private customer data or secrets belong here.

## Automation and Pages
Collection runs at UTC 06:00 and 07:00 with a Europe/Berlin timezone guard choosing 08:00 local time (CET/CEST). A same-local-day success guard avoids duplicate scheduled runs. GitHub Actions may delay or skip scheduled runs; this is not a strict delivery SLA. Manual runs bypass the guard.

The collector tests, queries TED, commits JSON to main. Pages runs on main pushes **and collection workflow completion**, because GITHUB_TOKEN pushes do not trigger another push workflow. Pages always checks out main and packages docs plus data. A failed scan deploys its error status while retaining prior successful data. Enable GitHub Pages with GitHub Actions and allow contents writes. `collector/sources.json` is a source inventory; TED implementation and filtering live in `collector/ted.py`.

## 教育科研与职业培训范围

默认展示高校、研究所、职业学校／技术学校、职业培训中心／企业实训中心、工商会／手工业协会的采购线索，可切换“全部采购机构”。分类在每次采集时自动运行，检查采购机构、项目名称和完整程序描述；不把机构关键词作为 TED 查询的硬性限制，以免漏掉市县政府代采项目。

机构关键词包含 Universität/TU/Hochschule/FH/HAW/ETH、Fraunhofer/Helmholtz/Leibniz/Max Planck、Berufsschule/Berufskolleg/Berufsfachschule/Fachschule/Technikerschule/HTL、Berufsbildungszentrum/Bildungszentrum/Ausbildungszentrum/Lehrwerkstatt、IHK/HWK 等。医院不会仅因名称包含 Universitätsklinikum 就被视作高校实验室。市县采购方加正文教育机构关键词只标记“代采线索，待核实”，不把采购机关名称替换成学校。

机构跟进 A/B/C 与产品匹配 P1/P2/P3 独立：A 表示目标机构名称匹配且涉及机器人；B 表示教育科研／培训线索需要进一步核实；C 表示暂未识别目标机构。均不推断预算或采购能力。职业教育中的机器人设备采购不再因标题含 Berufsausbildung 而被排除；纯培训服务仍排除。中文翻译映射和原始公告保持分开。

此更新扩展机构识别和看板筛选，不表示新增接入德国本地平台或 SIMAP；仍仅展示已验证来源的真实公告。没有匹配项目的类型显示为零。
