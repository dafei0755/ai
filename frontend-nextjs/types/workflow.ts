/**
 * 工作流可视化类型定义
 * 
 * 定义 16 步智能项目分析工作流的节点和边
 */

// @ts-nocheck
import { Node, Edge } from '@xyflow/react';

/**
 * 节点状态类型
 */
export type NodeStatus = 'pending' | 'running' | 'completed' | 'error' | 'skipped';

/**
 * 工作流节点数据
 */
export interface WorkflowNodeData {
  /** 节点标签 */
  label: string;
  /** 节点描述 */
  description: string;
  /** 节点状态 */
  status: NodeStatus;
  /** Agent 名称 */
  agent?: string;
  /** 执行详情 */
  detail?: string;
  /** 开始时间 */
  startTime?: string;
  /** 结束时间 */
  endTime?: string;
  /** 错误信息 */
  error?: string;
}

/**
 * 工作流节点类型（继承 React Flow 的 Node）
 */
export type WorkflowNode = Node<WorkflowNodeData>;

/**
 * 工作流边类型
 */
export type WorkflowEdge = Edge;

/**
 * 工作流阶段定义（16 步流程）
 */
export const WORKFLOW_STAGES = [
  {
    id: 'input_analyzer',
    label: '输入分析',
    description: '分析用户输入，识别项目类型和需求',
    agent: '需求分析师'
  },
  {
    id: 'question_generator',
    label: '问题生成',
    description: '生成针对性问题以获取更多信息',
    agent: '需求分析师'
  },
  {
    id: 'requirement_synthesizer',
    label: '需求综合',
    description: '整合用户输入和回答，生成完整需求',
    agent: '需求分析师'
  },
  {
    id: 'expert_team_builder',
    label: '专家团队组建',
    description: '根据需求动态生成专家团队',
    agent: '项目总监'
  },
  {
    id: 'expert_analysis',
    label: '专家分析',
    description: '各领域专家并行分析需求',
    agent: '多个领域专家'
  },
  {
    id: 'integration',
    label: '结果整合',
    description: '整合专家分析结果',
    agent: '项目总监'
  },
  {
    id: 'red_team_review',
    label: '红队评审',
    description: '红队挑战方案中的问题',
    agent: '红队评审员'
  },
  {
    id: 'blue_team_defense',
    label: '蓝队答辩',
    description: '蓝队回应红队挑战',
    agent: '蓝队答辩员'
  },
  {
    id: 'judge_decision',
    label: '评委裁决',
    description: '评委基于红蓝对抗做出裁决',
    agent: '评审委员'
  },
  {
    id: 'client_review',
    label: '甲方审核',
    description: '甲方审核方案并提出修改意见',
    agent: '甲方代表'
  },
  {
    id: 'revision',
    label: '方案修订',
    description: '根据审核意见修订方案',
    agent: '项目总监'
  },
  {
    id: 'final_review',
    label: '最终评审',
    description: '甲方最终确认方案',
    agent: '甲方代表'
  },
  {
    id: 'report_generation',
    label: '报告生成',
    description: '生成结构化分析报告',
    agent: '报告生成器'
  },
  {
    id: 'quality_check',
    label: '质量检查',
    description: '检查报告质量和完整性',
    agent: '质量保证'
  },
  {
    id: 'report_aggregation',
    label: '报告聚合',
    description: '使用 LLM 聚合最终报告',
    agent: 'LLM 聚合器'
  },
  {
    id: 'completion',
    label: '完成',
    description: '工作流完成，输出最终报告',
    agent: '系统'
  }
] as const;

/**
 * 节点位置布局（垂直流程图）
 */
export const getNodePosition = (index: number) => {
  const spacing = 120; // 节点间距
  const startY = 50;
  
  // 计算列（每列最多 4 个节点）
  const col = Math.floor(index / 4);
  const row = index % 4;
  
  return {
    x: 50 + col * 350, // 水平间距 350px
    y: startY + row * spacing
  };
};

/**
 * 创建初始工作流节点
 */
export function createInitialNodes(): WorkflowNode[] {
  return WORKFLOW_STAGES.map((stage, index) => ({
    id: stage.id,
    type: 'workflowNode', // 自定义节点类型
    position: getNodePosition(index),
    data: {
      label: stage.label,
      description: stage.description,
      status: 'pending',
      agent: stage.agent
    }
  }));
}

/**
 * 创建工作流边（定义节点之间的连接）
 */
export function createInitialEdges(): WorkflowEdge[] {
  const edges: WorkflowEdge[] = [];
  
  // 主流程连接
  for (let i = 0; i < WORKFLOW_STAGES.length - 1; i++) {
    edges.push({
      id: `e${i}-${i + 1}`,
      source: WORKFLOW_STAGES[i].id,
      target: WORKFLOW_STAGES[i + 1].id,
      animated: false,
      style: { stroke: '#94a3b8' }
    });
  }
  
  // 可以添加额外的条件分支边
  // 例如：修订 -> 最终评审（如果需要多轮）
  edges.push({
    id: 'e-revision-loop',
    source: 'revision',
    target: 'client_review',
    animated: false,
    style: { stroke: '#f59e0b', strokeDasharray: '5,5' },
    label: '需要再次审核'
  });
  
  return edges;
}

/**
 * 根据节点状态获取样式
 */
export function getNodeStyle(status: NodeStatus) {
  switch (status) {
    case 'pending':
      return {
        background: '#252525',
        border: '1px solid #333',
        color: '#888'
      };
    case 'running':
      return {
        background: '#1e1e1e',
        border: '1px solid #4d6bfe',
        color: '#fff',
        boxShadow: '0 0 15px rgba(77, 107, 254, 0.3)'
      };
    case 'completed':
      return {
        background: '#1e1e1e',
        border: '1px solid #10b981',
        color: '#fff'
      };
    case 'error':
      return {
        background: '#2a1515',
        border: '1px solid #ef4444',
        color: '#fca5a5'
      };
    case 'skipped':
      return {
        background: '#2a2010',
        border: '1px solid #f59e0b',
        color: '#fcd34d'
      };
    default:
      return {};
  }
}
