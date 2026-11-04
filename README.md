# 欧洲五国教育科研机器人采购情报

https://gxy-worldpeace.github.io/dach-robotics-dashboard/

中文看板，重点关注高校、研究所、职业学校、职业培训中心及 IHK/HWK。机构跟进 A/B/C 与产品匹配 P1/P2/P3 独立。只导入公开官方来源；摘要与关键词评分不代表技术合规、采购资格或预算能力。

## 已接入来源

| 来源 | 访问方式与范围 | 限制 |
| --- | --- | --- |
| TED | 官方免密钥 Search API，德国／奥地利／瑞士／荷兰／比利时，仍有投标截止日期的 competition 公告 | 非全部历史；若原公告未同步延期可能漏检，因此增加门户核验 |
| 德国 Bekanntmachungsservice（BKMS） | 官方 Open Data `https://oeffentlichevergabe.de/api/notice-exports`；CSV 索引 + 原始 eForms XML；上月与本月 | 数据截至德国时间前一日；只覆盖向该服务提交的公告，不能声称覆盖全部地方采购 |
| DFG | `https://bieterportal.dfg.de/?l=1` 官方公开列表；自动解析项目编号和当前截止日期 | 网页结构可能变动；未公开的发布日期留空 |
| 瑞士 SIMAP | 已接入公开搜索与详情接口 | 见下方五国扩展范围及限制 |
| 奥地利 USP | 已接入官方公开列表及详情 | 最近 90 天关键词；详情访问异常记录 partial |
| 荷兰 TenderNed | 已接入公开 TNS JSON | 最近 90 天；不使用需凭证的 XML API |
| 德国区域平台 | 6 个 NRW／城市 ZIP 端点 | 同时解析 UBL 和旧格式；非全部德国地方平台 |
| 比利时 BOSA 本地接口 | 暂未直接接入，匿名访问 403 | 目前通过 TED 部分覆盖 |

BKMS 官方说明与 CC0 许可：https://oeffentlichevergabe.de/ui/de/publicationPolicy
API 文档：https://oeffentlichevergabe.de/documentation/swagger-ui/opendata/index.html
BKMS 的 CSV 格式不包含本采集器需要的投标截止字段，因此不能用有效期或开标时间代替截止时间。截止时间从原始 XML 的 TenderSubmissionDeadlinePeriod / ParticipationRequestReceptionPeriod 读取。问答截止时间不会当作投标截止时间。

## 公告阶段与去重

- `data/tenders.json`：已确认有未来截止日期的投标中项目。
- `data/opportunities.json`：按采购程序去重后的投标中、采购预告、历史／结果公告、状态待核实项目；网站主要读取此文件。
- `data/history.json`：保留不同来源、版本和首次发现时间。公告缺失不等于取消。
- `data/scan_status.json`：每个来源的成功／失败、扫描范围与数量。单个来源失败保留其历史数据，并明确警告数据可能陈旧；其他来源继续更新，工作流返回失败以便排查。
- `data/coverage_audit.json`：每轮自动检查 BAM、DFG、Wildau、Magdeburg-Stendal 四个已知真实样本是否仍能检出。

身份合并使用采购程序 UUID、官方公告 UUID、精确的采购方+项目编号，或明确的 subreport 项目 ID。保留所有原始公告 ID 与链接，不按相似标题盲目去重。DFG 门户与 BKMS 的项目编号缺失时，仅在采购方+标题完全一致且对应唯一采购程序时补充关联。当前 DFG 列表可以修正该程序的截止时间，页面保留原公告字段与核验链接。结果公告不会因带有未来日期而成为投标中。

采购预告和缺少截止日期的公告不会混入投标中。历史选项仅表示已收录公告的截止已过或已公布结果，不保证该采购已完成。

## 教育科研分类

检查采购方、项目名称和正文关键词：Universität/TU/Hochschule/FH/HAW/ETH、Fraunhofer/Helmholtz/Leibniz/Max Planck/DFG、Berufsschule/Berufskolleg/Fachschule/Technikerschule/BBS/HTL、Bildungszentrum/Ausbildungszentrum/Lehrwerkstatt、IHK/HWK 等。

市县政府正文提到学校时仅标注“代采线索，最终用户待核实”。单纯要求企业提供 IHK/HWK 注册证明不能当作商会采购。医院名称包含 Universitätsklinikum 不等于大学机器人实验室。普通机器人操作培训也不等于培训中心采购。

## 本地运行与检查

Python 3.12+，只用标准库，无 API 密钥。

```
python -m unittest discover -s tests -v
python -m collector.fetch
```

BKMS 完整归档存入被忽略的 `.cache/bkms/`（可用 BKMS_CACHE_DIR 改目录），按当天日期缓存，不提交原始归档、公共联系人表或中间数据。每天获取上月与本月的 CSV / XML，约百 MB 量级。导出不含当天新公告，此限制在页面展示。原始月归档仅用于解析，不是看板数据文件。

## GitHub Actions 与 Pages

