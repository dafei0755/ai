/**
 * 将四条使命的JSON数据转换为自然语言呈现
 * v7.302.6: 添加空值检查，支持流式输出时数据不完整的情况
 * v7.302.10: 支持两种数据结构（嵌套content和扁平结构）
 */

import {
  FourMissions,
  Mission1UserProblemAnalysis,
  Mission2ClearObjectives,
  Mission3TaskDimensions,
  Mission4ExecutionRequirements,
} from '@/types';

/**
 * v7.302.10: 获取使命内容，支持嵌套和扁平两种结构
 */
function getMissionContent<T>(mission: any): T | null {
  if (!mission) return null;
  // 嵌套结构：mission.content
  if (mission.content && typeof mission.content === 'object') {
    return mission.content as T;
  }
  // 扁平结构：mission 本身就是内容
  return mission as T;
}

/**
 * 使命1：用户问题分析 - 转换为自然语言
 */
export function formatMission1ToNaturalLanguage(mission: Mission1UserProblemAnalysis): string {
  const content = getMissionContent<any>(mission);
  if (!content) return '';

  const parts: string[] = [];

  if (content.user_identity || content.project_type) {
    parts.push(`根据您的描述，我理解您可能是${content.user_identity || '用户'}，正在进行${content.project_type || '项目设计'}。`);
  }

  if (content.project_location || content.project_scale || content.core_theme) {
    parts.push('\n**项目背景**');
    if (content.project_location) parts.push(`地点：${content.project_location}`);
    if (content.project_scale) parts.push(`规模：${content.project_scale}`);
    if (content.core_theme) parts.push(`核心主题：${content.core_theme}`);
  }

  if (content.core_tension) {
    parts.push(`\n**设计挑战**\n这个项目的核心张力在于：${content.core_tension}`);
  }

  if (content.key_constraints && content.key_constraints.length > 0) {
    parts.push(`关键约束包括：${content.key_constraints.join('、')}`);
  }

  if (content.user_motivation) {
    parts.push(`\n**您的动机**\n${content.user_motivation}`);
  }

  return parts.join('\n');
}

/**
 * 使命2：明确目标 - 转换为自然语言
 */
export function formatMission2ToNaturalLanguage(mission: Mission2ClearObjectives): string {
  const content = getMissionContent<any>(mission);
  if (!content) return '';

  const parts: string[] = [];

  if (content.final_deliverable_type || content.output_format || content.target_audience) {
    parts.push('**我将为您提供**');
    parts.push(`${content.final_deliverable_type || '分析报告'}，采用${content.output_format || '文档'}的形式，面向${content.target_audience || '用户'}。`);
  }

  if (content.key_deliverables && content.key_deliverables.length > 0) {
    const deliverablesText = content.key_deliverables
      .map((d: any, i: number) => `${i + 1}. **${d.name}**${d.priority === 'MUST_HAVE' ? '（必需）' : '（可选）'}：${d.description}`)
      .join('\n');
    parts.push(`\n**核心交付内容**\n${deliverablesText}`);
  }

  if (content.success_criteria && content.success_criteria.length > 0) {
    const criteriaText = content.success_criteria
      .map((c: any, i: number) => `${i + 1}. ${c}`)
      .join('\n');
    parts.push(`\n**成功标准**\n${criteriaText}`);
  }

  return parts.join('\n');
}

/**
 * 使命3：任务维度 - 转换为自然语言
 */
