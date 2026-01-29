'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft,
  Search,
  ExternalLink,
  Image as ImageIcon,
  ChevronRight,
  Loader2,
  Send,
  ArrowUp,
  Brain,
  Sparkles,
  CheckCircle,
  AlertCircle,
  Globe,
  Clock,
  Star,
  History,
  X,
  MessageCircle,
  Target,
  ListChecks,
  Circle,
  Bug,
  Trash2,
  Plus,
  Edit3,
  Check,
  ChevronLeft,
  PanelLeft,        // 🆕 v7.283: 侧边栏切换按钮
  Shield,           // v7.281: 置信度图标
  Link as LinkIcon, // v7.281: 引用图标
  AlertTriangle,    // v7.281: 冲突警告图标
} from 'lucide-react';
import { UserQuestionCard } from '@/components/UserQuestionCard';  // v7.290: 用户问题卡片公共组件

// ============================================================================
// v7.222: 调试模式配置
// ============================================================================
const DEBUG_MODE = process.env.NODE_ENV === 'development';  // 开发环境自动启用
const DEBUG_SSE_EVENTS = DEBUG_MODE;  // SSE事件日志
const DEBUG_STATE_CHANGES = DEBUG_MODE;  // 状态变化日志
const DEBUG_PHASE_TRANSITIONS = DEBUG_MODE;  // 阶段转换日志
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ImageViewer from '@/components/search/ImageViewer';
import DeepAnalysisCard from '@/components/search/DeepAnalysisCard';
import FourMissionsDisplay from '@/components/search/FourMissionsDisplay';  // v7.302: 4条使命展示
import Step2TaskListEditor from '@/components/search/Step2TaskListEditor';  // v7.300: 可编辑任务列表
import type { DeepAnalysisResult, Step2SearchPlan, EditableSearchStep, FourMissions } from '@/types';
// v7.290: 搜索页面为独立体验，移除侧边栏组件

// 类型定义
interface SourceCard {
  title: string;
  url: string;
  siteName: string;
  siteIcon: string;
  snippet: string;
  summary: string;
  datePublished: string;
  referenceNumber: number;
  isWhitelisted: boolean;
  id?: string;       // 🆕 v7.167: 完整ID
  shortId?: string;  // 🆕 v7.167: 短ID用于引用格式 [编号:短ID]
}

interface ImageResult {
  url: string;
  thumbnailUrl: string;
  title: string;
  sourceUrl: string;
  width: number;
  height: number;
}

// v7.282: 搜索目标类型（新主用接口，替代 SearchTask）
interface SearchTarget {
  id: string;
  question: string;           // 要回答什么问题
  search_for: string;         // 具体搜索内容
  why_need: string;           // 贡献说明
  success_when: string[];     // 成功标准
  preset_keywords: string[];  // 预设搜索词
  priority: number;
  status: 'pending' | 'searching' | 'partial' | 'complete';
  completion_score: number;
  category: string;           // 动机类型
  can_parallel: boolean;
  dependencies: string[];
}

// v7.208: 搜索任务类型
// ⚠️ REMOVED (v7.301): SearchTask 和 SearchMasterLine 已完全移除
// 使用 FrameworkChecklist 作为唯一的搜索方向展示

// v7.240: 框架清单类型
// v7.270.1: 添加向后兼容字段 (name, description) 用于处理旧数据
interface FrameworkChecklist {
  core_summary: string;
  main_directions: Array<{
    direction?: string;
    purpose?: string;
    expected_outcome?: string;
    // 向后兼容字段
    name?: string;
    description?: string;
  }>;
  boundaries: string[];
  answer_goal: string;
  generated_at: string;
  plain_text: string;

  // v7.250 新增：深度分析摘要
  user_context?: {
    identity: string;
    occupation: string;
    implicit_needs: string[];
  };
  key_entities?: Array<{
    type: string;
    name: string;
    detail: string;
  }>;
  analysis_perspectives?: string[];
  core_tension?: string;
  user_task?: string;
  sharpness_check?: {
    specificity: string;
    actionability: string;
    depth: string;
  };
}

// v7.208: 任务进度类型
// ⚠️ REMOVED (v7.301): TaskProgress 已移除，进度追踪将整合到 FrameworkChecklist

// v7.170: 搜索主题
interface SearchTopic {
  topicId: number;
  topicName: string;
  searchQuery: string;
  purpose: string;
}

// v7.170: 搜索计划
interface SearchPlan {
  analysis: string;
  aspects: string[];
  topics: SearchTopic[];
  totalRounds: number;
  strategy: string;
}

// v7.170: 轮次记录
interface RoundRecord {
  round: number;
  topicName: string;
  searchQuery: string;
  sourcesFound: number;
  sources: SourceCard[];
  executionTime?: number;
  status: 'pending' | 'searching' | 'complete';
  // v7.188: 思考内容（融入轮次而非单独卡片）
  reasoningContent?: string;  // 推理过程（is_reasoning=true）
  thinkingContent?: string;   // 最终思考（is_reasoning=false）
  showThinking?: boolean;     // 是否展开思考内容
  // v7.191: 问题分析阶段标记
  isAnalysisPhase?: boolean;  // 是否为问题分析阶段（Round 0）
}

// v7.170: 搜索状态
// v7.222: 添加 currentPhase 明确区分三个流程阶段
interface SearchState {
  // 基础状态
  status: 'idle' | 'planning' | 'searching' | 'thinking' | 'answering' | 'analyzing' | 'done' | 'error';
  statusMessage: string;

  // v7.222: 明确的阶段标识（解决时序混乱问题）
  // - 'analysis': Phase 0 需求理解与深度分析（DeepSeek推理）
  // - 'search': Phase 2 多轮搜索（执行搜索计划）
  // - 'synthesis': Phase 3 答案生成（综合分析生成最终回答）
  currentPhase: 'idle' | 'analysis' | 'search' | 'synthesis' | 'done';

  // v7.205: L0 结构化信息提取
  l0Content: string;           // L0 流式内容（JSON 字符串）
  l0Phase: 'idle' | 'extracting' | 'complete';  // L0 阶段状态
  structuredInfo: StructuredUserInfo | null;    // L0 提取结果

  // v7.188: 问题分析阶段
  analysisContent: string;           // 流式分析推理内容
  analysisSaved?: boolean;           // v7.193: 标记分析是否已保存到 Round 0

  // Phase 1: 搜索规划
  searchPlan: SearchPlan | null;

  // Phase 2: 多轮搜索
  rounds: RoundRecord[];
  currentRound: number;
  totalRounds: number;

  // Phase 3: 深度思考（v7.188: 改为按轮次累积）
  thinkingContent: string;           // 保留用于兼容
  isThinking: boolean;
  currentRoundReasoning: string;     // v7.188: 当前轮推理过程
  currentRoundThinking: string;      // v7.188: 当前轮最终思考
  currentThinkingRound: number;      // v7.188: 当前正在累积思考的轮次

  // v7.218: 区分Phase 0解题思考和Phase 2轮次思考
  problemSolvingThinking: string;    // v7.218: Phase 0解题思考内容（只应有一轮）
  isProblemSolvingPhase: boolean;    // v7.218: 当前是否处于解题思考阶段

  // 🔧 v7.195: 按轮次独立存储思考内容，解决轮次切换时的内容回退问题
  roundThinkingMap: Record<number, { reasoning: string; thinking: string }>;

  // Phase 4: 回答
  answerContent: string;
  answerThinkingContent: string;  // 🆕 答案生成的思考过程
  isAnswering: boolean;

  // 结果
  sources: SourceCard[];
  images: ImageResult[];
  executionTime: number;
  error: string | null;

  // 深度模式标记
  isDeepMode: boolean;

  // v7.240: 框架清单（v7.301: 作为唯一的搜索方向展示）
  frameworkChecklist: FrameworkChecklist | null;

  // 🆕 v7.285: 等待用户确认框架清单后再开始搜索
  awaitingConfirmation: boolean;

  // 🆕 v7.280: 深度分析结果
  deepAnalysisResult: DeepAnalysisResult | null;

  // 🆕 v7.302: 4条使命结果
  fourMissionsResult: FourMissions | null;

  // v7.218: 分析进度状态（解决164秒无进度提示问题）
  analysisProgress: {
    stage: string;
    stageName: string;
    message: string;
    estimatedTime: number;
    currentStep: number;
    totalSteps: number;
    startTime?: number;
  } | null;

  // v7.226: 对话内容缓冲区（用于检测系统思考内容）
  _dialogueBuffer: string;

  // v7.281: 答案质量评估
  qualityAssessment: AnswerQualityAssessment | null;
}

// v7.281: 答案质量评估接口
interface AnswerQualityAssessment {
  confidence: {
    overall_confidence: number;
    confidence_level: string;  // "高" | "中" | "低"
    dimension_scores: {
      info_sufficiency: number;
      info_quality: number;
      source_coverage: number;
      consistency: number;
      goal_alignment: number;
    };
    confidence_note: string;
  };
  citation: {
    valid: boolean;
    total_citations: number;
    valid_citations: number[];
    invalid_citations: number[];
    citation_coverage: number;
    warning: string;
  };
  conflicts: {
    has_conflicts: boolean;
    count: number;
  };
}

// v7.205: L0 结构化用户信息类型
interface StructuredUserInfo {
  demographics: {
    location: string;
    location_context: string;
    age: string;
    age_context: string;
    gender: string;
    occupation: string;
    occupation_context: string;
    education: string;
    education_context: string;
  };
  identity_tags: string[];
  lifestyle: {
    living_situation: string;
    family_status: string;
    hobbies: string[];
    pets: string[];
  };
  project_context: {
    type: string;
    scale: string;
    scale_context: string;
    constraints: string[];
    budget_range: string;
    timeline: string;
  };
  preferences: {
    style_references: string[];
    style_keywords: string[];
    color_palette: string[];
    material_preferences: string[];
    cultural_influences: string[];
  };
  core_request: {
    explicit_need: string;
    implicit_needs: string[];
  };
  location_considerations: {
    climate: string;
    architecture: string;
    lifestyle: string;
  };
  completeness: {
    provided_dimensions: string[];
    missing_dimensions: string[];
    confidence_score: number;
  };
}

