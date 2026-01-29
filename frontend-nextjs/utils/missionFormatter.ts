/**
 * 将四条使命的JSON数据转换为自然语言呈现
 */

import {
  FourMissions,
  Mission1UserProblemAnalysis,
  Mission2ClearObjectives,
  Mission3TaskDimensions,
  Mission4ExecutionRequirements,
} from '@/types';

/**
 * 使命1：用户问题分析 - 转换为自然语言
 */
export function formatMission1ToNaturalLanguage(mission: Mission1UserProblemAnalysis): string {
  const { content } = mission;

  return `根据您的描述，我理解您可能是${content.user_identity}，正在进行${content.project_type}。

**项目背景**
地点：${content.project_location}
规模：${content.project_scale}
核心主题：${content.core_theme}

**设计挑战**
这个项目的核心张力在于：${content.core_tension}

关键约束包括：${content.key_constraints.join('、')}

**您的动机**
${content.user_motivation}`;
}

/**
 * 使命2：明确目标 - 转换为自然语言
 */
export function formatMission2ToNaturalLanguage(mission: Mission2ClearObjectives): string {
  const { content } = mission;

  const deliverablesText = content.key_deliverables
    .map((d, i) => `${i + 1}. **${d.name}**${d.priority === 'MUST_HAVE' ? '（必需）' : '（可选）'}：${d.description}`)
    .join('\n');

  const criteriaText = content.success_criteria
    .map((c, i) => `${i + 1}. ${c}`)
    .join('\n');

  return `**我将为您提供**
${content.final_deliverable_type}，采用${content.output_format}的形式，面向${content.target_audience}。

**核心交付内容**
${deliverablesText}

**成功标准**
${criteriaText}`;
}

/**
 * 使命3：任务维度 - 转换为自然语言
 */
export function formatMission3ToNaturalLanguage(mission: Mission3TaskDimensions): string {
  const { content } = mission;

  const stepsText = content.key_steps
    .map((s, i) => `**步骤${i + 1}：${s.action}**\n目的：${s.purpose}\n预期输出：${s.expected_output}`)
    .join('\n\n');

  const breakthroughsText = content.breakthrough_points
    .map((b, i) => `**突破点${i + 1}：${b.point}**\n为什么关键：${b.why_key}\n如何利用：${b.how_to_leverage}`)
    .join('\n\n');

  return `**解题思路**
这是一个${content.task_type}任务，复杂度为${content.complexity_level}。

我将采用${content.solution_approach}的方法论来解决。

需要的专业能力：${content.required_expertise.join('、')}

**关键步骤**
${stepsText}

**突破点**
${breakthroughsText}`;
}

/**
 * 使命4：执行要求 - 转换为自然语言
 */
export function formatMission4ToNaturalLanguage(mission: Mission4ExecutionRequirements): string {
  const { content } = mission;

  const standardsText = content.quality_standards.map((s, i) => `${i + 1}. ${s}`).join('\n');
  const constraintsText = content.constraints_to_respect.map((c, i) => `${i + 1}. ${c}`).join('\n');
  const antiPatternsText = content.anti_patterns.map((a, i) => `${i + 1}. ${a}`).join('\n');
  const risksText = content.risk_alerts.map((r, i) => `${i + 1}. ${r}`).join('\n');
  const toolsText = content.recommended_tools.map((t, i) => `${i + 1}. ${t}`).join('\n');

  return `**质量标准**
${standardsText}

**必须遵守的约束**
${constraintsText}

**应避免的做法**
${antiPatternsText}

**潜在风险提醒**
${risksText}

**推荐工具**
${toolsText}`;
}

/**
 * 将所有使命转换为完整的自然语言描述
 */
export function formatAllMissionsToNaturalLanguage(missions: FourMissions): string {
  return `# ${missions.creation_command}

## 我的理解

${formatMission1ToNaturalLanguage(missions.mission_1_user_problem_analysis)}

---

${formatMission2ToNaturalLanguage(missions.mission_2_clear_objectives)}

---

${formatMission3ToNaturalLanguage(missions.mission_3_task_dimensions)}

---

## 注意事项

${formatMission4ToNaturalLanguage(missions.mission_4_execution_requirements)}`;
}
