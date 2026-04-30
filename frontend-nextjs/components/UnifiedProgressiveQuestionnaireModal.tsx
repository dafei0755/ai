// components/UnifiedProgressiveQuestionnaireModal.tsx
// v7.105: 统一的三步递进式问卷组件 - 连续流畅的用户体验
// 特性：步骤指示器、平滑过渡动画、统一UI风格、localStorage缓存、必填字段验证
// v7.112: 集成骨架屏加载动画，优化确认等待体验
// v7.147: 添加 Step 4 问卷汇总展示
// v7.154: 统一确认按钮，移除 QuestionnaireSummaryDisplay 内部按钮

'use client';

import { CheckCircle2, ArrowRight, Loader2 } from 'lucide-react';
import { useState, useEffect, useRef, Fragment } from 'react';
import { Radar } from 'react-chartjs-2';
import NProgress from 'nprogress';
import 'nprogress/nprogress.css';
import QuestionnaireSkeletonLoader from './QuestionnaireSkeletonLoader';
import { api } from '@/lib/api';
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

// ============================================================================
// 输出意图相关类型定义（从 OutputIntentConfirmationModal 整合）
// ============================================================================
interface DeliveryOption {
  id: string;
  label: string;
  desc: string;
  recommended: boolean;
  evidence?: string[];
}

interface IdentityModeOption {
  id: string;
  label: string;
  spatial_need?: string;
  recommended: boolean;
  evidence_sources?: string[];
}

interface DeliveryTypesConfig {
  message: string;
  options: DeliveryOption[];
  max_select: number;
}

interface IdentityModesConfig {
  message: string;
  options: IdentityModeOption[];
}

// 🆕 v12.1: AI 检测的约束推荐项
interface RecommendedConstraintOption {
  id: string;
  label: string;
  desc: string;
  category: 'domain_capability' | 'project_constraint';
  recommended: boolean;
  source: string;
  evidence: string[];
}

interface RecommendedConstraintsConfig {
  message: string;
  options: RecommendedConstraintOption[];
}

// 🆕 v13.1: 需求分析复盘卡片数据
interface RequirementsReviewData {
  breakthrough_insight?: string;
  core_tensions?: Array<{ name: string; implication: string }>;
  info_quality?: {
    score: number;
    confidence_level: string;
    present_dimensions: string[];
    missing_dimensions: string[];
  };
  primary_deliverables?: Array<{ type: string; description: string; priority: string }>;
  design_mode?: { mode: string; confidence: number } | null;
}

// 🆕 v13.1: 意图确认复盘卡片数据
interface IntentReviewData {
  confirmed_deliveries?: Array<{ id: string; label: string }>;
  confirmed_identity_modes?: Array<{ id: string; label: string }>;
  confirmed_constraints?: Array<{ label: string; desc: string }>;
  intent_changed?: boolean;
  depth_hint?: string;
  mandatory_dimensions?: string[];
}

export interface OutputIntentConfirmationData {
  interaction_type: 'output_intent_confirmation';
  title?: string;
  delivery_types?: DeliveryTypesConfig;
  identity_modes?: IdentityModesConfig;
  /** 🆕 v12.1: AI 检测到的约束推荐 */
  recommended_constraints?: RecommendedConstraintsConfig;
  /** 🆕 v13.1: 需求分析复盘卡片 */
  requirements_review?: RequirementsReviewData;
}

export interface OutputIntentConfirmPayload {
  selected_deliveries: string[];
  selected_modes: string[];
  /** 🆕 v11.2: 自定义交付项详情（含 label/desc），供后端按需使用 */
  custom_delivery_details?: Array<{ id: string; label: string; desc: string }>;
  /** 🆕 v12.1: 用户确认的约束列表（AI推荐 + 用户手动添加） */
  confirmed_constraints?: Array<{ id: string; label: string; desc: string; source: 'ai_recommended' | 'user_added' }>;
  /** 🆕 v12.1: 用户保留的视觉参考图索引 */
  kept_visual_reference_indices?: number[];
  /** @deprecated 向后兼容，使用 confirmed_constraints 替代 */
  user_constraints?: Array<{ label: string; desc: string }>;
}

// 🆕 v7.130: 简化 Props 接口，使用统一的 stepData 和 onConfirm
// 🆕 v7.147: 支持 Step 4 (问卷汇总)
// 🔄 v10.2 Path B: 输出意图从 stepData.output_intent 提取，内部处理 Step 0→Step 1 本地切换
interface UnifiedProgressiveQuestionnaireModalProps {
  isOpen: boolean;
  currentStep: number; // 0=关闭, 1=意图确认, 2=任务梳理, 3=信息补全, 4=雷达图, 5=需求洞察
  stepData?: any;      // 🆕 v7.130: 统一数据对象（v10.2: 可含 output_intent 子字段）
  onConfirm: (data?: any) => void;  // 🆕 v7.130: 统一确认回调
  onSkip: () => void;   // 🆕 v7.130: 统一跳过回调
  sessionId?: string;
  userInput?: string;  // 🆕 用户原始需求文本，作为 stepData.user_input 不存在时的兜底显示
  inline?: boolean;    // 内联模式：嵌入右侧面板，不使用全屏模态浮窗
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
  category?: string;                // v8.001: Phase 1 类别名（用于分组渲染）
}

interface EditableQuestion {
  id: string;
  type: string;
  question: string;
  options?: string[];
  userAnswer?: string | string[];
}

// ============================================================================
// 静态映射表：交付类型 → 预期生成任务类别（前端短期过渡方案）
// 后端稳定后可通过 source_delivery_type 字段动态替代
// ============================================================================
const DELIVERY_TYPE_TASK_PREVIEW: Record<string, string[]> = {
  design_professional_report: ['概念框架', '设计哲学', '空间策略', '材料系统', '文化认同'],
  investment_operations_analysis: ['商业模型', '回报分析', '治理结构', '运营逻辑'],
  policy_submission: ['政策对齐', '社会效益', '风险评估', '合规审批'],
  construction_deepening: ['结构系统', '材料规格', '成本估算', '施工工艺'],
  aesthetic_essay: ['设计理念', '大师精神', '文明表达', '美学叙事'],
};

