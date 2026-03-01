// components/report/PerspectiveProjections.tsx
// v10.0: 多维投射视角切换组件
// 包含：五轴雷达图 + Tab切换 + 投射内容渲染

'use client';

import { useState, useMemo } from 'react';
import { PerspectiveOutput } from '@/types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Eye, BarChart3, Users, Building2, Landmark, Palette, ChevronDown } from 'lucide-react';

// ==============================================================================
// 视角元数据
// ==============================================================================

const PERSPECTIVE_META: Record<string, {
  label: string;
  icon: React.ReactNode;
  color: string;
  bgGradient: string;
  audience: string;
}> = {
  design_professional: {
    label: '设计专业版',
    icon: <Palette className="w-4 h-4" />,
    color: 'text-violet-400',
    bgGradient: 'from-violet-500/10 to-purple-500/10',
    audience: '建筑师 / 设计师',
  },
  investor_operator: {
    label: '投资运营版',
    icon: <BarChart3 className="w-4 h-4" />,
    color: 'text-emerald-400',
    bgGradient: 'from-emerald-500/10 to-green-500/10',
    audience: '投资人 / 运营团队',
  },
  government_policy: {
    label: '政策汇报版',
    icon: <Landmark className="w-4 h-4" />,
    color: 'text-blue-400',
    bgGradient: 'from-blue-500/10 to-cyan-500/10',
    audience: '政府 / 审批部门',
  },
  construction_execution: {
    label: '施工深化版',
    icon: <Building2 className="w-4 h-4" />,
    color: 'text-amber-400',
    bgGradient: 'from-amber-500/10 to-orange-500/10',
    audience: '施工方 / 工程团队',
  },
  aesthetic_critique: {
    label: '美学评论版',
    icon: <Eye className="w-4 h-4" />,
    color: 'text-rose-400',
    bgGradient: 'from-rose-500/10 to-pink-500/10',
    audience: '媒体 / 学术界',
  },
};

const AXIS_LABELS: Record<string, string> = {
  identity: '身份轴',
  power: '权力轴',
  operation: '生产轴',
  emotion: '情绪轴',
  civilization: '文明轴',
};

// ==============================================================================
// 五轴雷达图 (SVG)
// ==============================================================================

function FiveAxisRadar({ scores }: { scores: Record<string, number> }) {
  const size = 200;
  const center = size / 2;
  const radius = 70;
  const axes = ['identity', 'power', 'operation', 'emotion', 'civilization'];

  // 五角形顶点坐标计算
  const getPoint = (axisIndex: number, value: number) => {
    const angle = (Math.PI * 2 * axisIndex) / axes.length - Math.PI / 2;
    const r = radius * Math.max(0, Math.min(1, value));
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
    };
  };

  // 网格线（3层）
  const gridLevels = [0.33, 0.66, 1.0];

  // 数据点
  const dataPoints = axes.map((axis, i) => getPoint(i, scores[axis] || 0));
  const dataPath = dataPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z';

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* 网格线 */}
        {gridLevels.map((level) => {
          const points = axes.map((_, i) => getPoint(i, level));
          const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z';
          return <path key={level} d={path} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />;
        })}

        {/* 轴线 */}
        {axes.map((_, i) => {
          const p = getPoint(i, 1.0);
          return <line key={i} x1={center} y1={center} x2={p.x} y2={p.y} stroke="rgba(255,255,255,0.15)" strokeWidth="1" />;
        })}

        {/* 数据区域 */}
        <path d={dataPath} fill="rgba(139, 92, 246, 0.25)" stroke="rgb(139, 92, 246)" strokeWidth="2" />

        {/* 数据点 */}
        {dataPoints.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r="4" fill="rgb(139, 92, 246)" stroke="white" strokeWidth="1.5" />
        ))}

        {/* 轴标签 */}
        {axes.map((axis, i) => {
          const labelP = getPoint(i, 1.25);
          return (
            <text
              key={axis}
              x={labelP.x}
              y={labelP.y}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="rgba(255,255,255,0.7)"
              fontSize="11"
              fontWeight="500"
            >
              {AXIS_LABELS[axis] || axis}
            </text>
          );
        })}
      </svg>

      {/* 分数列表 */}
      <div className="flex flex-wrap gap-2 mt-2 justify-center">
        {axes.map((axis) => (
          <span key={axis} className="text-xs px-2 py-0.5 bg-white/5 rounded text-gray-400">
            {AXIS_LABELS[axis]}: {((scores[axis] || 0) * 100).toFixed(0)}%
          </span>
        ))}
      </div>
    </div>
  );
}

