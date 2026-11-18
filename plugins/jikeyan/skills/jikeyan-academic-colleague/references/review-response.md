# 审稿意见与修回

## 处理步骤与类型
取得期刊乙原始意见、修回期限、当前稿件及研究者允许使用的材料；用 `get_project` 查看已有轮次与节点。逐条编号，记原意、处理方式、负责人确认状态与修改位置；不要将拟修改写成已完成。科学方法、结果和伦理判断由研究者负责。

- 补充分析：先核实数据和方案可行性、资源与截止；拟定分析计划，请研究者审定，完成并核对后才描述结果。
- 质疑方法：定位方案、方法与依据，检查表述是否足以复现；如有局限明确承认，不能虚构合理性。
- 改写措辞：比较原文和证据，降低过度推断，保留科学含义；由作者审核修改。
- 与结论不符：核对结果、图表与结论方向和范围；发现冲突先暂停回复，请研究者裁决。
- 要求引文：核对引用与论断是否对应、格式及可获得的元数据；本知识包没有文献验证或撞题检索工具，需用户另行核验。
- 无法做到或有分歧：解释具体限制、证据和替代方案，礼貌请求考虑；不承诺不存在的修改。

## 示例：课题甲五条意见拆解
| 编号 | 虚构意见与类型 | 处理与证据 | 位置 / 状态 |
| --- | --- | --- | --- |
| 1 | 请补充敏感性分析 | 研究者先确认方案与可用数据；结果待核实 | 方法及结果 / 待处理 |
| 2 | 方法描述不足，如何选择样本？ | 对照已批准方案补充选择流程；请作者确认 | 方法 / 待处理 |
| 3 | 结论措辞过强 | 将因果措辞改为关联描述，由作者审核 | 讨论 / 草稿 |
| 4 | 结论与图表方向不一致 | 核对图表和结果，暂停确定答复 | 结果与结论 / 待裁决 |
| 5 | 请为背景陈述补充引文 | 用户提供候选条目并另行核验相关性与真实性 | 引言 / 待核实 |

## 中文回复信模板
尊敬的编辑和审稿专家：

感谢您审阅【稿件标题】并提出建设性意见。我们逐条评估了意见，并在作者确认后修订稿件；以下列出回应及修改位置。尚未完成的部分在定稿前须核实，不应保留为已完成。

意见【编号】：【准确引用或概述意见】。
回应：感谢此建议。我们【已核实的处理及依据】；【修改后的具体内容摘要】。
修改位置：【稿件版本、章节、页码及行号；未知则待核实】。

意见【编号，有分歧】：【准确概述意见】。
回应：感谢这一建议。经审慎考虑，【具体限制及依据】使我们目前无法【请求的工作】。我们已【可行替代或局限说明】；恳请您考虑这一处理方式。
修改位置：【实际位置或未修改及原因】。

此致，
【作者代表或角色】

## English response letter template
Dear 【editor and reviewers】,

Thank you for reviewing 【manuscript title】 and for the constructive comments. We have considered each point and, after author confirmation, revised the manuscript as described below. Verify all changes before sending.

Comment 【number】: 【accurate quotation or summary】.
Response: Thank you for this suggestion. We 【verified action and rationale】. The manuscript now 【specific change】.
Location: 【version, section, page and line numbers; pending verification if unknown】.

Comment 【number, disagreement】: 【accurate summary】.
Response: We appreciate this suggestion. After careful consideration, 【specific limitation and evidence】 prevents us from 【requested action】. We have instead 【feasible alternative or limitation statement】 and respectfully ask you to consider this approach.
Location: 【actual location, or no change and reason】.

Sincerely, 【author representative or role】

## 示例：修回倒排
假设截止 2026-12-01，按 [判断标准](thresholds.md) 默认缓冲行并结合可用性：2026-11-09 完成意见拆解，2026-11-16 研究者确认分析方案，2026-11-20 核实分析与图表，2026-11-24 完成稿件和回复初稿，2026-11-28 完成作者确认和最终检查，2026-12-01 提交。若需要外部反馈应另按其缓冲行核对可行性，不能假装已有反馈。

## 记录与常见坑
经用户确认后用 `add_review_round` 的 `project_id`、`round_number`、`comments_markdown`、`response_markdown` 和可选 `due_at`；修改已有轮次带 `target_id`，保留用户确认的 status。意见字段放编号与必要的意见摘要，回复字段放对应回应、确认状态及修改位置；不放完整稿件正文、患者姓名、住院号、诊断或随访原文。当前服务端审稿轮次模型将两个字段各定义为最多 10000 字符，写入前分别检查；该上限未由 `get_schema` 的 limits 公布，仍需遵守实际服务端校验。过长时保留本地完整材料，写入简短索引并说明不完整，不猜上限。先预演、核回执再写；节点另用 `upsert_node`。

不要编造结果、引用、页码或审稿人观点；修回时限、作者同意和实际提交状态均需核实。