每天 Europe/Berlin 08:00 计划采集。UTC 06:00 / 07:00 两个候选 cron 按夏令时选择，按本地日期防止重复成功运行。Actions 可能延迟或跳过，非严格准点服务。修改 collector / tests / collection workflow 时也运行测试与采集，支持手动触发。

采集自动提交 data 到 main；Pages 监听 main push 和采集工作流完成，以覆盖 GITHUB_TOKEN 提交不会触发 push 工作流的情况。失败扫描也发布错误状态与保留数据。需要 Pages 配置为 GitHub Actions，内容写权限可用。

中文译文单独存储在 `docs/translations.zh.json`，跨来源合并后保留原已译公告的译文。尚未翻译的新项目明确显示待翻译，不自动编造中文内容。原文和原平台链接可展开查看。

## 覆盖核查结果（2026-11-04）

- BAM：原来未接入国家级 UVgO 来源，已由 BKMS 检出。
- Magdeburg-Stendal：国家级公告版本更新；旧截止 11 月 4 日，新版 11 月 6 日 10:00。
- DFG 移动串联机器人：TED 原公告字段为 11 月 2 日，DFG 当前官方门户为 11 月 13 日 12:00，已单独核验。
- TH Wildau：官方导出为拟进行采购，未提供可靠投标截止；归入采购预告。原平台页面本次返回 404，不把聚合站期限当作已核实事实。

这些修复扩大覆盖范围，但尚未直接接入所有州平台及学校网站；奥地利 USP 和 SIMAP 接入范围见下方五国扩展说明。地方未上报公告、早于上月月初且未更新的公告仍可能遗漏。

## 五国与地方平台扩展（2026-11-04）

监控国家扩展为德国、奥地利、瑞士、荷兰、比利时。**部分覆盖，绝不声称已接入全部地方平台**。国家／州／市未公开或未向汇总平台上报的采购仍可能缺失。

| 来源 | 实际采集方式 | 范围与限制 |
| --- | --- | --- |
| TED | 官方 Search API，DEU/AUT/CHE/NLD/BEL | 欧盟级公告，关键词与未来投标截止日期；不能替代五国本地公告 |
| 德国 BKMS、DFG | 原有官方数据源继续运行 | 上述时间窗口和限制保留 |
| 德国区域平台 | GovData 明确列出的 NRW、Metropole Ruhr、BLB NRW、Westfalen、Köln、Aachen XML ZIP | 同时支持 UBL eForms 与 NOTICE_NAT 旧格式；原始发布日期缺失时留空，不使用 ZIP 更新时间伪造公告发布日期 |
| SIMAP（瑞士） | 官方匿名公开搜索与详情接口，滚动游标分页 | 最近 90 天的六组关键词；automation/automatisierung 限供应类项目以减少建筑／服务噪声。覆盖平台发布的联邦、州、市公告，不覆盖未公开采购 |
| USP（奥地利） | 当前官方公开 DataTables JSON 列表及服务器渲染详情 | 最近 90 天五组关键词；遵守页面公布的请求间隔。列表仅公开日期时保留日期，不编造时间；详情失败按 partial 记录 |
| TenderNed（荷兰） | 官方公开 TNS JSON 服务 | 最近 90 天，按发布顺序分页，单页最多 100；公开 XML API 需要账号，此项目没有使用该接口或任何凭证 |
| BOSA（比利时） | 尚未直接接入 | 官方公开站点的匿名搜索接口返回 403；比利时目前通过 TED 部分覆盖，未绕过访问限制 |
| Rheinland 区域平台 | 尚未接入 | GovData 所列端点本次返回 403，列入缺口 |

公开文档：
- TenderNed：https://data.overheid.nl/dataset/aankondigingen-van-overheidsopdrachten---tenderned
- SIMAP：https://www.simap.ch/api-doc/
- USP：https://ausschreibungen.usp.gv.at/at.gv.bmdw.eproc-p/public/tenderlist
- 德国区域 ZIP 目录：https://data.gov.de/suche/daten/ausschreibungen-vergabemarktplatz-nrw

`collector/source_registry.json` 管理已启用和受限来源；`data/source_coverage.json` 每次采集自动生成每国数量、每来源运行结果、实际窗口、错误与缺口。66 个州／省／大区是核查清单，**不是已接入平台数量，也不代表 66 个地区全覆盖**。页面可展开查看每个地区的缺口。

所有启用来源继续由现有 GitHub Actions 在 Europe/Berlin 08:00 自动采集，来源间使用最多 4 个工作线程；单个来源内遵守分页与间隔。单源失败不会阻止其他来源更新，状态会注明异常并保留历史。多个来源的项目按程序 ID、精确引用或官方平台 ID 去重；TenderNed 与 SIMAP 的官方链接可用于与 TED 关联。缺少可靠关联键的疑似重复不会按相似标题强行合并。

扩展新区域 ZIP 来源时，应先验证官方出处、解析器、截止日期与去重，再向 registry 添加 `kind=vmp_zip` 和 `enabled=true`。访问受限或未验证来源不能标成 connected。未翻译的新公告仍明确标记“中文翻译待补充”。
