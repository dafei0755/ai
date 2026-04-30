/**
 * DeliveryView.tsx — v2.0 交付物展示看板
 * Created by GitHub Copilot · 2026-03-15
 *
 * 展示 DeliveryBundle 中的所有最终交付物，支持：
 *   - 按类型分组（文档 / 图纸 / 模型 / 其他）
 *   - 展开 / 折叠详情
 *   - 下载链接（如有 artifact_url）
 */

import React, { useState } from 'react';

// ── 类型定义 ──────────────────────────────────────────────

export type DeliverableType = 'document' | 'drawing' | 'model' | 'report' | 'other';

export interface DeliveryItem {
  deliverable_id: string;
  name: string;
  type: DeliverableType;
  owner_role: string;
  quality_score?: number;
  content_summary?: string;
  artifact_url?: string;
  tags?: string[];
}

export interface DeliveryBundleProps {
  sessionId: string;
  projectTitle?: string;
  deliverables: DeliveryItem[];
  completedAt?: string;
  /** 可选：显示「重新执行」按钮的回调 */
  onRerun?: () => void;
  /** 可选：显示「提交增量修改」按钮的回调 */
  onSubmitDelta?: () => void;
  className?: string;
}

// ── 辅助 ────────────────────────────────────────────────────

const TYPE_LABELS: Record<DeliverableType, string> = {
  document: '文档',
  drawing:  '图纸',
  model:    '模型',
  report:   '报告',
  other:    '其他',
};

const TYPE_ICON: Record<DeliverableType, string> = {
  document: '📄',
  drawing:  '📐',
  model:    '🧊',
  report:   '📊',
  other:    '📦',
};

function QualityBadge({ score }: { score?: number }) {
  if (score == null) return null;
  const color =
    score >= 0.85 ? 'bg-green-100 text-green-700' :
    score >= 0.65 ? 'bg-yellow-100 text-yellow-700' :
                    'bg-red-100 text-red-700';
  return (
    <span className={`px-1.5 py-0.5 text-xs rounded font-medium ${color}`}>
      {Math.round(score * 100)}分
    </span>
  );
}

function DeliverableCard({ item }: { item: DeliveryItem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border rounded-lg bg-white hover:shadow-sm transition-shadow">
      <button
        className="w-full text-left px-4 py-3 flex items-center gap-3"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className="text-lg flex-shrink-0">{TYPE_ICON[item.type]}</span>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-800 truncate">{item.name}</div>
          <div className="text-xs text-gray-400">
            {TYPE_LABELS[item.type]} · {item.owner_role}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <QualityBadge score={item.quality_score} />
          <span className="text-gray-400 text-xs">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t pt-3 space-y-2">
          {item.content_summary && (
            <p className="text-sm text-gray-600 leading-relaxed">{item.content_summary}</p>
          )}
          {item.tags && item.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {item.tags.map((tag) => (
                <span key={tag} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                  {tag}
                </span>
              ))}
            </div>
          )}
          {item.artifact_url && (
            <a
              href={item.artifact_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
            >
              ↓ 下载 / 查看
            </a>
          )}
        </div>
      )}
    </div>
  );
}

// ── 主组件 ──────────────────────────────────────────────────

const DeliveryView: React.FC<DeliveryBundleProps> = ({
  sessionId,
  projectTitle,
  deliverables,
  completedAt,
  onRerun,
  onSubmitDelta,
  className = '',
}) => {
  // 按类型分组
  const groups = deliverables.reduce<Partial<Record<DeliverableType, DeliveryItem[]>>>(
    (acc, item) => {
      const k = item.type;
      if (!acc[k]) acc[k] = [];
      acc[k]!.push(item);
      return acc;
    },
    {}
  );

  const avgScore =
    deliverables.length === 0
      ? null
      : deliverables.reduce((s, d) => s + (d.quality_score ?? 0), 0) / deliverables.length;

  return (
    <div className={`rounded-xl border bg-gray-50 shadow-sm p-5 space-y-5 ${className}`}>
      {/* 标题区 */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-gray-800">
            {projectTitle ?? '项目交付物'}
          </h3>
          {completedAt && (
            <p className="text-xs text-gray-400 mt-0.5">完成于 {completedAt}</p>
          )}
        </div>
        {avgScore != null && (
          <div className="text-right flex-shrink-0">
            <div className="text-2xl font-bold text-green-600">{Math.round(avgScore * 100)}</div>
            <div className="text-xs text-gray-400">综合评分</div>
          </div>
        )}
      </div>

      {/* 统计栏 */}
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="p-2 rounded-lg bg-white border">
          <div className="text-xl font-bold text-gray-800">{deliverables.length}</div>
          <div className="text-xs text-gray-400">总计交付物</div>
        </div>
        <div className="p-2 rounded-lg bg-white border">
          <div className="text-xl font-bold text-green-600">
            {deliverables.filter((d) => (d.quality_score ?? 0) >= 0.8).length}
          </div>
          <div className="text-xs text-gray-400">优质交付</div>
        </div>
        <div className="p-2 rounded-lg bg-white border">
          <div className="text-xl font-bold text-blue-600">
            {Object.keys(groups).length}
          </div>
          <div className="text-xs text-gray-400">类型数量</div>
        </div>
      </div>

      {/* 分组内容 */}
      {deliverables.length === 0 ? (
        <div className="py-8 text-center text-gray-400 text-sm">暂无交付物</div>
      ) : (
        (Object.entries(groups) as [DeliverableType, DeliveryItem[]][]).map(([type, items]) => (
          <div key={type} className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-medium text-gray-500 uppercase">
              <span>{TYPE_ICON[type]}</span>
              <span>{TYPE_LABELS[type]} ({items.length})</span>
            </div>
            <div className="space-y-2 pl-1">
              {items.map((item) => (
                <DeliverableCard key={item.deliverable_id} item={item} />
              ))}
            </div>
          </div>
        ))
      )}

      {/* 操作按钮 */}
      {(onRerun || onSubmitDelta) && (
        <div className="flex gap-3 pt-2 border-t">
          {onSubmitDelta && (
            <button
              onClick={onSubmitDelta}
              className="flex-1 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors"
            >
              提交增量修改
            </button>
          )}
          {onRerun && (
            <button
              onClick={onRerun}
              className="flex-1 py-2 text-sm font-medium rounded-lg border text-gray-600 hover:bg-gray-50 transition-colors"
            >
              重新执行
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default DeliveryView;
