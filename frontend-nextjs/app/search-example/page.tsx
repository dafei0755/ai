'use client';

/**
 * UCPPT搜索页面集成示例 - v7.270
 *
 * 展示如何在搜索页面中集成新的v7.270功能：
 * 1. 监听新事件（problem_solving_approach_ready, step1_complete, step2_start, step2_complete）
 * 2. 展示解题思路卡片
 * 3. 展示两步流程进度
 */

import React, { useState, useEffect } from 'react';
import { WorkflowRealtimeClient } from '@/lib/workflow-realtime-client';
import { ProblemSolvingApproach } from '@/types';
import ProblemSolvingApproachCard from '@/components/ProblemSolvingApproachCard';
import UcpptSearchProgress, { UcpptSearchPhase } from '@/components/UcpptSearchProgress';

export default function SearchPageExample() {
  // 状态管理
  const [problemSolvingApproach, setProblemSolvingApproach] = useState<ProblemSolvingApproach | null>(null);
  const [currentPhase, setCurrentPhase] = useState<UcpptSearchPhase>('step1');
  const [step1Status, setStep1Status] = useState<'pending' | 'in_progress' | 'completed'>('in_progress');
  const [step2Status, setStep2Status] = useState<'pending' | 'in_progress' | 'completed'>('pending');
  const [searchStatus, setSearchStatus] = useState<'pending' | 'in_progress' | 'completed'>('pending');
  const [messages, setMessages] = useState<string[]>([]);

  useEffect(() => {
    // 创建 WebSocket 连接
    const wsClient = new WorkflowRealtimeClient({
      url: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      sessionId: 'your-session-id', // 替换为实际的 session_id
      onMessage: (message) => {
        console.log('📨 收到消息:', message);

        // 处理新的 v7.270 事件
        // 使用类型断言处理可能的新事件类型
        const msg = message as { type: string; data?: unknown; status?: string };
        switch (msg.type) {
          // ==================== v7.270 新增事件 ====================

          case 'problem_solving_approach_ready':
            // 解题思路就绪
            console.log('🧠 解题思路就绪:', msg.data);
            setProblemSolvingApproach(msg.data as ProblemSolvingApproach);
            addMessage('✅ 解题思路已生成');
            break;

          case 'step1_complete':
            // 第一步完成
            console.log('✅ Step 1 完成:', msg.data);
            setStep1Status('completed');
            setCurrentPhase('step2');
            setStep2Status('in_progress');
            addMessage('✅ 第一步分析完成，开始生成搜索框架...');
            break;

          case 'step2_start':
            // 第二步开始
            console.log('🚀 Step 2 开始:', msg.data);
            setStep2Status('in_progress');
            addMessage(`🚀 ${(msg.data as { message?: string })?.message || '开始生成搜索任务清单...'}`);
            break;

          case 'step2_complete':
            // 第二步完成
            console.log('✅ Step 2 完成:', msg.data);
            setStep2Status('completed');
            setCurrentPhase('searching');
            setSearchStatus('in_progress');
            addMessage(`✅ 搜索框架已生成（${(msg.data as { target_count?: number })?.target_count || 0}个任务）`);
            break;

          // ==================== 其他事件 ====================

          case 'unified_dialogue_chunk':
            // 流式对话内容（第一步的思考过程）
            // 可以实时展示给用户
            break;

          case 'unified_dialogue_complete':
            // 对话完成
            addMessage('💭 深度分析完成');
            break;

          case 'search_framework_ready':
            // 搜索框架就绪（兼容旧流程）
            console.log('📋 搜索框架就绪:', msg.data);
            break;

          case 'status_update':
            // 状态更新
            if (msg.status === 'completed') {
              setSearchStatus('completed');
              addMessage('🎉 搜索完成！');
            }
            break;

          default:
            // 其他消息类型
            break;
        }
      },
      onError: (error) => {
        console.error('❌ WebSocket 错误:', error);
        addMessage('❌ 连接错误');
      },
      onClose: () => {
        console.log('🔌 WebSocket 连接关闭');
        addMessage('🔌 连接已关闭');
      },
    });

    wsClient.connect();

    // 清理
    return () => {
      wsClient.close();
    };
  }, []);

  const addMessage = (msg: string) => {
    setMessages((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* 页面标题 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h1 className="text-2xl font-bold text-gray-900">UCPPT 搜索模式 v7.270</h1>
          <p className="text-gray-600 mt-2">两步流程：需求理解 → 搜索框架生成 → 搜索执行</p>
        </div>

        {/* 进度指示器 */}
        <UcpptSearchProgress
          currentPhase={currentPhase}
          step1Status={step1Status}
          step2Status={step2Status}
          searchStatus={searchStatus}
        />

        {/* 解题思路卡片 */}
        {problemSolvingApproach && (
          <ProblemSolvingApproachCard approach={problemSolvingApproach} />
        )}

        {/* 消息日志 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">事件日志</h2>
          <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
            {messages.length === 0 ? (
              <p className="text-gray-500 text-sm">等待事件...</p>
            ) : (
              <div className="space-y-1">
                {messages.map((msg, index) => (
                  <div key={index} className="text-sm text-gray-700 font-mono">
                    {msg}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 使用说明 */}
        <div className="bg-blue-50 rounded-lg border border-blue-200 p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">集成说明</h3>
          <div className="space-y-2 text-sm text-blue-800">
            <p><strong>1. 监听新事件：</strong></p>
            <ul className="list-disc list-inside ml-4 space-y-1">
              <li><code className="bg-blue-100 px-2 py-0.5 rounded">problem_solving_approach_ready</code> - 解题思路就绪</li>
              <li><code className="bg-blue-100 px-2 py-0.5 rounded">step1_complete</code> - 第一步完成</li>
              <li><code className="bg-blue-100 px-2 py-0.5 rounded">step2_start</code> - 第二步开始</li>
              <li><code className="bg-blue-100 px-2 py-0.5 rounded">step2_complete</code> - 第二步完成</li>
            </ul>
            <p className="mt-3"><strong>2. 展示组件：</strong></p>
            <ul className="list-disc list-inside ml-4 space-y-1">
              <li><code className="bg-blue-100 px-2 py-0.5 rounded">ProblemSolvingApproachCard</code> - 解题思路卡片</li>
              <li><code className="bg-blue-100 px-2 py-0.5 rounded">UcpptSearchProgress</code> - 两步流程进度</li>
            </ul>
            <p className="mt-3"><strong>3. 向后兼容：</strong></p>
            <p className="ml-4">旧流程仍然可用，新事件为可选增强功能</p>
          </div>
        </div>
      </div>
    </div>
  );
}
