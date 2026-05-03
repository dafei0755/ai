'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Info, Lock, Eye } from 'lucide-react';
import type { ProjectOverview, ReadinessItem, StageInfo, ViewKey } from './mock/mockData';
import { MOCK_VIEW_BADGES } from './mock/mockData';

const VIEW_TABS: { key: ViewKey; label: string }[] = [
  { key: 'overview', label: '项目概览' },
  { key: 'spaces',   label: '空间内容' },
  { key: 'files',    label: '项目资料' },
  { key: 'history',  label: '历史记录' },
];

interface DecisionViewProps {
  overview: ProjectOverview;
  stages: StageInfo[];
  activeView: ViewKey;
  onViewChange: (view: ViewKey) => void;
  onAction: (label: string) => void;
  onCapabilityClick: (key: 'floor_plan' | 'scheme_canvas') => void;
  onAdvisorPrefill?: (text: string) => void;
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
const MOCK_SPACES = [
  {
    key: 'lobby',
    name: '公共大堂',
    status: 'S1 概念',
    statusColor: 'bg-sky-100 text-sky-700',
    desc: '品牌第一印象区域，HAY 克制美学与峨眉山景观的核心交汇点。设计挑战：如何在进门5秒内建立「山间轻居」的气质感知。',
    tags: ['品牌锚点', '动线核心', '体验优先'],
    area: '约 80–120㎡',
  },
  {
    key: 'guestroom',
    name: '标准客房',
    status: 'S1 概念',
    statusColor: 'bg-sky-100 text-sky-700',
    desc: '运营主体空间，目标：让客人在山景环境中体验到 HAY 家具的功能主义美感，而非堆砌风格符号。',
    tags: ['运营主体', '功能主义', '山景朝向'],
    area: '约 35–45㎡ × N间',
  },
  {
    key: 'dining',
    name: '餐饮轻服务',
    status: '待规划',
    statusColor: 'bg-slate-100 text-slate-600',
    desc: '轻餐饮服务区，满足早餐和简单社交需求。与公共区共享空间策略，避免功能分割带来的管理复杂度。',
    tags: ['轻运营', '社交触点'],
    area: '待定',
  },
  {
    key: 'outdoor',
    name: '半户外观景',
    status: 'S1 概念',
    statusColor: 'bg-amber-100 text-amber-700',
    desc: '七里坪山景是最核心的竞争资产。半户外区域是将自然景观转化为可售卖体验的关键节点，也是社交媒体传播的主要出口。',
    tags: ['核心卖点', '传播节点', '山景资产'],
    area: '约 40–60㎡',
  },
];

function SpacesView({ onAdvisorPrefill }: { onAdvisorPrefill?: (t: string) => void }) {
  return (
    <div className="space-y-5 pb-8">
      <section>
        <button className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white/85 px-4 py-3 text-left transition hover:border-slate-300">
          <div className="flex items-center gap-3">
            <h4 className="ui-type-subtitle font-semibold text-slate-700">空间视图内容</h4>
            <span className="ui-type-meta text-slate-400">{MOCK_SPACES.length} 条</span>
          </div>
        </button>
      </section>

      <div className="cockpit-adaptive-grid cockpit-grid-files">
        {MOCK_SPACES.map(space => (
          <button
            key={space.key}
            onClick={() => onAdvisorPrefill?.(`我想深化${space.name}的设计方向`)}
            className="cockpit-card cockpit-card-interactive cockpit-card-accent-files cockpit-file-card flex flex-col p-5 text-left group"
          >
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="ui-type-meta font-medium text-slate-400">空间规划</span>
              <span className={`cockpit-card-chip text-[10px] font-medium ${space.statusColor}`}>{space.status}</span>
            </div>
            <h3 className="cockpit-card-title mb-2 text-slate-900 group-hover:text-sky-600">{space.name}</h3>
            <p className="ui-type-body text-slate-600 flex-1 mb-4 line-clamp-3">{space.desc}</p>
            <div className="flex flex-wrap gap-1 mb-3">
              {space.tags.map(t => (
                <span key={t} className="cockpit-card-chip cockpit-card-chip-accent">{t}</span>
              ))}
            </div>
            <div className="flex items-center justify-between pt-3 border-t border-slate-100">
              <span className="cockpit-card-chip">{space.area}</span>
              <span className="ui-type-meta text-sky-600">进入深化 →</span>
            </div>
          </button>
        ))}
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
  activeView,
  onViewChange,
  onAction,
  onCapabilityClick,
  onAdvisorPrefill,
}: DecisionViewProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [softUnlockCapability, setSoftUnlockCapability] = useState<'floor_plan' | 'scheme_canvas' | null>(null);

  const handleCapabilityClick = (key: 'floor_plan' | 'scheme_canvas') => {
    setSoftUnlockCapability(key);
    onCapabilityClick(key);
  };

  return (
    <div className="flex flex-col h-full min-h-0 bg-[#f5f5f7]">
      {/* Sticky Header */}
      <div className="border-b border-slate-200 bg-white/90 backdrop-blur pl-20 pr-6 py-4 shrink-0 sticky top-0 z-10">
        <div className="cockpit-header-row">
          <div className="cockpit-header-main">
            <h3 className="cockpit-panel-title text-slate-800">项目底盘</h3>
            <span className="cockpit-header-note">智能决策中枢</span>
            <button
              onClick={() => onAdvisorPrefill?.(`解释当前阶段「${overview.stage.label}」意味着什么`)}
              className="cockpit-card-chip cockpit-card-chip-accent hover:bg-slate-200 transition-colors cursor-pointer"
            >
              {overview.stage.label}
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

      {/* Scrollable Body */}
      <div className="flex-1 min-h-0 overflow-y-auto pl-20 pr-6 py-6">
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
          <OverviewContent
            overview={overview}
            onAction={onAction}
            onCapabilityClick={handleCapabilityClick}
            onAdvisorPrefill={onAdvisorPrefill}
          />
        )}
        {!softUnlockCapability && activeView === 'spaces' && (
          <SpacesView onAdvisorPrefill={onAdvisorPrefill} />
        )}
        {!softUnlockCapability && activeView === 'files' && (
          <div className="cockpit-empty">项目资料 — Sprint 4 对接 WorkspaceContentPanel</div>
        )}
        {!softUnlockCapability && activeView === 'history' && (
          <div className="cockpit-empty">历史记录 — Sprint 7 实现</div>
        )}
      </div>
    </div>
  );
}
