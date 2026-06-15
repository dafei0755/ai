'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Info, Lock, Eye } from 'lucide-react';
import type { ProjectOverview, ReadinessItem, StageInfo, ViewKey } from './mock/mockData';
import { MOCK_VIEW_BADGES } from './mock/mockData';
import { ProjectGrowthCanvasView } from './ProjectGrowthCanvasView';

const VIEW_TABS: { key: ViewKey; label: string }[] = [
  { key: 'overview', label: '项目智能画布' },
  { key: 'spaces',   label: '空间内容' },
  { key: 'files',    label: '项目资料' },
  { key: 'history',  label: '历史记录' },
];

interface DecisionViewProps {
  overview: ProjectOverview;
  projectLabel?: string;
  onProjectLabelChange?: (currentTitle: string) => void;
  stages: StageInfo[];
  activeView: ViewKey;
  onViewChange: (view: ViewKey) => void;
  onAction: (label: string) => void;
  onCapabilityClick: (key: 'floor_plan' | 'scheme_canvas') => void;
  onAdvisorPrefill?: (text: string) => void;
  onSwitchModule?: (target: 'floor_plan' | 'scheme_canvas') => void;
  /** 会话 id — 透传给项目底盘，用于挂载 PlanSandboxPanel 到平面推演悬浮工作台 */
  sessionId?: string;
  /** 打开地理工作台回调 */
  onOpenGeoWorkspace?: () => void;
}

