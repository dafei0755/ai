# 激活包范围草案人工复核清单

- 生成时间: `2026-06-15T13:03:10`
- 边界: 本清单不得自动写入正式激活包、Registry 或知识库。
- 复核结果只能作为人工裁决记录；正式包编写必须另走激活包校验流程。

## 可选裁决

- `approve_for_formal_pack_authoring`
- `request_more_evidence`
- `keep_observing`
- `reject_scope`

## 复核项

### activation_scope_draft.public_cultural.cultural_public_experience

- 项目类型: `public_cultural`
- 空间主轴: `cultural_public_experience` / 文化公共空间：叙事体验、展陈秩序与公众使用
- 样本数: 12
- 平均置信度: 0.823
- 默认裁决: `request_more_evidence`
- 复核角色: domain_expert, knowledge_architect, product_owner
- 阻断项: 无

#### 检查点

- 适用边界是否足够窄，是否能说明哪些项目可以使用这个激活包。
- 不适用边界是否明确，是否能防止相邻空间被误激活。
- 父级项目类型、空间主轴和样本证据是否一致。
- 必须补齐的定义是否完整：routing_boundary, assumptions, non_goals, required_slots, type_method_profile, risk_control, knowledge_recall_plan, regression_samples。
- required_slots 是否能支持首轮问诊，不会暴露内部术语给终端用户。
- risk_control 是否覆盖安全、法规、机电、运营或知识覆盖封顶风险。
- knowledge_recall_plan 是否只调用审核通过的知识卡，不直接召回原始研究长文。
- 最小复核门槛是否可执行：确认是否确实需要正式激活包，而不是继续使用基础空间推理框架。；确认适用边界、不适用边界和父级项目类型，不得扩大到所有相邻空间。；补齐 required_slots、risk_control 和最小知识卡清单后，才能转写正式激活包。；正式激活包上线前必须通过激活包校验器、190 条压力测试和用户侧文案守门。。

#### 裁决记录模板

- decision:
- reviewer:
- reviewed_at:
- reason:
- required_changes:

### activation_scope_draft.personal_residential.private_residential_life_order

- 项目类型: `personal_residential`
- 空间主轴: `private_residential_life_order` / 私人住宅：家庭秩序、生活方式与精神需求
- 样本数: 17
- 平均置信度: 0.768
- 默认裁决: `request_more_evidence`
- 复核角色: domain_expert, knowledge_architect, product_owner
- 阻断项: 无

#### 检查点

- 适用边界是否足够窄，是否能说明哪些项目可以使用这个激活包。
- 不适用边界是否明确，是否能防止相邻空间被误激活。
- 父级项目类型、空间主轴和样本证据是否一致。
- 必须补齐的定义是否完整：routing_boundary, assumptions, non_goals, required_slots, type_method_profile, risk_control, knowledge_recall_plan, regression_samples。
- required_slots 是否能支持首轮问诊，不会暴露内部术语给终端用户。
- risk_control 是否覆盖安全、法规、机电、运营或知识覆盖封顶风险。
- knowledge_recall_plan 是否只调用审核通过的知识卡，不直接召回原始研究长文。
- 最小复核门槛是否可执行：确认是否确实需要正式激活包，而不是继续使用基础空间推理框架。；确认适用边界、不适用边界和父级项目类型，不得扩大到所有相邻空间。；补齐 required_slots、risk_control 和最小知识卡清单后，才能转写正式激活包。；正式激活包上线前必须通过激活包校验器、190 条压力测试和用户侧文案守门。。

#### 裁决记录模板

- decision:
- reviewer:
- reviewed_at:
- reason:
- required_changes:

