// components/UnifiedProgressiveQuestionnaireModal.tsx
// v7.105: 统一的三步递进式问卷组件 - 连续流畅的用户体验
// 特性：步骤指示器、平滑过渡动画、统一UI风格、localStorage缓存、必填字段验证
// v7.112: 集成骨架屏加载动画，优化确认等待体验
// v7.147: 添加 Step 4 问卷汇总展示
// v7.154: 统一确认按钮，移除 QuestionnaireSummaryDisplay 内部按钮

'use client';

import { CheckCircle2, ArrowRight, Loader2 } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { Radar } from 'react-chartjs-2';
import NProgress from 'nprogress';
import 'nprogress/nprogress.css';
import QuestionnaireSkeletonLoader from './QuestionnaireSkeletonLoader';
import { QuestionnaireSummaryDisplay, type QuestionnaireSummaryDisplayRef } from './QuestionnaireSummaryDisplay';
import type { RestructuredRequirements } from '@/types';
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

// 🆕 v8.3: 统一5步渐进式问卷（Step 1: 输出意图确认）
// Step 1: 输出意图确认 + 需求分析判断 + 双动机展示
// Step 2: 任务梳理
// Step 3: 信息补全
// Step 4: 雷达图配置
// Step 5: 方案洞察（问卷汇总）
interface UnifiedProgressiveQuestionnaireModalProps {
  isOpen: boolean;
  currentStep: number; // 0=关闭, 1=输出意图, 2=任务梳理, 3=信息补全, 4=雷达图, 5=方案洞察
  stepData?: any;      // 🆕 v8.3: 统一数据对象（包含Step 1的requirements_judgement等）
  onConfirm: (data?: any) => void;  // 🆕 v7.130: 统一确认回调
  onSkip: () => void;   // 🆕 v7.130: 统一跳过回调
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

const FRONTCHAIN_STEPS = [
  { number: 1, label: '意图确认', icon: '1' },
  { number: 2, label: '任务梳理', icon: '2' },
  { number: 3, label: '信息补全', icon: '3' },
  { number: 4, label: '雷达图配置', icon: '4' },
  { number: 5, label: '方案洞察', icon: '5' },
];

// 🎯 v8.3: 简化组件参数
export function UnifiedProgressiveQuestionnaireModal({
  isOpen,
  currentStep,
  stepData,
  onConfirm,
  onSkip,
  sessionId = 'default'
}: UnifiedProgressiveQuestionnaireModalProps) {
  const [dimensionValues, setDimensionValues] = useState<Record<string, number>>({});
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isLoading, setIsLoading] = useState(false); // 骨架屏加载状态
  const [loadingMessage, setLoadingMessage] = useState('AI 正在智能分析...');

  // Step 1: 输出意图确认状态
  const [selectedDeliveries, setSelectedDeliveries] = useState<string[]>([]);
  const [selectedModes, setSelectedModes] = useState<string[]>([]);

  // 任务编辑状态
  const [editedTasks, setEditedTasks] = useState<EditableTask[]>([]);
  const [originalTasksCount, setOriginalTasksCount] = useState(0);
  const [isSummaryExpanded, setIsSummaryExpanded] = useState(false); // 需求摘要折叠状态

  // 🆕 v7.154: QuestionnaireSummaryDisplay ref，用于获取编辑内容
  const summaryDisplayRef = useRef<QuestionnaireSummaryDisplayRef>(null);

  // Ref for content container to control scroll position
  const contentRef = useRef<HTMLDivElement>(null);

  // 🆕 v8.3: 当步骤数据更新时，停止加载状态
  useEffect(() => {
    if (currentStep === 1 && (stepData?.delivery_types || stepData?.requirements_judgement)) {
      setIsLoading(false);
      NProgress.done();
    } else if (currentStep === 2 && stepData?.extracted_tasks) {
      setIsLoading(false);
      NProgress.done();
    } else if (currentStep === 3 && stepData?.questionnaire) {
      setIsLoading(false);
      NProgress.done();
    } else if (currentStep === 4 && stepData?.dimensions) {
      setIsLoading(false);
      NProgress.done();
    } else if (currentStep === 5 && stepData?.restructured_requirements) {
      setIsLoading(false);
      NProgress.done();
    }
  }, [currentStep, stepData]);