// ── 准备度条 ──────────────────────────────────────────────────────────────
function ReadinessBar({ item }: { item: ReadinessItem }) {
  const [hover, setHover] = useState(false);
  const barColor =
    item.level === 'sufficient'   ? 'bg-sky-500'   :
    item.level === 'concept_only' ? 'bg-amber-400' : 'bg-slate-200';
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="ui-type-body text-slate-800 truncate">{item.label}</span>
          <div className="relative">
            <button
              onMouseEnter={() => setHover(true)}
              onMouseLeave={() => setHover(false)}
              className="text-slate-400 hover:text-slate-600"
            >
              <Info className="w-3 h-3" />
            </button>
            {hover && (
              <div className="absolute left-0 top-5 z-20 bg-white border border-slate-200 rounded px-2 py-1 text-[10px] text-slate-500 whitespace-nowrap shadow-sm">
                {item.systemName}
              </div>
            )}
          </div>
        </div>
        <span className="shrink-0 cockpit-card-chip">{item.statusLabel}</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${item.progressPct}%` }} />
      </div>
      <p className="ui-type-meta text-slate-400">{item.upgradeHint}</p>
    </div>
  );
}

// ── 空间视图内容 ──────────────────────────────────────────────────────────
function SpacesView({
  onAdvisorPrefill,
}: {
  onAdvisorPrefill?: (t: string) => void;
  onSwitchModule?: (target: 'floor_plan' | 'scheme_canvas') => void;
}) {
  return (
    <div className="space-y-5 pb-8">
      <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
        <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-slate-400">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
            <polyline points="9 22 9 12 15 12 15 22"/>
          </svg>
        </div>
        <p className="text-sm text-slate-500">暂无空间数据</p>
        <p className="text-xs text-slate-400 max-w-xs">空间信息将在问卷完成、上传平面图后自动提取</p>
        <button
          onClick={() => onAdvisorPrefill?.('帮我梳理这个项目的主要空间类型和功能分区')}
          className="mt-2 text-xs text-sky-600 hover:text-sky-700 transition-colors"
        >
          问高参：梳理空间分区 →
        </button>
      </div>
    </div>
  );
}

// ── 项目资料视图 ──────────────────────────────────────────────────────────
function FilesView({ onAdvisorPrefill }: { onAdvisorPrefill?: (t: string) => void }) {
  return (
    <div className="space-y-5 pb-8">
      <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
        <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-slate-400">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
        </div>
        <p className="text-sm text-slate-500">暂无项目资料</p>
        <p className="text-xs text-slate-400 max-w-xs">上传平面图、方案文件后，资料将自动归入此处</p>
        <button
          onClick={() => onAdvisorPrefill?.('我想整理这个项目目前已有的资料清单')}
          className="mt-2 text-xs text-sky-600 hover:text-sky-700 transition-colors"
        >
          问高参：整理资料清单 →
        </button>
      </div>
    </div>
  );
}

// ── 历史记录视图 ──────────────────────────────────────────────────────────
function HistoryView({ onAdvisorPrefill }: { onAdvisorPrefill?: (t: string) => void }) {
  return (
    <div className="space-y-3 pb-8">
      <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
        <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-slate-400">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
        </div>
        <p className="text-sm text-slate-500">暂无历史记录</p>
        <p className="text-xs text-slate-400 max-w-xs">项目推进过程中的关键决策和缺口记录将自动沉淀至此</p>
        <button
          onClick={() => onAdvisorPrefill?.('帮我回顾一下目前这个项目我们讨论了什么')}
          className="mt-2 text-xs text-sky-600 hover:text-sky-700 transition-colors"
        >
          问高参：回顾讨论 →
        </button>
      </div>
    </div>
  );
}

// ── 软解锁面板 ────────────────────────────────────────────────────────────
function SoftUnlockView({
  capability,
  onUnlock,
}: {
  capability: 'floor_plan' | 'scheme_canvas';
  onUnlock?: () => void;
}) {
  const isFloorPlan = capability === 'floor_plan';
  return (
    <div className="flex flex-col items-center justify-center h-full px-8 py-16 text-center">
      <div className="mb-4 w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
        {isFloorPlan ? <Eye className="w-6 h-6 text-slate-500" /> : <Lock className="w-6 h-6 text-slate-500" />}
      </div>
      <h3 className="ui-type-subtitle font-bold text-slate-800 mb-2">
        {isFloorPlan ? '平面推演 · 预览可用' : '方案画布 · 概念级可用'}
      </h3>
      <p className="ui-type-body text-slate-500 max-w-sm leading-relaxed mb-6">
        {isFloorPlan
          ? '上传平面图后，系统可识别空间结构并启动推演。当前可浏览示例，无法正式推演。'
          : '项目底盘完成后，方案画布可进入概念画板。当前已可创建气质参考看板。'}
      </p>
      <div className="flex flex-col gap-2 w-full max-w-xs">
        <button
          onClick={onUnlock}
          className="cockpit-card cockpit-card-interactive cockpit-card-accent-files px-5 py-3 text-sm font-semibold text-sky-700 rounded-xl border border-sky-200 hover:border-sky-400 transition-all"
        >
          {isFloorPlan ? '上传平面图，开始推演' : '进入概念画板（草稿模式）'}
        </button>
        <p className="ui-type-meta text-slate-400">
          {isFloorPlan ? '完成项目底盘后解锁正式推演' : '冻结项目底盘后解锁完整画布'}
        </p>
      </div>
    </div>
  );
}

// ── 概览内容 ─────────────────────────────────────────────────────────────
function OverviewContent({
  overview,
  onAction,
  onCapabilityClick,
  onAdvisorPrefill,
}: {
  overview: ProjectOverview;
  onAction: (label: string) => void;
  onCapabilityClick: (key: 'floor_plan' | 'scheme_canvas') => void;
  onAdvisorPrefill?: (text: string) => void;
}) {
  const [gapsExpanded, setGapsExpanded] = useState(false);
  const visible = gapsExpanded ? overview.gapItems : overview.gapItems.slice(0, 3);

  return (
    <div className="space-y-5 pb-8">
      {/* 一句话判断 */}
      <div className="cockpit-card p-5">
        <p className="ui-type-subtitle font-bold text-slate-900 leading-snug">{overview.oneLiner}</p>
        <p className="ui-type-meta text-slate-500 mt-2">
          当前阶段：{overview.stage.label}
          {overview.stage.hint && <span className="opacity-70"> · {overview.stage.hint}</span>}
        </p>
      </div>

      {/* 已明确 / 待补 */}
      <div className="cockpit-adaptive-grid" style={{ '--cockpit-grid-min': '18rem' } as React.CSSProperties}>
        <div className="cockpit-card cockpit-card-accent-files p-5">
          <p className="ui-type-meta font-semibold text-slate-500 mb-3">已明确</p>
          <ul className="space-y-1.5">
            {overview.confirmedItems.map((item, i) => (
              <li key={i} className="flex items-start gap-2 ui-type-body text-slate-800">
                <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-sky-500 shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div className="cockpit-card p-5">
          <p className="ui-type-meta font-semibold text-slate-500 mb-3">一起补完会更准</p>
          <ul className="space-y-1.5">
            {visible.map((item, i) => (
              <li
                key={i}
                onClick={() => onAdvisorPrefill?.(`帮我补充：${item}`)}
                className="flex items-start gap-2 ui-type-body text-slate-500 cursor-pointer hover:text-sky-600 transition-colors"
              >
                <span className="mt-1.5 w-1.5 h-1.5 rounded-full border border-sky-400 shrink-0" />
                {item}
              </li>
            ))}
          </ul>
          {overview.gapItems.length > 3 && (
            <button
              onClick={() => setGapsExpanded(v => !v)}
              className="mt-3 flex items-center gap-1 ui-type-meta text-sky-600 hover:text-sky-700"
            >
              {gapsExpanded ? <><ChevronUp className="w-3 h-3" />收起</> : <><ChevronDown className="w-3 h-3" />查看更多</>}
            </button>
          )}
        </div>
      </div>

      {/* 主矛盾 */}
      <button
        onClick={() => onAdvisorPrefill?.('详细解释当前主矛盾，以及你的判断思路')}
        className="cockpit-card cockpit-card-interactive w-full p-5 text-left"
      >
        <p className="ui-type-meta font-semibold text-slate-500 mb-3">当前主矛盾</p>
        <div className="flex flex-wrap items-center gap-2 mb-3">
          {overview.mainContradiction.sides.map((side, i) => (
            <span key={i} className="flex items-center gap-2">
              <span className="cockpit-card-chip cockpit-card-chip-accent text-slate-800">{side}</span>
              {i < overview.mainContradiction.sides.length - 1 && (
                <span className="ui-type-meta font-bold text-slate-400">vs</span>
              )}
            </span>
          ))}
        </div>
        <p className="ui-type-body text-slate-600 italic leading-relaxed border-l-2 border-sky-400 pl-3">
          {overview.mainContradiction.advisorNote}
        </p>
      </button>

      {/* 能力状态 */}
      <section>
        <p className="ui-type-meta font-semibold text-slate-500 mb-2">当前能力状态</p>
        <div className="cockpit-adaptive-grid" style={{ '--cockpit-grid-min': '14rem' } as React.CSSProperties}>
          {overview.capabilities.map(cap => (
            <button
              key={cap.key}
              onClick={() => {
                if (cap.key !== 'project_base') {
                  onCapabilityClick(cap.key as 'floor_plan' | 'scheme_canvas');
                }
              }}
              className={`cockpit-card cockpit-card-interactive flex flex-col gap-2 p-4 text-left ${
                cap.state === 'active' ? 'cockpit-card-accent-files' : ''
              }`}
            >
              <span className="ui-type-subtitle font-semibold text-slate-900">{cap.label}</span>
              <span className={`cockpit-card-chip w-fit ${cap.state === 'active' ? 'cockpit-card-chip-accent' : ''}`}>
                {cap.statusLabel}
              </span>
              {cap.actionLabel && (
                <span className="ui-type-meta text-sky-600 mt-1">{cap.actionLabel} →</span>
              )}
            </button>
          ))}
        </div>
      </section>

      {/* 推进程度 */}
      <div className="cockpit-card p-5">
        <p className="ui-type-meta font-semibold text-slate-500 mb-4">当前可推进程度</p>
        <div className="space-y-4">
          {overview.readiness.map((item, i) => (
            <ReadinessBar key={i} item={item} />
          ))}
        </div>
      </div>

      {/* 推荐下一步 */}
      <section>
        <p className="ui-type-meta font-semibold text-slate-500 mb-2">推荐下一步</p>
        <div className="space-y-2">
          {overview.recommendedActions.map((action, i) => (
            <button
              key={i}
              onClick={() => {
                onAction(action.label);
                onAdvisorPrefill?.(action.label);
              }}
              className={`cockpit-card cockpit-card-interactive w-full flex flex-col gap-1 p-4 text-left ${
                action.isPrimary ? 'cockpit-card-accent-files' : ''
              }`}
            >
              <span className={`ui-type-body font-semibold ${action.isPrimary ? 'text-sky-600' : 'text-slate-900'}`}>
                {action.isPrimary && '→ '}{action.label}
              </span>
              <span className="ui-type-meta text-slate-500 leading-relaxed">{action.benefit}</span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

// ── 主组件 ────────────────────────────────────────────────────────────────
export function DecisionView({
  overview,
  projectLabel,
  onProjectLabelChange,
  activeView,
  onViewChange,
  onAction,
  onCapabilityClick,
  onAdvisorPrefill,
  onSwitchModule,
  sessionId,
  onOpenGeoWorkspace,
}: DecisionViewProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [softUnlockCapability, setSoftUnlockCapability] = useState<'floor_plan' | 'scheme_canvas' | null>(null);
  const resolvedProjectSummary = projectLabel || overview.name || '未命名项目';
  const isCanvasView = !softUnlockCapability && activeView === 'overview';

  const handleCapabilityClick = (key: 'floor_plan' | 'scheme_canvas') => {
    if (onSwitchModule) {
      onSwitchModule(key);
    } else {
      setSoftUnlockCapability(key);
    }
    onCapabilityClick(key);
  };

  return (
    <div className={`flex h-full min-h-0 flex-col ${isCanvasView ? 'bg-[var(--canvas-bg)]' : 'bg-[#f5f5f7]'}`}>
      {!isCanvasView && (
        <div className="shrink-0 sticky top-0 z-10 border-b border-slate-200 bg-white/90 pb-4 pl-[108px] pr-6 pt-6 backdrop-blur">
          <div className="cockpit-header-row">
            <div className="cockpit-header-main">
              <button
                type="button"
                onClick={() => onProjectLabelChange?.(resolvedProjectSummary)}
                className="max-w-[36rem] truncate text-left text-[18px] font-semibold leading-6 tracking-normal text-slate-900 transition-colors hover:text-sky-700"
                title="点击修改项目摘要"
              >
                {resolvedProjectSummary}
              </button>
            </div>
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索判断、缺口或推荐动作..."
              className="cockpit-search-input cockpit-header-search"
            />
          </div>

          <div className="flex items-center gap-2 mt-3">
            {VIEW_TABS.map(tab => {
              const badge = MOCK_VIEW_BADGES[tab.key];
              return (
                <button
                  key={tab.key}
                  onClick={() => { onViewChange(tab.key); setSoftUnlockCapability(null); }}
                  className={`cockpit-filter-pill flex items-center gap-1.5 ${activeView === tab.key ? 'cockpit-filter-pill-active' : ''}`}
                >
                  {tab.label}
                  {badge && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                      activeView === tab.key ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-600'
                    }`}>{badge}</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Scrollable Body */}
      <div
        className={
          isCanvasView
            ? 'flex-1 min-h-0 overflow-hidden'
            : 'flex-1 min-h-0 overflow-y-auto pl-20 pr-6 py-6'
        }
      >
        {softUnlockCapability && (
          <SoftUnlockView
            capability={softUnlockCapability}
            onUnlock={() => {
              setSoftUnlockCapability(null);
              onAdvisorPrefill?.(
                softUnlockCapability === 'floor_plan'
                  ? '我想上传平面图，开始平面推演'
                  : '我想进入概念画板，开始方案表达'
              );
            }}
          />
        )}

        {!softUnlockCapability && activeView === 'overview' && (
          <ProjectGrowthCanvasView
            overview={overview}
            projectLabel={resolvedProjectSummary}
            tabs={VIEW_TABS.map(tab => ({
              key: tab.key,
              label: tab.label === '项目智能画布' ? '全部' : tab.label,
              active: activeView === tab.key,
              badge: MOCK_VIEW_BADGES[tab.key],
              onClick: () => { onViewChange(tab.key); setSoftUnlockCapability(null); },
            }))}
            onAdvisorPrefill={onAdvisorPrefill}
            sessionId={sessionId}
            onOpenGeoWorkspace={onOpenGeoWorkspace}
          />
        )}
        {!softUnlockCapability && activeView === 'spaces' && (
          <SpacesView onAdvisorPrefill={onAdvisorPrefill} onSwitchModule={onSwitchModule} />
        )}
        {!softUnlockCapability && activeView === 'files' && (
          <FilesView onAdvisorPrefill={onAdvisorPrefill} />
        )}
        {!softUnlockCapability && activeView === 'history' && (
          <HistoryView onAdvisorPrefill={onAdvisorPrefill} />
        )}
      </div>
    </div>
  );
}