// 🆕 v7.130: 简化组件参数
export function UnifiedProgressiveQuestionnaireModal({
  isOpen,
  currentStep,
  stepData,
  onConfirm,
  onSkip,
  sessionId = 'default',
  userInput: userInputProp = '',
  inline = false,
}: UnifiedProgressiveQuestionnaireModalProps) {
  const getErrorCodeMessage = (errorCode?: string, generationSource?: string) => {
    if (!errorCode) return null;

    if (errorCode === 'LLM_AUTH_401') {
      return '当前模型鉴权失败（401），已自动切换为降级方案，您仍可继续流程。';
    }
    if (generationSource?.includes('fallback')) {
      return 'AI 生成暂不可用，已自动切换为降级方案。';
    }
    return null;
  };
  const [dimensionValues, setDimensionValues] = useState<Record<string, number>>({});
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isLoading, setIsLoading] = useState(false); // 骨架屏加载状态
  const [loadingMessage, setLoadingMessage] = useState('AI 正在智能分析...');

  // 🔄 v10.2 Path B: 输出意图从 stepData.output_intent 提取，Step 1 为本地阶段
  const [selectedDeliveries, setSelectedDeliveries] = useState<string[]>([]);
  const [selectedModes, setSelectedModes] = useState<string[]>([]);
  const [outputIntentPhase, setOutputIntentPhase] = useState<'pending' | 'confirmed'>('pending');
  const [confirmedOutputIntent, setConfirmedOutputIntent] = useState<OutputIntentConfirmPayload | null>(null);
  const outputIntentInitialized = useRef(false);

  // 🆕 v11.1: 自定义新增交付类型
  const [customDeliveries, setCustomDeliveries] = useState<Array<{ id: string; label: string; desc: string }>>([]);
  const [showAddDelivery, setShowAddDelivery] = useState(false);
  const [newDeliveryLabel, setNewDeliveryLabel] = useState('');
  const [newDeliveryDesc, setNewDeliveryDesc] = useState('');

  // 🆕 v11.2: 编辑/删除交付类型选项
  const [hiddenDeliveryIds, setHiddenDeliveryIds] = useState<string[]>([]);
  const [editingDeliveryId, setEditingDeliveryId] = useState<string | null>(null);
  const [editDeliveryDraft, setEditDeliveryDraft] = useState<{ label: string; desc: string }>({ label: '', desc: '' });
  const [editedDeliveryValues, setEditedDeliveryValues] = useState<Record<string, { label: string; desc: string }>>({});

  // 🆕 v11.2: 编辑/删除体验视角选项
  const [hiddenModeIds, setHiddenModeIds] = useState<string[]>([]);
  const [editingModeId, setEditingModeId] = useState<string | null>(null);
  const [editModeDraft, setEditModeDraft] = useState<{ label: string; desc: string }>({ label: '', desc: '' });
  const [editedModeValues, setEditedModeValues] = useState<Record<string, { label: string; desc: string }>>({});

  // 🆕 v11.2: 前置约束条件分组
  const [userConstraints, setUserConstraints] = useState<Array<{ id: string; label: string; desc: string }>>([]);
  const [showAddConstraint, setShowAddConstraint] = useState(false);
  const [newConstraintLabel, setNewConstraintLabel] = useState('');
  const [newConstraintDesc, setNewConstraintDesc] = useState('');
  const [editingConstraintId, setEditingConstraintId] = useState<string | null>(null);
  const [editConstraintDraft, setEditConstraintDraft] = useState<{ label: string; desc: string }>({ label: '', desc: '' });

  // 🆕 v11.2: 输出意图视觉参考上传（v12.1: 增加 description/referenceIndex）
  const [intentFiles, setIntentFiles] = useState<Array<{
    id: string;
    file: File;
    previewUrl?: string;
    status: 'pending' | 'uploading' | 'done' | 'error';
    description: string;
    referenceIndex: number;
  }>>([])
  const [intentUploadError, setIntentUploadError] = useState<string | null>(null);
  const intentFileInputRef = useRef<HTMLInputElement>(null);

  // 🆕 v12.1: 文档参考上传（PDF/Word/TXT）
  const [docFiles, setDocFiles] = useState<Array<{
    id: string;
    file: File;
    status: 'pending' | 'uploading' | 'done' | 'error';
    referenceIndex: number;
    description: string;
  }>>([])
  const [docUploadError, setDocUploadError] = useState<string | null>(null);
  const docFileInputRef = useRef<HTMLInputElement>(null);

  // 图片浮窗预览
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!lightboxUrl) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === ' ') {
        e.preventDefault();
        setLightboxUrl(null);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [lightboxUrl]);

  // 🆕 v12.1: AI 检测约束的选中状态
  const [selectedConstraintIds, setSelectedConstraintIds] = useState<string[]>([]);

  // 🆕 v11.0: Step1（意图确认）是独立 interrupt，stepData 本身就是 output_intent_confirmation payload
  const outputIntentData: OutputIntentConfirmationData | null =
    currentStep === 1 ? (stepData as OutputIntentConfirmationData) ?? null : null;

  // 当前是否处于输出意图步骤
  const isOutputIntentStep = currentStep === 1;

  // 初始化输出意图默认选择
  useEffect(() => {
    if (outputIntentData && !outputIntentInitialized.current) {
      const deliveryOptions = outputIntentData.delivery_types?.options ?? [];
      const identityOptions = outputIntentData.identity_modes?.options ?? [];
      setSelectedDeliveries(deliveryOptions.filter(o => o.recommended).map(o => o.id));
      setSelectedModes(identityOptions.filter(o => o.recommended).map(o => o.id));
      // 🆕 v12.1: 初始化 AI 推荐约束（recommended=true 的默认勾选）
      const constraintOptions = outputIntentData.recommended_constraints?.options ?? [];
      setSelectedConstraintIds(constraintOptions.filter(o => o.recommended).map(o => o.id));
      setOutputIntentPhase('pending');
      setConfirmedOutputIntent(null);
      outputIntentInitialized.current = true;
    }
    if (!outputIntentData) {
      outputIntentInitialized.current = false;
      setOutputIntentPhase('pending');
      setConfirmedOutputIntent(null);
    }
  }, [outputIntentData]);

  // 任务编辑状态
  const [editedTasks, setEditedTasks] = useState<EditableTask[]>([]);
  const [originalTasksCount, setOriginalTasksCount] = useState(0);
  const [isSummaryExpanded, setIsSummaryExpanded] = useState(false); // 需求摘要折叠状态
  const [isInsightsExpanded, setIsInsightsExpanded] = useState(false); // Step 4 深度洞察折叠状态

  // 🆕 v7.154: QuestionnaireSummaryDisplay ref，用于获取编辑内容
  const summaryDisplayRef = useRef<QuestionnaireSummaryDisplayRef>(null);

  // Ref for content container to control scroll position
  const contentRef = useRef<HTMLDivElement>(null);

  // 🆕 v7.130: 当步骤数据更新时，停止加载状态
  // 🆕 v7.147: 添加 Step 4 支持
  // 🆕 v9.3: 添加 Step 0 (output_intent_confirmation) 支持，防止回路时 spinner 永久锁死
  useEffect(() => {
    if (currentStep === 1 && stepData?.interaction_type === 'output_intent_confirmation') {
      // output_intent_detection 回路重路由时清除 spinner
      setIsLoading(false);
      NProgress.done();
      // 🆕 v11.2: 自动预选推荐交付类型和视角（移除"跳过"按钮后的默认值保障）
      const recDeliveries: string[] = stepData?.delivery_types?.options
        ?.filter((o: any) => o.recommended)
        .map((o: any) => o.id) ?? [];
      if (recDeliveries.length > 0) setSelectedDeliveries(recDeliveries);
      const recModes: string[] = stepData?.identity_modes?.options
        ?.filter((o: any) => o.recommended)
        .map((o: any) => o.id) ?? [];
      if (recModes.length > 0) setSelectedModes(recModes);
    } else if (currentStep === 2 && stepData?.extracted_tasks) {
      setIsLoading(false);
      NProgress.done();
    } else if (currentStep === 3 && stepData?.questionnaire) {
      setIsLoading(false);
      NProgress.done();
    } else if (currentStep === 4 && stepData?.dimensions) {
      setIsLoading(false);
      NProgress.done();
    } else if (currentStep === 5 && (stepData?.confirmed_core_tasks || stepData?.restructured_requirements)) {
      setIsLoading(false);
      NProgress.done();
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
        priority: task.priority,
        category: task.category,   // v8.001: 保留 Phase 1 分组类别
      })));
      setOriginalTasksCount(stepData.extracted_tasks.length);
    }
  }, [stepData?.extracted_tasks, isOpen, currentStep, sessionId]);

  // 自动保存任务草稿到localStorage
  useEffect(() => {
    if (sessionId && editedTasks.length > 0 && currentStep === 2 && isOpen) {
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
    if (currentStep === 4 && stepData?.dimensions) {
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
    if (currentStep === 3 && stepData?.questionnaire?.questions) {
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

  // 🔄 v10.2: stepData 必须存在（output_intent 也在 stepData 内）
  // 🆕 v11.2: step 1 允许 stepData 为 null（骨架屏过渡，等待 interrupt 到来）
  if (!stepData && currentStep !== 1) return null;

  const title = stepData?.title;
  const message = stepData?.message;

  // 步骤配置
  // 步骤配置：始终显示全部 5 个步骤，内部编号统一为 1-5
  // 🔄 v11.0: Step 1 意图确认始终展示，移除条件判断
  const allSteps = [
    { number: 1, label: '意图确认', icon: '1' },
    { number: 2, label: '任务梳理', icon: '2' },
    { number: 3, label: '信息补全', icon: '3' },
    { number: 4, label: '偏好雷达图', icon: '4' },
    { number: 5, label: '需求洞察', icon: '5' },
  ];

  // 当前生效的步骤号（用于stepper高亮，与 currentStep 保持一致）
  const effectiveStep = currentStep;

  // 🆕 v12.1: 图片参考上传（单张，仅图片格式）
  const MAX_IMAGE_COUNT = 8;
  const handleIntentFileAdd = async (fileList: FileList) => {
    if (!sessionId || sessionId === 'default') return;
    const file = fileList[0]; // 单张上传
    if (!file) return;
    // 前端数量限制
    if (intentFiles.length >= MAX_IMAGE_COUNT) {
      setIntentUploadError(`最多上传 ${MAX_IMAGE_COUNT} 张参考图`);
      return;
    }
    const entry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      file,
      previewUrl: URL.createObjectURL(file),
      status: 'uploading' as const,
      description: '',
      referenceIndex: -1,
    };
    setIntentFiles(prev => [...prev, entry]);
    setIntentUploadError(null);
    try {
      const result = await api.attachFilesToSession(sessionId, [file], [
        { filename: file.name, categories: [], custom_description: '' }
      ]);
      setIntentFiles(prev => prev.map(f =>
        f.id === entry.id ? { ...f, status: 'done', referenceIndex: result.start_index } : f
      ));
    } catch (err: any) {
      setIntentFiles(prev => prev.map(f =>
        f.id === entry.id ? { ...f, status: 'error' } : f
      ));
      const errMsg = err?.response?.status === 413
        ? `文件 ${file.name} 超过 10MB 限制`
        : '图片上传失败，请重试';
      setIntentUploadError(errMsg);
    }
  };

  // 🆕 v12.1: 删除图片参考（同步后端）
  const handleIntentFileDelete = async (entryId: string) => {
    const entry = intentFiles.find(f => f.id === entryId);
    if (!entry) return;
    if (entry.previewUrl) URL.revokeObjectURL(entry.previewUrl);
    setIntentFiles(prev => prev.filter(f => f.id !== entryId));
    // 同步删除后端
    if (entry.referenceIndex >= 0 && sessionId && sessionId !== 'default') {
      try {
        await api.deleteVisualReference(sessionId, entry.referenceIndex);
        // 删除后需要刷新其他条目的 referenceIndex
        setIntentFiles(prev => prev.map(f =>
          f.referenceIndex > entry.referenceIndex
            ? { ...f, referenceIndex: f.referenceIndex - 1 }
            : f
        ));
      } catch (e) {
        console.warn('删除后端视觉参考失败:', e);
      }
    }
  };

  // 🆕 v12.1: 文档参考上传（PDF/Word/TXT）
  // 🆕 文档描述变更（本地状态）
  const handleDocDescriptionChange = (entryId: string, desc: string) => {
    setDocFiles(prev => prev.map(f =>
      f.id === entryId ? { ...f, description: desc } : f
    ));
  };

  const handleDocFileAdd = async (fileList: FileList) => {
    if (!sessionId || sessionId === 'default') return;
    const file = fileList[0];
    if (!file) return;
    const entry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      file,
      status: 'uploading' as const,
      referenceIndex: -1,
      description: '',
    };
    setDocFiles(prev => [...prev, entry]);
    setDocUploadError(null);
    try {
      const result = await api.attachFilesToSession(sessionId, [file], [
        { filename: file.name, categories: ['document'], custom_description: '' }
      ]);
      setDocFiles(prev => prev.map(f =>
        f.id === entry.id ? { ...f, status: 'done', referenceIndex: result.start_index } : f
      ));
    } catch (err: any) {
      setDocFiles(prev => prev.map(f =>
        f.id === entry.id ? { ...f, status: 'error' } : f
      ));
      setDocUploadError(err?.response?.status === 413 ? '文件超过 10MB 限制' : '文档上传失败，请重试');
    }
  };

  // 🆕 v12.1: 更新图片描述（本地状态，提交时批量同步）
  const handleImageDescriptionChange = (entryId: string, desc: string) => {
    setIntentFiles(prev => prev.map(f =>
      f.id === entryId ? { ...f, description: desc } : f
    ));
  };

  // 🆕 v7.130: 验证信息补全步骤的必填字段（使用统一的 stepData）
  const validateStep3Required = (): boolean => {
    // 验证第3步（信息补全）必填字段
    if (currentStep !== 3 || !stepData?.questionnaire?.questions) return true;

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
  const handleConfirmClick = async () => {
    // 🔥 v7.401: 防止重复提交（防抖）
    if (isLoading) {
      console.warn('⚠️ [v7.401 防抖] 请勿重复提交，正在处理中...');
      return;
    }

    // 🆕 v12.1: Step1 独立 interrupt，构建完整 payload 并批量同步图片描述
    if (isOutputIntentStep && outputIntentData) {
      const deliveryOptions = outputIntentData.delivery_types?.options ?? [];
      const identityOptions = outputIntentData.identity_modes?.options ?? [];
      const constraintOptions = outputIntentData.recommended_constraints?.options ?? [];

      // 构建 confirmed_constraints: AI 推荐中被勾选的 + 用户手动添加的
      const confirmedConstraints: Array<{ id: string; label: string; desc: string; source: 'ai_recommended' | 'user_added' }> = [];
      // AI 推荐项
      for (const opt of constraintOptions) {
        if (selectedConstraintIds.includes(opt.id)) {
          confirmedConstraints.push({ id: opt.id, label: opt.label, desc: opt.desc, source: 'ai_recommended' });
        }
      }
      // 用户手动添加的文字补充
      for (const c of userConstraints) {
        confirmedConstraints.push({ id: c.id, label: c.label, desc: c.desc, source: 'user_added' });
      }

      const payload: OutputIntentConfirmPayload = {
        selected_deliveries: selectedDeliveries.length > 0
          ? selectedDeliveries
          : deliveryOptions.filter((o: any) => o.recommended).map((o: any) => o.id),
        selected_modes: selectedModes.length > 0
          ? selectedModes
          : identityOptions.filter((o: any) => o.recommended).map((o: any) => o.id),
        custom_delivery_details: customDeliveries.filter(c => selectedDeliveries.includes(c.id)),
        // 🆕 v12.1: 统一约束列表
        confirmed_constraints: confirmedConstraints.length > 0 ? confirmedConstraints : undefined,
        // 🆕 v12.1: 保留的视觉参考索引
        kept_visual_reference_indices: intentFiles
          .filter(f => f.status === 'done' && f.referenceIndex >= 0)
          .map(f => f.referenceIndex),
      };

      console.log('🎯 [v12.1] 输出意图确认，恢复后端:', payload);
      setIsLoading(true);
      setLoadingMessage('正在同步图片描述...');

      // 批量同步图片描述到后端（提交时一次性同步）
      const descSyncPromises = intentFiles
        .filter(f => f.status === 'done' && f.referenceIndex >= 0 && f.description.trim())
        .map(f => api.describeVisualReference(sessionId!, f.referenceIndex, f.description.trim()));
      try {
        await Promise.all(descSyncPromises);
      } catch (e) {
        console.warn('部分图片描述同步失败:', e);
      }

      setLoadingMessage('正在按确认意图生成任务列表...');
      onConfirm(payload);
      return;
    }

    // 第3步（信息补全）需要验证必填字段
    if (currentStep === 3 && !validateStep3Required()) {
      alert('请完成所有必填项（标记 * 的问题）');
      return;
    }

    // 启动加载状态和进度条
    setIsLoading(true);
    NProgress.start();

    // 设置加载提示文案
    if (currentStep === 2) {
      setLoadingMessage('AI 正在智能拆解任务...');
    } else if (currentStep === 3) {
      setLoadingMessage('正在分析缺失的信息项...');
    } else if (currentStep === 4) {
      setLoadingMessage('正在生成需求洞察...');
    } else if (currentStep === 5) {
      setLoadingMessage('正在分配角色和任务...');
    }

    // 根据步骤构建数据并调用统一的 onConfirm
    if (currentStep === 2) {
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
        // 🔄 v10.2 Path B: 捆绑输出意图确认数据
        const confirmPayload: any = { extracted_tasks: validTasks };
        if (confirmedOutputIntent) {
          confirmPayload.output_intent = confirmedOutputIntent;
          console.log('📦 [v10.2] Step2 捆绑输出意图:', confirmedOutputIntent);
        }
        onConfirm(confirmPayload);
      } else {
        // 无任务修改，但可能有输出意图确认
        if (confirmedOutputIntent) {
          console.log('📦 [v10.2] Step2 仅输出意图:', confirmedOutputIntent);
          onConfirm({ output_intent: confirmedOutputIntent });
        } else {
          onConfirm();
        }
      }
    } else if (currentStep === 3) {
      clearQuestionnaireCache(sessionId);
      onConfirm({ answers });
    } else if (currentStep === 4) {
      onConfirm({ dimension_values: dimensionValues });
    } else if (currentStep === 5) {
      // 🆕 v7.154: Step 5 需求洞察确认，检查是否有编辑修改
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
  // 🆕 v7.147: 添加 Step 4 支持
  const getConfirmButtonText = () => {
    // 🆕 v11.0: 输出意图步骤
    if (isOutputIntentStep) {
      return '确认意图，生成任务';
    }

    if (currentStep === 2) {
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
      case 3: return '确认补充信息';
      case 4: return '确认偏好设置';
      case 5: return '确认无误，继续';
      default: return '确认';
    }
  };

  // 🆕 v11.1: 自定义交付类型 - 新增确认
  const handleConfirmAddCustomDelivery = () => {
    const label = newDeliveryLabel.trim();
    const desc = newDeliveryDesc.trim();
    if (!label || !desc) return; // 名称和描述均必填

    const maxSelect = outputIntentData?.delivery_types?.max_select ?? 3;
    const totalSelected = selectedDeliveries.length;
    if (totalSelected >= maxSelect) {
      alert(`最多只能选择 ${maxSelect} 项交付类型`);
      return;
    }

    const newId = `custom_${Date.now()}`;
    const newItem = { id: newId, label, desc };
    setCustomDeliveries(prev => [...prev, newItem]);
    setSelectedDeliveries(prev => [...prev, newId]);
    setNewDeliveryLabel('');
    setNewDeliveryDesc('');
    setShowAddDelivery(false);
  };

  // 🆕 v11.2: 删除交付类型选项
  const handleDeleteDelivery = (id: string, isCustom: boolean) => {
    if (isCustom) {
      setCustomDeliveries(prev => prev.filter(d => d.id !== id));
    } else {
      setHiddenDeliveryIds(prev => [...prev, id]);
    }
    setSelectedDeliveries(prev => prev.filter(x => x !== id));
  };

  // 🆕 v11.2: 开始编辑交付类型选项
  const handleStartEditDelivery = (id: string, label: string, desc: string) => {
    setEditingDeliveryId(id);
    setEditDeliveryDraft({ label, desc });
  };

  // 🆕 v11.2: 确认编辑交付类型选项
  const handleConfirmEditDelivery = (id: string, isCustom: boolean) => {
    const { label, desc } = editDeliveryDraft;
    if (!label.trim()) return;
    if (isCustom) {
      setCustomDeliveries(prev => prev.map(d => d.id === id ? { ...d, label: label.trim(), desc: desc.trim() } : d));
    } else {
      setEditedDeliveryValues(prev => ({ ...prev, [id]: { label: label.trim(), desc: desc.trim() } }));
    }
    setEditingDeliveryId(null);
  };

  // 🆕 v11.2: 删除体验视角选项
  const handleDeleteMode = (id: string) => {
    setHiddenModeIds(prev => [...prev, id]);
    setSelectedModes(prev => prev.filter(x => x !== id));
  };

  // 🆕 v11.2: 开始编辑体验视角选项
  const handleStartEditMode = (id: string, label: string, desc: string) => {
    setEditingModeId(id);
    setEditModeDraft({ label, desc });
  };

  // 🆕 v11.2: 确认编辑体验视角选项
  const handleConfirmEditMode = (id: string) => {
    const { label, desc } = editModeDraft;
    if (!label.trim()) return;
    setEditedModeValues(prev => ({ ...prev, [id]: { label: label.trim(), desc: desc.trim() } }));
    setEditingModeId(null);
  };

  // 🆕 v11.2: 前置约束条件 - 新增
  const handleConfirmAddConstraint = () => {
    const label = newConstraintLabel.trim();
    const desc = newConstraintDesc.trim();
    if (!label) return;
    setUserConstraints(prev => [...prev, { id: `constraint_${Date.now()}`, label, desc }]);
    setNewConstraintLabel('');
    setNewConstraintDesc('');
    setShowAddConstraint(false);
  };

  // 🆕 v11.2: 前置约束条件 - 保存编辑
  const handleConfirmEditConstraint = (id: string) => {
    const { label, desc } = editConstraintDraft;
    if (!label.trim()) return;
    setUserConstraints(prev => prev.map(c => c.id === id ? { ...c, label: label.trim(), desc: desc.trim() } : c));
    setEditingConstraintId(null);
  };

  // 任务编辑相关函数
  const handleEditTask = (index: number) => {
    setEditedTasks(prev => {
      const result: EditableTask[] = [];
      prev.forEach((t, i) => {
        if (i === index) {
          result.push({ ...t, isEditing: true });
        } else if (t.isNew && t.isEditing) {
          // discard other unsaved new tasks
        } else {
          result.push({ ...t, isEditing: false });
        }
      });
      return result;
    });
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
    const userAddedCount = editedTasks.filter(t => t.isNew).length;
    if (userAddedCount >= 10) {
      alert('手动新增任务最多10个');
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

    // 滚动到新任务卡片
    setTimeout(() => {
      document.getElementById('task-new-editing')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 150);
  };

  const updateTaskField = (index: number, field: keyof EditableTask, value: any) => {
    setEditedTasks(prev => prev.map((t, i) =>
      i === index ? { ...t, [field]: value } : t
    ));
  };

  // 渲染 Step 1
  const renderStep1Content = () => {
    const { user_input_summary, task_groups } = stepData || {};

    // 计算修改统计
    const validTasks = editedTasks.filter(t => !t.isEditing);
    const addedCount = validTasks.filter(t => t.isNew).length;
    const deletedCount = originalTasksCount - (validTasks.length - addedCount);

    const summaryPreview = user_input_summary?.length > 50
      ? user_input_summary.substring(0, 50) + '...'
      : user_input_summary;

    // v8.001: 按 task_groups 分组构建渲染顺序
    // task_groups 来自后端分组元数据，包含 category 和 task_ids
    // 若无分组数据则退化为平铺列表
    const renderGroups: Array<{ category: string | null; taskIndices: number[] }> = [];

    if (task_groups && task_groups.length > 0) {
      // 构建 id -> editedTasks 索引的快速查找
      const idToIndex: Record<string, number> = {};
      editedTasks.forEach((t, i) => { if (t.id) idToIndex[t.id] = i; });

      // 按分组顺序排列
      const assignedIndices = new Set<number>();
      for (const group of task_groups) {
        const indices: number[] = [];
        for (const tid of (group.task_ids || [])) {
          const idx = idToIndex[tid];
          if (idx !== undefined && !assignedIndices.has(idx)) {
            indices.push(idx);
            assignedIndices.add(idx);
          }
        }
        // 也捕捉同 category 但不在 task_ids 里的新增任务
        editedTasks.forEach((t, i) => {
          if (!assignedIndices.has(i) && (t.category === group.category || (!t.category && group.category === '基础调研'))) {
            indices.push(i);
            assignedIndices.add(i);
          }
        });
        if (indices.length > 0) {
          renderGroups.push({ category: group.category, taskIndices: indices });
        }
      }
      // 剩余未分配的任务（用户新增且无 category）放到末尾
      const remaining = editedTasks.map((_, i) => i).filter(i => !assignedIndices.has(i));
      if (remaining.length > 0) {
        renderGroups.push({ category: null, taskIndices: remaining });
      }
    } else {
      // 无分组数据，退化为单组平铺
      renderGroups.push({ category: null, taskIndices: editedTasks.map((_, i) => i) });
    }

    // 全局序号计数（用于显示连续编号）
    let globalTaskNum = 0;

    // 🆕 v13.1: 意图确认复盘卡片数据
    const intentReview = (stepData as any)?.intent_review as IntentReviewData | undefined;

    return (
      <div className="space-y-4">
        {/* 🆕 v13.1: 复盘卡片 2 — 意图确认结果 */}
        {intentReview && (intentReview.confirmed_deliveries?.length || intentReview.confirmed_constraints?.length) && (
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-5 space-y-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">意图确认结果</p>

            {/* 交付方向 */}
            {intentReview.confirmed_deliveries && intentReview.confirmed_deliveries.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-gray-500">交付方向</span>
                {intentReview.confirmed_deliveries.map((d: any, i: number) => (
                  <span key={i} className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full font-medium">
                    {d.label}
                  </span>
                ))}
              </div>
            )}

            {/* 身份模式 */}
            {intentReview.confirmed_identity_modes && intentReview.confirmed_identity_modes.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-gray-500">身份模式</span>
                {intentReview.confirmed_identity_modes.map((m: any, i: number) => (
                  <span key={i} className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full font-medium">
                    {m.label}
                  </span>
                ))}
              </div>
            )}

            {/* 约束条件 */}
            {intentReview.confirmed_constraints && intentReview.confirmed_constraints.length > 0 && (
              <div className="space-y-1">
                <span className="text-xs text-gray-500">约束条件</span>
                {intentReview.confirmed_constraints.map((c: any, i: number) => (
                  <p key={i} className="text-sm text-gray-700">• {c.label}{c.desc ? `：${c.desc}` : ''}</p>
                ))}
              </div>
            )}

            {/* 意图偏离提示 */}
            {intentReview.intent_changed && (
              <p className="text-xs text-amber-600 font-medium">⚡ 您调整了 AI 推荐的意图方向，任务列表已据此重新生成</p>
            )}

            <p className="text-xs text-gray-400 pt-1">↓ 基于以上意图，AI 拆解了以下任务</p>
          </div>
        )}

        {/* 任务分组列表 */}
        <div className="task-list-container space-y-6">
          {renderGroups.map((group, groupIdx) => (
            <div key={groupIdx}>
              {/* 分组标题行 */}
              {group.category && (
                <div className="flex items-center gap-2 mb-3 mt-2">
                  <div className="h-px flex-1 bg-gray-200" />
                  <span className="px-3 py-1 text-base font-bold text-gray-700 bg-gray-100 rounded-full whitespace-nowrap">
                    {group.category}
                  </span>
                  <div className="h-px flex-1 bg-gray-200" />
                </div>
              )}
              {/* 该分组的任务卡片 */}
              <div className="space-y-3">
                {group.taskIndices.map((index) => {
                  globalTaskNum += 1;
                  const displayNum = globalTaskNum;
                  const task = editedTasks[index];
                  const isEditing = task.isEditing;
                  const isNew = task.isNew;

                  return (
              <div
                key={index}
                id={isNew && isEditing ? 'task-new-editing' : undefined}
                className={`relative group bg-white rounded-xl p-4 transition-all duration-200 ${
                  isNew ? 'border-l-4 border-l-green-500' : ''
                } ${isEditing ? 'ring-2 ring-gray-300 shadow-lg' : 'hover:shadow-md cursor-pointer'}`}
              >
                {/* 新增任务标记（右移以避开删除按钮） */}
                {isNew && !isEditing && (
                  <div className="absolute top-2 right-9 px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                    新增
                  </div>
                )}
                {/* 删除按钮：hover 时显示，仅查看模式 */}
                {!isEditing && (
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDeleteTask(index); }}
                    title="删除任务"
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-md hover:bg-red-50 text-red-400 hover:text-red-600"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}

                {isEditing ? (
                  // 编辑模式
                  <div className="space-y-4">
                    <div className="flex items-start gap-3">
                      <div className="step-badge w-8 h-8 text-sm">
                        {displayNum}
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
                            className="input-base text-sm placeholder:text-gray-400"
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
                            className="input-base text-sm placeholder:text-gray-400 resize-none"
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
                            className="btn-primary-sm"
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
                  // 查看模式：点击卡片进入编辑
                  <div className="flex items-start gap-3" onClick={() => handleEditTask(index)}>
                    <div className="step-badge w-8 h-8 text-sm">
                      {displayNum}
                    </div>
                    <div className="flex-1 min-w-0 space-y-2">
                      {/* 标题行：标题 + 动机标签 */}
                      <div className="flex items-center gap-2 flex-wrap">
                        {/* 任务标题 */}
                        <h4 className="font-medium text-gray-900">
                          {task.title}
                        </h4>

                        {/* 动机类型标签（驱动力维度，与分组category正交） */}
                        {task.motivation_label && (
                          <span className="badge-gray flex-shrink-0">
                            {task.motivation_label}
                          </span>
                        )}

                        {/* 🆕 v11.1: 来源交付类型 badge（后端 source_delivery_type 字段，向下兼容） */}
                        {(task as any).source_delivery_type && (
                          <span className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-600 border border-blue-100 flex-shrink-0">
                            <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                            来源：{(task as any).source_delivery_type}
                          </span>
                        )}

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

                      {/* v7.105: AI推理说明 + 关键词 */}
                      {(task.ai_reasoning || (task.source_keywords && task.source_keywords.length > 0)) && (
                        <div className="space-y-1.5">
                          {task.ai_reasoning && (
                            <p className="text-xs text-gray-600 leading-relaxed italic">{task.ai_reasoning}</p>
                          )}
                          {task.source_keywords && task.source_keywords.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                              {task.source_keywords.map((keyword: string, idx: number) => (
                                <span key={idx} className="badge-gray text-xs">
                                  {keyword}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* v7.105: 依赖关系 */}
                      {task.dependencies && task.dependencies.length > 0 && (
                        <div className="text-xs text-gray-600">
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
                      )}

                      {/* v7.105: 预期产出 */}
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
                  </div>
                )}
              </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* 添加任务按钮 */}
        <div className="flex items-center gap-4 my-8">
          <div className="flex-1 border-t border-dashed border-gray-300"></div>
          <button
            onClick={handleAddTask}
            disabled={editedTasks.filter(t => t.isNew).length >= 10}
            className="transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
          >
            <div className="w-10 h-10 rounded-full bg-gray-100 group-hover:bg-gray-200 flex items-center justify-center transition-colors">
              <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </div>
          </button>
          <div className="flex-1 border-t border-dashed border-gray-300"></div>
        </div>
      </div>
    );
  };
  const renderStep3Content = () => {
    // 优先检测 loading 状态（信息补全提交后立即切屏时）
    if (stepData?.isLoading) {
      return <QuestionnaireSkeletonLoader type="radar" message="正在生成偏好维度..." />;
    }

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
        {(() => {
          const radarErrorCode = stepData?.radar_error_code || stepData?.dimension_meta?.error_code;
          const radarSource = stepData?.radar_generation_source || stepData?.dimension_meta?.generation_source;
          const msg = getErrorCodeMessage(radarErrorCode, radarSource);
          if (!msg) return null;
          return (
            <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M4.93 19h14.14c1.54 0 2.5-1.67 1.73-3L13.73 4c-.77-1.33-2.69-1.33-3.46 0L3.2 16c-.77 1.33.19 3 1.73 3z" /></svg>
              <span>{msg}</span>
            </div>
          );
        })()}
        {/* 🆕 v12.1: 偏好调优说明提示 */}
        <div className="flex items-center gap-2 px-4 py-2.5 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          <span>以下为偏好调优，不会改变已确认的交付约束</span>
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          {/* 左侧：固定雷达图 */}
          <div className="md:sticky md:top-0 md:self-start">
            <div className="bg-white rounded-xl p-6 shadow-sm">
              <div className="flex flex-col items-center mb-4 gap-1">
                <h3 className="text-base font-medium text-gray-900 text-center">
                  偏好雷达图
                </h3>
                {stepData?.dimension_meta && (
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    stepData.dimension_meta.degraded
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-green-100 text-green-700'
                  }`}>
                    {stepData.dimension_meta.degraded
                      ? `通用模板 (${stepData.dimension_meta.fallback_reason?.slice(0, 20) || '降级'})`
                      : `AI专属生成 (${dimensions?.length || 0}维)`
                    }
                  </span>
                )}
              </div>
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
                <div key={dimId} className="card-white">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="step-badge w-6 h-6 text-xs">
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
      return <QuestionnaireSkeletonLoader type="questions" message="正在分析缺失的信息项..." />;
    }

    const { questionnaire } = stepData || {};
    if (!questionnaire) return null;

    const { introduction, questions, note } = questionnaire;

    return (
      <div className="space-y-6">
        {(() => {
          const gapErrorCode = stepData?.gap_filling_error_code || stepData?.questionnaire_meta?.error_code;
          const gapSource = stepData?.gap_filling_generation_source || stepData?.questionnaire_meta?.generation_source;
          const msg = getErrorCodeMessage(gapErrorCode, gapSource);
          if (!msg) return null;
          return (
            <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M4.93 19h14.14c1.54 0 2.5-1.67 1.73-3L13.73 4c-.77-1.33-2.69-1.33-3.46 0L3.2 16c-.77 1.33.19 3 1.73 3z" /></svg>
              <span>{msg}</span>
            </div>
          );
        })()}
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
                  <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium ${
                    isRequired
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-500'
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
    // 🆕 v10.x: 输出意图步骤
    if (isOutputIntentStep && outputIntentData) {
      return renderOutputIntentContent();
    }

    // 🆕 v11.2: 步骤1但数据尚未到达 → 意图确认骨架屏
    if (isOutputIntentStep && !outputIntentData) {
      return <QuestionnaireSkeletonLoader type="intent" message="正在解析项目意图配置，请稍候..." />;
    }

    // 如果正在加载，显示骨架屏
    if (isLoading) {
      const skeletonType =
        currentStep === 2 ? 'tasks' :
        currentStep === 3 ? 'questions' :
        currentStep === 4 ? 'radar' :
        'insights';
      return <QuestionnaireSkeletonLoader type={skeletonType} message={loadingMessage} />;
    }

    // 直接映射步骤到渲染函数
    switch (currentStep) {
      case 2: return renderStep1Content();
      case 3: return renderStep2Content();
      case 4: return renderStep3Content();
      case 5: return renderStep4Content();
      default: return null;
    }
  };

  // 🆕 v10.x: 渲染输出意图确认内容（整合自 OutputIntentConfirmationModal）
  const renderOutputIntentContent = () => {
    if (!outputIntentData) return null;

    const deliveryOptions: DeliveryOption[] = outputIntentData.delivery_types?.options ?? [];
    const maxSelect = outputIntentData.delivery_types?.max_select ?? 3;
    const identityOptions: IdentityModeOption[] = outputIntentData.identity_modes?.options ?? [];
    const isDeliveryLimitReached = selectedDeliveries.length >= maxSelect;

    const toggleDelivery = (id: string) => {
      setSelectedDeliveries(prev => {
        if (prev.includes(id)) return prev.filter(x => x !== id);
        if (prev.length >= maxSelect) return prev;
        return [...prev, id];
      });
    };

    const toggleMode = (id: string) => {
      setSelectedModes(prev =>
        prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
      );
    };

    // 渲染编辑表单（交付类型 / 视角通用）
    const renderInlineEditForm = (
      draft: { label: string; desc: string },
      onChangeDraft: (d: { label: string; desc: string }) => void,
      onConfirm: () => void,
      onCancel: () => void,
      labelPlaceholder = '名称（必填）',
      descPlaceholder = '描述'
    ) => (
      <div className="bg-white border border-dashed border-blue-300 rounded-xl px-4 py-3 space-y-2">
        <input
          type="text"
          value={draft.label}
          onChange={e => onChangeDraft({ ...draft, label: e.target.value })}
          placeholder={labelPlaceholder}
          className="input-sm"
          autoFocus
        />
        <textarea
          value={draft.desc}
          onChange={e => onChangeDraft({ ...draft, desc: e.target.value })}
          placeholder={descPlaceholder}
          rows={2}
          className="input-sm resize-none"
        />
        <div className="flex items-center gap-2">
          <button
            onClick={onConfirm}
            disabled={!draft.label.trim()}
            className="px-3 py-1 bg-blue-500 hover:bg-blue-600 disabled:opacity-40 text-white text-sm rounded-lg transition-colors"
          >
            保存
          </button>
          <button
            onClick={onCancel}
            className="px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-600 text-sm rounded-lg transition-colors"
          >
            取消
          </button>
        </div>
      </div>
    );

    // 编辑/删除 hover 按钮
    const renderEditDeleteButtons = (onEdit: () => void, onDelete: () => void) => (
      <div className="absolute top-2 right-2 hidden group-hover:flex items-center gap-0.5 z-10">
        <button
          onClick={e => { e.stopPropagation(); onEdit(); }}
          className="p-1.5 rounded-md text-gray-400 hover:text-blue-500 hover:bg-blue-50 transition-colors"
          title="编辑"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        </button>
        <button
          onClick={e => { e.stopPropagation(); onDelete(); }}
          className="p-1.5 rounded-md text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
          title="删除"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    );

    // 🆕 v13.1: 需求分析复盘卡片数据
    const reqReview = outputIntentData?.requirements_review;

    return (
      <div className="space-y-6">
        {/* 🆕 v13.1: 复盘卡片 1 — 需求分析摘要 */}
        {reqReview && (reqReview.breakthrough_insight || (reqReview.core_tensions && reqReview.core_tensions.length > 0) || reqReview.info_quality) && (
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-5 space-y-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">需求分析摘要</p>

            {/* 项目本质 */}
            {reqReview.breakthrough_insight && (
              <p className="text-gray-800 font-medium leading-relaxed">
                &ldquo;{reqReview.breakthrough_insight}&rdquo;
              </p>
            )}

            {/* 核心矛盾 */}
            {reqReview.core_tensions && reqReview.core_tensions.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs text-gray-500">核心矛盾</p>
                {reqReview.core_tensions.map((t: any, i: number) => (
                  <p key={i} className="text-sm text-gray-700">• {t.name}{t.implication ? `：${t.implication}` : ''}</p>
                ))}
              </div>
            )}

            {/* 信息充足度 */}
            {reqReview.info_quality && (
              <div className="space-y-1.5">
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <div className="flex items-center gap-1.5">
                    <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full transition-all"
                           style={{width: `${Math.min((reqReview.info_quality.score || 0) * 100, 100)}%`}} />
                    </div>
                    <span>信息充足度 {Math.round((reqReview.info_quality.score || 0) * 100)}%</span>
                  </div>
                  <span className="text-gray-400">|</span>
                  <span>置信度: {reqReview.info_quality.confidence_level === 'high' ? '高' : reqReview.info_quality.confidence_level === 'medium' ? '中' : '低'}</span>
                </div>
                {reqReview.info_quality.present_dimensions && reqReview.info_quality.present_dimensions.length > 0 && (
                  <p className="text-xs text-gray-500">
                    <span className="text-green-600">✓ 已识别:</span> {reqReview.info_quality.present_dimensions.join('、')}
                  </p>
                )}
                {reqReview.info_quality.missing_dimensions && reqReview.info_quality.missing_dimensions.length > 0 && (
                  <p className="text-xs text-gray-500">
                    <span className="text-gray-400">○ 待补充:</span> {reqReview.info_quality.missing_dimensions.join('、')}
                  </p>
                )}
              </div>
            )}

            <p className="text-xs text-gray-400 pt-1">↓ 基于以上分析，AI 推荐以下输出意图</p>
          </div>
        )}

        {/* 交付类型 */}
        {outputIntentData.delivery_types && (
          <div>
            <div className="text-sm font-medium text-gray-700 mb-1">
              {outputIntentData.delivery_types.message}
            </div>
            <div className="text-xs text-gray-400 mb-3">
              最多选择 {maxSelect} 项
              {isDeliveryLimitReached && (
                <span className="text-orange-500 ml-2">已达上限</span>
              )}
            </div>
            <div className="space-y-2">
              {/* 后端预设交付类型 */}
              {deliveryOptions
                .filter(option => !hiddenDeliveryIds.includes(option.id))
                .map((option) => {
                  const effectiveLabel = editedDeliveryValues[option.id]?.label ?? option.label;
                  const effectiveDesc = editedDeliveryValues[option.id]?.desc ?? option.desc;
                  const isSelected = selectedDeliveries.includes(option.id);
                  const isDisabled = !isSelected && isDeliveryLimitReached;

                  if (editingDeliveryId === option.id) {
                    return (
                      <div key={option.id}>
                        {renderInlineEditForm(
                          editDeliveryDraft,
                          setEditDeliveryDraft,
                          () => handleConfirmEditDelivery(option.id, false),
                          () => setEditingDeliveryId(null)
                        )}
                      </div>
                    );
                  }

                  return (
                    <div
                      key={option.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => !isDisabled && toggleDelivery(option.id)}
                      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); if (!isDisabled) toggleDelivery(option.id); }}}
                      className={`group relative w-full text-left rounded-xl px-4 py-3 transition-all duration-200 ${
                        isSelected
                          ? 'bg-white border-l-4 border-l-blue-500 shadow-sm'
                          : isDisabled
                          ? 'bg-white border border-gray-200 opacity-50 cursor-not-allowed'
                          : 'bg-white border border-gray-200 hover:shadow-md cursor-pointer'
                      }`}
                    >
                      {renderEditDeleteButtons(
                        () => handleStartEditDelivery(option.id, effectiveLabel, effectiveDesc),
                        () => handleDeleteDelivery(option.id, false)
                      )}
                      <div className="flex items-center gap-2 pr-14">
                        <div className={`w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                          isSelected ? 'border-blue-500 bg-blue-500' : 'border-gray-300'
                        }`}>
                          {isSelected && (
                            <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 12 12">
                              <path d="M10 3L5 8.5 2 5.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
                            </svg>
                          )}
                        </div>
                        <span className="text-sm font-medium text-gray-800">{effectiveLabel}</span>
                        {option.recommended && (
                          <span className="text-xs px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-600 font-medium">推荐</span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-1 ml-6">{effectiveDesc}</p>
                      {DELIVERY_TYPE_TASK_PREVIEW[option.id] && (
                        <p className="text-xs text-gray-400 mt-1.5 ml-6">
                          预计生成任务：{DELIVERY_TYPE_TASK_PREVIEW[option.id].join(' / ')}
                        </p>
                      )}
                    </div>
                  );
                })}

              {/* 自定义新增的交付类型 */}
              {customDeliveries.map((option) => {
                const isSelected = selectedDeliveries.includes(option.id);
                const isDisabled = !isSelected && isDeliveryLimitReached;

                if (editingDeliveryId === option.id) {
                  return (
                    <div key={option.id}>
                      {renderInlineEditForm(
                        editDeliveryDraft,
                        setEditDeliveryDraft,
                        () => handleConfirmEditDelivery(option.id, true),
                        () => setEditingDeliveryId(null)
                      )}
                    </div>
                  );
                }

                return (
                  <div
                    key={option.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => !isDisabled && toggleDelivery(option.id)}
                    onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); if (!isDisabled) toggleDelivery(option.id); }}}
                    className={`group relative w-full text-left rounded-xl px-4 py-3 transition-all duration-200 ${
                      isSelected
                        ? 'bg-white border-l-4 border-l-blue-500 shadow-sm'
                        : isDisabled
                        ? 'bg-white border border-gray-200 opacity-50 cursor-not-allowed'
                        : 'bg-white border border-gray-200 hover:shadow-md cursor-pointer'
                    }`}
                  >
                    {renderEditDeleteButtons(
                      () => handleStartEditDelivery(option.id, option.label, option.desc),
                      () => handleDeleteDelivery(option.id, true)
                    )}
                    <div className="flex items-center gap-2 pr-14">
                      <div className={`w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                        isSelected ? 'border-blue-500 bg-blue-500' : 'border-gray-300'
                      }`}>
                        {isSelected && (
                          <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 12 12">
                            <path d="M10 3L5 8.5 2 5.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
                          </svg>
                        )}
                      </div>
                      <span className="text-sm font-medium text-gray-800">{option.label}</span>
                      <span className="text-xs px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 font-medium">自定义</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1 ml-6">{option.desc}</p>
                  </div>
                );
              })}

              {/* 内联新增输入框 */}
              {showAddDelivery && (
                <div className="bg-white border border-dashed border-blue-300 rounded-xl px-4 py-3 space-y-2">
                  <input
                    type="text"
                    value={newDeliveryLabel}
                    onChange={e => setNewDeliveryLabel(e.target.value)}
                    placeholder="交付类型名称（必填）"
                    className="input-sm"
                    autoFocus
                  />
                  <textarea
                    value={newDeliveryDesc}
                    onChange={e => setNewDeliveryDesc(e.target.value)}
                    placeholder="交付类型描述（必填）"
                    rows={2}
                    className="input-sm resize-none"
                  />
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleConfirmAddCustomDelivery}
                      disabled={!newDeliveryLabel.trim() || !newDeliveryDesc.trim()}
                      className="px-3 py-1 bg-blue-500 hover:bg-blue-600 disabled:opacity-40 text-white text-sm rounded-lg transition-colors"
                    >
                      确认添加
                    </button>
                    <button
                      onClick={() => { setShowAddDelivery(false); setNewDeliveryLabel(''); setNewDeliveryDesc(''); }}
                      className="px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-600 text-sm rounded-lg transition-colors"
                    >
                      取消
                    </button>
                  </div>
                </div>
              )}

              {/* + 按钮 */}
              {!showAddDelivery && (
                <div className="flex items-center gap-4 pt-1">
                  <div className="flex-1 border-t border-dashed border-gray-300" />
                  <button
                    onClick={() => setShowAddDelivery(true)}
                    disabled={isDeliveryLimitReached}
                    title={isDeliveryLimitReached ? `已达上限 ${maxSelect} 项` : '添加自定义交付类型'}
                    className="transition-all disabled:opacity-40 disabled:cursor-not-allowed group"
                  >
                    <div className="w-8 h-8 rounded-full bg-gray-100 group-hover:bg-gray-200 flex items-center justify-center transition-colors">
                      <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                    </div>
                  </button>
                  <div className="flex-1 border-t border-dashed border-gray-300" />
                </div>
              )}
            </div>
          </div>
        )}

        {/* 🆕 v12.1: 设计参考（合并视觉参考 + 文档参考 + 文字补充） */}
        <div>

          {/* ── 📷图片参考 ── */}
          <div className="mb-4">
            <div className="flex items-center mb-2">
              <span className="text-xs font-medium text-gray-600 flex items-center gap-1">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                图片参考
                {intentFiles.length > 0 && (
                  <span className="text-gray-400">({intentFiles.length}/{MAX_IMAGE_COUNT})</span>
                )}
              </span>
            </div>
            <input
              ref={intentFileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg,image/webp"
              className="hidden"
              onChange={e => { if (e.target.files) { handleIntentFileAdd(e.target.files); e.target.value = ''; } }}
            />
            {intentFiles.length > 0 && (
              <div className="space-y-3 mb-2">
                {intentFiles.map(entry => (
                  <div key={entry.id} className="flex items-start gap-3 bg-white border border-gray-200 rounded-xl p-3 group relative">
                    {/* 缩略图 */}
                    <div className="w-16 self-stretch flex-shrink-0 rounded-lg overflow-hidden border border-gray-100 bg-gray-50 relative">
                      {entry.previewUrl && (
                        <button type="button" onClick={() => setLightboxUrl(entry.previewUrl!)} className="block w-full h-full cursor-zoom-in" title="点击查看大图">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={entry.previewUrl} alt={entry.file.name} className="w-full h-full object-cover hover:opacity-80 transition-opacity" />
                        </button>
                      )}
                      {entry.status === 'uploading' && (
                        <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                          <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
                        </div>
                      )}
                      {entry.status === 'error' && (
                        <div className="absolute inset-0 bg-red-500/60 flex items-center justify-center">
                          <span className="text-white text-xs font-medium">失败</span>
                        </div>
                      )}
                    </div>
                    {/* 描述输入 */}
                    <div className="flex-1 min-w-0">
                      <textarea
                        value={entry.description}
                        onChange={e => handleImageDescriptionChange(entry.id, e.target.value)}
                        placeholder="必填 · 说明图片类型和用途，如：客厅平面草图 / 现场实拍照片 / 北欧风格参考 / 甲方提供的效果图"
                        rows={3}
                        className={`w-full h-full px-2.5 py-1.5 border rounded-lg text-sm text-gray-800 placeholder:text-gray-400 focus:ring-2 focus:outline-none resize-none ${
                          entry.status === 'done' && !entry.description.trim()
                            ? 'border-red-300 bg-red-50/30 focus:ring-red-300'
                            : 'border-gray-200 focus:ring-blue-400'
                        }`}
                      />
                    </div>
                    {/* 删除按钮 */}
                    {entry.status !== 'uploading' && (
                      <button
                        onClick={() => handleIntentFileDelete(entry.id)}
                        className="absolute top-2 right-2 w-5 h-5 rounded-full bg-gray-100 hover:bg-red-100 text-gray-400 hover:text-red-500 hidden group-hover:flex items-center justify-center transition-colors"
                        title="删除此参考图"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
            {intentUploadError && (
              <p className="text-xs text-red-500 mb-2">{intentUploadError}</p>
            )}
            <button
              onClick={() => intentFileInputRef.current?.click()}
              disabled={!sessionId || sessionId === 'default' || intentFiles.length >= MAX_IMAGE_COUNT}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl border border-dashed border-gray-300 hover:border-blue-400 hover:bg-blue-50/30 text-sm text-gray-400 hover:text-blue-500 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              添加参考图（JPG/PNG/WebP，最大 10MB），传达平面、视觉风格、色彩、材质等；
            </button>
          </div>

          {/* 分隔线 */}
          <div className="border-t border-gray-100 my-3" />

          {/* ── 📄文档参考 ── */}
          <div className="mb-4">
            <div className="flex items-center mb-2">
              <span className="text-xs font-medium text-gray-600 flex items-center gap-1">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                文档参考
              </span>
            </div>
            <input
              ref={docFileInputRef}
              type="file"
              accept=".pdf,.doc,.docx,.txt"
              className="hidden"
              onChange={e => { if (e.target.files) { handleDocFileAdd(e.target.files); e.target.value = ''; } }}
            />
            {docFiles.length > 0 && (
              <div className="space-y-3 mb-2">
                {docFiles.map(entry => (
                  <div key={entry.id} className="flex items-start gap-3 bg-white border border-gray-200 rounded-xl p-3 group relative">
                    {/* 文件图标区 */}
                    <div className="w-16 self-stretch flex-shrink-0 rounded-lg overflow-hidden border border-gray-100 bg-gray-50 flex flex-col items-center justify-center gap-1 relative">
                      <span className="text-2xl leading-none">📄</span>
                      <span className="text-[10px] text-gray-400 font-medium uppercase">
                        {entry.file.name.split('.').pop()}
                      </span>
                      {entry.status === 'uploading' && (
                        <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                          <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
                        </div>
                      )}
                      {entry.status === 'error' && (
                        <div className="absolute inset-0 bg-red-500/60 flex items-center justify-center">
                          <span className="text-white text-xs font-medium">失败</span>
                        </div>
                      )}
                    </div>
                    {/* 描述输入 */}
                    <div className="flex-1 min-w-0">
                      <textarea
                        value={entry.description}
                        onChange={e => handleDocDescriptionChange(entry.id, e.target.value)}
                        placeholder="必填 · 说明文档类型和用途，如：甲方任务书 / 原始平面图纸 / 项目说明书 / 竞品参考报告"
                        rows={3}
                        className={`w-full h-full px-2.5 py-1.5 border rounded-lg text-sm text-gray-800 placeholder:text-gray-400 focus:ring-2 focus:outline-none resize-none ${
                          entry.status === 'done' && !entry.description.trim()
                            ? 'border-red-300 bg-red-50/30 focus:ring-red-300'
                            : 'border-gray-200 focus:ring-blue-400'
                        }`}
                      />
                    </div>
                    {/* 删除按钮 */}
                    {entry.status !== 'uploading' && (
                      <button
                        onClick={() => setDocFiles(prev => prev.filter(f => f.id !== entry.id))}
                        className="absolute top-2 right-2 w-5 h-5 rounded-full bg-gray-100 hover:bg-red-100 text-gray-400 hover:text-red-500 hidden group-hover:flex items-center justify-center transition-colors"
                        title="删除此文档"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
            {docUploadError && (
              <p className="text-xs text-red-500 mb-2">{docUploadError}</p>
            )}
            <button
              onClick={() => docFileInputRef.current?.click()}
              disabled={!sessionId || sessionId === 'default'}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-dashed border-gray-300 hover:border-blue-400 hover:bg-blue-50/30 text-sm text-gray-400 hover:text-blue-500 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              添加甲方任务书 / 设计说明等文档（PDF/Word/TXT）
            </button>
          </div>

        </div>
      </div>
    );
  };

  // 🆕 v13.0: 渲染 Step 4 - 需求洞察（复盘面板 + 校正后任务列表 + 深度洞察）
  const renderStep4Content = () => {
    const tasks: any[] = stepData?.confirmed_core_tasks || [];
    const taskGroups: any[] = stepData?.task_groups || [];
    const projectEssence: string = stepData?.project_essence || '';
    const keyConflicts: any[] = stepData?.key_conflicts || [];
    const implicitReqs: any[] = stepData?.implicit_requirements || [];
    // 🆕 v13.0: 复盘对象
    const review: any = stepData?.task_calibration_review || null;
    const counts = review?.counts || {};
    const effectiveness = review?.effectiveness || {};

    // 优先检测 loading 状态（雷达图提交后立即切屏时）
    if (stepData?.isLoading || (tasks.length === 0 && !stepData?.restructured_requirements)) {
      return <QuestionnaireSkeletonLoader type="insights" message="正在生成需求洞察..." />;
    }

    // 按 task_groups 分组渲染，无分组时退化为平铺
    type RenderGroup = { category: string | null; taskItems: any[] };
    const renderGroups: RenderGroup[] = [];
    if (taskGroups.length > 0 && tasks.length > 0) {
      const idToTask: Record<string, any> = {};
      tasks.forEach(t => { if (t.id) idToTask[t.id] = t; });
      const assigned = new Set<string>();
      for (const g of taskGroups) {
        const items: any[] = [];
        for (const tid of (g.task_ids || [])) {
          if (idToTask[tid] && !assigned.has(tid)) {
            items.push(idToTask[tid]);
            assigned.add(tid);
          }
        }
        if (items.length > 0) renderGroups.push({ category: g.category || null, taskItems: items });
      }
      const remaining = tasks.filter(t => !assigned.has(t.id));
      if (remaining.length > 0) renderGroups.push({ category: null, taskItems: remaining });
    } else if (tasks.length > 0) {
      renderGroups.push({ category: null, taskItems: tasks });
    }

    const priorityStyles: Record<string, string> = {
      high: 'bg-red-50 text-red-700 border border-red-200',
      medium: 'bg-amber-50 text-amber-700 border border-amber-200',
      low: 'bg-gray-50 text-gray-600 border border-gray-200',
    };
    const priorityLabels: Record<string, string> = { high: 'P0 核心', medium: 'P1 重要', low: 'P2 补充' };

    // 校正动作 badge 样式
    const correctionBadge = (action: string) => {
      switch (action) {
        case 'added':
          return <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700 font-medium">+新增</span>;
        case 'enhanced':
          return <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-medium">↑优化</span>;
        case 'reprioritized':
          return <span className="text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 font-medium">⬆强化</span>;
        case 'invalidated':
          return <span className="text-xs px-1.5 py-0.5 rounded bg-gray-200 text-gray-500 font-medium">⚠无效</span>;
        default:
          return null;
      }
    };

    let globalNum = 0;

    return (
      <div className="space-y-5">
        {/* 项目本质横幅 */}
        {projectEssence && (
          <div className="rounded-xl bg-blue-50 border border-blue-100 px-5 py-4">
            <p className="text-xs font-semibold text-blue-600 uppercase tracking-wider mb-1">项目本质</p>
            <p className="text-gray-800 font-medium leading-relaxed">&ldquo;{projectEssence}&rdquo;</p>
          </div>
        )}

        {/* 🆕 v13.0: 复盘面板 */}
        {review ? (
          <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
            {/* 动态 summary_line */}
            <div className="px-5 py-3 bg-gradient-to-r from-gray-50 to-white border-b border-gray-100">
              <p className="text-sm text-gray-600 leading-relaxed">
                {review.summary_line || 'AI 已综合信息补全与偏好设置，完成任务校正'}
              </p>
            </div>

            {/* 四卡网格：增加 / 无效动作 / 优化 / 强化 */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-gray-100">
              {/* 增加 */}
              <div className="bg-white px-4 py-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <span className="w-2 h-2 rounded-full bg-green-400" />
                  <span className="text-xs font-semibold text-gray-500">增加</span>
                </div>
                <p className="text-xl font-bold text-gray-900">{counts.added || 0}</p>
                {(review.added_items || []).slice(0, 2).map((item: any, i: number) => (
                  <p key={i} className="text-xs text-gray-500 mt-1 truncate">{item.title}</p>
                ))}
              </div>
              {/* 无效动作 */}
              <div className="bg-white px-4 py-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <span className="w-2 h-2 rounded-full bg-gray-400" />
                  <span className="text-xs font-semibold text-gray-500">无效动作</span>
                </div>
                <p className="text-xl font-bold text-gray-900">{counts.invalidated || 0}</p>
                {(review.invalidated_items || []).slice(0, 2).map((item: any, i: number) => (
                  <p key={i} className="text-xs text-gray-500 mt-1 truncate">{item.title}</p>
                ))}
              </div>
              {/* 优化（信息补全） */}
              <div className="bg-white px-4 py-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <span className="w-2 h-2 rounded-full bg-blue-400" />
                  <span className="text-xs font-semibold text-gray-500">约束优化</span>
                </div>
                <p className="text-xl font-bold text-gray-900">{counts.optimized || 0}</p>
                {(review.optimized_items || []).slice(0, 2).map((item: any, i: number) => (
                  <p key={i} className="text-xs text-gray-500 mt-1 truncate">{item.label}: {item.evidence}</p>
                ))}
              </div>
              {/* 🔄 v14.0: 设计驱动力（替代原始权重数字） */}
              <div className="bg-white px-4 py-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <span className="w-2 h-2 rounded-full bg-purple-400" />
                  <span className="text-xs font-semibold text-gray-500">设计驱动力</span>
                </div>
                <p className="text-xl font-bold text-gray-900">{counts.strengthened || 0}</p>
                {(review.strengthened_items || []).slice(0, 2).map((item: any, i: number) => (
                  <p key={i} className="text-xs text-gray-500 mt-1 truncate">
                    {item.label}{item.design_driver ? ` · ${item.design_driver}` : (item.weight ? `·${item.weight}` : '')}
                    {item.tendency_label ? ` → ${item.tendency_label}` : (item.tendency ? ` → ${item.tendency}` : '')}
                  </p>
                ))}
              </div>
            </div>

            {/* 🔄 v14.0: 效果检验行 — 显示覆盖率 */}
            <div className="px-5 py-2.5 bg-gray-50 border-t border-gray-100 flex items-center gap-4 flex-wrap">
              <span className="text-xs text-gray-400">效果检验</span>
              <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
                effectiveness.gap_filling_effective
                  ? 'bg-green-50 text-green-700 border border-green-200'
                  : 'bg-gray-100 text-gray-500 border border-gray-200'
              }`}>
                {effectiveness.gap_filling_effective ? '✓' : '–'} 信息补全{effectiveness.gap_filling_effective ? '有效' : '待增强'}
              </span>
              <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
                effectiveness.radar_effective
                  ? 'bg-green-50 text-green-700 border border-green-200'
                  : 'bg-gray-100 text-gray-500 border border-gray-200'
              }`}>
                {effectiveness.radar_effective ? '✓' : '–'} 维度响应
                {effectiveness.radar_evidence?.coverage_rate != null
                  ? ` ${Math.round(effectiveness.radar_evidence.coverage_rate * 100)}%`
                  : (effectiveness.radar_effective ? '有效' : '待增强')}
              </span>
            </div>

            {/* 🆕 v14.0: 维度响应对账 */}
            {review.radar_response_ledger && review.radar_response_ledger.length > 0 && (
              <div className="px-5 py-2.5 border-t border-gray-100">
                <p className="text-xs text-gray-400 mb-1.5">维度响应对账</p>
                <div className="flex flex-wrap gap-1.5">
                  {review.radar_response_ledger.slice(0, 6).map((item: any, i: number) => (
                    <span
                      key={i}
                      className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${
                        item.responded
                          ? 'bg-green-50 text-green-700 border-green-200'
                          : 'bg-amber-50 text-amber-700 border-amber-200'
                      }`}
                    >
                      {item.responded ? '✓' : '○'} {item.dimension_label}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* 向后兼容：旧会话无 review 时显示静态文案 */
          <p className="text-sm text-gray-500">AI 已综合信息补全与偏好设置，以下为校正后的任务清单</p>
        )}

        {/* 校正后任务清单 */}
        {tasks.length > 0 && (
          <div className="space-y-6">
            <div className="task-list-container space-y-6">
              {renderGroups.map((group, gi) => (
                <div key={gi}>
                  {group.category && (
                    <div className="flex items-center gap-2 mb-3 mt-2">
                      <div className="h-px flex-1 bg-gray-200" />
                      <span className="px-3 py-1 text-base font-bold text-gray-700 bg-gray-100 rounded-full whitespace-nowrap">{group.category}</span>
                      <div className="h-px flex-1 bg-gray-200" />
                    </div>
                  )}
                  <div className="space-y-3">
                    {group.taskItems.map((task: any) => {
                      globalNum += 1;
                      const num = globalNum;
                      const pri = task.priority || 'medium';
                      const cAction = task._correction_action || '';
                      const isInvalidated = cAction === 'invalidated';
                      return (
                        <div key={task.id || num} className={`card-white ${isInvalidated ? 'opacity-50' : ''}`}>
                          <div className="flex items-start gap-3">
                            <div className="step-badge w-8 h-8 text-sm">{num}</div>
                            <div className="flex-1 min-w-0 space-y-2">
                              <div className="flex items-center gap-2 flex-wrap">
                                <h4 className={`font-medium ${isInvalidated ? 'text-gray-400 line-through' : 'text-gray-900'}`}>{task.title}</h4>
                                {correctionBadge(cAction)}
                                {task.motivation_label && (
                                  <span className="badge-gray flex-shrink-0">{task.motivation_label}</span>
                                )}
                              </div>
                              {task.description && (
                                <p className="text-sm text-gray-600 leading-relaxed">{task.description}</p>
                              )}
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${priorityStyles[pri] || priorityStyles.medium}`}>
                                  {priorityLabels[pri] || pri}
                                </span>
                                {task.expected_output && (
                                  <span className="text-xs text-gray-400">产出：{task.expected_output}</span>
                                )}
                                {task._correction_reason && cAction !== 'unchanged' && (
                                  <span className="text-xs text-gray-400 italic">({task._correction_reason})</span>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 深度洞察折叠区 */}
        {(keyConflicts.length > 0 || implicitReqs.length > 0) && (
          <div className="border border-gray-200 rounded-xl overflow-hidden">
            <button
              onClick={() => setIsInsightsExpanded(v => !v)}
              className="w-full flex items-center justify-between px-5 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
            >
              <span className="text-sm font-semibold text-gray-700">深度洞察（关键冲突 / 隐性需求）</span>
              <svg
                className={`w-4 h-4 text-gray-500 transition-transform ${isInsightsExpanded ? 'rotate-180' : ''}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {isInsightsExpanded && (
              <div className="px-5 py-4 space-y-4 bg-white">
                {keyConflicts.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">关键冲突</p>
                    <ul className="space-y-1">
                      {keyConflicts.map((c: any, i: number) => (
                        <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                          <span className="mt-1 w-1.5 h-1.5 rounded-full bg-gray-400 flex-shrink-0" />
                          {typeof c === 'string' ? c : c.description || JSON.stringify(c)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {implicitReqs.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">隐性需求</p>
                    <ul className="space-y-1">
                      {implicitReqs.map((r: any, i: number) => (
                        <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                          <span className="mt-1 w-1.5 h-1.5 rounded-full bg-blue-300 flex-shrink-0" />
                          {typeof r === 'string' ? r : r.requirement || r.description || JSON.stringify(r)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  // 🔄 v10.2 Path B: 不再需要过渡加载状态（Step 0→Step 1 是本地切换，无网络往返）

  const _uqmOuterCls = inline
    ? 'flex-1 flex flex-col overflow-hidden'
    : 'fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4';
  const _uqmInnerCls = inline
    ? 'bg-[var(--card-bg)] w-full overflow-hidden flex flex-col rounded-2xl'
    : 'ui-card-shell ui-card-shell-strong bg-white rounded-2xl max-w-6xl w-full h-[85vh] overflow-hidden flex flex-col';
  return (
    <div className={_uqmOuterCls}>
      {isLoading ? (
        // 加载页面 - 保持步骤一致性
        <div className={_uqmInnerCls}>

          {/* 步骤指示器 - 仅非内联模式显示 */}
          {!inline && (
          <div className="border-b border-gray-200 bg-white px-10 py-4">
            <div className="flex items-center mb-4">
              {allSteps.map((step, index) => (
                <Fragment key={step.number}>
                  <div className="flex flex-col items-center" style={{minWidth: '72px'}}>
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-medium transition-all duration-300 ${
                      effectiveStep === step.number
                        ? 'bg-blue-600 text-white shadow-md'
                        : effectiveStep > step.number
                        ? 'bg-gray-500 text-white'
                        : 'bg-gray-100 text-gray-400'
                    }`}>
                      {effectiveStep > step.number ? (
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        step.icon
                      )}
                    </div>
                    <span className={`mt-2 text-sm font-medium ${
                      effectiveStep === step.number ? 'text-gray-800' : 'text-gray-500'
                    }`}>
                      {step.label}
                    </span>
                  </div>

                  {index < allSteps.length - 1 && (
                    <div className={`h-px flex-1 mx-2 rounded-full transition-all duration-500 ${
                      effectiveStep > step.number ? 'bg-green-500' : 'bg-gray-300'
                    }`} />
                  )}
                </Fragment>
              ))}
            </div>
          </div>
          )}

          {/* Header - 需求显示（仅非内联模式）*/}
          {!inline && (
          <div className="border-b border-gray-200 px-10 bg-white" style={{minHeight: '80px', display: 'flex', alignItems: 'center'}}>
            <div className="flex items-center gap-2 w-full py-5">
              <span className="text-sm font-medium text-gray-700 flex-shrink-0">需求：</span>
              <span className="text-sm leading-snug text-gray-600 line-clamp-2 flex-1 min-w-0">
                {stepData?.user_input || stepData?.user_input_summary || userInputProp || ''}
              </span>
            </div>
          </div>
          )}

          {/* 加载内容区域 - 使用骨架屏 */}
          <div className={`flex-1 overflow-y-auto ${inline ? 'px-4 py-4' : 'px-10 py-6 bg-[#f5f5f7]'}`}>
            <QuestionnaireSkeletonLoader
              type={
                currentStep === 2 ? 'tasks' :
                currentStep === 3 ? 'questions' :
                currentStep === 4 ? 'radar' :
                'insights'
              }
              message={currentStep === 3 ? '正在分析缺失的信息项...' : loadingMessage}
            />
          </div>
        </div>
      ) : (
        // 正常的问卷界面
      <div className={_uqmInnerCls}>

        {/* 步骤指示器 - 仅非内联模式显示 */}
        {!inline && (
        <div className="border-b border-gray-200 bg-white px-10 py-4">
          <div className="flex items-center mb-4">
            {allSteps.map((step, index) => (
              <Fragment key={step.number}>
                <div className="flex flex-col items-center" style={{minWidth: '72px'}}>
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-medium transition-all duration-300 ${
                    effectiveStep === step.number
                      ? 'bg-blue-600 text-white shadow-md'
                      : effectiveStep > step.number
                      ? 'bg-gray-500 text-white'
                      : 'bg-gray-100 text-gray-400'
                  }`}>
                    {effectiveStep > step.number ? '✓' : step.icon}
                  </div>
                  <div className={`mt-2 text-xs font-medium text-center transition-colors ${
                    effectiveStep === step.number
                      ? 'text-gray-800'
                      : effectiveStep > step.number
                      ? 'text-gray-700'
                      : 'text-gray-500'
                  }`}>
                    {step.label}
                  </div>
                </div>
                {index < allSteps.length - 1 && (
                  <div className={`h-px flex-1 mx-2 rounded-full transition-all duration-500 ${
                    effectiveStep > step.number
                      ? 'bg-green-500'
                      : 'bg-gray-300'
                  }`} />
                )}
              </Fragment>
            ))}
          </div>
        </div>
        )}

        {/* Header（仅非内联模式显示）*/}
        {!inline && (
        <div className="border-b border-gray-200 px-10 bg-white" style={{minHeight: '80px', display: 'flex', alignItems: 'center'}}>
          {/* 固定需求显示 - 所有步骤通用，固定高度不可交互 */}
          <div className="flex items-center gap-2 w-full py-5">
            <span className="text-sm font-medium text-gray-700 flex-shrink-0">需求：</span>
            <span className="text-sm leading-snug text-gray-600 line-clamp-2 flex-1 min-w-0">
              {stepData?.user_input || stepData?.user_input_summary || userInputProp || ''}
            </span>
          </div>
        </div>
        )}

        {/* Content */}
        <div ref={contentRef} className={`flex-1 overflow-y-auto ${inline ? 'px-4 py-4' : 'px-10 py-6 bg-[#f5f5f7]'}`}>
          <div className={`transition-all duration-200 ${isTransitioning ? 'opacity-0 translate-y-2' : 'opacity-100 translate-y-0'}`}>
            {renderContent()}
          </div>
        </div>

        {/* Footer */}
        <div className={`${inline ? 'px-4 py-3 border-t border-[var(--border-color)]' : 'px-10 py-4 bg-white'} flex items-center justify-end gap-3`}>
          <button
            onClick={handleConfirmClick}
            disabled={
              isLoading ||
              (currentStep === 3 && !validateStep3Required()) ||
              (isOutputIntentStep && selectedDeliveries.length === 0) ||
              (isOutputIntentStep && intentFiles.some(f => f.status === 'done' && !f.description.trim())) ||
              (isOutputIntentStep && docFiles.some(f => f.status === 'done' && !f.description.trim()))
            }
            className="btn-primary-lg flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>{getConfirmButtonText()}</span>
            {(isOutputIntentStep || currentStep < 5) && <ArrowRight className="w-4 h-4" />}
          </button>
        </div>
      </div>
      )}

      {/* 图片浮窗预览 */}
      {lightboxUrl && (
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 cursor-pointer"
          onClick={() => setLightboxUrl(null)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={lightboxUrl}
            alt="预览"
            className="max-w-[90vw] max-h-[90vh] rounded-xl shadow-2xl object-contain"
          />
        </div>
      )}
    </div>
  );
}