// v7.207: 统一分析展示组件（合并 L0 对话 + L1-L5 分析）
// v7.219: 增强流式输出效果
// v7.220: 合并 AnalysisProgressCard，消除重复卡片
const TaskUnderstandingCard = ({ content, isExpanded, onToggle, isLoading, isWaiting }: {
  content: string;
  isExpanded: boolean;
  onToggle: () => void;
  isLoading?: boolean;
  isWaiting?: boolean;  // v7.220: 等待 DeepSeek 响应中（尚未有流式内容）
}) => {
  // v7.220: 动态省略号效果 - Hooks 必须在条件判断之前调用
  const [dots, setDots] = useState('');
  useEffect(() => {
    if (!isWaiting || content) return;
    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 500);
    return () => clearInterval(interval);
  }, [isWaiting, content]);

  // v7.220: 等待中或加载中都应该显示
  if (!content && !isLoading && !isWaiting) return null;

  // v7.219: 流式输出或等待时强制展开
  const shouldExpand = isExpanded || isLoading || isWaiting;

  return (
    <div className="ucppt-card">
      {/* v7.243: 标题栏 - 使用统一样式类 - v7.300: 移除折叠功能，始终展开 */}
      <div className="ucppt-card-header ucppt-card-header-expanded">
        <div className="flex items-center gap-3">
          <div className={`ucppt-icon-circle ${isWaiting && !content ? 'ucppt-icon-indigo' : 'ucppt-icon-blue'}`}>
            {isWaiting && !content ? (
              <Brain className="w-4 h-4 text-indigo-600 dark:text-indigo-400 animate-pulse" />
            ) : (
              <Target className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className={isWaiting && !content ? 'ucppt-title-indigo' : 'ucppt-title-blue'}>
              需求理解与深度分析
            </span>
          </div>
        </div>
      </div>

      {/* 对话内容 - v7.219: 流式输出时也显示内容 - v7.300: 始终展开显示 */}
      {content && (
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700">
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <div className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
              {/* v7.219: 流式输出时显示光标 */}
              {isLoading && <span className="text-blue-500 animate-pulse">▋</span>}
            </div>
          </div>
        </div>
      )}

      {/* v7.220: 等待 DeepSeek 响应时的提示（合并自 AnalysisProgressCard） - 隐藏提示 */}
      {/* 用户反馈：不希望显示DeepSeek推理引擎启动提示 */}
      {/* {shouldExpand && isWaiting && !content && (
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
            <span className="text-indigo-600 dark:text-indigo-400">▋</span>
            <span className="ml-1">正在启动 DeepSeek 深度推理引擎{dots}</span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
            💡 正在调用 DeepSeek 深度推理引擎，思考内容将实时呈现
          </p>
        </div>
      )} */}

      {/* 加载中占位（流式输出开始但暂无内容时显示） - v7.300: 始终显示 */}
      {isLoading && !isWaiting && !content && (
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center gap-2 text-blue-500">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">正在理解您的需求并进行深度分析...</span>
        </div>
      )}
    </div>
  );
};

// v7.240: 框架清单展示组件
// v7.285: 可编辑版本 - 支持点击内容直接编辑、删除任务、添加任务
const FrameworkChecklistCard = ({
  checklist,
  isExpanded,
  onToggle,
  onUpdateChecklist,
}: {
  checklist: FrameworkChecklist | null;
  isExpanded: boolean;
  onToggle: () => void;
  onUpdateChecklist?: (updated: FrameworkChecklist) => void;
}) => {
  // 编辑状态管理
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingField, setEditingField] = useState<'direction' | 'purpose' | 'expected_outcome' | null>(null);
  const [editValue, setEditValue] = useState('');
  const [isAddingNew, setIsAddingNew] = useState(false);
  const [newDirection, setNewDirection] = useState({ direction: '', purpose: '', expected_outcome: '' });
  const editInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 当开始编辑时聚焦输入框
  useEffect(() => {
    if (editingIndex !== null && editInputRef.current) {
      editInputRef.current.focus();
    }
    if (isAddingNew && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [editingIndex, editingField, isAddingNew]);

  if (!checklist) return null;

  // 开始编辑某个字段
  const handleStartEdit = (index: number, field: 'direction' | 'purpose' | 'expected_outcome', currentValue: string) => {
    if (!onUpdateChecklist) return; // 如果没有更新回调，不允许编辑
    setEditingIndex(index);
    setEditingField(field);
    setEditValue(currentValue || '');
  };

  // 保存编辑
  const handleSaveEdit = () => {
    if (editingIndex === null || editingField === null || !onUpdateChecklist) return;

    const updatedDirections = [...checklist.main_directions];
    updatedDirections[editingIndex] = {
      ...updatedDirections[editingIndex],
      [editingField]: editValue,
    };

    onUpdateChecklist({
      ...checklist,
      main_directions: updatedDirections,
    });

    setEditingIndex(null);
    setEditingField(null);
    setEditValue('');
  };

  // 取消编辑
  const handleCancelEdit = () => {
    setEditingIndex(null);
    setEditingField(null);
    setEditValue('');
  };

  // 删除任务
  const handleDelete = (index: number) => {
    if (!onUpdateChecklist) return;
    if (!confirm('确定删除这个搜索方向吗？')) return;

    const updatedDirections = checklist.main_directions.filter((_, i) => i !== index);
    onUpdateChecklist({
      ...checklist,
      main_directions: updatedDirections,
    });
  };

  // 添加新任务
  const handleAddNew = () => {
    if (!onUpdateChecklist || !newDirection.direction.trim()) return;

    const updatedDirections = [...checklist.main_directions, {
      direction: newDirection.direction.trim(),
      purpose: newDirection.purpose.trim(),
      expected_outcome: newDirection.expected_outcome.trim(),
    }];

    onUpdateChecklist({
      ...checklist,
      main_directions: updatedDirections,
    });

    setNewDirection({ direction: '', purpose: '', expected_outcome: '' });
    setIsAddingNew(false);
  };

  // 键盘事件处理
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSaveEdit();
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  // 渲染可编辑的文本字段
  const renderEditableText = (
    index: number,
    field: 'direction' | 'purpose' | 'expected_outcome',
    value: string | undefined,
    placeholder: string,
    className: string
  ) => {
    const isEditing = editingIndex === index && editingField === field;
    const displayValue = value || '';

    if (isEditing) {
      return (
        <div className="flex items-center gap-1">
          <input
            ref={editInputRef}
            type="text"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleSaveEdit}
            className="flex-1 px-2 py-1 text-sm border border-indigo-300 dark:border-indigo-600 rounded bg-white dark:bg-gray-900 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            placeholder={placeholder}
          />
          <button
            onClick={handleSaveEdit}
            className="p-1 text-emerald-500 hover:text-emerald-600 dark:text-emerald-400"
            title="保存"
          >
            <Check className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleCancelEdit}
            className="p-1 text-gray-400 hover:text-gray-500"
            title="取消"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      );
    }

    return (
      <span
        onClick={(e) => {
          e.stopPropagation();
          handleStartEdit(index, field, displayValue);
        }}
        className={`${className} ${onUpdateChecklist ? 'cursor-text hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded px-1 -mx-1 transition-colors' : ''}`}
        title={onUpdateChecklist ? '点击编辑' : undefined}
      >
        {displayValue || <span className="italic text-gray-400">{placeholder}</span>}
      </span>
    );
  };

  return (
    <div className="ucppt-card">
      {/* v7.243: 标题栏 - 使用统一样式类 - v7.300: 移除折叠功能，始终展开 */}
      <div className="ucppt-card-header ucppt-card-header-expanded">
        <div className="flex items-center gap-3">
          <div className="ucppt-icon-circle ucppt-icon-indigo">
            <Target className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div className="flex items-center gap-2">
            <span className="ucppt-title-indigo">
              搜索框架清单
            </span>
            {/* 已隐藏: {checklist.main_directions.length}个方向 徽章 */}
            {/* 已隐藏: (可编辑) 文本 */}
          </div>
        </div>
      </div>

      {/* 内容区域 - v7.300: 始终显示 */}
      <div className="ucppt-card-content space-y-4">
        {/* 已隐藏: 核心问题卡片 */}

        {/* 搜索主线 - 可编辑版本 */}
          <div>
            {/* 已隐藏: 搜索主线标题和可编辑提示 */}
            <div className="space-y-2">
              {checklist.main_directions.map((direction, index) => (
                <div
                  key={index}
                  className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700 group relative"
                >
                  <div className="flex items-start gap-2">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-indigo-500 text-white text-xs flex items-center justify-center font-medium mt-0.5">
                      {index + 1}
                    </span>
                    <div className="flex-1 min-w-0 space-y-1">
                      {/* 任务名称 - 可编辑 */}
                      <div className="text-sm font-medium text-gray-800 dark:text-gray-200">
                        {renderEditableText(
                          index,
                          'direction',
                          direction.direction || direction.name,
                          '输入搜索方向...',
                          ''
                        )}
                      </div>
                      {/* 目的 - 可编辑 */}
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        <span className="text-indigo-500 dark:text-indigo-400">目的:</span>{' '}
                        {renderEditableText(
                          index,
                          'purpose',
                          direction.purpose || direction.description,
                          '描述搜索目的...',
                          ''
                        )}
                      </div>
                      {/* 期望结果 - 可编辑 */}
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        <span className="text-emerald-500 dark:text-emerald-400">期望:</span>{' '}
                        {renderEditableText(
                          index,
                          'expected_outcome',
                          direction.expected_outcome,
                          '描述期望结果...',
                          ''
                        )}
                      </div>
                    </div>
                    {/* 删除按钮 */}
                    {onUpdateChecklist && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(index);
                        }}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 text-red-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                        title="删除此搜索方向"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* 添加新任务 */}
            {onUpdateChecklist && (
              <div className="mt-3">
                {isAddingNew ? (
                  <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                    <div className="flex items-start gap-2 mb-3">
                      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-indigo-500 text-white text-xs flex items-center justify-center font-medium mt-0.5">
                        {checklist.main_directions.length + 1}
                      </span>
                      <div className="flex-1 space-y-2">
                        <textarea
                          value={newDirection.direction}
                          onChange={(e) => setNewDirection({ ...newDirection, direction: e.target.value })}
                          className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-indigo-500 focus:outline-none resize-none"
                          placeholder="输入搜索方向名称..."
                          rows={2}
                        />
                        <textarea
                          value={newDirection.purpose}
                          onChange={(e) => setNewDirection({ ...newDirection, purpose: e.target.value })}
                          className="w-full px-3 py-2 text-xs border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 focus:ring-2 focus:ring-indigo-500 focus:outline-none resize-none"
                          placeholder="目的: 描述搜索目的..."
                          rows={2}
                        />
                        <textarea
                          value={newDirection.expected_outcome}
                          onChange={(e) => setNewDirection({ ...newDirection, expected_outcome: e.target.value })}
                          className="w-full px-3 py-2 text-xs border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 focus:ring-2 focus:ring-indigo-500 focus:outline-none resize-none"
                          placeholder="期望: 描述期望结果..."
                          rows={2}
                        />
                      </div>
                    </div>
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => {
                          setIsAddingNew(false);
                          setNewDirection({ direction: '', purpose: '', expected_outcome: '' });
                        }}
                        className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                      >
                        取消
                      </button>
                      <button
                        onClick={handleAddNew}
                        disabled={!newDirection.direction.trim()}
                        className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        确认添加
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="relative flex items-center">
                    <div className="flex-grow border-t border-dashed border-gray-300 dark:border-gray-600"></div>
                    <button
                      onClick={() => setIsAddingNew(true)}
                      className="mx-3 flex-shrink-0 w-4 h-4 rounded-full bg-gray-400 dark:bg-gray-600 hover:bg-indigo-500 hover:dark:bg-indigo-600 text-white flex items-center justify-center transition-all hover:scale-110 shadow-sm"
                      title="添加新搜索方向"
                    >
                      <Plus className="w-2.5 h-2.5" />
                    </button>
                    <div className="flex-grow border-t border-dashed border-gray-300 dark:border-gray-600"></div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 搜索边界（不涉及） */}
          {checklist.boundaries && checklist.boundaries.length > 0 && (
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-1.5 font-medium flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                搜索边界（不涉及）
              </div>
              <div className="flex flex-wrap gap-1.5">
                {checklist.boundaries.map((boundary, index) => (
                  <span
                    key={index}
                    className="text-xs px-2 py-0.5 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded border border-red-200 dark:border-red-700"
                  >
                    {boundary}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 已隐藏: 回答目标 */}

          {/* v7.250 新增：深度分析洞察 */}
          {(checklist.user_context?.identity || checklist.key_entities?.length || checklist.core_tension || checklist.user_task) && (
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-3 font-medium flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-purple-500" />
                深度分析洞察
              </div>

              {/* 用户画像 */}
              {checklist.user_context?.identity && (
                <div className="text-xs text-gray-600 dark:text-gray-300 mb-2">
                  <span className="text-purple-500 dark:text-purple-400 font-medium">用户特征:</span> {checklist.user_context.identity}
                </div>
              )}

              {/* 隐性需求 */}
              {checklist.user_context?.implicit_needs && checklist.user_context.implicit_needs.length > 0 && (
                <div className="text-xs text-gray-600 dark:text-gray-300 mb-2">
                  <span className="text-purple-500 dark:text-purple-400 font-medium">隐性需求:</span> {checklist.user_context.implicit_needs.slice(0, 2).join('、')}
                </div>
              )}

              {/* 关键实体 */}
              {checklist.key_entities && checklist.key_entities.length > 0 && (
                <div className="mb-2">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1.5 font-medium">关键实体:</div>
                  <div className="flex flex-wrap gap-1.5">
                    {checklist.key_entities.map((entity, idx) => (
                      <span
                        key={idx}
                        className="text-xs px-2 py-0.5 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded border border-blue-200 dark:border-blue-700"
                        title={entity.detail || entity.type}
                      >
                        {entity.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* 核心张力 */}
              {checklist.core_tension && (
                <div className="text-xs text-gray-600 dark:text-gray-300 mb-2">
                  <span className="text-orange-500 dark:text-orange-400 font-medium">核心张力:</span> {checklist.core_tension}
                </div>
              )}

              {/* 用户任务 JTBD */}
              {checklist.user_task && (
                <div className="text-xs text-gray-600 dark:text-gray-300">
                  <span className="text-green-500 dark:text-green-400 font-medium">用户任务:</span> {checklist.user_task}
                </div>
              )}

              {/* 分析视角 */}
              {checklist.analysis_perspectives && checklist.analysis_perspectives.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {checklist.analysis_perspectives.map((perspective, idx) => (
                    <span
                      key={idx}
                      className="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 rounded"
                    >
                      {perspective}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
    </div>
  );
};

// 🆕 v7.218: 深度分析启动卡片（流式思考样式，无进度条）
// v7.219: 改为流式输出样式，显示动态打字效果提示
const AnalysisProgressCard = ({ progress }: {
  progress: {
    stage: string;
    stageName: string;
    message: string;
    estimatedTime: number;
    currentStep: number;
    totalSteps: number;
    startTime?: number;
  };
}) => {
  const [dots, setDots] = useState('');

  useEffect(() => {
    // 动态省略号效果，模拟流式输出
    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 500);

    return () => clearInterval(interval);
  }, []);

  // v7.243: 使用统一的 ucppt-card 样式类
  return (
    <div className="ucppt-card p-4">
      <div className="flex items-start gap-3">
        <Brain className="w-5 h-5 text-indigo-600 dark:text-indigo-400 animate-pulse flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="ucppt-title-indigo">
              {progress.stageName}
            </span>
            <span className="text-xs text-indigo-600 dark:text-indigo-400">
              DeepSeek推理
            </span>
          </div>
          {/* 流式输出提示文字 */}
          <div className="ucppt-thinking-text">
            <span className="text-indigo-600 dark:text-indigo-400">▋</span>
            <span className="ml-1">{progress.message}{dots}</span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
            💡 正在调用 DeepSeek 深度推理引擎，思考内容将实时呈现
          </p>
        </div>
      </div>
    </div>
  );
};

// 🆕 v7.217: 解题思考过程展示组件
const ThinkingContentCard = ({ content, isExpanded, onToggle }: {
  content: string;
  isExpanded: boolean;
  onToggle: () => void;
}) => {
  if (!content) return null;

  return (
    <div className="ucppt-card">
      {/* v7.243: 标题栏 - 使用统一样式类 */}
      <div
        className={`ucppt-card-header ${isExpanded ? 'ucppt-card-header-expanded' : 'ucppt-card-header-collapsed'}`}
        onClick={onToggle}
      >
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-purple-600 dark:text-purple-400" />
          <span className="ucppt-title-purple">解题思考过程</span>
          <span className="text-xs text-purple-600 dark:text-purple-400">
            DeepSeek推理
          </span>
        </div>
        <ChevronRight
          className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
        />
      </div>

      {/* 思考内容 */}
      {isExpanded && (
        <div className="ucppt-card-content">
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <div className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// 🆕 v7.217: 搜索轮次展示组件
// v7.219: 优化展示，默认展开显示搜索结果
// v7.220.1: 过滤掉 Round 0（分析阶段由 TaskUnderstandingCard 单独显示）
// v7.222: 合并 DeepSearchProgress，统一搜索进度展示
// v7.227: 全面扁平化，移除折叠功能，所有内容直接展示
// v7.229: 思考内容持久化显示，不再思考完就消失
const UnifiedSearchProgressCard = ({
  rounds,
  searchPlan,
  currentRound,
  currentPhase,
  status,
  statusMessage,
  currentRoundReasoning,
  currentRoundThinking,
  currentThinkingRound,
  roundThinkingMap,
  isExpanded,
  onToggle
}: {
  rounds: RoundRecord[];
  searchPlan: SearchPlan | null;
  currentRound: number;
  currentPhase: 'idle' | 'analysis' | 'search' | 'synthesis' | 'done';
  status: string;
  statusMessage: string;
  currentRoundReasoning: string;
  currentRoundThinking: string;
  currentThinkingRound: number;
  roundThinkingMap: Record<number, { reasoning: string; thinking: string }>;
  isExpanded: boolean;
  onToggle: () => void;
}) => {
  // v7.220.1: 过滤掉分析阶段（Round 0），避免重复显示
  // v7.224: 添加排序确保轮次按正确顺序显示
  // v7.242: 添加去重逻辑，防止相同轮次号重复显示
  const searchRounds = rounds
    .filter(r => !(r.round === 0 && r.isAnalysisPhase))
    .reduce((acc, round) => {
      // 按轮次号去重，保留最新的（有更多数据的）
      const existingIndex = acc.findIndex(r => r.round === round.round);
      if (existingIndex >= 0) {
        // 如果新的有来源而旧的没有，用新的替换
        if ((round.sources?.length || 0) > (acc[existingIndex].sources?.length || 0)) {
          acc[existingIndex] = round;
        }
      } else {
        acc.push(round);
      }
      return acc;
    }, [] as typeof rounds)
    .sort((a, b) => a.round - b.round);

  // v7.222: 统一的进度判断
  const isSearchPhase = currentPhase === 'search';
  const isSynthesisPhase = currentPhase === 'synthesis';
  const isSearching = isSearchPhase && (status === 'searching' || status === 'thinking');
  const completedRounds = searchRounds.filter(r => r.status === 'complete').length;

  // 如果既没有计划也没有轮次，不显示
  if (!searchPlan && searchRounds.length === 0 && !isSearching) return null;

  // v7.227: 根据阶段确定标题和颜色
  const getPhaseInfo = () => {
    if (isSynthesisPhase) {
      return {
        title: '答案生成中',
        subtitle: statusMessage || '正在综合搜索结果生成回答...',
        iconBgClass: 'bg-emerald-100 dark:bg-emerald-900/30',
        iconClass: 'text-emerald-600 dark:text-emerald-400',
        titleClass: 'text-emerald-600 dark:text-emerald-400',
        icon: Sparkles,
      };
    }
    if (isSearching) {
      return {
        title: `深度搜索 ${completedRounds > 0 ? `(${completedRounds}轮完成)` : ''}`,
        subtitle: statusMessage || '规划先行 · 多轮搜索 · 深度思考',
        iconBgClass: 'bg-orange-100 dark:bg-orange-900/30',
        iconClass: 'text-orange-600 dark:text-orange-400',
        titleClass: 'text-orange-600 dark:text-orange-400',
        icon: Search,
      };
    }
    return {
      title: `搜索完成 (${completedRounds}轮)`,
      subtitle: statusMessage || `共找到 ${searchRounds.reduce((sum, r) => sum + r.sourcesFound, 0)} 个来源`,
      iconBgClass: 'bg-indigo-100 dark:bg-indigo-900/30',
      iconClass: 'text-indigo-600 dark:text-indigo-400',
      titleClass: 'text-indigo-600 dark:text-indigo-400',
      icon: History,
    };
  };

  const phaseInfo = getPhaseInfo();
  const IconComponent = phaseInfo.icon;

  // v7.227: 全部内容直接展示，无折叠
  // v7.243: 调整卡片间距，从 space-y-12 改为 space-y-6
  return (
    <div className="mb-6 space-y-6">
      {/* 标题栏 - 简化扁平化 */}
      <div className="flex items-center gap-3 px-2">
        <div className={`w-8 h-8 rounded-full ${phaseInfo.iconBgClass} flex items-center justify-center flex-shrink-0`}>
          <IconComponent className={`w-4 h-4 ${phaseInfo.iconClass} ${isSearching ? 'animate-pulse' : ''}`} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className={`text-sm font-medium ${phaseInfo.titleClass}`}>
              {phaseInfo.title}
            </span>
            {isSearching && (
              <div className={`flex items-center gap-1 ${phaseInfo.titleClass} text-xs`}>
                <Loader2 className="w-3 h-3 animate-spin" />
                搜索中...
              </div>
            )}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {phaseInfo.subtitle}
          </p>
        </div>
      </div>

      {/* 搜索规划 */}
      {/* v7.241: 增加内边距 */}
      {searchPlan && (
        <div className="bg-blue-50 dark:bg-blue-900/10 rounded-lg p-4">
          <div className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 mb-3">
            <Brain className="w-4 h-4" />
            <span className="font-medium">搜索规划</span>
          </div>
          {searchPlan.analysis && (
            <div className="text-sm text-gray-600 dark:text-gray-400 mb-3">
              {searchPlan.analysis}
            </div>
          )}
          {searchPlan.aspects && searchPlan.aspects.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {searchPlan.aspects.map((aspect, i) => (
                <span key={i} className="px-2 py-0.5 bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 text-xs rounded border border-blue-200 dark:border-blue-700">
                  {aspect}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* v7.227: 轮次列表 - 全部展开，无折叠 */}
      {/* v7.229: 思考内容持久化显示 */}
      {searchRounds.map((round) => {
        const hasSources = round.sources && round.sources.length > 0;
        // v7.229: 获取该轮次保存的思考内容
        const savedThinking = roundThinkingMap[round.round] || { reasoning: '', thinking: '' };
        const roundReasoning = round.reasoningContent || savedThinking.reasoning;
        const hasThinkingContent = roundReasoning && roundReasoning.length > 0;
        // 判断是否是当前正在思考的轮次
        const isCurrentlyThinking = isSearching && status === 'thinking' && currentThinkingRound === round.round;

        return (
          // v7.243: 使用统一的 ucppt-round-card 样式类
          <div key={round.round} className="ucppt-round-card">
            {/* 轮次标题行 */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="ucppt-title-indigo">
                  第{round.round}轮
                </span>
                {/* v7.242: 过滤掉包含"第X轮"的topicName，避免重复显示 */}
                {round.topicName && !/第\s*\d+\s*轮/.test(round.topicName) && (
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {round.topicName}
                  </span>
                )}
                {round.status === 'complete' && (
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                )}
                {isCurrentlyThinking && (
                  <div className="flex items-center gap-1 text-purple-500">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    <span className="text-xs">思考中</span>
                  </div>
                )}
              </div>
            </div>

            {/* 搜索查询 */}
            {round.searchQuery && (
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                查询: {round.searchQuery}
              </div>
            )}

            {/* v7.243: 思考内容 - 使用统一样式类 */}
            {(hasThinkingContent || isCurrentlyThinking) && (
              <div className="mb-3">
                <div className="ucppt-thinking-text">
                  {isCurrentlyThinking ? (currentRoundReasoning || currentRoundThinking) : roundReasoning}
                  {isCurrentlyThinking && (
                    <span className="inline-block w-1.5 h-4 bg-purple-500 ml-0.5 animate-pulse rounded-sm" />
                  )}
                </div>
              </div>
            )}

            {/* v7.243: 来源列表 - 使用统一样式类 */}
            {hasSources && (
              <div className="ucppt-results-divider space-y-1">
                <div className="ucppt-result-count">
                  找到 {round.sources.length} 个结果
                </div>
                {round.sources.map((source, idx) => (
                  <a
                    key={idx}
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ucppt-result-link"
                  >
                    {/* Favicon */}
                    <img
                      src={`https://www.google.com/s2/favicons?domain=${new URL(source.url).hostname}&sz=16`}
                      alt=""
                      className="w-4 h-4 flex-shrink-0"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                    />
                    <span className="truncate">{source.title || source.url}</span>
                  </a>
                ))}
              </div>
            )}

            {/* 无来源时显示 */}
            {!hasSources && round.status === 'complete' && (
              <div className="text-xs text-gray-400 dark:text-gray-500 italic">
                本轮未找到相关来源
              </div>
            )}
          </div>
        );
      })}

      {/* v7.243: 实时思考进度 - 使用统一的 ucppt-round-card 样式 */}
      {isSearching && status === 'thinking' && (currentRoundReasoning || currentRoundThinking) &&
       !searchRounds.some(r => r.round === currentThinkingRound) && (
        <div className="ucppt-round-card">
          {/* 轮次标题行 - 与完成状态保持一致 */}
          <div className="flex items-center gap-2 mb-3">
            <span className="ucppt-title-indigo">
              第{currentThinkingRound || currentRound}轮
            </span>
            <div className="flex items-center gap-1 text-purple-500">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span className="text-xs">思考中</span>
            </div>
          </div>
          {/* v7.243: 思考内容使用统一样式 */}
          <div>
            <div className="ucppt-thinking-text">
              {currentRoundReasoning || currentRoundThinking}
              <span className="inline-block w-1.5 h-4 bg-purple-500 ml-0.5 animate-pulse rounded-sm" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// v7.205: L0 结构化信息展示组件（保留用于兼容旧版）- v7.209: 简化为扁平化样式
const StructuredInfoCard = ({ info, isExpanded, onToggle }: {
  info: StructuredUserInfo | null;
  isExpanded: boolean;
  onToggle: () => void;
}) => {
  if (!info) return null;

  const hasProfile = Object.values(info.demographics || {}).some(v => v) ||
                     (info.identity_tags || []).length > 0;

  const hasPreferences = (info.preferences?.style_references || []).length > 0 ||
                         (info.preferences?.style_keywords || []).length > 0;

  const hasImplicitNeeds = (info.core_request?.implicit_needs || []).length > 0;

  return (
    <div className="ucppt-card">
      {/* v7.243: 标题栏 - 使用统一样式类 */}
      <div
        className={`ucppt-card-header ${isExpanded ? 'ucppt-card-header-expanded' : 'ucppt-card-header-collapsed'}`}
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <div className="ucppt-icon-circle ucppt-icon-blue">
            <Target className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <span className="ucppt-title-blue">用户画像识别</span>
            <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
              置信度: {((info.completeness?.confidence_score || 0) * 100).toFixed(0)}%
            </span>
          </div>
        </div>
        <ChevronRight
          className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
        />
      </div>

      {/* 展开内容 */}
      {isExpanded && (
        <div className="ucppt-card-content space-y-4">
          {/* 基础信息 */}
          {hasProfile && (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {info.demographics?.location && (
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-2 border border-gray-200 dark:border-gray-700">
                  <span className="text-xs text-gray-500 dark:text-gray-400 block">地点</span>
                  <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{info.demographics.location}</span>
                  {info.demographics.location_context && (
                    <span className="text-xs text-gray-400 block mt-0.5">{info.demographics.location_context}</span>
                  )}
                </div>
              )}
              {info.demographics?.age && (
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-2 border border-gray-200 dark:border-gray-700">
                  <span className="text-xs text-gray-500 dark:text-gray-400 block">年龄</span>
                  <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{info.demographics.age}</span>
                  {info.demographics.age_context && (
                    <span className="text-xs text-gray-400 block mt-0.5">{info.demographics.age_context}</span>
                  )}
                </div>
              )}
              {info.demographics?.gender && (
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-2 border border-gray-200 dark:border-gray-700">
                  <span className="text-xs text-gray-500 dark:text-gray-400 block">性别</span>
                  <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{info.demographics.gender}</span>
                </div>
              )}
              {info.demographics?.education && (
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-2 border border-gray-200 dark:border-gray-700">
                  <span className="text-xs text-gray-500 dark:text-gray-400 block">背景</span>
                  <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{info.demographics.education}</span>
                  {info.demographics.education_context && (
                    <span className="text-xs text-gray-400 block mt-0.5">{info.demographics.education_context}</span>
                  )}
                </div>
              )}
              {info.project_context?.scale && (
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-2 border border-gray-200 dark:border-gray-700">
                  <span className="text-xs text-gray-500 dark:text-gray-400 block">规模</span>
                  <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{info.project_context.scale}</span>
                  {info.project_context.scale_context && (
                    <span className="text-xs text-gray-400 block mt-0.5">{info.project_context.scale_context}</span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* 身份标签 */}
          {(info.identity_tags || []).length > 0 && (
            <div>
              <span className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">身份标签</span>
              <div className="flex flex-wrap gap-2">
                {info.identity_tags.map((tag, i) => (
                  <span
                    key={i}
                    className="px-3 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-full text-sm font-medium border border-blue-200 dark:border-blue-700"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 风格偏好 */}
          {hasPreferences && (
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
              <span className="text-xs text-gray-500 dark:text-gray-400 mb-2 block">风格偏好</span>
              {(info.preferences?.style_references || []).length > 0 && (
                <div className="mb-2">
                  <span className="text-sm text-gray-600 dark:text-gray-400">参照: </span>
                  <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
                    {info.preferences.style_references.join(', ')}
                  </span>
                </div>
              )}
              {(info.preferences?.style_keywords || []).length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {info.preferences.style_keywords.map((kw, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 rounded text-xs border border-indigo-200 dark:border-indigo-700"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              )}
              {(info.preferences?.color_palette || []).length > 0 && (
                <div className="mt-2 flex items-center gap-2">
                  <span className="text-xs text-gray-500 dark:text-gray-400">色彩:</span>
                  <div className="flex gap-1">
                    {info.preferences.color_palette.slice(0, 6).map((color, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded text-xs"
                      >
                        {color}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 隐性需求推断 */}
          {hasImplicitNeeds && (
            <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 border border-amber-200 dark:border-amber-700">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-amber-500" />
                <span className="text-xs text-amber-700 dark:text-amber-400 font-medium">智能推断的隐性需求</span>
              </div>
              <ul className="space-y-1">
                {info.core_request.implicit_needs.map((need, i) => (
                  <li key={i} className="text-sm text-amber-800 dark:text-amber-300 flex items-start gap-2">
                    <span className="text-amber-400 mt-1">•</span>
                    {need}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 地点考量 */}
          {info.location_considerations?.climate && (
            <div className="text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded p-2 border border-gray-200 dark:border-gray-700">
              <span className="font-medium">地点考量: </span>
              {info.location_considerations.climate}
              {info.location_considerations.architecture && ` | ${info.location_considerations.architecture}`}
            </div>
          )}

          {/* 缺失信息提示 */}
          {(info.completeness?.missing_dimensions || []).length > 0 && (
            <div className="text-xs text-gray-400 dark:text-gray-500 flex items-center gap-1">
              <AlertCircle className="w-3 h-3" />
              <span>未提供: {info.completeness.missing_dimensions.join(', ')}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default function SearchResultPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params?.session_id as string;

  // v7.290: 独立搜索页面，无侧边栏

  // 状态
  const [query, setQuery] = useState('');
  const [followUpQuery, setFollowUpQuery] = useState('');
  const [deepMode, setDeepMode] = useState(false);  // 深度搜索开关
  const [searchState, setSearchState] = useState<SearchState>({
    status: 'idle',
    statusMessage: '',
    currentPhase: 'idle',         // v7.222: 明确阶段标识
    l0Content: '',              // v7.205: L0 流式内容
    l0Phase: 'idle',            // v7.205: L0 阶段状态
    structuredInfo: null,       // v7.205: L0 提取结果
    analysisContent: '',          // v7.188: 流式分析内容
    analysisSaved: false,         // v7.193: 分析是否已保存
    searchPlan: null,
    rounds: [],
    currentRound: 0,
    totalRounds: 0,
    thinkingContent: '',
    isThinking: false,
    currentRoundReasoning: '',   // v7.188
    currentRoundThinking: '',    // v7.188
    currentThinkingRound: 0,     // v7.188: 跟踪当前轮次
    roundThinkingMap: {},        // 🔧 v7.195: 按轮次独立存储
    problemSolvingThinking: '',  // v7.218: Phase 0解题思考
    isProblemSolvingPhase: true, // v7.218: 初始为解题阶段
    answerContent: '',
    answerThinkingContent: '',   // 🆕 答案生成的思考过程
    isAnswering: false,
    sources: [],
    images: [],
    executionTime: 0,
    error: null,
    isDeepMode: false,
    // v7.240: 框架清单（v7.301: 作为唯一的搜索方向展示）
    frameworkChecklist: null,
    // 🆕 v7.280: 深度分析结果
    deepAnalysisResult: null,
    // 🆕 v7.302: 4条使命结果
    fourMissionsResult: null,
    // v7.218: 分析进度
    analysisProgress: null,
    // v7.226: 对话缓冲区
    _dialogueBuffer: '',
    // v7.281: 答案质量评估
    qualityAssessment: null,
    // v7.280: 等待用户确认
    awaitingConfirmation: false,
  });

  // 🆕 v7.300: 4步工作流状态
  const [step2Plan, setStep2Plan] = useState<Step2SearchPlan | null>(null);
  const [isValidatingPlan, setIsValidatingPlan] = useState(false);
  const [isConfirmingPlan, setIsConfirmingPlan] = useState(false);

  const [showThinking, setShowThinking] = useState(false);  // 默认折叠思考过程（历史记录友好）
  const [showAllImages, setShowAllImages] = useState(false);
  const [imageViewerOpen, setImageViewerOpen] = useState(false);
  const [imageViewerIndex, setImageViewerIndex] = useState(0);
  const [showHistory, setShowHistory] = useState(false);  // 搜索历史浮动面板
  const [searchHistory, setSearchHistory] = useState<{query: string; timestamp: string; sessionId: string}[]>([]);
  const [expandedRounds, setExpandedRounds] = useState<Set<number>>(new Set());  // 🆕 v7.171: 展开的轮次
  const [showBackToTop, setShowBackToTop] = useState(false);  // 🆕 v7.178: 返回顶部按钮状态
  const [autoCollapseTimer, setAutoCollapseTimer] = useState<NodeJS.Timeout | null>(null);  // 🆕 自动折叠计时器
  const [structuredInfoExpanded, setStructuredInfoExpanded] = useState(true);  // 🆕 v7.205: L0 用户画像展开状态
  const [frameworkChecklistExpanded, setFrameworkChecklistExpanded] = useState(true);  // 🆕 v7.240: 框架清单展开状态（v7.301: 唯一的搜索方向展示）
  const [thinkingExpanded, setThinkingExpanded] = useState(true);  // 🆕 v7.217: 解题思考过程展开状态
  const [roundsExpanded, setRoundsExpanded] = useState(true);  // 🆕 v7.217: 搜索轮次展开状态
  const [deepAnalysisExpanded, setDeepAnalysisExpanded] = useState(true);  // 🆕 v7.280: 深度分析展开状态
  const pendingSearchRef = useRef<{query: string; deepMode: boolean} | null>(null);  // 🆕 v7.290: 待启动的搜索参数

  // 🆕 v7.251: 自动滚动控制状态（类似 DeepSeek 流式输出时自动上滚）
  const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(true);
  const [isUserScrolling, setIsUserScrolling] = useState(false);
  const lastScrollTopRef = useRef(0);
  const scrollToBottomThrottleRef = useRef<number>(0);

  const contentRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const isInitialMount = useRef(true);  // 防止 React 严格模式下双重执行

  // 🔧 DEBUG: 状态变化追踪 - 用于调试思考内容回退问题
  useEffect(() => {
    console.log('📊 [STATE] searchState 变化:', {
      status: searchState.status,
      currentRound: searchState.currentRound,
      currentThinkingRound: searchState.currentThinkingRound,
      roundsCount: searchState.rounds?.length ?? 0,
      currentReasoningLength: searchState.currentRoundReasoning?.length ?? 0,
      currentThinkingLength: searchState.currentRoundThinking?.length ?? 0,
      thinkingContentLength: searchState.thinkingContent?.length ?? 0,
      isThinking: searchState.isThinking,
    });
  }, [
    searchState.status,
    searchState.currentRound,
    searchState.currentThinkingRound,
    searchState.rounds?.length,
    searchState.currentRoundReasoning,
    searchState.currentRoundThinking,
    searchState.thinkingContent,
    searchState.isThinking,
  ]);

  // 保存搜索结果到后端数据库（持久化）
  const saveSearchStateToBackend = useCallback(async (state: SearchState, q: string) => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      await fetch(`${backendUrl}/api/search/session/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          query: q,
          sources: state.sources,
          images: state.images,
          thinkingContent: state.thinkingContent,
          answerContent: state.answerContent,
          searchPlan: state.searchPlan,
          rounds: state.rounds,
          totalRounds: state.totalRounds,
          executionTime: state.executionTime,
          isDeepMode: state.isDeepMode,
          // 🆕 v7.219: 保存需求洞察相关字段（完整链路持久化）
          l0Content: state.l0Content,
          problemSolvingThinking: state.problemSolvingThinking,
          structuredInfo: state.structuredInfo,
          // v7.240: 保存框架清单（v7.301: 唯一的搜索方向展示）
          frameworkChecklist: state.frameworkChecklist,
        }),
      });
      console.log('✅ 搜索会话已保存到后端, session_id:', sessionId);
    } catch (e) {
      console.error('保存搜索会话失败:', e);
    }
  }, [sessionId]);

  // 从后端加载搜索会话
  const loadSearchStateFromBackend = useCallback(async (): Promise<{state: SearchState | null; query: string | null; deepMode: boolean; error?: string}> => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${backendUrl}/api/search/session/${sessionId}`);

      // 🔧 v7.283: 处理后端错误响应
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ 后端返回错误:', response.status, errorText);

        // 区分不同的HTTP错误
        if (response.status === 404) {
          return { state: null, query: null, deepMode: false, error: 'not_found' };
        } else if (response.status >= 500) {
          return { state: null, query: null, deepMode: false, error: 'server_error' };
        } else {
          return { state: null, query: null, deepMode: false, error: 'unknown' };
        }
      }

      const data = await response.json();

      console.log('🔍 [DEBUG] 后端返回数据:', {
        success: data.success,
        hasSession: !!data.session,
        status: data.session?.status,
        answerContent: data.session?.answerContent?.length,
        content: data.session?.content?.length,
        sourcesCount: data.session?.sources?.length,
        roundsCount: data.session?.rounds?.length,
      });

      // 🆕 v7.189: 如果是guest会话且用户已登录，自动关联到用户账户
      if (data.success && data.session && sessionId.startsWith('guest-')) {
        try {
          const token = localStorage.getItem('wp_jwt_token');
          if (token) {
            // 用户已登录，尝试关联此guest会话
            const associateResponse = await fetch(`${backendUrl}/api/search/session/associate?session_id=${sessionId}`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
              }
            });

            if (associateResponse.ok) {
              const associateData = await associateResponse.json();
              if (associateData.success) {
                console.log('[Search Page v7.189] ✅ 自动关联guest会话到用户账户:', sessionId);
              }
            }
          }
        } catch (e) {
          console.error('[Search Page v7.189] ⚠️ 关联guest会话失败:', e);
          // 不阻塞搜索功能，静默失败
        }
      }

      if (data.success && data.session) {
        const session = data.session;
        // 🔧 修复：检查是否有搜索结果（包括 rounds 数据）
        const hasResults = session.answerContent ||
                          session.content ||
                          (session.sources && session.sources.length > 0) ||
                          (session.rounds && session.rounds.length > 0) ||
                          session.status === 'completed';

        if (hasResults) {
          // 🔧 v7.219: 从 rounds 中聚合 sources（如果 session.sources 为空）
          const loadedRounds = session.rounds || [];
          let loadedSources = session.sources || [];
          if (loadedSources.length === 0 && loadedRounds.length > 0) {
            loadedSources = loadedRounds.flatMap((round: RoundRecord) => round.sources || []);
            console.log('🔧 v7.219: 从 rounds 聚合 sources:', loadedSources.length);
          }

          // 已有搜索结果，直接恢复
          return {
            state: {
              status: 'done',
              statusMessage: '',
              currentPhase: 'done' as const,  // v7.240: 添加缺失字段
              l0Content: session.l0Content || '',           // v7.206: 恢复对话内容
              l0Phase: 'complete' as const,                  // v7.206: 恢复L0阶段
              structuredInfo: session.structuredInfo || null, // v7.206: 恢复结构化信息
              searchPlan: session.searchPlan || null,
              rounds: loadedRounds,
              currentRound: session.totalRounds || 0,
              totalRounds: session.totalRounds || 0,
              thinkingContent: session.thinkingContent || session.reasoning || '',
              isThinking: false,
              currentRoundReasoning: '',
              currentRoundThinking: '',
              currentThinkingRound: 0,
              roundThinkingMap: {},  // 🔧 v7.195: 恢复时清空（已保存到 rounds）
              analysisContent: '',
              analysisSaved: true,
              answerContent: session.answerContent || session.content || '',
              answerThinkingContent: session.answerThinkingContent || '', // v7.206
              isAnswering: false,
              sources: loadedSources,
              images: session.images || [],
              executionTime: session.executionTime || 0,
              error: null,
              isDeepMode: session.isDeepMode || false,
              // v7.240: 恢复框架清单（v7.301: 唯一的搜索方向展示）
              frameworkChecklist: session.frameworkChecklist || null,
              // 🆕 v7.219: 恢复需求洞察相关字段
              problemSolvingThinking: session.problemSolvingThinking || '',
              isProblemSolvingPhase: false,
              analysisProgress: null,
              _dialogueBuffer: '',  // v7.240: 添加缺失字段
              // v7.281: 恢复质量评估
              qualityAssessment: session.qualityAssessment || null,
              // v7.280: 深度分析结果
              deepAnalysisResult: session.deepAnalysisResult || null,
              // v7.302: 4条使命结果
              fourMissionsResult: session.fourMissionsResult || null,
              // v7.280: 等待用户确认
              awaitingConfirmation: false,
            },
            query: session.query || null,
            deepMode: session.isDeepMode || false,
          };
        } else {
          // 只有查询，没有结果（待执行搜索）
          return {
            state: null,
            query: session.query || null,
            deepMode: session.isDeepMode || false,
          };
        }
      }
    } catch (e) {
      console.error('❌ 加载搜索会话异常:', e);
      // 网络错误或解析错误
      return { state: null, query: null, deepMode: false, error: 'network_error' };
    }
    return { state: null, query: null, deepMode: false };
  }, [sessionId]);

  // 初始化：从后端加载会话数据
  useEffect(() => {
    // React 严格模式会挂载两次，只在第一次执行
    if (!isInitialMount.current) return;
    isInitialMount.current = false;

    console.log('🔍 加载搜索会话, session_id:', sessionId);

    loadSearchStateFromBackend().then(({ state, query: loadedQuery, deepMode: loadedDeepMode, error }) => {
      console.log('🔍 [DEBUG] 加载结果:', { hasState: !!state, hasQuery: !!loadedQuery, deepMode: loadedDeepMode, error });

      // 🔧 v7.283: 优先处理后端错误
      if (error) {
        if (error === 'server_error') {
          console.error('❌ 后端服务异常（500错误），请检查后端日志');
          setSearchState(prev => ({
            ...prev,
            status: 'error',
            error: '后端服务暂时不可用，请稍后重试或联系管理员',
          }));
          return;
        } else if (error === 'network_error') {
          console.error('❌ 网络连接失败');
          setSearchState(prev => ({
            ...prev,
            status: 'error',
            error: '无法连接到后端服务，请检查网络连接',
          }));
          return;
        }
        // not_found 或 unknown 错误继续往下处理
      }

      if (state) {
        // 已有完整结果或历史记录，直接恢复（不重新搜索）
        console.log('✅ 从后端恢复搜索会话, session_id:', sessionId, 'status:', state.status);
        if (loadedQuery) setQuery(loadedQuery);
        setDeepMode(loadedDeepMode);
        setSearchState(state);
      } else if (loadedQuery) {
        // 🔧 v7.290: 区分新会话和未完成的历史会话
        // 使用 localStorage 检查会话创建时间（因为 sessionId 中的日期不含时分秒）
        const recentSessionsJson = localStorage.getItem('recent_search_sessions');
        const recentSessions: Record<string, number> = recentSessionsJson ? JSON.parse(recentSessionsJson) : {};
        const sessionCreatedAt = recentSessions[sessionId];
        const now = Date.now();

        // 如果会话在 localStorage 中且创建时间 < 1分钟，认为是新会话
        const isRecentSession = sessionCreatedAt && (now - sessionCreatedAt < 60000);

        if (isRecentSession) {
          // 新会话：设置query并标记需要启动搜索
          console.log('📝 [v7.290] 新搜索会话，标记自动启动搜索:', loadedQuery);
          setQuery(loadedQuery);
          setDeepMode(loadedDeepMode);
          // 🆕 v7.290: 使用 ref 存储搜索参数，避免直接调用 startSearch 导致的初始化顺序问题
          pendingSearchRef.current = { query: loadedQuery, deepMode: loadedDeepMode };
        } else {
          // 旧会话或未完成的会话：显示错误提示，不自动重新搜索
          console.warn('⚠️ 历史会话未完成或数据丢失:', sessionId, loadedQuery);
          setQuery(loadedQuery);
          setDeepMode(loadedDeepMode);
          setSearchState(prev => ({
            ...prev,
            status: 'error',
            error: '此搜索会话未完成或数据已丢失。请点击"开始新搜索"重新开始。',
          }));
        }
      } else {
        // 会话不存在，显示错误
        console.error('❌ 搜索会话不存在:', sessionId);
        setSearchState(prev => ({
          ...prev,
          status: 'error',
          error: '搜索会话不存在或已过期',
        }));
      }
    });
  }, [sessionId, loadSearchStateFromBackend]);  // 🔧 v7.290: 移除 startSearch 依赖避免初始化顺序问题

  // 🆕 v7.290: 监听待启动搜索并触发（解决 startSearch 初始化顺序问题）
  useEffect(() => {
    if (pendingSearchRef.current && query) {
      const { query: searchQuery, deepMode: searchDeepMode } = pendingSearchRef.current;
      pendingSearchRef.current = null;  // 清除标记
      console.log('🚀 [v7.290] 触发待启动搜索:', searchQuery);
      // 延迟确保状态已设置，此时 startSearch 已通过闭包访问（已定义）
      setTimeout(() => {
        startSearch(searchQuery, searchDeepMode);
      }, 100);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);  // 🔧 仅依赖 query，startSearch 通过闭包访问

  // 🆕 v7.171: 搜索完成时自动保存到后端
  useEffect(() => {
    if (searchState.status === 'done' && query && searchState.answerContent) {
      saveSearchStateToBackend(searchState, query);
    }
  }, [searchState.status, query, searchState.answerContent, saveSearchStateToBackend]);

  // 🆕 自动折叠深度搜索：当状态变为 'answering' 时，延迟自动折叠
  useEffect(() => {
    // 清除之前的计时器
    if (autoCollapseTimer) {
      clearTimeout(autoCollapseTimer);
      setAutoCollapseTimer(null);
    }

    // 当状态变为 'answering' 时开始计时
    if (searchState.status === 'answering' && showThinking) {
      console.log('🔄 开始5秒自动折叠计时器', { status: searchState.status, showThinking });
      const timer = setTimeout(() => {
        console.log('⏰ 执行自动折叠');
        setShowThinking(false);
        setAutoCollapseTimer(null);
      }, 5000); // 5秒延迟，更柔和

      setAutoCollapseTimer(timer);
    }

    // 🔧 修复：当搜索完成时清除计时器
    if (searchState.status === 'done' || searchState.status === 'error') {
      if (autoCollapseTimer) {
        clearTimeout(autoCollapseTimer);
        setAutoCollapseTimer(null);
        console.log('🛑 搜索完成，清除自动折叠计时器');
      }
    }

    // 清理函数
    return () => {
      if (autoCollapseTimer) {
        clearTimeout(autoCollapseTimer);
      }
    };
  }, [searchState.status, showThinking]); // 🔧 修复：移除 autoCollapseTimer 依赖，避免无限循环

  // 🆕 v7.178: 监听滚动 - 控制返回顶部按钮显示
  useEffect(() => {
    const handleScroll = () => {
      const scrollPosition = window.scrollY;
      const pageHeight = document.documentElement.scrollHeight - window.innerHeight;
      const scrollPercentage = pageHeight > 0 ? scrollPosition / pageHeight : 0;

      // 滚动超过三分之二时显示按钮
      setShowBackToTop(scrollPercentage > 0.66);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // 🆕 v7.251: 检测是否接近底部（用于自动滚动控制）
  const isNearBottom = useCallback(() => {
    const scrollTop = window.scrollY;
    const windowHeight = window.innerHeight;
    const documentHeight = document.documentElement.scrollHeight;
    const threshold = 150; // 距离底部150px以内视为"在底部"
    return scrollTop + windowHeight >= documentHeight - threshold;
  }, []);

  // 🆕 v7.251: 监听滚动事件，检测用户手动滚动（用于暂停/恢复自动滚动）
  useEffect(() => {
    let scrollTimeout: NodeJS.Timeout | null = null;

    const handleUserScroll = () => {
      const currentScrollTop = window.scrollY;

      // 用户向上滚动超过10px - 禁用自动滚动
      if (currentScrollTop < lastScrollTopRef.current - 10) {
        setIsAutoScrollEnabled(false);
        setIsUserScrolling(true);
      } else if (isNearBottom()) {
        // 用户滚动到底部 - 重新启用自动滚动
        setIsAutoScrollEnabled(true);
        setIsUserScrolling(false);
      }

      lastScrollTopRef.current = currentScrollTop;

      if (scrollTimeout) clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        setIsUserScrolling(false);
      }, 150);
    };

    window.addEventListener('scroll', handleUserScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleUserScroll);
      if (scrollTimeout) clearTimeout(scrollTimeout);
    };
  }, [isNearBottom]);

  // 🆕 v7.251: 自动滚动到底部（节流处理，类似 DeepSeek 流式输出时自动上滚）
  const scrollToBottom = useCallback(() => {
    if (!isAutoScrollEnabled || isUserScrolling) return;

    const now = Date.now();
    if (now - scrollToBottomThrottleRef.current < 100) return; // 100ms 节流
    scrollToBottomThrottleRef.current = now;

    requestAnimationFrame(() => {
      window.scrollTo({
        top: document.documentElement.scrollHeight,
        behavior: 'smooth'
      });
    });
  }, [isAutoScrollEnabled, isUserScrolling]);

  // 🆕 v7.251: 流式输出时自动滚动
  useEffect(() => {
    const isStreaming =
      searchState.status === 'analyzing' ||
      searchState.status === 'searching' ||
      searchState.status === 'thinking' ||
      searchState.status === 'answering';

    if (isStreaming) {
      scrollToBottom();
    }
  }, [
    searchState.l0Content,              // Phase 0 分析内容
    searchState.currentRoundReasoning,  // 轮次推理内容
    searchState.currentRoundThinking,   // 轮次思考内容
    searchState.rounds.length,          // 新轮次
    searchState.answerContent,          // 最终回答
    searchState.status,
    scrollToBottom
  ]);

  // 🆕 v7.178: 返回顶部处理函数
  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  };

  // 开始搜索
  const startSearch = useCallback(async (searchQuery: string, isDeep?: boolean) => {
    // 使用传入的参数或当前状态
    const useDeepMode = isDeep !== undefined ? isDeep : deepMode;

    // 🆕 开始新搜索时展开思考过程
    setShowThinking(true);

    // 清除任何现有的自动折叠计时器
    if (autoCollapseTimer) {
      clearTimeout(autoCollapseTimer);
      setAutoCollapseTimer(null);
    }

    // 保存到搜索历史
    const now = new Date();
    const timestamp = `${now.getMonth() + 1}月${now.getDate()}日 ${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}`;
    const historyItem = { query: searchQuery, timestamp, sessionId };
    const history = JSON.parse(localStorage.getItem('searchHistory') || '[]');
    // 避免重复，最多保存50条
    const filtered = history.filter((h: {query: string}) => h.query !== searchQuery);
    localStorage.setItem('searchHistory', JSON.stringify([historyItem, ...filtered].slice(0, 50)));

    // 重置状态
    setSearchState({
      status: 'searching',
      statusMessage: useDeepMode ? '正在启动深度反思搜索...' : '正在搜索相关资料...',
      currentPhase: 'analysis',  // v7.240: 添加缺失字段
      l0Content: '',              // v7.206: 重置对话内容
      l0Phase: 'idle',            // v7.206: 重置L0阶段
      structuredInfo: null,       // v7.206: 重置结构化信息
      searchPlan: null,
      rounds: [],
      currentRound: 0,
      totalRounds: 0,
      thinkingContent: '',
      isThinking: false,
      currentRoundReasoning: '',
      currentRoundThinking: '',
      currentThinkingRound: 0,
      roundThinkingMap: {},  // 🔧 v7.195: 重置时清空
      analysisContent: '',
      analysisSaved: false,
      answerContent: '',
      answerThinkingContent: '',  // v7.206: 重置答案思考内容
      isAnswering: false,
      sources: [],
      images: [],
      executionTime: 0,
      error: null,
      isDeepMode: useDeepMode,
      // v7.240: 重置框架清单（v7.301: 唯一的搜索方向展示）
      frameworkChecklist: null,
      // v7.219: 重置需求洞察相关字段
      problemSolvingThinking: '',
      isProblemSolvingPhase: false,
      analysisProgress: null,
      // v7.226: 重置对话缓冲区
      _dialogueBuffer: '',
      // v7.280: 重置确认等待状态
      awaitingConfirmation: false,
      // v7.280: 重置深度分析结果
      deepAnalysisResult: null,
      // v7.302: 重置4条使命结果
      fourMissionsResult: null,
      // v7.281: 重置质量评估
      qualityAssessment: null,
    });

    try {
      // 🆕 v7.280: 使用 step1_only 模式，先只执行分析，等用户确认后再搜索
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

      // 🔧 v7.280: 添加 Authorization header（如果已登录）
      const token = localStorage.getItem('wp_jwt_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${backendUrl}/api/search/ucppt/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          query: searchQuery,
          session_id: sessionId,
          max_rounds: 10,  // ucppt 最多10轮迭代
          confidence_threshold: 0.8,
          phase_mode: 'step1_only',  // 🆕 v7.280: 仅执行分析阶段
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      let buffer = '';

      console.log('🔍 开始读取 SSE 流...');

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          console.log('🔍 SSE 流结束 (done=true)');
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // 按双换行分割完整的 SSE 事件
        const events = buffer.split('\n\n');
        buffer = events.pop() || ''; // 保留不完整的事件

        for (const eventBlock of events) {
          if (!eventBlock.trim()) continue;

          const lines = eventBlock.split('\n');
          let eventType = '';
          let dataStr = '';

          for (const line of lines) {
            const trimmedLine = line.trim();
            if (trimmedLine.startsWith('event:')) {
              eventType = trimmedLine.replace('event:', '').trim();
            } else if (trimmedLine.startsWith('data:')) {
              dataStr = trimmedLine.replace('data:', '').trim();
            }
          }

          if (eventType && dataStr) {
            try {
              const data = JSON.parse(dataStr);
              console.log(`📨 收到事件: ${eventType}`, data);
              handleSSEEvent(eventType, data);
            } catch (e) {
              console.error('Failed to parse SSE data:', e, dataStr);
            }
          }
        }
      }

      console.log('🔍 SSE 读取循环结束');
    } catch (error) {
      console.error('Search failed:', error);
      setSearchState(prev => ({
        ...prev,
        status: 'error',
        error: error instanceof Error ? error.message : '搜索失败',
      }));
    }
  }, [sessionId]);

  // 🆕 v7.300: 更新搜索计划（用于 Step2TaskListEditor）
  const handleUpdateStep2Plan = useCallback((updatedPlan: Step2SearchPlan) => {
    console.log('📋 [v7.300] 更新搜索计划:', updatedPlan);
    setStep2Plan(updatedPlan);
  }, []);

  // 🆕 v7.300: 验证搜索计划并获取智能补充建议
  const handleValidateStep2Plan = useCallback(async () => {
    if (!step2Plan || !sessionId) return { has_suggestions: false, suggestions: [] };

    setIsValidatingPlan(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const token = localStorage.getItem('wp_jwt_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${backendUrl}/api/search/step2/validate`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          session_id: sessionId,
          search_plan: step2Plan,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('📋 [v7.300] 验证结果:', result);
      return {
        has_suggestions: result.has_suggestions || false,
        suggestions: result.suggestions || [],
      };
    } catch (error) {
      console.error('❌ [v7.300] 验证搜索计划失败:', error);
      return { has_suggestions: false, suggestions: [] };
    } finally {
      setIsValidatingPlan(false);
    }
  }, [step2Plan, sessionId]);

  // 🆕 v7.300: 确认搜索计划并开始执行
  const handleConfirmStep2PlanAndStart = useCallback(async () => {
    if (!step2Plan) return;

    console.log('📋 [v7.300] 确认搜索计划并开始执行');
    setIsConfirmingPlan(true);

    // 关闭等待确认状态
    setSearchState(prev => ({
      ...prev,
      awaitingConfirmation: false,
      status: 'searching',
      statusMessage: '正在启动搜索...',
    }));

    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const token = localStorage.getItem('wp_jwt_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // 先确认计划
      await fetch(`${backendUrl}/api/search/step2/confirm`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          session_id: sessionId,
          search_plan: step2Plan,
        }),
      });

      // 构建框架数据用于 Step 2 执行
      const frameworkData = {
        core_question: step2Plan.core_question,
        answer_goal: step2Plan.answer_goal,
        search_steps: step2Plan.search_steps,
      };

      // 调用 Step 2 Only API 执行搜索
      const response = await fetch(`${backendUrl}/api/search/ucppt/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          query: query,
          session_id: sessionId,
          max_rounds: 10,
          confidence_threshold: 0.8,
          phase_mode: 'step2_only',
          framework_data: frameworkData,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // 处理 SSE 流（复用现有逻辑）
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('无法获取响应流');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            const eventType = line.slice(7).trim();
            // 处理事件（复用现有的 SSE 事件处理逻辑）
            console.log(`📡 [v7.300] SSE 事件: ${eventType}`);
          } else if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              console.log('📡 [v7.300] SSE 数据:', data);
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      }
    } catch (error) {
      console.error('❌ [v7.300] 执行搜索失败:', error);
      setSearchState(prev => ({
        ...prev,
        status: 'error',
        error: error instanceof Error ? error.message : '执行搜索失败',
      }));
    } finally {
      setIsConfirmingPlan(false);
    }
  }, [step2Plan, sessionId, query]);

  // 🆕 v7.280: 用户确认框架清单后继续搜索（调用 Step 2 API）
  const handleConfirmAndStartSearch = useCallback(async () => {
    console.log('📋 [v7.280] 用户确认框架清单，调用 Step 2 API');
    console.log('📋 [v7.280] 当前框架清单:', searchState.frameworkChecklist);

    // 关闭等待确认状态
    setSearchState(prev => ({
      ...prev,
      awaitingConfirmation: false,
      status: 'searching',
      statusMessage: '正在启动搜索...',
    }));

    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

      // 构建用户编辑后的框架数据
      const frameworkData = {
        core_question: searchState.frameworkChecklist?.core_summary || '',
        answer_goal: searchState.frameworkChecklist?.answer_goal || '',
        boundary: '',
        framework_checklist: searchState.frameworkChecklist ? {
          core_summary: searchState.frameworkChecklist.core_summary,
          main_directions: searchState.frameworkChecklist.main_directions,
          boundaries: searchState.frameworkChecklist.boundaries,
          answer_goal: searchState.frameworkChecklist.answer_goal,
        } : null,
      };

      console.log('📋 [v7.280] 发送框架数据:', frameworkData);

      // 🔧 v7.280: 添加 Authorization header（如果已登录）
      const token = localStorage.getItem('wp_jwt_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // 调用 Step 2 Only API
      const response = await fetch(`${backendUrl}/api/search/ucppt/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          query: query,
          session_id: sessionId,
          max_rounds: 10,
          confidence_threshold: 0.8,
          phase_mode: 'step2_only',
          framework_data: frameworkData,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // 处理 SSE 流
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      let buffer = '';

      console.log('🔍 [v7.280] 开始读取 Step 2 SSE 流...');

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          console.log('🔍 [v7.280] Step 2 SSE 流结束');
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const eventBlock of events) {
          if (!eventBlock.trim()) continue;

          const lines = eventBlock.split('\n');
          let eventType = '';
          let dataStr = '';

          for (const line of lines) {
            const trimmedLine = line.trim();
            if (trimmedLine.startsWith('event:')) {
              eventType = trimmedLine.replace('event:', '').trim();
            } else if (trimmedLine.startsWith('data:')) {
              dataStr = trimmedLine.replace('data:', '').trim();
            }
          }

          if (eventType && dataStr) {
            try {
              const data = JSON.parse(dataStr);
              console.log(`📡 [v7.280] Step 2 事件: ${eventType}`, data);
              handleSSEEvent(eventType, data);
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      }

    } catch (error) {
      console.error('❌ [v7.280] Step 2 搜索失败:', error);
      setSearchState(prev => ({
        ...prev,
        status: 'error',
        error: error instanceof Error ? error.message : '搜索失败',
      }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchState.frameworkChecklist, query, sessionId]);

  // 处理 SSE 事件 - v7.207 统一分析（合并 L0 + L1-L5）
  // v7.222: 添加调试日志和 currentPhase 跟踪
  const handleSSEEvent = useCallback((eventType: string, data: any) => {
    // v7.222: 调试模式日志
    if (DEBUG_SSE_EVENTS) {
      console.log(`🔵 [SSE] ${eventType}:`, JSON.stringify(data).slice(0, 200));
    }

    switch (eventType) {
      // ==================== Ucppt Phase 0+1: 统一分析 (v7.207) ====================

      // v7.207: 统一对话内容流式输出（thinking 内容展示给用户）
      // v7.218: 同时存储到 problemSolvingThinking 用于解题思考卡片展示
      // v7.222: 设置 currentPhase = 'analysis'
      // v7.225: 过滤JSON系统思考内容，避免暴露在前端
      // v7.226: 增强过滤，识别描述JSON格式的系统思考痕迹
      case 'unified_dialogue_chunk':
        {
          const content = data.content || '';

          // v7.226: 累积到临时缓冲区进行整体检测
          setSearchState(prev => {
            const newBuffer = (prev._dialogueBuffer || '') + content;

            // v7.226: 检测是否为系统思考内容（不应展示给用户）
            // 包括JSON格式内容和描述JSON的元思考
            const isSystemThinking = (
              // 检测JSON对象/数组格式
              /^\s*\{\s*"/.test(newBuffer.trim()) ||
              /^\s*\[\s*\{/.test(newBuffer.trim()) ||
              // 检测典型的JSON字段名模式
              /"(user_profile|demographics|core_request|preferences|initial_assessment|current_round_planning|global_alignment|cumulative_progress|validation_criteria|expected_info|depends_on)"\s*:/.test(newBuffer) ||
              // v7.226: 检测描述JSON格式的系统提示痕迹
              /用户要求.*?JSON格式/.test(newBuffer) ||
              /输出.*?JSON/.test(newBuffer) ||
              /回顾上轮.*?必填/.test(newBuffer) ||
              /本轮规划.*?必填/.test(newBuffer) ||
              /累积进展.*?必填/.test(newBuffer) ||
              /全局校准.*?必填/.test(newBuffer) ||
              /initial_assessment|current_round_planning|global_alignment|cumulative_progress/.test(newBuffer)
            );

            if (isSystemThinking) {
              console.log('🔒 [v7.226] 检测到系统思考内容，跳过前端展示');
              return {
                ...prev,
                _dialogueBuffer: newBuffer,  // 保持缓冲但不展示
                status: 'analyzing',
                currentPhase: 'analysis',
                l0Phase: 'extracting',
                isProblemSolvingPhase: true,
                statusMessage: '正在深度分析...',
              };
            }

            // 非系统思考内容，累积展示
            return {
              ...prev,
              _dialogueBuffer: '',  // 清空缓冲
              status: 'analyzing',
              currentPhase: 'analysis',
              l0Phase: 'extracting',
              isProblemSolvingPhase: true,
              statusMessage: '正在理解您的需求并深度分析...',
              l0Content: (prev.l0Content || '') + newBuffer,
            };
          });
        }
        break;

      // v7.207: 统一对话完成
      case 'unified_dialogue_complete':
        console.log('💬 [v7.207] 统一分析对话完成');
        setSearchState(prev => ({
          ...prev,
          l0Phase: 'complete',
          statusMessage: '需求理解与深度分析完成',
        }));
        break;

      // v7.206 兼容: 旧版 L0 对话事件
      // v7.218: 同时存储到 problemSolvingThinking 用于解题思考卡片展示
      // v7.222: 设置 currentPhase = 'analysis'
      case 'l0_dialogue_chunk':
        // v7.224: 只累积到 l0Content，不再重复累积到 problemSolvingThinking
        setSearchState(prev => ({
          ...prev,
          status: 'analyzing',
          currentPhase: 'analysis',  // v7.222: 明确阶段
          l0Phase: 'extracting',
          isProblemSolvingPhase: true,  // v7.218: 标记为解题思考阶段
          statusMessage: '正在理解您的需求...',
          // v7.224: 累积对话内容到 l0Content（供 TaskUnderstandingCard 展示）
          l0Content: (prev.l0Content || '') + (data.content || ''),
        }));
        break;

      case 'l0_dialogue_complete':
        console.log('💬 [L0] 对话式分析完成');
        setSearchState(prev => ({
          ...prev,
          l0Phase: 'complete',
          statusMessage: '需求理解完成',
        }));
        break;

      // v7.207/v7.206: 用户画像就绪（系统内部，不展示JSON内容）
      case 'structured_info_ready':
        console.log('📋 [v7.207] 结构化信息就绪:', data);
        // 不更新 structuredInfo，因为 JSON 不再展示给用户
        break;

      // v7.205 兼容: 旧版事件（保留向后兼容）
      case 'l0_chunk':
        setSearchState(prev => ({
          ...prev,
          status: 'analyzing',
          l0Phase: 'extracting',
          statusMessage: '正在提取用户信息...',
          l0Content: (prev.l0Content || '') + (data.content || ''),
        }));
        break;

      case 'structured_info_extracted':
        console.log('📋 [L0] 结构化信息提取完成:', data);
        setSearchState(prev => ({
          ...prev,
          l0Phase: 'complete',
          structuredInfo: data,
          statusMessage: '用户信息提取完成',
        }));
        break;

      // ==================== Phase 处理 ====================

      // v7.218: 分析进度事件（解决164秒无进度提示问题）
      case 'analysis_progress':
        console.log('📊 [分析进度] 收到进度事件:', data);
        setSearchState(prev => {
          // v7.218: 如果是完成状态，清除进度显示
          // v7.229: 同时切换阶段到 search，避免页面"冻住"
          if (data.stage === 'complete') {
            return {
              ...prev,
              analysisProgress: null,
              currentPhase: 'search',  // v7.229: 明确切换到搜索阶段
              status: 'planning',       // v7.229: 状态切换到规划中
              statusMessage: data.message || '分析完成，准备开始搜索...',
            };
          }
          return {
            ...prev,
            status: 'analyzing',
            analysisProgress: {
              stage: data.stage || 'unknown',
              stageName: data.stage_name || '深度分析中',
              message: data.message || '正在进行深度分析...',
              estimatedTime: data.estimated_time || 180,
              currentStep: data.current_step || 0,
              totalSteps: data.total_steps || 3,
              startTime: prev.analysisProgress?.startTime || Date.now(),
            },
            statusMessage: data.message || '正在进行深度分析...',
          };
        });
        break;

      case 'phase':
        setSearchState(prev => {
          // v7.207: 处理统一分析阶段
          if (data.phase === 'unified_analysis') {
            return {
              ...prev,
              status: 'analyzing',
              l0Phase: 'extracting',
              statusMessage: data.message || '正在理解您的需求并深度分析...',
            };
          }
          // v7.206 兼容: 处理任务理解阶段
          if (data.phase === 'structured_extraction') {
            return {
              ...prev,
              status: 'analyzing',
              l0Phase: 'extracting',
              statusMessage: data.message || '正在理解您的需求...',
            };
          }
          return {
            ...prev,
            status: data.phase === 'synthesis' ? 'answering' : 'searching',
            statusMessage: data.message || data.phase_name || '',
          };
        });
        break;

      // v7.188: 流式问题分析（v7.207 已合并到 unified_dialogue_chunk，保留兼容）
      case 'analysis_chunk':
        setSearchState(prev => ({
          ...prev,
          status: 'analyzing',
          statusMessage: '正在分析问题...',
          // 累积分析推理内容
          analysisContent: (prev.analysisContent || '') + (data.content || ''),
        }));
        break;

      // v7.207: 问题分析完成，将对话内容或分析内容保存为 Round 0
      // v7.218: 标记解题思考阶段结束，开始多轮搜索阶段
      // v7.222: 切换 currentPhase 从 'analysis' 到 'search'
      case 'question_analyzed':
        console.log('📋 question_analyzed 事件:', data);
        if (DEBUG_PHASE_TRANSITIONS) {
          console.log('🔄 [PHASE] analysis → search');
        }
        setSearchState(prev => {
          // v7.207: 优先使用 l0Content（统一分析的对话内容），其次是 analysisContent
          const dialogueContent = prev.l0Content || prev.analysisContent || '';

          // v7.208: 提取搜索任务清单
          const masterLine = data.search_master_line || null;

          if (dialogueContent.trim()) {
            const analysisRound: RoundRecord = {
              round: 0,
              topicName: '需求理解与深度分析',  // v7.207: 更新标题
              searchQuery: data.answer_goal || '深度分析用户问题',
              sourcesFound: 0,
              sources: [],
              status: 'complete',
              isAnalysisPhase: true,
              reasoningContent: dialogueContent,
              showThinking: true,
            };
            return {
              ...prev,
              currentPhase: 'search',  // v7.222: 进入搜索阶段
              // v7.224: 检查是否已存在 Round 0，避免重复添加
              rounds: prev.rounds.some(r => r.round === 0 && r.isAnalysisPhase)
                ? prev.rounds
                : [analysisRound, ...prev.rounds],
              // v7.224: 不再清空 l0Content，保持 TaskUnderstandingCard 持续显示
              // l0Content: '',  // 保留内容供持续展示
              analysisContent: '',
              analysisSaved: true,
              // v7.218: 标记解题思考阶段结束
              isProblemSolvingPhase: false,
              statusMessage: data.message || `识别到 ${data.total_aspects || 0} 个关键信息面`,
            };
          }
          return {
            ...prev,
            analysisSaved: true,
            // v7.218: 标记解题思考阶段结束
            isProblemSolvingPhase: false,
            statusMessage: data.message || `识别到 ${data.total_aspects || 0} 个关键信息面`,
          };
        });
        break;

      // v7.208: 搜索主线就绪（单独事件，与 question_analyzed 互补）
      // ⚠️ REMOVED (v7.301): 已移除 SearchMasterLine，此事件不再处理
      case 'search_master_line_ready':
        console.log('⚠️ [v7.301] search_master_line_ready 事件已废弃，请使用 search_framework_ready');
        break;

      // 🆕 v7.237: 搜索框架就绪（v7.220 引入的新事件，替代 search_master_line_ready）
      // v7.301: 简化处理，只保留 frameworkChecklist，移除 masterLine 转换
      // v7.302: 检测并解析4条使命格式
      case 'search_framework_ready':
        console.log('📋 [v7.302] 搜索框架就绪:', data);
        {
          // v7.302: 检测是否为4条使命格式
          const has4Missions = data.four_missions &&
            data.four_missions.mission_1_user_problem_analysis &&
            data.four_missions.mission_2_clear_objectives &&
            data.four_missions.mission_3_task_dimensions &&
            data.four_missions.mission_4_execution_requirements;

          if (has4Missions) {
            // v7.302: 使用4条使命格式
            console.log('✅ [v7.302] 检测到4条使命格式');
            const fourMissions: FourMissions = data.four_missions;

            setSearchState(prev => ({
              ...prev,
              fourMissionsResult: fourMissions,
              statusMessage: `已完成4条使命分析`,
              awaitingConfirmation: true,
            }));
          } else {
            // v7.240: 提取框架清单（旧格式）
            // v7.250: 新增深度分析摘要字段
            // v7.301: 简化处理，只保留 frameworkChecklist
            const frameworkChecklist: FrameworkChecklist | null = data.framework_checklist ? {
              core_summary: data.framework_checklist.core_summary || '',
              main_directions: data.framework_checklist.main_directions || [],
              boundaries: data.framework_checklist.boundaries || [],
              answer_goal: data.framework_checklist.answer_goal || '',
              generated_at: data.framework_checklist.generated_at || '',
              plain_text: data.framework_checklist.plain_text || '',
              // v7.250 新增字段
              user_context: data.framework_checklist.user_context || undefined,
              key_entities: data.framework_checklist.key_entities || undefined,
              analysis_perspectives: data.framework_checklist.analysis_perspectives || undefined,
              core_tension: data.framework_checklist.core_tension || undefined,
              user_task: data.framework_checklist.user_task || undefined,
              sharpness_check: data.framework_checklist.sharpness_check || undefined,
            } : null;

            console.log('📋 [v7.301] 框架清单接收:', {
              hasChecklist: !!frameworkChecklist,
              coreSummary: frameworkChecklist?.core_summary,
              directionsCount: frameworkChecklist?.main_directions.length,
            });

            setSearchState(prev => ({
              ...prev,
              // v7.240: 存储框架清单（v7.301: 唯一的搜索方向展示）
              frameworkChecklist: frameworkChecklist,
              statusMessage: `已规划 ${frameworkChecklist?.main_directions.length || 0} 个搜索方向${data.quality_grade ? ` (${data.quality_grade})` : ''}`,
              // v7.280: 框架就绪后进入等待确认状态，允许用户编辑搜索方向
              awaitingConfirmation: true,
            }));
          }
        }
        break;

      // v7.271: 解题思路就绪
      case 'problem_solving_approach_ready':
        console.log('📋 [v7.271] 解题思路就绪:', data);
        setSearchState(prev => ({
          ...prev,
          statusMessage: '解题思路已生成，正在规划搜索任务...',
        }));
        break;

      // v7.271: 第一步完成
      case 'step1_complete':
        console.log('✅ [v7.271] 第一步完成:', data);
        setSearchState(prev => ({
          ...prev,
          statusMessage: '需求分析完成，开始生成搜索任务...',
        }));
        break;

      // v7.271: 第二步开始
      case 'step2_start':
        console.log('🚀 [v7.271] 第二步开始:', data);
        setSearchState(prev => ({
          ...prev,
          statusMessage: data.message || '正在生成搜索任务清单...',
        }));
        break;

      // v7.271: 第二步完成
      case 'step2_complete':
        console.log('✅ [v7.271] 第二步完成:', data);
        setSearchState(prev => ({
          ...prev,
          statusMessage: `搜索任务清单已生成（${data.target_count || 0}个任务）`,
        }));
        break;

      // 🆕 v7.300: 可编辑搜索计划就绪（第2步任务分解）
      case 'step2_plan_ready':
        console.log('📋 [v7.300] 可编辑搜索计划就绪:', data);
        {
          const searchSteps = (data.search_steps || []).map((step: any, idx: number) => ({
            id: step.id || `S${idx + 1}`,
            step_number: step.step_number || idx + 1,
            task_description: step.task_description || '',
            expected_outcome: step.expected_outcome || '',
            search_keywords: step.search_keywords || [],
            priority: step.priority || 'medium',
            can_parallel: step.can_parallel !== false,
            status: step.status || 'pending',
            completion_score: step.completion_score || 0,
            is_user_added: step.is_user_added || false,
            is_user_modified: step.is_user_modified || false,
          }));
          const stepsPerPage = 5;
          const plan: Step2SearchPlan = {
            session_id: data.session_id || sessionId || '',
            query: data.query || query || '',
            core_question: data.core_question || '',
            answer_goal: data.answer_goal || '',
            search_steps: searchSteps,
            max_rounds_per_step: data.max_rounds_per_step || 3,
            quality_threshold: data.quality_threshold || 0.7,
            user_added_steps: data.user_added_steps || [],
            user_deleted_steps: data.user_deleted_steps || [],
            user_modified_steps: data.user_modified_steps || [],
            current_page: 1,
            total_pages: Math.max(1, Math.ceil(searchSteps.length / stepsPerPage)),
            is_confirmed: false,
          };
          setStep2Plan(plan);
          setSearchState(prev => ({
            ...prev,
            awaitingConfirmation: true,
            statusMessage: `已生成 ${plan.search_steps.length} 个搜索任务，可编辑后运行`,
          }));
        }
        break;

      // v7.208: 搜索任务进度更新
      // ⚠️ REMOVED (v7.301): 已移除 taskProgress，此事件不再处理
      case 'task_progress':
        console.log('⚠️ [v7.301] task_progress 事件已废弃');
        break;

      case 'framework':
        console.log('📐 知识框架:', data);
        setSearchState(prev => ({
          ...prev,
          statusMessage: `知识框架: ${(data.core_concepts || []).join(', ')}`,
          searchPlan: {
            analysis: `核心概念: ${(data.core_concepts || []).join(', ')}`,
            aspects: data.dimensions || [],
            topics: data.sub_questions || data.initial_gaps || [],
            totalRounds: data.total_questions || 0,  // 子问题数量
            strategy: 'ucppt 缺口驱动迭代',
          },
          // 记录子问题数量用于进度显示
          totalRounds: data.total_questions || 0,
        }));
        break;

      // ==================== Ucppt Phase 2: 迭代搜索 ====================

      // v7.188: 流式思考内容，按轮次和类型累积
      // 🔧 v7.195: 使用 roundThinkingMap 按轮次独立存储，解决轮次切换时的内容回退问题
      // 🔧 v7.218: 根据 phase 字段区分 Phase 0（解题思考）和 Phase 2（轮次思考）
      // v7.222: 设置 currentPhase = 'search'
      // v7.226: 过滤系统思考痕迹（JSON格式描述等）
      case 'thinking_chunk':
        setSearchState(prev => {
          const content = data.content || '';
          const isReasoning = data.is_reasoning === true;
          const chunkRound = data.round || prev.currentRound || 1;
          const phase = data.phase || 'search_round';  // v7.218: 默认为搜索轮次

          // 🔧 DEBUG: 调试日志 - 追踪思考内容更新（优化版）
          if (DEBUG_STATE_CHANGES) {
            console.log('🧠 [THINKING] 内容更新:', {
              round: chunkRound,
              isReasoning,
              phase,
              contentLength: content.length,
              currentRound: prev.currentRound,
              thinkingRound: prev.currentThinkingRound,
            });
          }

          // v7.226: 检测并过滤系统思考痕迹
          const existingRoundContent = prev.roundThinkingMap[chunkRound] || { reasoning: '', thinking: '' };
          const newContent = isReasoning
            ? existingRoundContent.reasoning + content
            : existingRoundContent.thinking + content;

          // 检测系统思考模式（JSON格式描述、框架结构等）
          const isSystemThinking = (
            /用户要求.*?JSON格式/.test(newContent) ||
            /输出.*?JSON/.test(newContent) ||
            /回顾上轮.*?必填/.test(newContent) ||
            /本轮规划.*?必填/.test(newContent) ||
            /累积进展.*?必填/.test(newContent) ||
            /全局校准.*?必填/.test(newContent) ||
            /^\s*\{\s*"/.test(newContent.trim()) ||
            /initial_assessment|current_round_planning|global_alignment|cumulative_progress/.test(newContent) ||
            /"validation_criteria"|"expected_info"|"depends_on"/.test(newContent)
          );

          if (isSystemThinking) {
            console.log('🔒 [v7.226] thinking_chunk: 检测到系统思考内容，跳过展示');
            // 保持状态但不更新展示内容
            return {
              ...prev,
              status: 'thinking',
              currentPhase: 'search',
              isThinking: true,
              currentThinkingRound: chunkRound,
              isProblemSolvingPhase: false,
              statusMessage: `第${chunkRound}轮·深度分析中...`,
            };
          }

          const updatedRoundContent = {
            reasoning: isReasoning ? existingRoundContent.reasoning + content : existingRoundContent.reasoning,
            thinking: !isReasoning ? existingRoundContent.thinking + content : existingRoundContent.thinking,
          };

          return {
            ...prev,
            status: 'thinking',
            currentPhase: 'search',  // v7.222: 明确是搜索阶段的思考
            isThinking: true,
            currentThinkingRound: chunkRound,
            isProblemSolvingPhase: false,  // v7.218: 收到 thinking_chunk 说明已进入搜索阶段
            // 🔧 v7.195: 更新 roundThinkingMap（按轮次独立存储）
            roundThinkingMap: {
              ...prev.roundThinkingMap,
              [chunkRound]: updatedRoundContent,
            },
            // 当前轮次的实时显示内容
            currentRoundReasoning: updatedRoundContent.reasoning,
            currentRoundThinking: updatedRoundContent.thinking,
            statusMessage: isReasoning ? `第${chunkRound}轮·深度推理中...` : `第${chunkRound}轮·思考中...`,
          };
        });
        break;

      case 'narrative_thinking':
        // 非流式思考完成（fallback）
        console.log('📝 [THINKING] 非流式思考完成:', data);
        setSearchState(prev => ({
          ...prev,
          status: 'thinking',
          isThinking: false,
          statusMessage: data.message || '思考完成',
        }));
        break;

      case 'round_start':
        console.log('🔍 round_start 事件:', data);
        // v7.188: 不再在此处清空思考内容，改为在 thinking_chunk 检测轮次变化时清空
        // v7.280: 搜索轮次开始，关闭框架清单编辑模式
        {
          // 🔧 DEBUG: 调试日志 - 追踪轮次开始时的状态
          console.log('🔍 [DEBUG] round_start 状态:', {
            newRound: data.round,
            prevRound: searchState.currentRound,
            currentThinkingRound: searchState.currentThinkingRound,
            currentReasoningLength: searchState.currentRoundReasoning?.length ?? 0,
            currentThinkingLength: searchState.currentRoundThinking?.length ?? 0,
            roundsCount: searchState.rounds?.length ?? 0,
          });

          // 构建动态状态消息
          const progress = data.progress;
          const targetGap = data.target_gap;
          let statusMsg = '';

          if (progress) {
            statusMsg = `已回答 ${progress.answered}/${progress.total} 个问题`;
          }
          if (targetGap) {
            // 这里可以根据 targetGap 进一步定制 statusMsg 或其他逻辑
          }
          setSearchState(prev => {
            // v7.229: 检查轮次是否已存在
            const existingRound = prev.rounds.find(r =>
              r.round === data.round && !r.isAnalysisPhase
            );

            if (existingRound) {
              // 轮次已存在，只更新状态
              return {
                ...prev,
                status: 'searching',
                statusMessage: statusMsg,
                currentRound: data.round,
                currentThinkingRound: data.round,  // v7.229: 更新当前思考轮次
                awaitingConfirmation: false,  // v7.280: 搜索开始后关闭编辑模式
              };
            }

            // v7.229: 创建占位轮次卡片，让思考内容能够正确显示在轮次内
            const placeholderRound: RoundRecord = {
              round: data.round,
              topicName: data.target_aspect || data.topicName || `第 ${data.round} 轮搜索`,
              searchQuery: data.query || '',
              sourcesFound: 0,
              sources: [],
              status: 'searching',  // 标记为搜索中
            };

            return {
              ...prev,
              status: 'searching',
              statusMessage: statusMsg,
              currentRound: data.round,
              currentThinkingRound: data.round,  // v7.229: 更新当前思考轮次
              rounds: [...prev.rounds, placeholderRound],
              awaitingConfirmation: false,  // v7.280: 搜索开始后关闭编辑模式
            };
          });
        }
        break;

      case 'round_sources':
        console.log('📦 round_sources 事件:', data);
        setSearchState(prev => {
          // 🔧 DEBUG: 调试日志 - 追踪保存时的内容状态
          console.log('📦 [DEBUG] round_sources 保存前状态:', {
            round: data.round,
            sourcesCount: (data.sources || []).length,
            currentThinkingRound: prev.currentThinkingRound,
            currentReasoningLength: prev.currentRoundReasoning?.length ?? 0,
            currentThinkingLength: prev.currentRoundThinking?.length ?? 0,
            roundsCount: prev.rounds?.length ?? 0,
          });

          const roundSources: SourceCard[] = (data.sources || []).map((s: any, idx: number) => ({
            title: s.title || '',
            url: s.url || '',
            siteName: s.siteName || s.site_name || '',
            siteIcon: s.siteIcon || '',
            snippet: s.content || s.snippet || '',
            summary: s.summary || '',
            datePublished: s.datePublished || '',
            referenceNumber: prev.sources.length + idx + 1,
            isWhitelisted: s.isWhitelisted || false,
            id: s.url || '',
            shortId: `${data.round}-${idx + 1}`,
          }));

          // 🔧 v7.195: 从 roundThinkingMap 读取对应轮次的思考内容
          // 这样即使轮次已切换，也能正确获取该轮次的完整内容
          const roundThinkingContent = prev.roundThinkingMap[data.round] || { reasoning: '', thinking: '' };

          // 🔧 DEBUG: 调试日志 - 确认保存的内容
          console.log('📦 [DEBUG] round_sources 保存内容:', {
            round: data.round,
            reasoningLength: roundThinkingContent.reasoning.length,
            thinkingLength: roundThinkingContent.thinking.length,
          });

          // v7.229: 检查轮次是否已存在（由 round_start 创建的占位轮次）
          const existingRoundIndex = prev.rounds.findIndex(r =>
            r.round === data.round && !r.isAnalysisPhase
          );

          if (existingRoundIndex >= 0) {
            // v7.229: 轮次已存在，更新它（而不是创建新的）
            const existingRound = prev.rounds[existingRoundIndex];

            // 如果已有来源，跳过
            if (existingRound.sources && existingRound.sources.length > 0) {
              console.warn(`⚠️ [round_sources] 轮次 ${data.round} 已有 ${existingRound.sources.length} 个来源，跳过`);
              return prev;
            }

            // 更新占位轮次
            const updatedRounds = [...prev.rounds];
            updatedRounds[existingRoundIndex] = {
              ...existingRound,
              topicName: data.target_aspect || existingRound.topicName,
              searchQuery: data.query || existingRound.searchQuery,
              sourcesFound: data.sources_count || roundSources.length,
              sources: roundSources,
              status: 'complete',
              reasoningContent: roundThinkingContent.reasoning,
              thinkingContent: roundThinkingContent.thinking,
              showThinking: true,
            };

            console.log(`📦 [round_sources] 更新轮次 ${data.round} | 来源=${roundSources.length}`);

            return {
              ...prev,
              rounds: updatedRounds,
              sources: [...prev.sources, ...roundSources],
            };
          }

          // 轮次不存在，创建新的
          const newRound: RoundRecord = {
            round: data.round,
            topicName: data.target_aspect || `第 ${data.round} 轮搜索`,
            searchQuery: data.query || '',
            sourcesFound: data.sources_count || roundSources.length,
            sources: roundSources,
            executionTime: 0,
            status: 'complete',
            reasoningContent: roundThinkingContent.reasoning,
            thinkingContent: roundThinkingContent.thinking,
            showThinking: true,
          };

          return {
            ...prev,
            rounds: [...prev.rounds, newRound],
            sources: [...prev.sources, ...roundSources],
          };
        });
        break;

      case 'round_reflecting':
        setSearchState(prev => ({
          ...prev,
          statusMessage: data.message || '评估信息充分度...',
        }));
        break;

      case 'round_complete':
        console.log('✅ round_complete 事件:', data);
        {
          // 构建包含多维度评估的消息
          const progress = data.progress;
          const evaluation = data.evaluation;
          let statusMsg = `搜索完成`;

          if (progress) {
            statusMsg += ` | 进度 ${progress.answered}/${progress.total}`;
          }
          if (evaluation) {
            statusMsg += ` | 覆盖${(evaluation.coverage * 100).toFixed(0)}%`;
          } else {
            statusMsg += ` | 置信度 ${(data.confidence * 100).toFixed(0)}%`;
          }

          if (!data.should_continue) {
            statusMsg += ' | 即将完成';
          }

          setSearchState(prev => ({
            ...prev,
            statusMessage: statusMsg,
          }));
        }
        break;

      case 'search_complete':
        console.log('🎯 search_complete 事件:', data);
        {
          let statusMsg = `搜索完成: ${data.reason}`;
          if (data.questions_answered !== undefined) {
            statusMsg += ` | 回答了 ${data.questions_answered}/${data.questions_total} 个问题`;
          }
          statusMsg += ` | 共 ${data.totalRounds || data.total_rounds || 0} 轮`;

          setSearchState(prev => ({
            ...prev,
            statusMessage: statusMsg,
            totalRounds: data.totalRounds || data.total_rounds || prev.totalRounds,
          }));
        }
        break;

      // ==================== Ucppt Phase 3: 深度钻取 ====================
      case 'drill_start':
        setSearchState(prev => ({
          ...prev,
          statusMessage: `深度钻取: ${data.concept}`,
        }));
        break;

      case 'drill_complete':
        console.log('🔬 drill_complete 事件:', data);
        break;

      // ==================== Ucppt Phase 4: 生成回答 ====================
      // v7.222: 设置 currentPhase = 'synthesis'，明确与搜索阶段区分
      case 'answer_chunk':
        {
          const ansContent = data.content || '';
          const isThinking = data.is_thinking === true;

          if (DEBUG_PHASE_TRANSITIONS && isThinking) {
            console.log('🔄 [PHASE] search → synthesis (answer thinking)');
          }

          if (isThinking) {
            // 思考过程内容（答案构思阶段）
            setSearchState(prev => ({
              ...prev,
              status: 'answering',
              currentPhase: 'synthesis',  // v7.222: 进入综合阶段
              isAnswering: true,
              answerThinkingContent: prev.answerThinkingContent + ansContent,
            }));
          } else {
            // 实际答案内容
            setSearchState(prev => ({
              ...prev,
              status: 'answering',
              currentPhase: 'synthesis',  // v7.222: 综合阶段
              isAnswering: true,
              answerContent: prev.answerContent + ansContent,
            }));
          }
        }
        break;

      case 'answer_thinking_complete':
        if (DEBUG_PHASE_TRANSITIONS) {
          console.log('🔄 [PHASE] synthesis: thinking → content');
        }
        setSearchState(prev => ({
          ...prev,
          statusMessage: data.message || '开始生成详细答案...',
        }));
        break;

      // v7.281: 答案质量评估
      case 'answer_quality_assessment':
        console.log('📊 [v7.281] 答案质量评估:', data);
        setSearchState(prev => ({
          ...prev,
          qualityAssessment: {
            confidence: data.confidence,
            citation: data.citation,
            conflicts: data.conflicts,
          },
          statusMessage: data.message || prev.statusMessage,
        }));
        break;

      // ==================== 完成和错误 ====================
      case 'done':
        console.log('✅ done 事件:', data);
        {
          const finalRounds = data.totalRounds || data.total_rounds || 0;
          // 🔧 v7.219: 兼容两种字段名，防止 NaN；fallback 到本地计数
          const finalConfidence = data.final_confidence ?? data.final_completeness ?? 0;
          const totalSources = data.total_sources ?? 0;
          if (DEBUG_PHASE_TRANSITIONS) {
            console.log('🔄 [PHASE] → done');
          }
          setSearchState(prev => ({
            ...prev,
            status: 'done',
            currentPhase: 'done',  // v7.222: 标记完成
            statusMessage: `完成: ${finalRounds} 轮 | ${totalSources || prev.sources.length} 来源 | 置信度 ${(finalConfidence * 100).toFixed(0)}%`,
            executionTime: data.execution_time || 0,
            isAnswering: false,
            totalRounds: finalRounds,
          }));
        }
        break;

      case 'error':
        setSearchState(prev => ({
          ...prev,
          status: 'error',
          error: data.message || '搜索失败',
        }));
        break;

      // ==================== 兼容旧事件（保留） ====================
      case 'planning_start':
        setSearchState(prev => ({
          ...prev,
          status: 'planning',
          statusMessage: data.message || '正在分析问题，制定搜索计划...',
        }));
        break;

      case 'planning_complete':
        console.log('🎯 planning_complete 事件:', data);
        {
          const planRounds = data.totalRounds || data.total_rounds || 0;
          setSearchState(prev => ({
            ...prev,
            status: 'planning',
            statusMessage: '搜索计划已生成',
            searchPlan: {
              analysis: data.analysis || '',
              aspects: data.aspects || [],
              topics: data.topics || [],
              totalRounds: planRounds,
              strategy: data.strategy || '',
            },
            totalRounds: planRounds,
          }));
        }
        break;

      case 'search_round_start':
        console.log('🔍 search_round_start 事件:', data);
        {
          const roundTotal = data.totalRounds || data.total_rounds || 0;
          setSearchState(prev => ({
            ...prev,
            status: 'searching',
            statusMessage: `第 ${data.round}/${roundTotal} 轮：${data.topicName}`,
            currentRound: data.round,
            totalRounds: roundTotal || prev.totalRounds,
          }));
        }
        break;

      case 'search_round_complete':
        console.log('📦 search_round_complete 事件:', data);
        setSearchState(prev => {
          // v7.229: 检查轮次是否已存在（由 round_sources 创建）
          const existingRoundIndex = prev.rounds.findIndex(r =>
            r.round === data.round && !r.isAnalysisPhase
          );

          if (existingRoundIndex >= 0) {
            // 轮次已存在，只更新状态，保留思考内容
            console.log(`📦 [search_round_complete] 轮次 ${data.round} 已存在，仅更新状态`);
            const updatedRounds = [...prev.rounds];
            updatedRounds[existingRoundIndex] = {
              ...updatedRounds[existingRoundIndex],
              status: 'complete',
              executionTime: data.executionTime || updatedRounds[existingRoundIndex].executionTime,
            };
            return {
              ...prev,
              statusMessage: `第 ${data.round} 轮完成，找到 ${data.sourcesFound} 个来源`,
              rounds: updatedRounds,
            };
          }

          // 轮次不存在，创建新的（包含思考内容）
          const roundThinkingContent = prev.roundThinkingMap[data.round] || { reasoning: '', thinking: '' };
          const roundSources: SourceCard[] = (data.sources || []).map((s: any) => ({
            title: s.title || '',
            url: s.url || '',
            siteName: s.siteName || '',
            siteIcon: s.siteIcon || '',
            snippet: s.snippet || '',
            summary: s.summary || '',
            datePublished: s.datePublished || '',
            referenceNumber: s.referenceNumber || 0,
            isWhitelisted: s.isWhitelisted || false,
            id: s.id || '',
            shortId: s.shortId || '',
          }));

          const newRound: RoundRecord = {
            round: data.round,
            topicName: data.topicName || '',
            searchQuery: data.searchQuery || '',
            sourcesFound: data.sourcesFound || 0,
            sources: roundSources,
            executionTime: data.executionTime,
            status: 'complete',
            // v7.229: 保留思考内容
            reasoningContent: roundThinkingContent.reasoning,
            thinkingContent: roundThinkingContent.thinking,
          };

          return {
            ...prev,
            statusMessage: `第 ${data.round} 轮完成，找到 ${data.sourcesFound} 个来源`,
            rounds: [...prev.rounds, newRound],
          };
        });
        break;

      case 'search_all_complete':
        console.log('✅ search_all_complete 事件:', data);
        setSearchState(prev => ({
          ...prev,
          statusMessage: `搜索完成，共找到 ${data.totalSources} 个来源`,
        }));
        break;

      case 'sources':
        setSearchState(prev => ({
          ...prev,
          sources: (data as any[]).map((s: any) => ({
            ...s,
            id: s.id || '',
            shortId: s.shortId || '',
          })) as SourceCard[],
        }));
        break;

      case 'images':
        setSearchState(prev => ({
          ...prev,
          images: data as ImageResult[],
        }));
        break;

      case 'thinking_start':
        setSearchState(prev => ({
          ...prev,
          status: 'thinking',
          statusMessage: data.message || '正在进行深度分析...',
          isThinking: true,
          thinkingContent: '',
        }));
        setShowThinking(true);
        break;

      // 注意：thinking_chunk 已在前面的 Ucppt Phase 2 部分处理，这里不再重复处理

      case 'thinking_complete':
        setSearchState(prev => ({
          ...prev,
          isThinking: false,
          statusMessage: '深度分析完成',
        }));
        break;

      case 'answer_start':
        setSearchState(prev => ({
          ...prev,
          status: 'answering',
          statusMessage: data.message || '正在生成回答...',
          isAnswering: true,
          answerContent: '',
        }));
        break;

      case 'answer_complete':
        setSearchState(prev => ({
          ...prev,
          isAnswering: false,
        }));
        break;

      case 'thinking':
        setSearchState(prev => ({
          ...prev,
          status: data.status === 'reasoning' ? 'thinking' : 'searching',
          statusMessage: data.message || '',
        }));
        break;

      case 'reasoning_chunk':
        setSearchState(prev => ({
          ...prev,
          status: 'thinking',
          thinkingContent: prev.thinkingContent + data,
        }));
        setShowThinking(true);
        break;

      case 'content_chunk':
        setSearchState(prev => ({
          ...prev,
          status: 'answering',
          answerContent: prev.answerContent + data,
        }));
        break;

      case 'content':
        setSearchState(prev => ({
          ...prev,
          answerContent: data,
        }));
        break;

      // 🆕 v7.280: 分阶段确认模式事件
      case 'awaiting_confirmation':
        console.log('📋 [v7.280] 收到等待确认事件:', data);
        setSearchState(prev => ({
          ...prev,
          awaitingConfirmation: true,
          status: 'analyzing',
          statusMessage: data.message || '分析完成，请确认搜索方向',
        }));
        break;

      case 'step1_complete':
        console.log('📋 [v7.280] Step 1 完成:', data);
        setSearchState(prev => ({
          ...prev,
          awaitingConfirmation: true,
          status: 'analyzing',
          statusMessage: '深度分析完成，请确认或编辑搜索方向后继续',
        }));
        break;

      case 'step2_start':
        console.log('🔍 [v7.280] Step 2 开始:', data);
        setSearchState(prev => ({
          ...prev,
          awaitingConfirmation: false,
          status: 'searching',
          statusMessage: data.message || '开始搜索...',
        }));
        break;

      default:
        console.log('未处理的事件类型:', eventType, data);
    }
  }, [sessionId, query]);  // v7.300: 添加 query 依赖用于 step2_plan_ready

  // 追问
  const handleFollowUp = () => {
    if (!followUpQuery.trim()) return;
    const newQuery = followUpQuery.trim();
    setFollowUpQuery('');
    setQuery(newQuery);
    startSearch(newQuery, deepMode);  // 使用当前的深度模式
  };

  // 渲染状态指示器 - 已禁用，因为推理和正文部分都有状态显示
  const renderStatusIndicator = () => {
    // v7.290: 显示错误状态
    if (searchState.status === 'error' && searchState.error) {
      return (
        <div className="mb-6 bg-red-50 dark:bg-red-900/20 rounded-xl p-5 border border-red-200 dark:border-red-800">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center flex-shrink-0">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-red-600 dark:text-red-400 font-medium mb-1">搜索失败</p>
              <p className="text-sm text-red-800 dark:text-red-200 leading-relaxed">
                {searchState.error}
              </p>
              <button
                onClick={() => {
                  // 重置状态，允许重新搜索
                  setSearchState(prev => ({
                    ...prev,
                    status: 'idle',
                    error: null,
                  }));
                }}
                className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-medium transition-colors"
              >
                <Search className="w-4 h-4" />
                重新搜索
              </button>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  // 渲染来源卡片
  const renderSourceCard = (source: SourceCard) => (
    <a
      key={source.id || source.referenceNumber}
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block p-3 rounded-lg border border-[var(--border-color)] bg-[var(--card-bg)] transition-all duration-200 hover:bg-[#2a2a2a] dark:hover:bg-[#2a2a2a] hover:border-[#404040]"
    >
      <div className="min-w-0">
        {/* 🆕 v7.167: 引用编号和短ID */}
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full bg-[var(--primary)] text-white text-xs font-medium flex-shrink-0">
            {source.referenceNumber}
          </span>
          <h4 className="font-medium text-[var(--foreground)] truncate text-sm">
            {source.title}
          </h4>
          {source.isWhitelisted && (
            <Star className="w-3.5 h-3.5 text-yellow-500 flex-shrink-0" />
          )}
          <ExternalLink className="w-3.5 h-3.5 text-[var(--foreground-secondary)] flex-shrink-0" />
        </div>

        {/* 站点名称和日期 */}
        <div className="flex items-center gap-2 mt-1 text-xs text-[var(--foreground-secondary)]">
          <span className="truncate">{source.siteName}</span>
          {source.datePublished && (
            <>
              <span>·</span>
              <Clock className="w-3 h-3" />
              <span>{new Date(source.datePublished).toLocaleDateString('zh-CN')}</span>
            </>
          )}
        </div>

        {/* 摘要 */}
        <p className="mt-2 text-xs text-[var(--foreground-secondary)] line-clamp-2">
          {source.snippet}
        </p>
      </div>
    </a>
  );

  // 打开图片查看器
  const openImageViewer = (index: number) => {
    setImageViewerIndex(index);
    setImageViewerOpen(true);
  };

  // 渲染图片区域
  const renderImagesSection = () => {
    const { images } = searchState;
    if (images.length === 0) return null;

    // 展示8张图片 + 1个查看全部占位 = 9格
    const maxDisplay = 8;
    const displayImages = showAllImages ? images : images.slice(0, maxDisplay);
    const hasMore = !showAllImages && images.length > maxDisplay;

    return (
      <div className="bg-[var(--card-bg)] rounded-xl border border-[var(--border-color)] p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-[var(--foreground)] flex items-center gap-2">
            <ImageIcon className="w-5 h-5 text-[var(--primary)]" />
            图片
          </h3>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {displayImages.map((image, idx) => (
            <button
              key={idx}
              onClick={() => openImageViewer(showAllImages ? idx : idx)}
              className="relative aspect-[4/3] rounded-lg overflow-hidden bg-[var(--sidebar-bg)] cursor-pointer group"
            >
              <img
                src={image.thumbnailUrl || image.url}
                alt={image.title || '图片'}
                className="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
                loading="lazy"
                onError={(e) => {
                  // 图片加载失败时尝试使用原始URL，如果已经是原始URL则隐藏
                  const target = e.target as HTMLImageElement;
                  if (target.src === image.thumbnailUrl && image.url) {
                    target.src = image.url;
                  } else {
                    target.style.display = 'none';
                  }
                }}
              />
            </button>
          ))}
          {/* 查看全部占位格 */}
          {hasMore && (
            <button
              onClick={() => setShowAllImages(true)}
              className="relative aspect-[4/3] rounded-lg overflow-hidden bg-purple-100 dark:bg-purple-900/30 cursor-pointer hover:bg-purple-200 dark:hover:bg-purple-900/50 transition-colors flex flex-col items-center justify-center gap-1"
            >
              <span className="text-2xl font-bold text-purple-600 dark:text-purple-300">+{images.length - maxDisplay}</span>
              <span className="text-xs text-purple-600 dark:text-purple-300">查看全部</span>
            </button>
          )}
        </div>
      </div>
    );
  };

  // v7.222: renderDeepSearchProgress 已删除，功能合并到 UnifiedSearchProgressCard

  // v7.170: 渲染深度思考过程
  // v7.188: 仅在搜索进行中显示实时思考进度，搜索完成后思考内容已融入各轮次
  const renderThinking = () => {
    const { thinkingContent, status, isThinking } = searchState;

    // v7.188: 搜索完成后不再显示独立的思考卡片（内容已融入各轮次）
    // v7.209: 修复类型错误，使用正确的状态值 'done' 而非 'complete'
    if (status === 'done' || status === 'error') return null;

    // 正在思考或有思考内容时显示
    if (!thinkingContent && !isThinking) return null;

    // 🆕 v7.181: 检测结构化推理步骤进度
    const detectSteps = (content: string) => {
      const steps = [
        { name: '问题分解', pattern: /第一步|Step\s*1/i, icon: '🔍' },
        { name: '信息提取', pattern: /第二步|Step\s*2/i, icon: '📋' },
        { name: '主题聚类', pattern: /第三步|Step\s*3/i, icon: '🗂️' },
        { name: '信息验证', pattern: /第四步|Step\s*4/i, icon: '✅' },
        { name: '概念提炼', pattern: /第五步|Step\s*5/i, icon: '💡' },
      ];
      return steps.map(step => ({
        ...step,
        completed: step.pattern.test(content)
      }));
    };

    const steps = detectSteps(thinkingContent);
    const completedSteps = steps.filter(s => s.completed).length;

    return (
      <div className="mb-6">
        {/* v7.243: 深度思考标题栏 - 根据展开状态动态设置圆角 */}
        <div
          className={`
            flex items-center justify-between p-4 cursor-pointer
            bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700
            hover:bg-purple-100 dark:hover:bg-purple-900/30
            transition-all duration-300
            ${thinkingExpanded ? 'rounded-t-xl' : 'rounded-xl'}
          `}
          onClick={() => {
            // 🔧 修复：用户手动操作时取消自动折叠计时器
            if (autoCollapseTimer) {
              clearTimeout(autoCollapseTimer);
              setAutoCollapseTimer(null);
              console.log('👤 用户手动操作，取消自动折叠计时器');
            }
            setShowThinking(!showThinking);
          }}
        >
          {/* v7.225: 扁平化样式适配 */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <Brain className={`w-6 h-6 text-purple-600 dark:text-purple-400 ${isThinking ? 'animate-pulse' : ''}`} />
              {isThinking && (
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full animate-ping" />
              )}
            </div>
            <div>
              <h3 className="text-purple-600 dark:text-purple-400 font-semibold">
                深度推理
              </h3>
              <p className="text-gray-500 dark:text-gray-400 text-xs mt-0.5">
                {isThinking ? '正在进行结构化分析...' : `已完成 ${completedSteps}/5 步 · ${thinkingContent.length} 字符`}
              </p>
            </div>
          </div>

          {/* 🆕 v7.181: 步骤进度指示器 - v7.225: 扁平化适配 */}
          <div className="flex items-center gap-2">
            {!isThinking && completedSteps > 0 && (
              <div className="hidden sm:flex items-center gap-1 mr-2">
                {steps.map((step, idx) => (
                  <div
                    key={idx}
                    className={`w-2 h-2 rounded-full transition-colors ${
                      step.completed ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'
                    }`}
                    title={`${step.icon} ${step.name}`}
                  />
                ))}
              </div>
            )}
            {isThinking && (
              <div className="flex items-center gap-1 text-purple-600 dark:text-purple-400 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" />
                思考中...
              </div>
            )}
            <ChevronRight
              className={`w-5 h-5 text-gray-400 transition-transform duration-300 ${showThinking ? 'rotate-90' : ''}`}
            />
          </div>
        </div>

        {/* 思考内容 - 可折叠 */}
        <div
          className={`
            overflow-hidden transition-all duration-300 ease-in-out
            ${showThinking ? 'opacity-100' : 'max-h-0 opacity-0'}
          `}
        >
          <div className="ai-thinking-content border border-t-0 border-[var(--border-color)] rounded-b-xl p-8">
            <div className="pr-4">
              <div className="ai-thinking-text">
                {thinkingContent.split('\n').map((line, idx) => {
                  // 🆕 v7.181: 识别结构化推理步骤并高亮显示
                  const isStep = line.match(/^###?\s*(第[一二三四五六七八九十]+步|Step\s*\d+)/i);
                  const isSubheading = line.match(/^###\s+/);
                  const isHeading = line.match(/^##\s+/) && !isSubheading;
                  const isSource = line.match(/^来源\s*\d+|^\[?\d+\]?[：:]/);
                  const isHighQuality = line.includes('高') && (line.includes('质量') || line.includes('相关'));
                  const isMediumQuality = line.includes('中') && (line.includes('质量') || line.includes('相关'));
                  const isLowQuality = line.includes('低') && (line.includes('质量') || line.includes('相关'));
                  const isTheme = line.match(/^[-•]\s*(主题|Topic)/i);

                  return (
                    <p key={idx} className={`
                      ${line.trim() === '' ? 'h-2' : ''}
                      ${line.startsWith('•') || line.startsWith('-') || line.startsWith('*') ? 'list-item' : ''}
                      ${line.match(/^\d+\./) ? 'numbered' : ''}
                      ${isStep ? 'text-purple-600 dark:text-purple-400 font-semibold text-base mt-4 mb-2 border-l-4 border-purple-500 pl-3 py-1' : ''}
                      ${isHeading ? 'text-indigo-600 dark:text-indigo-400 font-medium mt-3' : ''}
                      ${isSubheading ? 'text-blue-600 dark:text-blue-400 font-medium mt-2' : ''}
                      ${isSource ? 'bg-gray-50 dark:bg-gray-800/50 rounded px-2 py-1 my-1 text-sm border-l-2 border-blue-400' : ''}
                      ${isTheme ? 'text-amber-600 dark:text-amber-400 font-medium' : ''}
                      ${isHighQuality ? 'text-green-600 dark:text-green-400' : ''}
                      ${isMediumQuality ? 'text-amber-600 dark:text-amber-400' : ''}
                      ${isLowQuality ? 'text-gray-400 dark:text-gray-500' : ''}
                    `}>
                      {line.replace(/^#+\s*/, '')}
                    </p>
                  );
                })}
                {isThinking && (
                  <span className="ai-thinking-cursor" />
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // v7.170: 渲染回答内容
  const renderContent = () => {
    const { answerContent, status, sources, isAnswering } = searchState;

    if (!answerContent && !isAnswering) return null;

    // 🆕 v7.167: 提取正文中实际引用的来源编号（支持新格式 [编号:ID]）
    const extractReferencedNumbers = (text: string): number[] => {
      // 匹配 [1] 或 [1:abc123] 格式
      const matches = text.match(/\[(\d+)(?::[a-zA-Z0-9]+)?\]/g) || [];
      const numbers = matches.map(m => {
        const numMatch = m.match(/\[(\d+)/);
        return numMatch ? parseInt(numMatch[1]) : 0;
      }).filter(n => n > 0);
      // 去重并排序 - v7.209: 使用 Array.from 替代展开操作符以兼容较低版本 TypeScript target
      return Array.from(new Set(numbers)).sort((a, b) => a - b);
    };

    const referencedNumbers = extractReferencedNumbers(answerContent);
    const referencedSources = referencedNumbers
      .map(num => sources.find(s => s.referenceNumber === num))
      .filter((s): s is SourceCard => s !== undefined);

    return (
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* v7.242: 内容头部 - 统一扁平化样式，无底纹 */}
        <div className="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Sparkles className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              <div>
                <p className="text-sm text-purple-600 dark:text-purple-400 font-medium">AI 分析回答</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  基于 {sources.length} 个信息来源 · {isAnswering ? '生成中...' : '已完成'}
                </p>
              </div>
            </div>

            {isAnswering && (
              <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-xs">生成中</span>
              </div>
            )}
          </div>
        </div>

        {/* 正文内容 */}
        <div className="ai-thinking-content px-6 py-6">
          {/* 🆕 v7.242: 答案生成思考过程 - 统一扁平化样式 */}
          {searchState.answerThinkingContent && (
            <div className="mb-6">
              <div className="flex items-center gap-2 mb-3">
                <Brain className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                  答案构思过程
                </span>
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed whitespace-pre-wrap">
                {searchState.answerThinkingContent}
                {isAnswering && searchState.answerThinkingContent && (
                  <span className="inline-block w-1.5 h-4 bg-purple-500 dark:bg-purple-400 ml-0.5 animate-pulse rounded-sm" />
                )}
              </div>
            </div>
          )}

          <div className="ai-thinking-text">
            {answerContent.split('\n').map((line, idx) => {
              // 🆕 v7.180: 将 [1:abc123] 格式转换为 [1] 格式，只显示数字
              const cleanedLine = line.replace(/\[(\d+):[a-zA-Z0-9]+\]/g, '[$1]');
              return (
                <p key={idx} className={`
                  ${cleanedLine.trim() === '' ? 'h-2' : ''}
                  ${cleanedLine.startsWith('•') || cleanedLine.startsWith('-') || cleanedLine.startsWith('*') ? 'list-item' : ''}
                  ${cleanedLine.match(/^\d+\./) ? 'numbered' : ''}
                  ${cleanedLine.startsWith('#') ? 'heading' : ''}
                `}>
                  {cleanedLine.replace(/^#+\s*/, '')}
                </p>
              );
            })}
            {isAnswering && (
              <span className="ai-thinking-cursor" />
            )}
          </div>

          {/* 🆕 v7.171: References 参考来源列表 */}
          {/* 🔧 v7.175: 统一字体样式 - 白色背景配深色文字 */}
          {!isAnswering && referencedSources.length > 0 && (
            <div className="mt-8 pt-6 border-t border-gray-200">
              <h4 className="text-lg font-semibold text-gray-900 mb-5 flex items-center gap-2">
                <span>📚</span>
                <span>参考来源</span>
                <span className="text-sm font-normal text-gray-500">
                  ({referencedSources.length})
                </span>
              </h4>
              <div className="space-y-2">
                {referencedSources.map((source) => (
                  <div
                    key={source.id || source.referenceNumber}
                    className="group flex items-start gap-2 py-1"
                  >
                    <span className="text-sm font-medium text-[var(--primary)] flex-shrink-0">
                      [{source.referenceNumber}]
                    </span>
                    <div className="min-w-0 flex-1">
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm leading-relaxed text-gray-800 hover:text-[var(--primary)] hover:underline transition-colors"
                      >
                        {source.title}
                      </a>
                      <span className="text-xs text-gray-500 ml-2">
                        {source.siteName || new URL(source.url).hostname}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* v7.243: 底部信息栏 - 扁平化样式 */}
        {/* v7.281: 增加质量评估展示 */}
        {status === 'done' && (
          <div className="px-6 py-3 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between text-xs text-[var(--foreground-secondary)]">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1">
                  <Globe className="w-3.5 h-3.5" />
                  {sources.length} 个来源
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  {searchState.executionTime.toFixed(1)}秒
                </span>
                {/* v7.281: 置信度展示 */}
                {searchState.qualityAssessment && (
                  <span className={`flex items-center gap-1 ${
                    searchState.qualityAssessment.confidence.confidence_level === '高' ? 'text-green-600 dark:text-green-400' :
                    searchState.qualityAssessment.confidence.confidence_level === '中' ? 'text-yellow-600 dark:text-yellow-400' :
                    'text-red-600 dark:text-red-400'
                  }`}>
                    <Shield className="w-3.5 h-3.5" />
                    置信度 {(searchState.qualityAssessment.confidence.overall_confidence * 100).toFixed(0)}%
                    ({searchState.qualityAssessment.confidence.confidence_level})
                  </span>
                )}
                {/* v7.281: 引用统计 */}
                {searchState.qualityAssessment?.citation && (
                  <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400">
                    <LinkIcon className="w-3.5 h-3.5" />
                    {searchState.qualityAssessment.citation.total_citations} 处引用
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {/* v7.281: 冲突警告 */}
                {searchState.qualityAssessment?.conflicts?.has_conflicts && (
                  <span className="text-amber-600 dark:text-amber-400 flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    {searchState.qualityAssessment.conflicts.count}处冲突
                  </span>
                )}
                <span className="text-green-500 flex items-center gap-1">
                  <CheckCircle className="w-3.5 h-3.5" />
                  已完成
                </span>
              </div>
            </div>
            {/* v7.281: 置信度说明（可展开） */}
            {searchState.qualityAssessment?.confidence?.confidence_note && (
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                💡 {searchState.qualityAssessment.confidence.confidence_note}
              </p>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex h-screen bg-[var(--background)] text-[var(--foreground)] overflow-hidden relative">
      {/* v7.290: 独立搜索页面，无侧边栏 */}
      <div className="flex-1 flex flex-col relative h-full overflow-hidden w-full">
        {/* v7.290.1: 顶部导航栏 - 统一体验 */}
        <header className="sticky top-0 z-10 bg-[var(--sidebar-bg)] border-b border-[var(--border-color)]">
          <div className="flex items-center justify-between px-4 py-3">
            <div className="flex items-center gap-3">
              <button
                onClick={() => router.push('/')}
                className="p-2 text-[var(--foreground-secondary)] hover:text-[var(--foreground)] hover:bg-[var(--card-bg)] rounded-lg transition-colors"
                title="返回首页"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <h1 className="text-lg font-semibold">AI 搜索</h1>
            </div>
          </div>
        </header>

        {/* 主内容区 - 原有的搜索结果展示 */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-6 sm:px-8 lg:px-12 py-6">
            {/* 🆕 v7.182: 取消右侧图片模块，主内容区全宽 */}
            {/* 主内容区 */}
            <section ref={contentRef}>
            {/* 🆕 v7.180: 完整展示用户问题 - v7.290: 使用公共组件 */}
            <UserQuestionCard question={query} className="mb-6" />

            {/* v7.290: 状态指示器（错误提示等） - 显示在用户问题下方 */}
            {renderStatusIndicator()}

            {/* 🆕 v7.220: 统一分析卡片（合并 AnalysisProgressCard + TaskUnderstandingCard，消除重复） */}
            {/* v7.220.1: 修复卡片消失问题 - 也从 rounds[0] 读取已保存的分析内容 */}
            {(() => {
              // 检查 rounds[0] 是否为分析阶段（已保存的内容）
              const analysisRound = searchState.rounds.find(r => r.round === 0 && r.isAnalysisPhase);
              const savedContent = analysisRound?.reasoningContent || '';
              // 优先使用流式内容，其次使用已保存内容
              const displayContent = searchState.l0Content || savedContent;
              const shouldShow = displayContent || searchState.l0Phase === 'extracting' ||
                                (searchState.analysisProgress && searchState.status === 'analyzing');

              if (!shouldShow) return null;

              return (
                <TaskUnderstandingCard
                  content={displayContent}
                  isExpanded={structuredInfoExpanded}
                  onToggle={() => setStructuredInfoExpanded(!structuredInfoExpanded)}
                  isLoading={searchState.l0Phase === 'extracting'}
                  isWaiting={!!(searchState.analysisProgress && searchState.status === 'analyzing' && !displayContent)}
                />
              );
            })()}

            {/* v7.205 兼容: 如果有旧版结构化信息但没有对话内容，显示旧版卡片 */}
            {searchState.structuredInfo && !searchState.l0Content && (
              <StructuredInfoCard
                info={searchState.structuredInfo}
                isExpanded={structuredInfoExpanded}
                onToggle={() => setStructuredInfoExpanded(!structuredInfoExpanded)}
              />
            )}

            {/* 🆕 v7.240: 框架清单卡片 - 显示搜索主线和边界 */}
            {/* v7.285: 支持点击编辑、删除、添加搜索方向（仅搜索前可编辑） */}
            {searchState.frameworkChecklist && !step2Plan && (
              <>
                <FrameworkChecklistCard
                  checklist={searchState.frameworkChecklist}
                  isExpanded={frameworkChecklistExpanded}
                  onToggle={() => setFrameworkChecklistExpanded(!frameworkChecklistExpanded)}
                  onUpdateChecklist={searchState.awaitingConfirmation ? (updated) => {
                    setSearchState(prev => ({
                      ...prev,
                      frameworkChecklist: updated,
                    }));
                  } : undefined}  // 搜索中/搜索后只读
                />
                {/* v7.290: 搜索按钮 - 新会话(idle)或等待确认时显示 */}
                {(searchState.status === 'idle' || searchState.awaitingConfirmation) && query && (
                  <div className="mt-3 flex justify-center">
                    <button
                      onClick={() => {
                        if (searchState.awaitingConfirmation) {
                          handleConfirmAndStartSearch();
                        } else {
                          startSearch(query, deepMode);
                        }
                      }}
                      className="flex items-center gap-2 px-6 py-3 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-md transition-all hover:shadow-lg"
                    >
                      <Search className="w-4 h-4" />
                      {searchState.awaitingConfirmation ? '确认并开始搜索' : '开始搜索'}
                    </button>
                  </div>
                )}
              </>
            )}

            {/* 🆕 v7.300: 可编辑搜索任务列表 - 第2步任务分解 */}
            {step2Plan && (
              <Step2TaskListEditor
                plan={step2Plan}
                onUpdatePlan={handleUpdateStep2Plan}
                onConfirmAndStart={handleConfirmStep2PlanAndStart}
                onValidate={handleValidateStep2Plan}
                isConfirming={isConfirmingPlan}
                isValidating={isValidatingPlan}
                isReadOnly={searchState.status === 'searching' || searchState.status === 'done'}
              />
            )}

            {/* 🆕 v7.302: 4条使命展示卡片 - 优先显示新格式 */}
            {searchState.fourMissionsResult && (
              <FourMissionsDisplay
                missions={searchState.fourMissionsResult}
                className="mb-6"
              />
            )}

            {/* 🆕 v7.280: 深度分析结果卡片 - 显示完整的 L1-L5 维度和人性化维度 */}
            {searchState.deepAnalysisResult && !searchState.fourMissionsResult && (
              <DeepAnalysisCard
                analysis={searchState.deepAnalysisResult}
                isExpanded={deepAnalysisExpanded}
                onToggle={() => setDeepAnalysisExpanded(!deepAnalysisExpanded)}
              />
            )}

            {/* v7.224: 删除 ThinkingContentCard，其内容已合并到 TaskUnderstandingCard */}
            {/* 解题思考过程现在统一在"需求理解与深度分析"卡片中展示 */}

            {/* 🆕 v7.222: 统一搜索进度卡片（合并了 SearchRoundsCard 和 renderDeepSearchProgress） */}
            {/* 条件：有搜索计划、有轮次记录、或正在搜索阶段 */}
            {(searchState.searchPlan ||
              (searchState.rounds && searchState.rounds.length > 0) ||
              searchState.currentPhase === 'search' ||
              searchState.currentPhase === 'synthesis') && (
              <UnifiedSearchProgressCard
                rounds={searchState.rounds}
                searchPlan={searchState.searchPlan}
                currentRound={searchState.currentRound}
                currentPhase={searchState.currentPhase}
                status={searchState.status}
                statusMessage={searchState.statusMessage}
                currentRoundReasoning={searchState.currentRoundReasoning}
                currentRoundThinking={searchState.currentRoundThinking}
                currentThinkingRound={searchState.currentThinkingRound}
                roundThinkingMap={searchState.roundThinkingMap}
                isExpanded={roundsExpanded}
                onToggle={() => setRoundsExpanded(!roundsExpanded)}
              />
            )}

            {/* v7.188: 深度推理已融入各轮搜索卡片，不再需要独立卡片 */}
            {/* {renderThinking()} */}

            {/* 回答内容 - 增强版 */}
            {renderContent()}

            {/* 追问输入框 */}
            {searchState.status === 'done' && (
              <div className="mt-6 space-y-3">
                {/* 追问输入 */}
                <div className="relative">
                  <input
                    type="text"
                    value={followUpQuery}
                    onChange={(e) => setFollowUpQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleFollowUp()}
                    placeholder="继续追问..."
                    className="w-full px-4 py-3 pr-12 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={handleFollowUp}
                    disabled={!followUpQuery.trim()}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-blue-500 text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-600 transition-colors"
                  >
                    <ArrowUp className="w-4 h-4" />
                  </button>
                </div>

                {/* 新搜索按钮 */}
                <div className="flex items-center justify-center">
                  <button
                    onClick={() => {
                      // 跳转到首页（搜索模式）
                      router.push('/');
                    }}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm text-[var(--foreground-secondary)] hover:text-[var(--foreground)] hover:bg-[var(--sidebar-bg)] rounded-lg transition-colors"
                  >
                    <Search className="w-4 h-4" />
                    开始新搜索
                  </button>
                </div>
              </div>
            )}
          </section>

          {/* 🆕 v7.182: 图片模块已停用，以后专项开发 */}
          {/* <aside className="lg:col-span-3">
            <div className="sticky top-20">
              {renderImagesSection()}
            </div>
          </aside> */}
          </div>
        </main>
      </div>

      {/* 🆕 v7.182: 图片查看器已停用 */}
      {/* <ImageViewer
        images={searchState.images}
        initialIndex={imageViewerIndex}
        isOpen={imageViewerOpen}
        onClose={() => setImageViewerOpen(false)}
      /> */}

      {/* 搜索历史浮动面板 */}
      {showHistory && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-20">
          {/* 背景遮罩 */}
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setShowHistory(false)}
          />

          {/* 历史面板 - 🆕 v7.179: 加宽到 max-w-2xl (672px) */}
          <div className="relative w-full max-w-2xl mx-4 bg-[var(--card-bg)] rounded-2xl shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-4 duration-300">
            {/* 标题栏 */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border-color)]">
              <h2 className="text-lg font-semibold text-[var(--foreground)]">搜索历史</h2>
              <button
                onClick={() => setShowHistory(false)}
                className="p-1.5 hover:bg-[var(--sidebar-bg)] rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-[var(--foreground-secondary)]" />
              </button>
            </div>

            {/* 历史列表 */}
            <div className="max-h-[60vh] overflow-y-auto custom-scrollbar">
              {searchHistory.length === 0 ? (
                <div className="py-12 text-center text-[var(--foreground-secondary)]">
                  <History className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>暂无搜索历史</p>
                </div>
              ) : (
                <div className="divide-y divide-[var(--border-color)]">
                  {searchHistory.map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setShowHistory(false);
                        router.push(`/search/${item.sessionId}`);
                      }}
                      className="w-full px-5 py-4 text-left hover:bg-[var(--sidebar-bg)] transition-colors"
                    >
                      <p className="font-medium text-[var(--foreground)] truncate">
                        {item.query}
                      </p>
                      <p className="text-sm text-[var(--foreground-secondary)] mt-1">
                        {item.timestamp}
                      </p>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* 底部操作 */}
            {searchHistory.length > 0 && (
              <div className="px-5 py-3 border-t border-[var(--border-color)] bg-[var(--sidebar-bg)]">
                <button
                  onClick={() => {
                    localStorage.removeItem('searchHistory');
                    setSearchHistory([]);
                  }}
                  className="text-sm text-red-500 hover:text-red-600 font-medium"
                >
                  清除全部历史
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 🆕 v7.251: 跟随最新内容按钮（自动滚动禁用时显示） */}
      {!isAutoScrollEnabled && (
        searchState.status === 'analyzing' ||
        searchState.status === 'searching' ||
        searchState.status === 'thinking' ||
        searchState.status === 'answering'
      ) && (
        <button
          onClick={() => {
            setIsAutoScrollEnabled(true);
            window.scrollTo({
              top: document.documentElement.scrollHeight,
              behavior: 'smooth'
            });
          }}
          className="fixed bottom-24 right-8 z-50 flex items-center gap-2 px-4 py-2
                     bg-blue-600 text-white rounded-full shadow-lg
                     hover:bg-blue-700 transition-colors animate-bounce"
          aria-label="跟随最新内容"
        >
          <ChevronRight className="w-4 h-4 rotate-90" />
          <span className="text-sm">跟随最新内容</span>
        </button>
      )}

      {/* 🆕 v7.178: 返回顶部按钮 */}
      <button
        onClick={scrollToTop}
        className={`
          fixed bottom-8 right-8 z-50
          w-12 h-12 rounded-full
          bg-gradient-to-br from-blue-500 to-purple-600
          hover:from-blue-600 hover:to-purple-700
          shadow-lg hover:shadow-xl
          flex items-center justify-center
          transition-all duration-300 ease-in-out
          ${showBackToTop
            ? 'opacity-100 translate-y-0'
            : 'opacity-0 translate-y-4 pointer-events-none'}
        `}
        aria-label="返回顶部"
      >
        <ArrowUp className="w-6 h-6 text-white" />
      </button>
    </div>
  );
}
