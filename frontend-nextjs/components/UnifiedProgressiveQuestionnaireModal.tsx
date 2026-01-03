// components/UnifiedProgressiveQuestionnaireModal.tsx
// v7.105: 统一的三步递进式问卷组件 - 连续流畅的用户体验
// 特性：步骤指示器、平滑过渡动画、统一UI风格、localStorage缓存、必填字段验证
// v7.112: 集成骨架屏加载动画，优化确认等待体验

'use client';

import { CheckCircle2, ArrowRight } from 'lucide-react';
import { useState, useEffect } from 'react';
import { Radar } from 'react-chartjs-2';
import NProgress from 'nprogress';
import 'nprogress/nprogress.css';
import QuestionnaireSkeletonLoader from './QuestionnaireSkeletonLoader';
import {
  saveQuestionnaireCache,
  getQuestionnaireCache,
  clearQuestionnaireCache
} from '@/lib/questionnaire-cache';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

interface UnifiedProgressiveQuestionnaireModalProps {
  isOpen: boolean;
  currentStep: number; // 1, 2, 3
  step1Data?: any;
  step2Data?: any;
  step3Data?: any;
  onStep1Confirm: (data?: { extracted_tasks?: EditableTask[] }) => void;
  onStep2Confirm: (data: any) => void;
  onStep3Confirm: (data: any) => void;
  sessionId?: string;
}

interface EditableTask {
  // === 现有字段（保留）===
  id?: string;
  title: string;
  description: string;
  source_keywords?: string[];
  isEditing?: boolean;
  isNew?: boolean;

  // === 🆕 v7.105-v7.106 新增字段 ===
  motivation_type?:
    // 原有5类
    | 'functional' | 'emotional' | 'aesthetic' | 'social' | 'mixed'
    // 🆕 v7.106 新增7类
    | 'cultural' | 'commercial' | 'wellness' | 'technical'
    | 'sustainable' | 'professional' | 'inclusive';
  motivation_label?: string;        // 中文标签
  ai_reasoning?: string;            // AI推理说明
  confidence_score?: number;        // 置信度 (0-1)
  execution_order?: number;         // 执行顺序
  dependencies?: string[];          // 依赖任务ID
  expected_output?: string;         // 预期产出
  task_type?: string;               // 任务类型
  priority?: string;                // 优先级
}

interface EditableQuestion {
  id: string;
  type: string;
  question: string;
  options?: string[];
  userAnswer?: string | string[];
}