export function formatMission3ToNaturalLanguage(mission: Mission3TaskDimensions): string {
  const content = getMissionContent<any>(mission);
  if (!content) return '';

  const parts: string[] = [];

  if (content.task_type || content.complexity_level) {
    parts.push('**解题思路**');
    parts.push(`这是一个${content.task_type || '设计'}任务，复杂度为${content.complexity_level || '中等'}。`);
  }

  if (content.solution_approach) {
    parts.push(`我将采用${content.solution_approach}的方法论来解决。`);
  }

  if (content.required_expertise && content.required_expertise.length > 0) {
    parts.push(`需要的专业能力：${content.required_expertise.join('、')}`);
  }

  if (content.key_steps && content.key_steps.length > 0) {
    const stepsText = content.key_steps
      .map((s: any, i: number) => `**步骤${i + 1}：${s.action}**\n目的：${s.purpose}\n预期输出：${s.expected_output}`)
      .join('\n\n');
    parts.push(`\n**关键步骤**\n${stepsText}`);
  }

  if (content.breakthrough_points && content.breakthrough_points.length > 0) {
    const breakthroughsText = content.breakthrough_points
      .map((b: any, i: number) => `**突破点${i + 1}：${b.point}**\n为什么关键：${b.why_key}\n如何利用：${b.how_to_leverage}`)
      .join('\n\n');
    parts.push(`\n**突破点**\n${breakthroughsText}`);
  }

  return parts.join('\n');
}

/**
 * 使命4：执行要求 - 转换为自然语言
 */
export function formatMission4ToNaturalLanguage(mission: Mission4ExecutionRequirements): string {
  const content = getMissionContent<any>(mission);
  if (!content) return '';

  const parts: string[] = [];

  if (content.quality_standards && content.quality_standards.length > 0) {
    const standardsText = content.quality_standards.map((s: any, i: number) => `${i + 1}. ${s}`).join('\n');
    parts.push(`**质量标准**\n${standardsText}`);
  }

  if (content.constraints_to_respect && content.constraints_to_respect.length > 0) {
    const constraintsText = content.constraints_to_respect.map((c: any, i: number) => `${i + 1}. ${c}`).join('\n');
    parts.push(`\n**必须遵守的约束**\n${constraintsText}`);
  }

  if (content.anti_patterns && content.anti_patterns.length > 0) {
    const antiPatternsText = content.anti_patterns.map((a: any, i: number) => `${i + 1}. ${a}`).join('\n');
    parts.push(`\n**应避免的做法**\n${antiPatternsText}`);
  }

  if (content.risk_alerts && content.risk_alerts.length > 0) {
    const risksText = content.risk_alerts.map((r: any, i: number) => `${i + 1}. ${r}`).join('\n');
    parts.push(`\n**潜在风险提醒**\n${risksText}`);
  }

  if (content.recommended_tools && content.recommended_tools.length > 0) {
    const toolsText = content.recommended_tools.map((t: any, i: number) => `${i + 1}. ${t}`).join('\n');
    parts.push(`\n**推荐工具**\n${toolsText}`);
  }

  return parts.join('\n');
}

/**
 * 将所有使命转换为完整的自然语言描述
 */
export function formatAllMissionsToNaturalLanguage(missions: FourMissions): string {
  if (!missions) return '';

  const parts: string[] = [];

  if (missions.creation_command) {
    parts.push(`# ${missions.creation_command}`);
  }

  const mission1Text = missions.mission_1_user_problem_analysis
    ? formatMission1ToNaturalLanguage(missions.mission_1_user_problem_analysis)
    : '';
  if (mission1Text) {
    parts.push(`\n## 我的理解\n\n${mission1Text}`);
  }

  const mission2Text = missions.mission_2_clear_objectives
    ? formatMission2ToNaturalLanguage(missions.mission_2_clear_objectives)
    : '';
  if (mission2Text) {
    parts.push(`\n---\n\n${mission2Text}`);
  }

  const mission3Text = missions.mission_3_task_dimensions
    ? formatMission3ToNaturalLanguage(missions.mission_3_task_dimensions)
    : '';
  if (mission3Text) {
    parts.push(`\n---\n\n${mission3Text}`);
  }

  const mission4Text = missions.mission_4_execution_requirements
    ? formatMission4ToNaturalLanguage(missions.mission_4_execution_requirements)
    : '';
  if (mission4Text) {
    parts.push(`\n---\n\n## 注意事项\n\n${mission4Text}`);
  }

  return parts.join('\n');
}
