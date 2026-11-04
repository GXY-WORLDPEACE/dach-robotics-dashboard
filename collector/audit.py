"""Known genuine examples used to monitor coverage, not invented tender seeds."""
def audit(items,checked_at):
    cases=[
      ('BAM','BAM：柔性协作机器人上下料系统','d5ac23cd-3a48-4fa8-87eb-1b17e694c480','国家级 UVgO 公告；旧系统仅接入 TED，缺少国家级数据源。'),
      ('Magdeburg-Stendal','Magdeburg-Stendal：自动化搬运与码垛系统','e6c7549e-f612-4265-9731-8b04db662c65','国家级公告；新版延长截止日期，必须按公告版本更新。'),
      ('DFG Dresden','DFG：移动串联机器人','DFG_2026_III-WGI_EU31','TED 原公告截止字段为 11 月 2 日；DFG 当前官方列表为 11 月 13 日，旧过滤会漏掉延期项目。'),
      ('TH Wildau','TH Wildau：机械臂采购意向','CXP9YRUH331','官方导出标记拟进行采购，无可验证的投标截止日期；作为采购预告展示，不算投标中。原平台页面本次返回 404，详细意向期限待核实。'),
    ]
    out=[]
    for name,title,needle,reason in cases:
        matches=[x for x in items if needle in str(x.get('related_notice_ids',[]))+str(x.get('procurement_reference',''))+str(x.get('official_links',[]))]
        x=matches[0] if matches else {}
        out.append({'sample':name,'title':title,'found':bool(matches),'reason':reason,
                    'phase':x.get('phase'),'deadline':x.get('deadline'),'source_url':x.get('source_url'),
                    'deadline_source':x.get('deadline_source'),'project_id':x.get('id')})
    return {'checked_at':checked_at,'cases':out,'note':'基于当前官方采集数据的覆盖核查；不是全量覆盖保证。'}