export function UnifiedProgressiveQuestionnaireModal({
  isOpen,
  currentStep,
  step1Data,
  step2Data,
  step3Data,
  onStep1Confirm,
  onStep2Confirm,
  onStep3Confirm,
  sessionId = 'default'
}: UnifiedProgressiveQuestionnaireModalProps) {
  const [dimensionValues, setDimensionValues] = useState<Record<string, number>>({});
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isLoading, setIsLoading] = useState(false); // 骨架屏加载状态
  const [loadingMessage, setLoadingMessage] = useState('AI 正在智能分析...');

  // 任务编辑状态
  const [editedTasks, setEditedTasks] = useState<EditableTask[]>([]);
  const [originalTasksCount, setOriginalTasksCount] = useState(0);
  const [isSummaryExpanded, setIsSummaryExpanded] = useState(false); // 需求摘要折叠状态

  // 当步骤数据更新时，停止加载状态
  useEffect(() => {
    if (currentStep === 1 && step1Data?.extracted_tasks) {
      setIsLoading(false);
      NProgress.done();
    } else if (currentStep === 2 && step2Data?.dimensions) {
      setIsLoading(false);
      NProgress.done();
    } else if (currentStep === 3 && step3Data?.questionnaire) {
      setIsLoading(false);
      NProgress.done();
    }
  }, [currentStep, step1Data, step2Data, step3Data]);

  // 初始化任务列表
  useEffect(() => {
    if (step1Data?.extracted_tasks && isOpen && currentStep === 1) {
      // 尝试从localStorage恢复草稿
      try {
        const draftKey = `questionnaire-tasks-draft-${sessionId}`;
        const cached = localStorage.getItem(draftKey);
        if (cached) {
          const parsed = JSON.parse(cached);
          const cacheTime = parsed.timestamp || 0;
          // 1小时有效期
          if (Date.now() - cacheTime < 3600000) {
            setEditedTasks(parsed.tasks);
            setOriginalTasksCount(step1Data.extracted_tasks.length);
            return;
          }
        }
      } catch (e) {
        console.warn('Failed to restore task draft:', e);
      }

      // 没有缓存，使用原始数据
      setEditedTasks(step1Data.extracted_tasks.map((task: any) => ({
        // 现有字段 (v7.0)
        id: task.id,
        title: task.title || '',
        description: task.description || '',
        source_keywords: task.source_keywords || [],
        isEditing: false,
        isNew: false,

        // 🆕 v7.105 新增字段 - 完整复制（修复：问卷第一步不显示新字段）
        motivation_type: task.motivation_type,
        motivation_label: task.motivation_label,
        ai_reasoning: task.ai_reasoning,
        confidence_score: task.confidence_score,
        execution_order: task.execution_order,
        dependencies: task.dependencies || [],
        expected_output: task.expected_output,

        // 其他基础字段
        task_type: task.task_type,
        priority: task.priority
      })));
      setOriginalTasksCount(step1Data.extracted_tasks.length);
    }
  }, [step1Data?.extracted_tasks, isOpen, currentStep, sessionId]);

  // 自动保存任务草稿到localStorage
  useEffect(() => {
    if (sessionId && editedTasks.length > 0 && currentStep === 1 && isOpen) {
      try {
        const draftKey = `questionnaire-tasks-draft-${sessionId}`;
        localStorage.setItem(draftKey, JSON.stringify({
          tasks: editedTasks,
          timestamp: Date.now()
        }));
      } catch (e) {
        console.warn('Failed to save task draft:', e);
      }
    }
  }, [editedTasks, sessionId, currentStep, isOpen]);

  // 配置 NProgress
  useEffect(() => {
    NProgress.configure({ showSpinner: false, minimum: 0.08, easing: 'ease', speed: 300 });
  }, []);

  // 步骤切换时触发短暂过渡动画（200ms）
  useEffect(() => {
    if (isOpen) {
      setIsTransitioning(true);
      const timer = setTimeout(() => setIsTransitioning(false), 200);
      return () => clearTimeout(timer);
    }
  }, [currentStep, isOpen]);

  // 加载缓存
  useEffect(() => {
    if (sessionId && isOpen) {
      const cached = getQuestionnaireCache(sessionId);
      if (cached) {
        if (cached.dimensionValues) setDimensionValues(cached.dimensionValues);
        if (cached.answers) setAnswers(cached.answers);
      }
    }
  }, [sessionId, isOpen]);

  // 自动保存缓存
  useEffect(() => {
    if (sessionId && Object.keys(dimensionValues).length > 0 && isOpen) {
      saveQuestionnaireCache(sessionId, { step: 2, dimensionValues });
    }
  }, [dimensionValues, sessionId, isOpen]);

  useEffect(() => {
    if (sessionId && Object.keys(answers).length > 0 && isOpen) {
      saveQuestionnaireCache(sessionId, { step: 3, answers });
    }
  }, [answers, sessionId, isOpen]);

  // 初始化维度默认值
  useEffect(() => {
    if (step2Data?.dimensions && step2Data.dimensions.length > 0 && Object.keys(dimensionValues).length === 0) {
      const initialValues: Record<string, number> = {};
      step2Data.dimensions.forEach((dim: any) => {
        initialValues[dim.id || dim.dimension_id] = dim.default_value || 50;
      });
      setDimensionValues(initialValues);
    }
  }, [step2Data?.dimensions, dimensionValues]);

  // 调试：打印Step3问题数据 & 标准化类型
  useEffect(() => {
    if (currentStep === 3 && step3Data?.questionnaire?.questions) {
      console.log('🔍 Step3 Questions Debug:', step3Data.questionnaire.questions);

      // 🔧 标准化问题类型（修复 multi_choice -> multiple_choice）
      step3Data.questionnaire.questions = step3Data.questionnaire.questions.map((q: any) => {
        let normalizedType = q.type?.toLowerCase() || 'open_ended';

        // 修复常见的类型错误
        if (normalizedType === 'multi_choice' || normalizedType === 'multi-choice') {
          normalizedType = 'multiple_choice';
        } else if (normalizedType === 'single' || normalizedType === 'radio') {
          normalizedType = 'single_choice';
        } else if (normalizedType === 'text' || normalizedType === 'textarea' || normalizedType === 'open') {
          normalizedType = 'open_ended';
        }

        // 只允许三种有效类型
        const validTypes = ['single_choice', 'multiple_choice', 'open_ended'];
        if (!validTypes.includes(normalizedType)) {
          console.warn(`⚠️ 未知问题类型 "${q.type}" 已修正为 "open_ended"`);
          normalizedType = 'open_ended';
        }

        return { ...q, type: normalizedType };
      });

      step3Data.questionnaire.questions.forEach((q: any, index: number) => {
        console.log(`  Question ${index + 1}:`, {
          id: q.id,
          question: q.question,
          type: q.type,
          hasOptions: !!q.options,
          optionsCount: q.options?.length || 0,
          isRequired: q.is_required
        });
      });
    }
  }, [currentStep, step3Data]);

  if (!isOpen) return null;

  const getCurrentData = () => {
    switch (currentStep) {
      case 1: return step1Data;
      case 2: return step2Data;
      case 3: return step3Data;
      default: return null;
    }
  };

  const data = getCurrentData();
  if (!data) return null;

  const { title, message } = data;

  // 步骤配置
  const steps = [
    { number: 1, label: '任务梳理', icon: '1' },
    { number: 2, label: '偏好雷达图', icon: '2' },
    { number: 3, label: '信息补全', icon: '3' }
  ];

  // 验证Step 3必填字段
  const validateStep3Required = (): boolean => {
    if (currentStep !== 3 || !step3Data?.questionnaire?.questions) return true;

    const requiredQuestions = step3Data.questionnaire.questions.filter((q: any) => q.is_required);
    for (const q of requiredQuestions) {
      const answer = answers[q.id];
      if (!answer || (Array.isArray(answer) && answer.length === 0) || (typeof answer === 'string' && answer.trim() === '')) {
        return false;
      }
    }
    return true;
  };

  // 处理确认
  const handleConfirm = () => {
    // Step 3验证必填字段
    if (currentStep === 3 && !validateStep3Required()) {
      alert('请完成所有必填项（标记 * 的问题）');
      return;
    }

    // 启动加载状态和进度条
    setIsLoading(true);
    NProgress.start();

    // 设置加载提示文案
    if (currentStep === 1) {
      setLoadingMessage('AI 正在智能拆解任务...');
    } else if (currentStep === 2) {
      setLoadingMessage('正在生成多维度问卷...');
    } else {
      setLoadingMessage('正在提交问卷数据...');
    }

    // 立即执行，无延迟
    if (currentStep === 1) {
      // 检查是否有任务正在编辑
      const hasEditing = editedTasks.some(t => t.isEditing);
      if (hasEditing) {
        alert('请先完成任务编辑');
        setIsLoading(false);
        NProgress.done();
        return;
      }

      // 过滤掉未完成的新任务
      const validTasks = editedTasks.filter(t => !t.isEditing);

      // 检查是否有修改
      const hasModifications = validTasks.length !== originalTasksCount ||
        validTasks.some(t => t.isNew);

      if (hasModifications) {
        // 清除草稿缓存
        try {
          localStorage.removeItem(`questionnaire-tasks-draft-${sessionId}`);
        } catch (e) {
          console.warn('Failed to clear task draft:', e);
        }

        // 将修改后的任务传递给后端
        onStep1Confirm({ extracted_tasks: validTasks });
      } else {
        onStep1Confirm();
      }
    } else if (currentStep === 2) {
      onStep2Confirm({ dimension_values: dimensionValues });
    } else if (currentStep === 3) {
      clearQuestionnaireCache(sessionId);
      onStep3Confirm({ answers });
    }
  };

  // 获取确认按钮文本
  const getConfirmButtonText = () => {
    if (currentStep === 1) {
      const validTasks = editedTasks.filter(t => !t.isEditing);
      const addedCount = validTasks.filter(t => t.isNew).length;
      const deletedCount = originalTasksCount - (validTasks.length - addedCount);
      const modifiedCount = addedCount + deletedCount;

      if (modifiedCount > 0) {
        return `保存修改并继续（${modifiedCount}处修改）`;
      }
      return '确认任务列表';
    }

    switch (currentStep) {
      case 2: return '确认偏好设置';
      case 3: return '提交问卷';
      default: return '确认';
    }
  };

  // 任务编辑相关函数
  const handleEditTask = (index: number) => {
    setEditedTasks(prev => prev.map((t, i) =>
      i === index ? { ...t, isEditing: true } : t
    ));
  };

  const handleSaveTask = (index: number) => {
    const task = editedTasks[index];

    // 验证
    if (!task.title || task.title.trim().length < 5) {
      alert('任务标题至少需要5个字符');
      return;
    }
    if (!task.description || task.description.trim().length < 20) {
      alert('任务描述至少需要20个字符');
      return;
    }

    setEditedTasks(prev => prev.map((t, i) =>
      i === index ? { ...t, isEditing: false } : t
    ));
  };

  const handleCancelEdit = (index: number) => {
    const task = editedTasks[index];
    if (task.isNew) {
      // 删除未完成的新任务
      setEditedTasks(prev => prev.filter((_, i) => i !== index));
    } else {
      // 恢复原始数据
      const originalTask = step1Data?.extracted_tasks?.[index];
      if (originalTask) {
        setEditedTasks(prev => prev.map((t, i) =>
          i === index ? { ...originalTask, isEditing: false, isNew: false } : t
        ));
      }
    }
  };

  const handleDeleteTask = (index: number) => {
    if (editedTasks.length <= 1) {
      alert('至少需要保留1个任务');
      return;
    }

    if (confirm('确定要删除这个任务吗？')) {
      setEditedTasks(prev => prev.filter((_, i) => i !== index));
    }
  };

  const handleAddTask = () => {
    if (editedTasks.length >= 15) {
      alert('最多只能添加15个任务');
      return;
    }

    const newTask: EditableTask = {
      title: '',
      description: '',
      source_keywords: [],
      isEditing: true,
      isNew: true
    };

    setEditedTasks(prev => [...prev, newTask]);

    // 滚动到底部
    setTimeout(() => {
      const container = document.querySelector('.task-list-container');
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }, 100);
  };

  const updateTaskField = (index: number, field: keyof EditableTask, value: any) => {
    setEditedTasks(prev => prev.map((t, i) =>
      i === index ? { ...t, [field]: value } : t
    ));
  };

  // 渲染 Step 1
  const renderStep1Content = () => {
    const { user_input_summary } = step1Data || {};

    // 计算修改统计
    const validTasks = editedTasks.filter(t => !t.isEditing);
    const addedCount = validTasks.filter(t => t.isNew).length;
    const deletedCount = originalTasksCount - (validTasks.length - addedCount);

    const summaryPreview = user_input_summary?.length > 50
      ? user_input_summary.substring(0, 50) + '...'
      : user_input_summary;

    return (
      <div className="space-y-4">
        {/* 任务列表 */}}
        <div className="task-list-container space-y-6">
          {editedTasks.map((task, index) => {
            const isEditing = task.isEditing;
            const isNew = task.isNew;

            return (
              <div
                key={index}
                className={`relative group bg-white border rounded-xl p-4 transition-all duration-200 ${
                  isNew ? 'border-l-4 border-l-green-500 border-r border-r-gray-200 border-t border-t-gray-200 border-b border-b-gray-200' : 'border-gray-200'
                } ${isEditing ? 'ring-2 ring-blue-300 shadow-lg' : 'hover:shadow-md'}`}
              >
                {/* 新增任务标记 */}
                {isNew && !isEditing && (
                  <div className="absolute top-2 right-2 px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                    新增
                  </div>
                )}

                {isEditing ? (
                  // 编辑模式
                  <div className="space-y-4">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-gray-100 text-gray-600 rounded-lg flex items-center justify-center text-sm font-medium">
                        {index + 1}
                      </div>
                      <div className="flex-1 space-y-3">
                        {/* 标题输入 */}
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">
                            任务标题 <span className="text-red-500">*</span>
                            <span className="ml-2 text-gray-500">（至少5个字符）</span>
                          </label>
                          <input
                            type="text"
                            value={task.title}
                            onChange={(e) => updateTaskField(index, 'title', e.target.value)}
                            placeholder="输入任务标题..."
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm text-gray-900 placeholder:text-gray-400"
                          />
                          <div className="mt-1 text-xs text-gray-500">
                            {task.title.length}/5
                          </div>
                        </div>

                        {/* 描述输入 */}
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">
                            任务描述 <span className="text-red-500">*</span>
                            <span className="ml-2 text-gray-500">（至少20个字符）</span>
                          </label>
                          <textarea
                            value={task.description}
                            onChange={(e) => updateTaskField(index, 'description', e.target.value)}
                            placeholder="详细描述任务内容..."
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm text-gray-900 placeholder:text-gray-400 resize-none"
                            rows={3}
                          />
                          <div className="mt-1 text-xs text-gray-500">
                            {task.description.length}/20
                          </div>
                        </div>

                        {/* 操作按钮 */}
                        <div className="flex items-center gap-2 pt-2">
                          <button
                            onClick={() => handleSaveTask(index)}
                            disabled={task.title.trim().length < 5 || task.description.trim().length < 20}
                            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            保存
                          </button>
                          <button
                            onClick={() => handleCancelEdit(index)}
                            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm rounded-lg transition-colors"
                          >
                            取消
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  // 查看模式
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-8 h-8 bg-gray-100 text-gray-600 rounded-lg flex items-center justify-center text-sm font-medium">
                      {index + 1}
                    </div>
                    <div className="flex-1 min-w-0 space-y-2">
                      {/* 标题行：需求分类 + 标题 */}
                      <div className="flex items-center gap-2 flex-wrap">
                        {/* 动机类型标签 */}
                        {task.motivation_label && (
                          <span className={`px-2 py-0.5 text-xs font-medium rounded-full flex-shrink-0 ${
                            task.motivation_type === 'functional' ? 'bg-blue-100 text-blue-700' :
                            task.motivation_type === 'emotional' ? 'bg-pink-100 text-pink-700' :
                            task.motivation_type === 'aesthetic' ? 'bg-purple-100 text-purple-700' :
                            task.motivation_type === 'social' ? 'bg-green-100 text-green-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {task.motivation_label}
                          </span>
                        )}

                        {/* 任务标题 */}
                        <h4 className="font-medium text-gray-900 flex-1 min-w-0">
                          {task.title}
                        </h4>

                        {/* 置信度提示（低于0.7时显示） */}
                        {task.confidence_score && task.confidence_score < 0.7 && (
                          <div className="flex items-center gap-1 text-xs text-amber-600 flex-shrink-0">
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                            </svg>
                            <span>待确认</span>
                          </div>
                        )}
                      </div>

                      {/* 任务描述 */}
                      <p className="text-sm text-gray-600 leading-relaxed">
                        {task.description}
                      </p>

                      {/* 🆕 v7.105: AI推理说明 + 关键词 */}
                      {(task.ai_reasoning || (task.source_keywords && task.source_keywords.length > 0)) && (
                        <div className="p-3 bg-blue-50/50 border-l-2 border-blue-400 rounded">
                          <div className="flex items-start gap-2">
                            <svg className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                            </svg>
                            <div className="flex-1 space-y-2">
                              {task.ai_reasoning && (
                                <p className="text-xs text-gray-700 leading-relaxed">{task.ai_reasoning}</p>
                              )}
                              {task.source_keywords && task.source_keywords.length > 0 && (
                                <div className="flex flex-wrap gap-1.5">
                                  {task.source_keywords.map((keyword: string, idx: number) => (
                                    <span
                                      key={idx}
                                      className="px-2 py-0.5 bg-blue-100 text-blue-600 text-xs rounded-full"
                                    >
                                      {keyword}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* 🆕 v7.105: 依赖关系 */}
                      {task.dependencies && task.dependencies.length > 0 && (
                        <div className="flex items-start gap-2 text-xs text-gray-600">
                          <svg className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                          </svg>
                          <div className="flex-1">
                            <span className="font-medium">依赖任务：</span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {task.dependencies.map((depId: string, idx: number) => {
                                const depTask = editedTasks.find(t => t.id === depId);
                                return depTask ? (
                                  <span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded-full">
                                    #{depTask.execution_order || '?'} {depTask.title}
                                  </span>
                                ) : null;
                              })}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* 🆕 v7.105: 预期产出 */}
                      {task.expected_output && (
                        <div className="flex items-center gap-2 text-xs text-gray-600">
                          <svg className="w-4 h-4 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0015.414 6L12 2.586A2 2 0 0010.586 2H6zm5 6a1 1 0 10-2 0v3.586l-1.293-1.293a1 1 0 10-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 11.586V8z" clipRule="evenodd" />
                          </svg>
                          <span className="font-medium">预期产出：</span>
                          <span className="text-gray-700">{task.expected_output}</span>
                        </div>
                      )}
                    </div>

                    {/* 编辑/删除按钮 - 已有任务只显示编辑，新增任务显示编辑和删除 */}
                    <div className="flex-shrink-0 flex items-center gap-2">
                      <button
                        onClick={() => handleEditTask(index)}
                        className="p-1.5 bg-blue-50 hover:bg-blue-600 text-blue-600 hover:text-white rounded-lg transition-all duration-200 hover:shadow-md"
                        title="编辑任务"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      {/* 删除按钮仅对新增任务显示 */}
                      {isNew && (
                        <button
                          onClick={() => handleDeleteTask(index)}
                          className="p-1.5 bg-red-50 hover:bg-red-600 text-red-600 hover:text-white rounded-lg transition-all duration-200 hover:shadow-md"
                          title="删除任务"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* 添加任务按钮 */}
        <button
          onClick={handleAddTask}
          disabled={editedTasks.length >= 15}
          className="w-full py-3 mt-48 mb-32 border-2 border-dashed border-gray-300 hover:border-blue-400 hover:bg-blue-50 rounded-xl text-sm text-gray-600 hover:text-blue-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:border-gray-300 disabled:hover:bg-transparent disabled:hover:text-gray-600"
        >
          + 添加新任务 {editedTasks.length >= 15 && '（已达上限）'}
        </button>
      </div>
    );
  };

  // 渲染 Step 2
  const renderStep2Content = () => {
    const { dimensions } = step2Data || {};
    if (!dimensions || dimensions.length === 0) return null;

    const chartData = {
      labels: dimensions.map((d: any) => d.name || d.dimension_name),
      datasets: [
        {
          label: '偏好评分',
          data: dimensions.map((d: any) => dimensionValues[d.id || d.dimension_id] || 50),
          backgroundColor: 'rgba(59, 130, 246, 0.2)',
          borderColor: 'rgb(59, 130, 246)',
          borderWidth: 2,
          pointBackgroundColor: 'rgb(59, 130, 246)',
          pointBorderColor: '#fff',
          pointHoverBackgroundColor: '#fff',
          pointHoverBorderColor: 'rgb(59, 130, 246)',
          pointRadius: 4,
          pointHoverRadius: 6
        }
      ]
    };

    const chartOptions: any = {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          min: 0,
          max: 100,
          ticks: { stepSize: 20, display: false },
          pointLabels: {
            font: { size: 12, weight: 'bold' as const },
            color: 'rgb(75, 85, 99)'
          },
          grid: { color: 'rgba(156, 163, 175, 0.3)' },
          angleLines: { color: 'rgba(156, 163, 175, 0.3)' }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true }
      }
    };

    return (
      <div className="space-y-6">
        <div className="grid md:grid-cols-2 gap-6">
          {/* 左侧：固定雷达图 */}
          <div className="md:sticky md:top-0 md:self-start">
            <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
              <h3 className="text-base font-medium text-gray-900 mb-4 text-center">
                偏好雷达图
              </h3>
              <div className="h-80">
                <Radar data={chartData} options={chartOptions} />
              </div>
            </div>
          </div>

      {/* 右侧：滑块列表 */}
      <div className="space-y-4">
        {dimensions.map((dim: any, index: number) => {
          const dimId = dim.id || dim.dimension_id;
          const value = dimensionValues[dimId] || 50;

          return (
                <div key={dimId} className="bg-white border border-gray-200 rounded-xl p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-lg flex items-center justify-center text-xs font-medium">
                        {index + 1}
                      </span>
                      <span className="text-sm font-medium text-gray-900">
                        {dim.name || dim.dimension_name}
                      </span>
                    </div>
                    <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-1 rounded-full">
                      {value}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-xs text-gray-500 mb-2">
                    <span>{dim.left_label}</span>
                    <div className="flex-1 h-px bg-gray-300"></div>
                    <span>{dim.right_label}</span>
                  </div>

                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={value}
                    onChange={(e) => setDimensionValues(prev => ({ ...prev, [dimId]: parseInt(e.target.value) }))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                  />

                  {/* 阶段说明 */}
                  {dim.description && (
                    <p className="text-xs text-gray-500 mt-3">
                      {dim.description}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  // 渲染 Step 3
  const renderStep3Content = () => {
    const { questionnaire } = step3Data || {};
    if (!questionnaire) return null;

    const { introduction, questions, note } = questionnaire;

    return (
      <div className="space-y-6">
        {introduction && (
          <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
            <p className="text-sm text-gray-600">{introduction}</p>
          </div>
        )}

        {/* 必填/选填说明 */}
        <div className="flex items-center justify-between gap-4 px-4 py-3 bg-blue-50 rounded-lg border border-blue-200">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 bg-red-500 rounded flex items-center justify-center">
                <span className="text-white text-xs font-bold">*</span>
              </div>
              <span className="text-sm font-medium text-gray-900">必填项</span>
              <span className="text-xs text-gray-600">- 关键信息，影响分析质量</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 bg-gray-300 rounded flex items-center justify-center">
                <span className="text-gray-600 text-xs">?</span>
              </div>
              <span className="text-sm font-medium text-gray-900">选填项</span>
              <span className="text-xs text-gray-600">- 补充信息，帮助优化方案</span>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          {questions && questions.map((q: any, index: number) => {
            const isRequired = q.is_required;

            return (
              <div
                key={q.id || index}
                className={`rounded-xl p-5 transition-all ${
                  isRequired
                    ? 'bg-white border-2 border-red-200 shadow-sm'
                    : 'bg-gray-50 border border-gray-200 opacity-90'
                }`}
              >
                {/* 问题头部 */}
                <div className="flex items-start gap-3 mb-3">
                  {/* 序号徽章 */}
                  <div className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-xs font-medium ${
                    isRequired
                      ? 'bg-red-500 text-white shadow-sm'
                      : 'bg-gray-300 text-gray-600'
                  }`}>
                    {index + 1}
                  </div>

                  <div className="flex-1">
                    {/* 问题标题 */}
                    <h4 className="font-medium text-gray-900 mb-1">
                      {q.question}
                    </h4>

                    {/* 问题上下文 */}
                    {q.context && (
                      <p className="text-xs text-gray-500 italic leading-relaxed">
                        {q.context}
                      </p>
                    )}
                  </div>
                </div>

                {/* 问题输入区域 */}
                {q.type === 'single_choice' && q.options && (
                  <div className="space-y-2 ml-10">
                    {q.options.map((option: string, optIdx: number) => (
                      <label
                        key={optIdx}
                        className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors"
                      >
                        <input
                          type="radio"
                          name={q.id}
                          value={option}
                          checked={answers[q.id] === option}
                          onChange={(e) => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                          className="w-4 h-4 text-blue-600 accent-blue-600"
                        />
                        <span className="text-sm text-gray-900">{option}</span>
                      </label>
                    ))}
                  </div>
                )}

                {q.type === 'multiple_choice' && q.options && (
                  <div className="space-y-2 ml-10">
                    {q.options.map((option: string, optIdx: number) => (
                      <label
                        key={optIdx}
                        className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors"
                      >
                        <input
                          type="checkbox"
                          value={option}
                          checked={Array.isArray(answers[q.id]) && answers[q.id].includes(option)}
                          onChange={(e) => {
                            const current = answers[q.id] || [];
                            const updated = e.target.checked
                              ? [...current, option]
                              : current.filter((v: string) => v !== option);
                            setAnswers(prev => ({ ...prev, [q.id]: updated }));
                          }}
                          className="w-4 h-4 text-blue-600 rounded accent-blue-600"
                        />
                        <span className="text-sm text-gray-900">{option}</span>
                      </label>
                    ))}
                  </div>
                )}

                {q.type === 'open_ended' && (
                  <div className="ml-10">
                    <textarea
                      placeholder={q.placeholder || '请输入您的回答...'}
                      value={answers[q.id] || ''}
                      onChange={(e) => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900 resize-none"
                      rows={3}
                    />
                  </div>
                )}

                {/* 默认处理：如果类型未匹配，显示文本输入框 */}
                {!['single_choice', 'multiple_choice', 'open_ended'].includes(q.type) && (
                  <div className="ml-10">
                    <textarea
                      placeholder={q.placeholder || '请输入您的回答...'}
                      value={answers[q.id] || ''}
                      onChange={(e) => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900 resize-none"
                      rows={3}
                    />
                    {/* 开发环境下显示类型警告 */}
                    {process.env.NODE_ENV === 'development' && (
                      <p className="text-xs text-orange-600 mt-2 bg-orange-50 border border-orange-200 rounded px-2 py-1">
                        ⚠️ 系统检测到未知问题类型 &ldquo;{q.type}&rdquo;，已自动使用文本输入框
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {note && (
          <div className="text-xs text-gray-600 italic bg-blue-50 rounded-lg p-3">
            {note}
          </div>
        )}
      </div>
    );
  };

  // 渲染当前步骤内容
  const renderContent = () => {
    // 如果正在加载，显示骨架屏
    if (isLoading) {
      const skeletonType = currentStep === 1 ? 'tasks' : currentStep === 2 ? 'radar' : 'both';
      return <QuestionnaireSkeletonLoader type={skeletonType} message={loadingMessage} />;
    }

    switch (currentStep) {
      case 1: return renderStep1Content();
      case 2: return renderStep2Content();
      case 3: return renderStep3Content();
      default: return null;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      {isLoading ? (
        // 加载页面 - 保持步骤一致性
        <div className="bg-white rounded-2xl max-w-6xl w-full h-[85vh] overflow-hidden flex flex-col shadow-2xl border border-gray-200">

          {/* 步骤指示器 */}
          <div className="border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4">
            <div className="flex items-center justify-between mb-4">
              {steps.map((step, index) => (
                <div key={step.number} className="flex items-center flex-1">
                  <div className="flex flex-col items-center flex-1">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center text-lg font-medium transition-all duration-300 ${
                      currentStep === step.number
                        ? 'bg-blue-600 text-white shadow-lg scale-110'
                        : currentStep > step.number
                        ? 'bg-green-500 text-white'
                        : 'bg-gray-100 text-gray-400 border-2 border-gray-300'
                    }`}>
                      {currentStep > step.number ? (
                        <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        step.number
                      )}
                    </div>
                    <span className={`mt-2 text-sm font-medium ${
                      currentStep === step.number ? 'text-blue-600' : 'text-gray-500'
                    }`}>
                      {step.label}
                    </span>
                  </div>

                  {index < steps.length - 1 && (
                    <div className={`h-1 flex-1 mx-4 rounded transition-all duration-500 ${
                      currentStep > step.number ? 'bg-green-500' : 'bg-gray-300'
                    }`} />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Header - 需求显示 */}
          <div className="border-b border-gray-200 px-6 py-3 bg-white">
            {(step1Data?.user_input_summary || step2Data?.user_input_summary || step3Data?.user_input_summary) && (
              <div
                className="flex items-start gap-2 cursor-pointer hover:bg-gray-50 rounded-lg p-3 -m-2 transition-colors"
                onClick={() => setIsSummaryExpanded(!isSummaryExpanded)}
              >
                <span className="text-sm font-medium text-blue-600 flex-shrink-0">需求：</span>
                <div className="flex-1 min-w-0">
                  <span className={`text-sm leading-relaxed text-gray-600 ${isSummaryExpanded ? '' : 'line-clamp-6'}`}>
                    {step1Data?.user_input_summary || step2Data?.user_input_summary || step3Data?.user_input_summary}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* 加载内容区域 */}
          <div className="flex-1 flex items-center justify-center p-12">
            <div className="flex flex-col items-center justify-center space-y-6">
              {/* 加载动画 */}
              <svg
                className="animate-spin h-16 w-16 text-blue-500"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>

              {/* 加载提示文字 */}
              <div className="text-center space-y-2">
                <p className="text-lg font-medium text-gray-900">{loadingMessage}</p>
                <p className="text-sm text-gray-500">请稍候，AI 正在智能分析您的需求...</p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        // 正常的问卷界面
      <div className="bg-white rounded-2xl max-w-6xl w-full h-[85vh] overflow-hidden flex flex-col shadow-2xl border border-gray-200">

        {/* 步骤指示器 */}
        <div className="border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            {steps.map((step, index) => (
              <div key={step.number} className="flex items-center flex-1">
                <div className="flex flex-col items-center flex-1">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center text-lg font-medium transition-all duration-300 ${
                    currentStep === step.number
                      ? 'bg-blue-600 text-white shadow-lg scale-110'
                      : currentStep > step.number
                      ? 'bg-green-500 text-white'
                      : 'bg-gray-100 text-gray-400 border-2 border-gray-300'
                  }`}>
                    {currentStep > step.number ? '✓' : step.icon}
                  </div>
                  <div className={`mt-2 text-xs font-medium text-center transition-colors ${
                    currentStep === step.number
                      ? 'text-blue-600'
                      : currentStep > step.number
                      ? 'text-green-500'
                      : 'text-gray-500'
                  }`}>
                    {step.label}
                  </div>
                </div>
                {index < steps.length - 1 && (
                  <div className={`h-1 flex-1 mx-2 rounded-full transition-all duration-500 ${
                    currentStep > step.number
                      ? 'bg-green-500'
                      : 'bg-gray-300'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Header */}
        <div className="border-b border-gray-200 px-6 py-3 bg-white">
          {/* 固定需求显示 - 所有步骤通用（优先显示完整user_input，回退到摘要） */}
          {(step1Data?.user_input || step1Data?.user_input_summary ||
            step2Data?.user_input || step2Data?.user_input_summary ||
            step3Data?.user_input || step3Data?.user_input_summary) && (
            <div
              className="flex items-start gap-2 cursor-pointer hover:bg-gray-50 rounded-lg p-3 -m-2 transition-colors"
              onClick={() => setIsSummaryExpanded(!isSummaryExpanded)}
            >
              <span className="text-sm font-medium text-blue-600 flex-shrink-0">需求：</span>
              <div className="flex-1 min-w-0">
                <span className={`text-sm leading-relaxed text-gray-600 ${isSummaryExpanded ? '' : 'line-clamp-6'}`}>
                  {step1Data?.user_input || step1Data?.user_input_summary ||
                   step2Data?.user_input || step2Data?.user_input_summary ||
                   step3Data?.user_input || step3Data?.user_input_summary}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-4 bg-gray-50">
          <div className={`transition-all duration-200 ${isTransitioning ? 'opacity-0 translate-y-2' : 'opacity-100 translate-y-0'}`}>
            {renderContent()}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 px-6 py-4 bg-white flex items-center justify-end gap-3">
          <button
            onClick={handleConfirm}
            disabled={currentStep === 3 && !validateStep3Required()}
            className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>{getConfirmButtonText()}</span>
            {currentStep < 3 && <ArrowRight className="w-4 h-4" />}
          </button>
        </div>
      </div>
      )}
    </div>
  );
}