// ==============================================================================
// 主组件：PerspectiveProjections
// ==============================================================================

interface PerspectiveProjectionsProps {
  perspectiveOutputs: Record<string, PerspectiveOutput>;
  metaAxisScores?: Record<string, number> | null;
  activeProjections?: string[] | null;
}

export default function PerspectiveProjections({
  perspectiveOutputs,
  metaAxisScores,
  activeProjections,
}: PerspectiveProjectionsProps) {
  const perspectiveIds = useMemo(
    () => activeProjections?.filter((id) => perspectiveOutputs[id]) || Object.keys(perspectiveOutputs),
    [activeProjections, perspectiveOutputs]
  );

  const [activeTab, setActiveTab] = useState<string>(perspectiveIds[0] || '');
  const [expanded, setExpanded] = useState(true);

  if (perspectiveIds.length === 0) return null;

  const activePerspective = perspectiveOutputs[activeTab];

  return (
    <div id="perspective-projections" className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl overflow-hidden">
      {/* 标题栏 */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center">
            <Users className="w-4 h-4 text-violet-400" />
          </div>
          <div className="text-left">
            <h3 className="text-lg font-semibold text-white">多维投射视角</h3>
            <p className="text-sm text-gray-400">
              同一分析结果的 {perspectiveIds.length} 种受众话语版本
            </p>
          </div>
        </div>
        <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>

      {expanded && (
        <div className="px-6 pb-6">
          {/* 五轴雷达图 */}
          {metaAxisScores && Object.keys(metaAxisScores).length > 0 && (
            <div className="mb-6 flex justify-center">
              <FiveAxisRadar scores={metaAxisScores} />
            </div>
          )}

          {/* Tab 切换栏 */}
          <div className="flex gap-1 mb-4 overflow-x-auto border-b border-[var(--border-color)] pb-0">
            {perspectiveIds.map((id) => {
              const meta = PERSPECTIVE_META[id] || {
                label: id,
                icon: <Eye className="w-4 h-4" />,
                color: 'text-gray-400',
                bgGradient: 'from-gray-500/10 to-gray-500/10',
                audience: '',
              };
              const isActive = activeTab === id;

              return (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-all
                    ${isActive
                      ? `${meta.color} border-current bg-gradient-to-b ${meta.bgGradient}`
                      : 'text-gray-400 border-transparent hover:text-gray-300 hover:border-gray-600'
                    }`}
                >
                  {meta.icon}
                  {meta.label}
                </button>
              );
            })}
          </div>

          {/* 投射内容 */}
          {activePerspective && (
            <div className={`rounded-xl border border-[var(--border-color)] bg-gradient-to-br ${
              PERSPECTIVE_META[activeTab]?.bgGradient || 'from-gray-500/5 to-gray-500/5'
            }`}>
              {/* 受众标签栏 */}
              <div className="px-5 py-3 border-b border-[var(--border-color)] flex items-center gap-3 flex-wrap">
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">目标受众</span>
                {(activePerspective.target_audience || PERSPECTIVE_META[activeTab]?.audience?.split(' / ') || []).map((a, i) => (
                  <span key={i} className="text-xs px-2 py-0.5 bg-white/10 rounded-full text-gray-300">
                    {a}
                  </span>
                ))}
                {activePerspective.value_anchor && (
                  <>
                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wider ml-4">价值锚点</span>
                    <span className="text-xs px-2 py-0.5 bg-violet-500/20 rounded-full text-violet-300">
                      {activePerspective.value_anchor}
                    </span>
                  </>
                )}
              </div>

              {/* 正文内容 */}
              <div className="px-5 py-4 prose prose-invert prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {activePerspective.content || '（投射内容为空）'}
                </ReactMarkdown>
              </div>

              {/* 底部元信息 */}
              {(activePerspective.word_count || activePerspective.generated_at) && (
                <div className="px-5 py-2 border-t border-[var(--border-color)] flex items-center gap-4 text-xs text-gray-500">
                  {activePerspective.word_count && <span>{activePerspective.word_count.toLocaleString()} 字</span>}
                  {activePerspective.generated_at && (
                    <span>生成于 {new Date(activePerspective.generated_at).toLocaleString('zh-CN')}</span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