  // 🆕 v8.3: 初始化Step 1的选项（推荐选项默认选中）
  useEffect(() => {
    if (currentStep === 1 && stepData?.delivery_types) {
      const recommended = stepData.delivery_types.options.filter((o: any) => o.recommended).map((o: any) => o.id);
      setSelectedDeliveries(recommended);
    }
    if (currentStep === 1 && stepData?.identity_modes) {
      const recommended = stepData.identity_modes.options.filter((o: any) => o.recommended).map((o: any) => o.id);
      setSelectedModes(recommended);
    }
  }, [currentStep, stepData]);

  // 初始化任务列表
  useEffect(() => {
    if (stepData?.extracted_tasks && isOpen && currentStep === 2) {
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
            setOriginalTasksCount(stepData.extracted_tasks.length);
            return;
          }
        }
      } catch (e) {
        console.warn('Failed to restore task draft:', e);
      }

      // 没有缓存，使用原始数据
      setEditedTasks(stepData.extracted_tasks.map((task: any) => ({
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
      setOriginalTasksCount(stepData.extracted_tasks.length);
    }
  }, [stepData?.extracted_tasks, isOpen, currentStep, sessionId]);

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

  // Reset scroll position to top when step changes
  useEffect(() => {
    if (isOpen && !isLoading && contentRef.current) {
      contentRef.current.scrollTop = 0;
    }
  }, [currentStep, isOpen, isLoading]);

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

  // 🆕 v7.130: 初始化维度默认值（第3步雷达图）
  // 🔧 v7.146: 增强类型检查
  useEffect(() => {
    if (currentStep === 3 && stepData?.dimensions) {
      // 🔧 v7.146+: 兼容后端 v7.139+ 可能返回 { dimensions: [...] }
      const rawDimensions = stepData.dimensions;
      const resolvedDimensions = Array.isArray(rawDimensions)
        ? rawDimensions
        : Array.isArray(rawDimensions?.dimensions)
          ? rawDimensions.dimensions
          : null;

      // 类型验证
      if (!resolvedDimensions) {
        console.error('❌ Step3初始化: dimensions 不是数组', typeof rawDimensions, rawDimensions);
        return;
      }

      if (resolvedDimensions.length > 0 && Object.keys(dimensionValues).length === 0) {
        const initialValues: Record<string, number> = {};
        resolvedDimensions.forEach((dim: any) => {
          initialValues[dim.id || dim.dimension_id] = dim.default_value || 50;
        });
        setDimensionValues(initialValues);
        console.log('✅ Step3初始化: 已设置', resolvedDimensions.length, '个维度的默认值');
      }
    }
  }, [currentStep, stepData?.dimensions, dimensionValues]);

  // 🆕 v7.130: 调试打印第2步（信息补全）问题数据 & 标准化类型
  useEffect(() => {
    if (currentStep === 2 && stepData?.questionnaire?.questions) {
      console.log('🔍 Step2 Questions Debug:', stepData.questionnaire.questions);

      // 🔧 标准化问题类型（修复 multi_choice -> multiple_choice）
      stepData.questionnaire.questions = stepData.questionnaire.questions.map((q: any) => {
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

      // 调试输出
      stepData.questionnaire.questions.forEach((q: any, index: number) => {
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
  }, [currentStep, stepData]);

  if (!isOpen) return null;

  // 🆕 v7.130: 直接使用 stepData
  if (!stepData) return null;

  const { title, message } = stepData;

  // 当前 modal 内部步骤 1-4，对应前端完整 5 节点中的 2-5。
  const displayStep = currentStep > 0 ? currentStep + 1 : 0;

  // 🆕 v7.130: 验证信息补全步骤的必填字段（使用统一的 stepData）
  const validateStep3Required = (): boolean => {
    // 🆕 v7.130: 验证第2步（信息补全）必填字段
    if (currentStep !== 2 || !stepData?.questionnaire?.questions) return true;

    const requiredQuestions = stepData.questionnaire.questions.filter((q: any) => q.is_required);
    for (const q of requiredQuestions) {
      const answer = answers[q.id];
      if (!answer || (Array.isArray(answer) && answer.length === 0) || (typeof answer === 'string' && answer.trim() === '')) {
        return false;
      }
    }
    return true;
  };

  // 🆕 v7.130: 统一确认处理
  // 🆕 v7.147: 添加 Step 4 支持
  // 🆕 v7.401: 添加防抖机制，防止重复提交
  const handleConfirmClick = () => {
    // 🔥 v7.401: 防止重复提交（防抖）
    if (isLoading) {
      console.warn('⚠️ [v7.401 防抖] 请勿重复提交，正在处理中...');
      return;
    }

    // 第2步（信息补全）需要验证必填字段
    if (currentStep === 2 && !validateStep3Required()) {
      alert('请完成所有必填项（标记 * 的问题）');
      return;
    }

    // 启动加载状态和进度条
    setIsLoading(true);
    NProgress.start();

    // 🔧 v8.3: 更新加载提示文案（Step 1=输出意图）
    if (currentStep === 1) {
      setLoadingMessage('正在确认输出意图...');
    } else if (currentStep === 2) {
      setLoadingMessage('AI 正在智能拆解任务...');
    } else if (currentStep === 3) {
      setLoadingMessage('正在分析信息完整性...');
    } else if (currentStep === 4) {
      setLoadingMessage('正在生成雷达图维度...');
    } else if (currentStep === 5) {
      setLoadingMessage('正在生成需求洞察...');
    }

    // 🔧 v8.3: 根据步骤构建数据并调用统一的 onConfirm
    if (currentStep === 1) {
      // Step 1: 输出意图确认（交付类型 + 身份模式）
      console.log('🎯 Step 1: 输出意图确认', { selectedDeliveries, selectedModes });
      onConfirm({
        selected_deliveries: selectedDeliveries,
        selected_modes: selectedModes
      });
    } else if (currentStep === 2) {
      // Step 2: 任务梳理（原Step 1）
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
        onConfirm({ extracted_tasks: validTasks });
      } else {
        onConfirm();
      }
    } else if (currentStep === 3) {
      // Step 3: 信息补全（原Step 2）
      clearQuestionnaireCache(sessionId);
      onConfirm({ answers });
    } else if (currentStep === 4) {
      // Step 4: 雷达图配置（原Step 3）
      onConfirm({ dimension_values: dimensionValues });
    } else if (currentStep === 5) {
      // Step 5: 方案洞察（原Step 4）
      const modifications = summaryDisplayRef.current?.getModifications();
      if (modifications && Object.keys(modifications).length > 0) {
        console.log('📝 [Step5] 用户修改:', modifications);
        onConfirm({
          intent: 'confirm',
          modifications: modifications
        });
      } else {
        onConfirm();
      }
    }
  };

  // 获取确认按钮文本
  // 🔧 v8.3: 更新按钮文案以匹配新步骤映射
  const getConfirmButtonText = () => {
    if (currentStep === 1) {
      // Step 1: 输出意图确认
      return '确认开始问卷';
    } else if (currentStep === 2) {
      // Step 2: 任务梳理（原Step 1）
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
      case 3: return '确认偏好设置'; // 信息补全（原Step 2）
      case 4: return '提交问卷'; // 雷达图（原Step 3）
      case 5: return '确认无误，继续'; // 方案洞察（原Step 4）
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
      const originalTask = stepData?.extracted_tasks?.[index];
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

  // 🆕 v8.3: Step 1 - 输出意图确认（含需求分析判断+双动机）
  // 🆕 v8.3: 任务梳理UI（原Step 1，现为Step 2）
  const renderTaskExtractionContent = () => {
    return (
      <div className="space-y-4">
        {/* 任务列表标题 */}
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-800">任务列表</h3>
          <div className="text-sm text-gray-500">
            共 {editedTasks.length} 个任务 {originalTasksCount > 0 && `（原始 ${originalTasksCount} 个）`}
          </div>
        </div>

        {/* 任务卡片列表 */}
        <div className="task-list-container space-y-3 max-h-96 overflow-y-auto">
          {editedTasks.map((task, index) => (
            <div
              key={index}
              className={`border rounded-lg p-4 transition-all ${
                task.isEditing ? 'border-blue-400 bg-blue-50' : 'border-gray-200 bg-white hover:shadow-md'
              }`}
            >
              {task.isEditing ? (
                // 编辑模式
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      任务标题 <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={task.title}
                      onChange={(e) => updateTaskField(index, 'title', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="至少5个字符"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      任务描述 <span className="text-red-500">*</span>
                    </label>
                    <textarea
                      value={task.description}
                      onChange={(e) => updateTaskField(index, 'description', e.target.value)}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="至少20个字符"
                    />
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleSaveTask(index)}
                      className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
                    >
                      保存
                    </button>
                    <button
                      onClick={() => handleCancelEdit(index)}
                      className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
                    >
                      取消
                    </button>
                  </div>
                </div>
              ) : (
                // 显示模式
                <div className="space-y-2">
                  <div className="flex items-start justify-between">
                    <h4 className="text-base font-semibold text-gray-800 flex-1">{task.title}</h4>
                    <div className="flex gap-2 ml-3">
                      <button
                        onClick={() => handleEditTask(index)}
                        className="text-blue-600 hover:text-blue-800 text-sm"
                        title="编辑"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDeleteTask(index)}
                        className="text-red-600 hover:text-red-800 text-sm"
                        title="删除"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600 leading-relaxed">{task.description}</p>
                  {task.source_keywords && task.source_keywords.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {task.source_keywords.map((keyword, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 text-xs bg-gray-100 text-gray-700 rounded"
                        >
                          {keyword}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* 添加任务按钮 */}
        <button
          onClick={handleAddTask}
          disabled={editedTasks.length >= 15}
          className={`w-full py-3 border-2 border-dashed rounded-lg transition-all ${
            editedTasks.length >= 15
              ? 'border-gray-200 text-gray-400 cursor-not-allowed'
              : 'border-blue-300 text-blue-600 hover:bg-blue-50 hover:border-blue-400'
          }`}
        >
          <div className="flex items-center justify-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>{editedTasks.length >= 15 ? '已达到最大任务数' : '添加新任务'}</span>
          </div>
        </button>
      </div>
    );
  };

  // 🆕 v8.3: Step 1 - 输出意图确认UI
  const renderStep1Content = () => {
    const {
      delivery_types,
      identity_modes,
      requirements_judgement,
      motivation_routing_profile,
    } = stepData || {};

    const deliveryOptions = delivery_types?.options || [];
    const identityOptions = identity_modes?.options || [];

    return (
      <div className="space-y-6">
        {/* 需求分析师判断卡片 */}
        {requirements_judgement && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 space-y-3">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="text-sm font-semibold text-amber-800">需求分析师判断</div>
            </div>
            {requirements_judgement.summary && (
              <p className="text-sm text-amber-900 leading-relaxed">{requirements_judgement.summary}</p>
            )}
            {requirements_judgement.info_quality && (
              <div className="flex items-center gap-4 text-xs">
                <span className="text-amber-700">
                  信息完整度: <strong className="text-amber-900">{requirements_judgement.info_quality.score ?? 0}</strong>
                </span>
                <span className="px-2 py-0.5 bg-amber-200 text-amber-800 rounded">
                  {requirements_judgement.info_quality.confidence_level ?? 'medium'}
                </span>
              </div>
            )}
            {requirements_judgement.core_tensions && requirements_judgement.core_tensions.length > 0 && (
              <ul className="text-xs text-amber-800 space-y-1.5 pl-1">
                {requirements_judgement.core_tensions.slice(0, 3).map((t: any, idx: number) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-amber-600 mt-0.5">•</span>
                    <div>
                      <span className="font-medium">{t.name || '关键张力'}：</span>
                      <span className="text-amber-700">{t.implication || '待进一步补充'}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* 双动机展示 */}
        {motivation_routing_profile && (
          <div className="rounded-xl border border-blue-200 bg-blue-50 px-5 py-4 space-y-3">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <div className="text-sm font-semibold text-blue-800">双动机分析</div>
            </div>
            {motivation_routing_profile.primary_motivation && (
              <div className="space-y-1">
                <div className="text-xs text-blue-700">主要动机</div>
                <div className="text-sm text-blue-900">{motivation_routing_profile.primary_motivation}</div>
              </div>
            )}
            {motivation_routing_profile.secondary_motivation && (
              <div className="space-y-1">
                <div className="text-xs text-blue-700">次要动机</div>
                <div className="text-sm text-blue-900">{motivation_routing_profile.secondary_motivation}</div>
              </div>
            )}
          </div>
        )}

        {/* 交付类型选择 */}
        {delivery_types && (
          <div className="space-y-3">
            <div className="text-sm font-medium text-gray-700">{delivery_types.message || '交付类型：'}</div>
            <div className="space-y-2">
              {deliveryOptions.map((option: any) => {
                const isSelected = selectedDeliveries.includes(option.id);
                return (
                  <button
                    key={option.id}
                    onClick={() => {
                      setSelectedDeliveries(prev =>
                        prev.includes(option.id)
                          ? prev.filter(x => x !== option.id)
                          : [...prev, option.id]
                      );
                    }}
                    className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-all ${
                      isSelected
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-800">{option.label}</span>
                          {option.recommended && (
                            <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">推荐</span>
                          )}
                        </div>
                        {option.desc && <p className="text-sm text-gray-600 mt-1">{option.desc}</p>}
                      </div>
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                        isSelected ? 'bg-blue-500 border-blue-500' : 'border-gray-300'
                      }`}>
                        {isSelected && (
                          <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* 身份模式选择 */}
        {identity_modes && identityOptions.length > 0 && (
          <div className="space-y-3">
            <div className="text-sm font-medium text-gray-700">{identity_modes.message || '身份视角：'}</div>
            <div className="space-y-2">
              {identityOptions.map((option: any) => {
                const isSelected = selectedModes.includes(option.id);
                return (
                  <button
                    key={option.id}
                    onClick={() => {
                      setSelectedModes(prev =>
                        prev.includes(option.id)
                          ? prev.filter(x => x !== option.id)
                          : [...prev, option.id]
                      );
                    }}
                    className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-all ${
                      isSelected
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-800">{option.label}</span>
                          {option.recommended && (
                            <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">推荐</span>
                          )}
                        </div>
                        {option.spatial_need && (
                          <p className="text-sm text-gray-600 mt-1">{option.spatial_need}</p>
                        )}
                      </div>
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                        isSelected ? 'bg-blue-500 border-blue-500' : 'border-gray-300'
                      }`}>
                        {isSelected && (
                          <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  };

  // 🆕 v7.130: 渲染 Step 3（雷达图）
  const renderStep3Content = () => {
    const rawDimensions = stepData?.dimensions;
    const dimensions = Array.isArray(rawDimensions)
      ? rawDimensions
      : Array.isArray(rawDimensions?.dimensions)
        ? rawDimensions.dimensions
        : rawDimensions;

    // 🔧 v7.146: 增强类型检查，防止 dimensions 不是数组
    if (!dimensions) {
      console.error('❌ Step3: dimensions 为 undefined 或 null');
      return null;
    }
    if (!Array.isArray(dimensions)) {
      console.error('❌ Step3: dimensions 不是数组，实际类型:', typeof dimensions, dimensions);
      return null;
    }
    if (dimensions.length === 0) {
      console.warn('⚠️ Step3: dimensions 数组为空');
      return null;
    }

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
            <div className="bg-white rounded-xl p-6 shadow-sm">
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
                <div key={dimId} className="bg-white rounded-xl p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="flex-shrink-0 w-6 h-6 bg-gray-600 dark:bg-gray-400 text-white rounded-lg flex items-center justify-center text-xs font-medium">
                        {index + 1}
                      </span>
                      <span className="text-sm font-medium text-gray-900">
                        {dim.name || dim.dimension_name}
                      </span>
                    </div>
                    <span className="badge-gray font-medium">
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
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-gray-600"
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

  // 🆕 v7.130: 渲染 Step 2（信息补全问卷）
  // 🆕 v7.400: 支持loading骨架屏（Step 1确认后立即显示）
  const renderStep2Content = () => {
    // 🔥 v7.400: 优先检测loading状态
    if (stepData?.isLoading) {
      return (
        <div className="space-y-6">
          {/* 过渡提示 */}
          <div className="bg-[#f5f5f7] rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <Loader2 className="w-5 h-5 text-gray-600 dark:text-gray-400 animate-spin flex-shrink-0" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">正在理解您的需求并进行深度分析...</h3>
            </div>
            <p className="text-sm text-gray-400 mb-4">
              AI正在基于您确认的 <span className="text-gray-600 font-semibold">{editedTasks.length} 个任务</span>，智能分析信息完整性，为您生成精准的补充问题。
            </p>
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" />
                <span>分析项目目标与约束条件...</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{animationDelay: '0.2s'}} />
                <span>识别关键信息缺失维度...</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{animationDelay: '0.4s'}} />
                <span>生成针对性补充问题...</span>
              </div>
            </div>
          </div>

          {/* 骨架屏 */}
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg p-4 animate-pulse">
                <div className="h-4 bg-gray-700/50 rounded w-3/4 mb-3" />
                <div className="space-y-2">
                  <div className="h-3 bg-gray-700/30 rounded w-full" />
                  <div className="h-3 bg-gray-700/30 rounded w-5/6" />
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }

    const { questionnaire } = stepData || {};
    if (!questionnaire) return null;

    const { introduction, questions, note } = questionnaire;

    return (
      <div className="space-y-6">
        {/* 已隐藏：introduction 区域（包含完整度和缺失维度信息） */}
        {false && introduction && (
          <div className="bg-white rounded-xl p-5 shadow-sm">
            <p className="text-sm text-gray-600">{introduction}</p>
          </div>
        )}

        {/* 必填/选填说明 */}
        <div className="hidden">
          {/* 已隐藏：必填/选填说明 */}
        </div>

        <div className="space-y-4">
          {questions && questions.map((q: any, index: number) => {
            const isRequired = q.is_required;

            return (
              <div
                key={q.id || index}
                className={`rounded-xl p-5 transition-all ${
                  isRequired
                    ? 'bg-white shadow-sm'
                    : 'bg-[#f5f5f7] opacity-90'
                }`}
              >
                {/* 问题头部 */}
                <div className="flex items-start gap-3 mb-3">
                  {/* 序号徽章 */}
                  <div className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-xs font-medium ${
                    isRequired
                      ? 'bg-gray-600 text-white shadow-sm'
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
                          className="w-4 h-4 text-gray-600 accent-gray-600"
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
                          className="w-4 h-4 text-gray-600 rounded accent-gray-600"
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
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-gray-300 focus:bg-gray-50 bg-white text-gray-900 resize-none transition-all focus:outline-none"
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
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:border-gray-300 focus:bg-gray-50 bg-white text-gray-900 resize-none transition-all focus:outline-none"
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

        {/* 已隐藏：note 提示信息 */}
        {false && note && (
          <div className="text-xs text-gray-600 italic bg-[#f5f5f7] rounded-lg p-3">
            {note}
          </div>
        )}
      </div>
    );
  };

  // 渲染当前步骤内容
  // 🆕 v7.147: 添加 Step 4 支持
  const renderContent = () => {
    // 如果正在加载，显示骨架屏
    if (isLoading) {
      const skeletonType = currentStep === 1 ? 'tasks' : currentStep === 2 ? 'both' : 'radar';
      return <QuestionnaireSkeletonLoader type={skeletonType} message={loadingMessage} />;
    }

    // 🆕 v8.3: 步骤映射调整（Step 1=输出意图，Step 2-5=原Step 1-4）
    switch (currentStep) {
      case 1: return renderStep1Content(); // 输出意图确认
      case 2: return renderTaskExtractionContent(); // 任务梳理（原Step 1）✅ 已修复
      case 3: return renderStep2Content(); // 信息补全（原Step 2）
      case 4: return renderStep3Content(); // 雷达图（原Step 3）
      case 5: return renderStep4Content(); // 方案洞察（原Step 4）
      default: return null;
    }
  };

  // 🆕 v7.151: 渲染 Step 4 - 需求洞察（原问卷汇总+需求确认合并）
  // 🔧 v7.153: 增强状态检测
  const renderStep4Content = () => {
    // 检查数据是否存在
    if (!stepData?.restructured_requirements) {
      return (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-600 mx-auto mb-4"></div>
          <p className="text-gray-500">正在生成需求洞察...</p>
          <p className="text-sm text-gray-400 mt-2">AI 正在深度分析您的需求，请稍候</p>
        </div>
      );
    }

    // 🔧 v7.153: 检测洞察状态，处理 pending/degraded
    const insightStatus = stepData.restructured_requirements?.insight_summary?._status;
    const isPending = insightStatus === 'pending';

    // 如果状态是 pending，显示加载中（这种情况在 v7.153 后应该不会出现了）
    if (isPending) {
      return (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-600 mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">洞察正在生成中，请稍候...</p>
          <p className="text-sm text-gray-400 mt-2">系统正在分析您的需求，这可能需要几秒钟</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 text-sm text-gray-600 hover:text-gray-800 underline"
          >
            刷新页面
          </button>
        </div>
      );
    }

    // 🆕 v7.154: 确认逻辑已移至底部统一按钮，此处仅渲染展示组件
    return (
      <QuestionnaireSummaryDisplay
        ref={summaryDisplayRef}
        data={stepData.restructured_requirements as RestructuredRequirements}
        summaryText={stepData.requirements_summary_text}
        onConfirm={() => {}}  // 保留接口兼容，实际确认由底部按钮处理
        onBack={undefined}
      />
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      {isLoading ? (
        // 加载页面 - 保持步骤一致性
        <div className="bg-white rounded-2xl max-w-6xl w-full h-[85vh] overflow-hidden flex flex-col shadow-2xl border border-gray-200">

          {/* 步骤指示器 */}
          <div className="border-b border-gray-200 bg-white px-10 py-4">
            <div className="flex items-center justify-between mb-4">
              {FRONTCHAIN_STEPS.map((step, index) => (
                <div key={step.number} className="flex items-center flex-1">
                  <div className="flex flex-col items-center flex-1">
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-medium transition-all duration-300 ${
                      displayStep === step.number
                        ? 'bg-blue-600 text-white shadow-md'
                        : displayStep > step.number
                        ? 'bg-gray-500 text-white'
                        : 'bg-gray-100 text-gray-400'
                    }`}>
                      {displayStep > step.number ? (
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        step.number
                      )}
                    </div>
                    <span className={`mt-2 text-sm font-medium ${
                      displayStep === step.number ? 'text-gray-800' : 'text-gray-500'
                    }`}>
                      {step.label}
                    </span>
                  </div>

                  {index < FRONTCHAIN_STEPS.length - 1 && (
                    <div className={`h-px flex-1 mx-4 rounded-full transition-all duration-500 ${
                      displayStep > step.number ? 'bg-green-500' : 'bg-gray-300'
                    }`} />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Header - 需求显示 */}
          <div className="border-b border-gray-200 px-10 py-3 bg-white">
            {stepData?.user_input_summary && (
              <div
                className="flex items-start gap-2 cursor-pointer hover:bg-[#f5f5f7] rounded-lg p-3 -m-2 transition-colors"
                onClick={() => setIsSummaryExpanded(!isSummaryExpanded)}
              >
                <span className="text-sm font-medium text-gray-700 flex-shrink-0">需求：</span>
                <div className="flex-1 min-w-0">
                  <span className={`text-sm leading-relaxed text-gray-600 ${isSummaryExpanded ? '' : 'line-clamp-6'}`}>
                    {stepData.user_input_summary}
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
                className="animate-spin h-16 w-16 text-gray-600"
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
        <div className="border-b border-gray-200 bg-white px-10 py-4">
          <div className="flex items-center justify-between mb-4">
            {FRONTCHAIN_STEPS.map((step, index) => (
              <div key={step.number} className="flex items-center flex-1">
                <div className="flex flex-col items-center flex-1">
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-medium transition-all duration-300 ${
                    displayStep === step.number
                      ? 'bg-blue-600 text-white shadow-md'
                      : displayStep > step.number
                      ? 'bg-gray-500 text-white'
                      : 'bg-gray-100 text-gray-400'
                  }`}>
                    {displayStep > step.number ? '✓' : step.icon}
                  </div>
                  <div className={`mt-2 text-xs font-medium text-center transition-colors ${
                    displayStep === step.number
                      ? 'text-gray-800'
                      : displayStep > step.number
                      ? 'text-gray-700'
                      : 'text-gray-500'
                  }`}>
                    {step.label}
                  </div>
                </div>
                {index < FRONTCHAIN_STEPS.length - 1 && (
                  <div className={`h-px flex-1 mx-2 rounded-full transition-all duration-500 ${
                    displayStep > step.number
                      ? 'bg-green-500'
                      : 'bg-gray-300'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Header */}
        <div className="border-b border-gray-200 px-10 py-3 bg-white">
          {/* 固定需求显示 - 所有步骤通用（优先显示完整user_input，回退到摘要） */}
          {(stepData?.user_input || stepData?.user_input_summary) && (
            <div
              className="flex items-start gap-2 rounded-lg p-3 -m-2"
            >
              <span className="text-sm font-medium text-gray-700 flex-shrink-0">需求：</span>
              <div className="flex-1 min-w-0">
                <span className={`text-sm leading-relaxed text-gray-600 ${isSummaryExpanded ? '' : 'line-clamp-6'}`}>
                  {stepData?.user_input || stepData?.user_input_summary}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Content */}
        <div ref={contentRef} className="flex-1 overflow-y-auto px-10 py-6 bg-[#f5f5f7]">
          <div className={`transition-all duration-200 ${isTransitioning ? 'opacity-0 translate-y-2' : 'opacity-100 translate-y-0'}`}>
            {renderContent()}
          </div>
        </div>

        {/* Footer */}
        <div className="px-10 py-4 bg-white flex items-center justify-end gap-3">
          <button
            onClick={handleConfirmClick}
            disabled={currentStep === 2 && !validateStep3Required()}
            className="btn-primary-lg flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>{getConfirmButtonText()}</span>
            {currentStep < 4 && <ArrowRight className="w-4 h-4" />}
          </button>
        </div>
      </div>
      )}
    </div>
  );
}
