# 等待项跟进

## 操作步骤
用 `get_project` 读取未完成等待项的 `blocked_by_label`、`next_check_at`、`updated_at` 和可见进展；向用户核实最后实际回复、双方约定与请求内容。按对象对照 [判断标准](thresholds.md) 的内部或外部等待行；更新时间不证明收到回复。确认用户希望的期限和升级对象，只起草、不自动发送。

需要更新复查时，经用户同意用 `upsert_waiting_item` 传 `project_id`、title、`target_id`、原 status 和 `next_check_at`，先预演；只写日期时以 tz 当地上午解释。不把标签当实际指派。二次催询先确认前次是否发出及是否收到回复；仍无回应时向用户提出升级，由用户决定是否调整计划或通过适当渠道联系。

## 示例：内部合作者丙
假设课题甲等待合作者丙确认图表，约定 2026-11-12 回复，以下是可复制草稿。

中文：合作者丙，您好！课题甲的【材料名称】正在等待您的确认。烦请查看【具体问题】，并在【期望日期】前告知是否同意或需要修改。如时间不便，请告知可回复日期，我可以配合调整。谢谢！【署名】

English: Dear 【collaborator role】, I am following up on 【material】 for 【project】. Could you review 【specific question】 and reply by 【date】? If that timing is difficult, please suggest another date or let me know what you need. Thank you. 【signature】

二次催询（中）：您好，跟进此前关于【材料】的请求，尚未确认您的意见；请问【新日期】前能否回复，或建议其他时间？谢谢。【署名】

Second follow-up (EN): Dear 【collaborator role】, I am following up on my earlier request about 【material】. Could you reply by 【new date】 or suggest a workable date? Thank you. 【signature】

升级：仍无反馈时向用户说明依赖与截止冲突，建议由用户与课题负责人商议替代审核或调整节点，不自行联系他人。

## 院内科室或统计：完整话术
中文：您好！课题甲需要【科室或统计事项】，此前已提供【材料范围】。请问目前进度及预计反馈日期如何？如可行，希望在【期望日期】前收到结果；如需补充资料，请告知清单。谢谢！【署名】

English: Dear 【department or statistics team】, for 【project】 we requested 【work item】 and provided 【materials】. Could you share its status and expected completion date? A response by 【date】 would help; please tell us what additional materials are needed. Thank you. 【signature】

二次催询（中）：您好，关于此前【事项】再次请教进度；若【新日期】不便，请告知预计时间及所需补充材料，以便调整计划。谢谢。【署名】

Second follow-up (EN): Dear 【team】, I am checking again on 【work item】. If 【new date】 is not feasible, please share an estimate and any missing materials so we can adjust our plan. Thank you. 【signature】

升级：经用户决定，先请相关负责人协调排期或范围；没有明确授权不转交材料或发消息。

## 期刊或编辑部：完整话术
中文：尊敬的编辑部：您好！我们于【投稿日期】向期刊乙提交【稿件标题】，稿件编号【编号】。现礼貌询问【当前环节】的进展及是否需要我们补充材料；如方便，烦请告知预计时间。感谢您的协助！【署名】

English: Dear 【editorial office】, We submitted 【manuscript title】 to 【journal】 on 【submission date】 (manuscript ID: 【ID】). Could you kindly share the status of 【stage】 and let us know if any further information is needed? An estimated timeline, if available, would be appreciated. Thank you. 【signature】

二次催询（中）：尊敬的编辑部：就此前【询问日期】关于【稿件编号】的咨询再次致意；如有进展或需要补充材料，烦请告知。感谢您。【署名】

Second follow-up (EN): Dear 【editorial office】, I am following up on our inquiry of 【date】 about manuscript 【ID】. We would appreciate any update or request for additional information. Thank you for your assistance. 【signature】

升级：先核对期刊乙的流程及前次回复，再建议用户决定是否通过正式投稿系统联系编辑；不承诺回复时间。

## 常见坑
不要把无回复当成拒绝；不要写入患者信息或假造约定；未确认消息发出时不能说已经催过。
