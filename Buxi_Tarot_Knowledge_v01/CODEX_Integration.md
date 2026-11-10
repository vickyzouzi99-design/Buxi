# 接入给 Codex 的说明

这是独立资料包，不是代码覆盖补丁；尚未修改你的本地或远程 Buxi 项目。

1. 先查看 README.md、sources.json 和 validation_report.json，确认本包的来源范围与审核状态。
2. cards.json 包含78张牌；ID沿用此前 Buxi v0.2 的 major-0…major-21 及 wands/cups/swords/pentacles-1…14。宫廷牌11=侍从，12=骑士，13=王后，14=国王。仍需对当前仓库核对，不假定此后没有变化。
3. 不覆盖现有 tarotoo.json。本包是独立的 waite_1918/editorial_v01 来源分支，不能与 Tarotoo 混成同一作者的牌义。
4. 每次解读固定 knowledge_version 和 interpretation_policy。不要把每个来源的每种含义全部塞入提示词让模型任意挑选。
5. 对已抽牌，按 ID 和方向精确读取 editorial 下的中文改写；引用 metadata 和 evidence 另行传递。一般牌义问题可检索 retrieval_chunks.jsonl。此文件156条，未计算 embedding，未接入数据库，也未证明检索效果。
6. 默认知识块不包含危险历史断语；historical 层用于明确的原典研究查询和展开依据。模型仍须遵守应用边界，不把词表当成诊断或事件事实。
7. 所有条目 review_status=human_review_pending。内测可明确使用编辑初稿；不能通过脚本一键改成 expert_reviewed。缺少审核的状态必须保留。
8. 牌位来自项目规则；不要将用户问题、记忆或历史聊天写进专业库。
9. 接入后运行 eval_cases.jsonl 中的行为验收。这些是人工定义的测试规范，不是已经运行的模型评测结果。
10. 先运行 python validate.py 检查数据。该命令无网络、无第三方依赖；能验证结构与证据定位，不能验证翻译语义或对话质量。

建议回传给 UI 的 citation 对象包含：card_id、orientation、knowledge_version、content_kind、source_id、section、line_start、line_end、source_url。保留中文编辑标签和原文依据之间的区别。

不要自动训练模型。两本现代书的全文未被纳入；不能凭书目条目引用它们的具体观点或牌义。
