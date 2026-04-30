/**
 * 工作流可视化组件
 * 
 * 使用 React Flow 展示 16 步智能项目分析工作流
 * 支持实时状态更新和节点交互
 */

// @ts-nocheck
'use client';

import { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type NodeProps
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  type WorkflowNodeData,
  type NodeStatus,
  createInitialNodes,
  createInitialEdges,
  getNodeStyle
} from '@/types/workflow';

/**
 * 自定义节点组件
 */
function CustomWorkflowNode({ data }: NodeProps<any>) {
  const style = getNodeStyle(data.status);

  // 状态图标
  const statusIcon = ({
    pending: '⏸️',
    running: '▶️',
    completed: '✅',
    error: '❌',
    skipped: '⏭️'
  } as any)[data.status];

  return (
    <div
      className="px-4 py-3 rounded-lg min-w-[200px] cursor-pointer transition-all hover:scale-105"
      style={style}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{statusIcon}</span>
        <span className="font-semibold text-sm">{data.label}</span>
      </div>
      <div className="text-xs opacity-75 mb-2">{data.description}</div>
      {data.agent && (
        <div className="text-xs">
          <span className="opacity-60">Agent:</span> {data.agent}
        </div>
      )}
      {data.detail && (
        <div className="text-xs mt-1 italic">
          {data.detail}
        </div>
      )}
    </div>
  );
}

// 注册自定义节点类型
const nodeTypes = {
  workflowNode: CustomWorkflowNode
};

/**
 * WorkflowDiagram 组件属性
 */
export interface WorkflowDiagramProps {
  /** 当前执行的节点 ID */
  currentNode?: string;
  /** 节点详情映射 */
  nodeDetails?: Record<string, { status: NodeStatus; detail?: string; error?: string }>;
  /** 节点点击回调 */
  onNodeClick?: (nodeId: string) => void;
}

/**
 * 工作流可视化主组件
 */
export function WorkflowDiagram({ currentNode, nodeDetails, onNodeClick }: WorkflowDiagramProps) {
  // 初始化节点和边
  const initialNodes = useMemo(() => createInitialNodes(), []);
  const initialEdges = useMemo(() => createInitialEdges(), []);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes as any);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges as any);

  // 根据外部状态更新节点
  useMemo(() => {
    setNodes((nds: any) =>
      nds.map((node: any) => {
        const detail = nodeDetails?.[node.id];
        let newStatus: NodeStatus = node.data.status as NodeStatus;

        // 确定节点状态
        if (detail) {
          newStatus = detail.status;
        } else if (node.id === currentNode) {
          newStatus = 'running';
        }

        return {
          ...node,
          data: {
            ...node.data,
            status: newStatus,
            detail: detail?.detail,
            error: detail?.error
          }
        };
      })
    );

    // 更新边的动画（当前节点的输入边）
    if (currentNode) {
      setEdges((eds) =>
        eds.map((edge) => ({
          ...edge,
          animated: edge.target === currentNode
        }))
      );
    }
  }, [currentNode, nodeDetails, setNodes, setEdges]);

  // 节点点击处理
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: any) => {
      onNodeClick?.(node.id);
    },
    [onNodeClick]
  );

  return (
    <div className="w-full h-full bg-[var(--sidebar-bg)]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
        colorMode="dark"
      >
        {/* 背景网格 */}
        <Background color="#333" gap={16} />
        
        {/* 控制按钮（缩放、适应视图等） */}
        <Controls className="bg-[var(--card-bg)] border-[var(--border-color)] fill-white text-white" />
        
        {/* 小地图 */}
        <MiniMap
          nodeColor={(node) => {
            const data = node.data as WorkflowNodeData;
            switch (data.status) {
              case 'running':
                return '#4d6bfe';
              case 'completed':
                return '#10b981';
              case 'error':
                return '#ef4444';
              default:
                return '#333';
            }
          }}
          maskColor="rgba(0, 0, 0, 0.3)"
          position="bottom-right"
          className="bg-[var(--card-bg)] border border-[var(--border-color)]"
        />
      </ReactFlow>
    </div>
  );
}
