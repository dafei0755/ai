// components/SchemeGraph.tsx
// 方案图谱  InfraNodus 风格 · 持久化 Sigma 实例 · 连续 FA2 平滑布局
// 四色边（关联/因果/层次/冲突）+ Louvain 社区着色 + 节点增量变更
// Copilot 生成 2026-03-15（v3：smooth transition + InfraNodus style）

'use client';

import React, { useEffect, useRef } from 'react';
import Sigma from 'sigma';
import Graph from 'graphology';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import louvain from 'graphology-communities-louvain';
import type { GraphEdge, NodeRole } from '@/store/graphStore';
import { useGraphStore } from '@/store/graphStore';

// ── 社区调色板（20 色，InfraNodus 风格暖色系） ─────────────────────────────────
const COMMUNITY_PALETTE = [
  '#818cf8','#4ade80','#fbbf24','#22d3ee','#f87171',
  '#f472b6','#a78bfa','#34d399','#fb923c','#38bdf8',
  '#e879f9','#86efac','#fcd34d','#67e8f9','#fca5a5',
  '#c4b5fd','#6ee7b7','#fdba74','#7dd3fc','#f9a8d4',
];
function communityColor(id: number): string {
  return COMMUNITY_PALETTE[id % COMMUNITY_PALETTE.length];
}

// ── 边类型 → 视觉属性 ──────────────────────────────────────────────────────────
const EDGE_BASE_COLOR: Record<string, string> = {
  association:  'rgba(148,163,184,0.18)',  // 淡灰：大量共现
  causal:       'rgba(96,165,250,0.62)',   // 蓝：因果推导
  hierarchical: 'rgba(251,146,60,0.62)',   // 橙：层次包含
  conflict:     'rgba(239,68,68,0.78)',    // 红：矛盾张力
};
const EDGE_BASE_WIDTH: Record<string, number> = {
  association: 0.7, causal: 1.5, hierarchical: 1.5, conflict: 2.0,
};

function edgeVisual(edge: GraphEdge): { color: string; size: number } {
  const rt = edge.relType ?? (edge.isConflict ? 'conflict' : 'association');
  const base = EDGE_BASE_WIDTH[rt] ?? 0.7;
  return {
    color: EDGE_BASE_COLOR[rt] ?? EDGE_BASE_COLOR.association,
    size:  Math.min(base + edge.weight * 0.12, base * 3.5),
  };
}

// ── 节点状态色（stable 由 Louvain 覆写） ──────────────────────────────────────
function nodeStateColor(state: string): string {
  switch (state) {
    case 'streaming':   return 'rgba(129,140,248,0.35)';
    case 'pending':     return 'rgba(148,163,184,0.40)';
    case 'deprecated':  return 'rgba(15,23,42,0.6)';
    default:            return '#94a3b8';
  }
}

// ── 词频 → 节点大小 ────────────────────────────────────────────────────────────
function freqToSize(freq: number, maxFreq: number): number {
  if (maxFreq <= 1) return 7;
  return 4 + Math.sqrt(freq / maxFreq) * 22;
}

// ── Observer 角色 → 视觉属性（第三方洞察节点专属配色） ──────────────────────────
const ROLE_COLOR: Partial<Record<NodeRole, string>> = {
  purpose:     '#f4d03f',  // 金色 – 核心目标
  tension:     '#e74c3c',  // 红色 – 张力矛盾
  insight:     '#f39c12',  // 亮橙 – 洞察
  strategy:    '#1abc9c',  // 蓝绿 – 策略
  stakeholder: '#e67e22',  // 橙色 – 干系人
  constraint:  '#7f8c8d',  // 灰色 – 约束
  factor:      '#2ecc71',  // 绿色 – 影响因子
  gap:         '#94a3b8',  // 浅灰 – 缺口
  deliverable: '#9b59b6',  // 紫色 – 交付物
};
const ROLE_SIZE_MULT: Partial<Record<NodeRole, number>> = {
  purpose: 2.2, insight: 1.8, tension: 1.6,
  strategy: 1.2, stakeholder: 1.0, constraint: 1.0,
  factor: 0.9, gap: 0.85, deliverable: 1.0,
};

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

/** 对任意格式颜色字符串（#rrggbb / rgb() / rgba()）应用透明度 */
function applyAlpha(color: string, alpha: number): string {
  if (color.startsWith('#') && color.length >= 6) return hexToRgba(color.slice(0, 7), alpha);
  if (color.startsWith('rgba(')) return color.replace(/,\s*[\d.]+\)$/, `,${alpha.toFixed(2)}`)  + ')';
  if (color.startsWith('rgb('))  return `rgba(${color.slice(4, -1)},${alpha.toFixed(2)})`;
  return color;
}

// ── Props ──────────────────────────────────────────────────────────────────────
interface SchemeGraphProps {
  sessionId?: string;
  className?: string;
  showMockData?: boolean;
}

// ── 组件 ───────────────────────────────────────────────────────────────────────
export function SchemeGraph({ sessionId: _sessionId, className = '', showMockData = false }: SchemeGraphProps) {
  const containerRef     = useRef<HTMLDivElement>(null);
  const graphRef         = useRef<Graph | null>(null);
  const sigmaRef         = useRef<Sigma | null>(null);
  const layoutFrameRef   = useRef<number>(0);
  const tickRef          = useRef<number>(0);
  // 节点坐标记忆：FA2 布局后保存，新节点出现在附近，避免跳变
  const nodePositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map());
  // Canvas2D 渐变边覆盖层
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  // 悬停节点 id
  const [hoveredNode, setHoveredNode] = React.useState<string | null>(null);
  // 点击高亮节点 id（ref 供 reducer 闭包读取，state 驱动 UI）
  const selectedNodeRef = useRef<string | null>(null);
  const [selectedNode, setSelectedNode] = React.useState<string | null>(null);

  const { streaming, pending, stable, stableEdges, deprecated, loadMockData, pruneExpiredStreaming } = useGraphStore();

  useEffect(() => { if (showMockData) loadMockData(); }, []); // eslint-disable-line
  useEffect(() => {
    const t = setInterval(pruneExpiredStreaming, 5000);
    return () => clearInterval(t);
  }, [pruneExpiredStreaming]);

  // ── Effect 1：仅 mount 时创建 Sigma + 启动持续 FA2 循环 ────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    const g = new Graph({ multi: false, type: 'undirected' });
    graphRef.current = g;

    const onEnterNode = ({ node }: { node: string }) => setHoveredNode(node);
    const onLeaveNode = () => setHoveredNode(null);

    const renderer = new Sigma(g, containerRef.current, {
      renderEdgeLabels:      false,
      // 内置边全透明 — 由下方 Canvas2D 覆盖层绘制渐变边
      edgeReducer: (_, data) => ({ ...data, color: 'rgba(0,0,0,0)', size: 0 }),
      labelFont:             '"Inter","PingFang SC","Noto Sans SC",sans-serif',
      labelSize:             11,
      labelWeight:           '600',
      labelColor:            { color: '#e2e8f0' },
      minCameraRatio:        0.08,
      maxCameraRatio:        10,
      defaultEdgeType:       'line',
      allowInvalidContainer: true,
      nodeReducer: (nodeId, attrs) => {
        // deprecated 节点：隐藏
        if (attrs.state === 'deprecated') return { ...attrs, label: undefined, hidden: true };
        const role = attrs.nodeRole as NodeRole | undefined;
        const roleColor = role ? ROLE_COLOR[role] : undefined;
        const forceLabel = role === 'purpose' || role === 'tension' || role === 'insight';

        // ── 点击高亮逻辑 ──
        const sel = selectedNodeRef.current;
        if (sel) {
          const isSelected = nodeId === sel;
          const isNeighbor = g.hasNode(sel) && g.neighbors(sel).includes(nodeId);
          if (isSelected) {
            // 选中节点：白色描边高亮
            return { ...attrs, color: roleColor ?? attrs.color, borderColor: '#ffffff', borderSize: 3, zIndex: 2 };
          }
          if (isNeighbor) {
            // 邻居节点：正常显示，强制出标签
            const base = roleColor ?? attrs.color;
            return { ...attrs, color: base, zIndex: 1 };
          }
          // 无关节点：灰化 + 隐藏标签
          return { ...attrs, color: 'rgba(50,60,75,0.55)', label: undefined, zIndex: 0 };
        }

        // ── 无选中时的普通样式 ──
        if (forceLabel) {
          return { ...attrs, color: roleColor ?? attrs.color, borderColor: roleColor, borderSize: 2 };
        }
        if ((attrs.size as number) < 6) return { ...attrs, color: roleColor ?? attrs.color, label: undefined };
        return { ...attrs, color: roleColor ?? attrs.color };
      },
    });
    // 点击节点：切换高亮（再次点击取消）
    const onClickNode = ({ node }: { node: string }) => {
      const next = selectedNodeRef.current === node ? null : node;
      selectedNodeRef.current = next;
      setSelectedNode(next);
      renderer.refresh();
    };
    // 点击空白：取消高亮
    const onClickStage = () => {
      if (selectedNodeRef.current) {
        selectedNodeRef.current = null;
        setSelectedNode(null);
        renderer.refresh();
      }
    };

    renderer.on('enterNode', onEnterNode);
    renderer.on('leaveNode', onLeaveNode);
    renderer.on('clickNode',  onClickNode);
    renderer.on('clickStage', onClickStage);
    sigmaRef.current = renderer;

    // ── Canvas2D 渐变边覆盖层 ─────────────────────────────────────────────────
    const drawOverlay = () => {
      const canvas = overlayCanvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;
      const w = container.offsetWidth;
      const h = container.offsetHeight;
      // 同步物理像素尺寸（支持高 DPR 屏）
      const dpr = window.devicePixelRatio || 1;
      const pw = Math.round(w * dpr);
      const ph = Math.round(h * dpr);
      if (canvas.width !== pw || canvas.height !== ph) {
        canvas.width = pw;
        canvas.height = ph;
      }
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, w, h);

      const sel = selectedNodeRef.current;
      g.forEachEdge((_edgeId, attrs, source, target) => {
        // deprecated 节点跳过
        if (g.getNodeAttribute(source, 'state') === 'deprecated') return;
        if (g.getNodeAttribute(target, 'state') === 'deprecated') return;

        // 图空间坐标 → 屏幕 CSS 像素坐标（graphToViewport 接受图空间坐标）
        const { x: sx, y: sy } = renderer.graphToViewport({
          x: g.getNodeAttribute(source, 'x') as number,
          y: g.getNodeAttribute(source, 'y') as number,
        });
        const { x: tx, y: ty } = renderer.graphToViewport({
          x: g.getNodeAttribute(target, 'x') as number,
          y: g.getNodeAttribute(target, 'y') as number,
        });

        const isActive = !sel || source === sel || target === sel;
        const alpha    = isActive ? 0.82 : 0.05;
        const relType  = (attrs.relType as string) ?? 'association';
        const baseW    = EDGE_BASE_WIDTH[relType] ?? 0.7;
        const weight   = (attrs.weight as number) ?? 1;
        const lineW    = isActive
          ? Math.min(baseW + weight * 0.12, baseW * 3.5)
          : 0.35;

        // 节点颜色取 graphology 属性（已含 Louvain / Observer 角色色）
        const srcColor = (g.getNodeAttribute(source, 'color') as string) || '#94a3b8';
        const tgtColor = (g.getNodeAttribute(target, 'color') as string) || '#94a3b8';
        const grad = ctx.createLinearGradient(sx, sy, tx, ty);
        grad.addColorStop(0, applyAlpha(srcColor, alpha));
        grad.addColorStop(1, applyAlpha(tgtColor, alpha));

        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.lineTo(tx, ty);
        ctx.strokeStyle = grad;
        ctx.lineWidth   = lineW;
        if (relType === 'association') ctx.setLineDash([3, 5]);
        else ctx.setLineDash([]);
        ctx.stroke();
      });
      ctx.restore();
    };
    renderer.on('afterRender', drawOverlay);

    // FA2 设置（缓慢收敛，平滑感强）
    const FA2_SETTINGS = {
      gravity:            0.5,
      scalingRatio:       4,
      strongGravityMode:  false,
      barnesHutOptimize:  false,
      slowDown:           8,
      adjustSizes:        true,
    };

    let alive = true;
    const loop = () => {
      if (!alive) return;
      tickRef.current++;

      if (g.order > 1) {
        forceAtlas2.assign(g, {
          iterations: 3,
          settings: { ...forceAtlas2.inferSettings(g), ...FA2_SETTINGS },
        });
        // 持续保存位置，供后续新节点定位参考
        g.forEachNode((id, attrs) => {
          nodePositionsRef.current.set(id, { x: attrs.x as number, y: attrs.y as number });
        });
      }

      // streaming 脉冲（融合进 layout loop，不再单独 rAF）
      const sinVal = Math.sin(tickRef.current * 0.07);
      g.forEachNode((id, attrs) => {
        if (attrs.state === 'streaming') {
          g.setNodeAttribute(id, 'size',  5 + 3 * sinVal);
          g.setNodeAttribute(id, 'color', `rgba(129,140,248,${(0.2 + 0.25 * (sinVal + 1) / 2).toFixed(2)})`);
        }
      });

      renderer.refresh({ skipIndexation: false });
      layoutFrameRef.current = requestAnimationFrame(loop);
    };
    layoutFrameRef.current = requestAnimationFrame(loop);

    return () => {
      alive = false;
      cancelAnimationFrame(layoutFrameRef.current);
      renderer.off('enterNode',   onEnterNode);
      renderer.off('leaveNode',    onLeaveNode);
      renderer.off('clickNode',    onClickNode);
      renderer.off('clickStage',   onClickStage);
      renderer.off('afterRender',  drawOverlay);
      renderer.kill();
      graphRef.current = null;
      sigmaRef.current = null;
    };
  }, []); // ← 只在 mount 时运行一次

  // ── Effect 2：Store 变化时增量更新图（不重建 Sigma） ───────────────────────
  useEffect(() => {
    const g = graphRef.current;
    if (!g) return;

    // 计算 stable 词频上限
    let maxFreq = 1;
    stable.forEach(n => { if ((n.freq ?? 1) > maxFreq) maxFreq = n.freq ?? 1; });

    // 期望节点映射
    type DesiredNode = { label: string; size: number; state: string; freq: number };
    const desired = new Map<string, DesiredNode>();
    stable.forEach(n =>
      desired.set(n.id, { label: n.label, size: freqToSize(n.freq ?? 1, maxFreq), state: 'stable', freq: n.freq ?? 1 })
    );
    pending.forEach(n => {
      if (!desired.has(n.id)) {
        desired.set(n.id, {
          label: n.label, size: 6,
          state: streaming.has(n.id) ? 'streaming' : 'pending',
          freq: 1,
        });
      }
    });
    deprecated.forEach(n => {
      if (!desired.has(n.id)) desired.set(n.id, { label: n.label, size: 2, state: 'deprecated', freq: 1 });
    });

    // 1. 删除不再需要的节点（自动级联删除相关边）
    const toRemove = g.nodes().filter(id => !desired.has(id));
    toRemove.forEach(id => { try { g.dropNode(id); } catch (_) {} });

    // 2. 添加或更新节点
    let louvainNeeded = toRemove.length > 0;
    desired.forEach((d, id) => {
      if (!g.hasNode(id)) {
        // 新节点：先找保存的坐标，否则放在现有质心附近（避免远距离弹入）
        let x: number, y: number;
        const saved = nodePositionsRef.current.get(id);
        if (saved) {
          x = saved.x; y = saved.y;
        } else if (g.order > 0) {
          let cx = 0, cy = 0, cnt = 0;
          g.forEachNode((_, a) => { cx += a.x as number; cy += a.y as number; cnt++; });
          x = cx / cnt + (Math.random() - 0.5) * 0.4;
          y = cy / cnt + (Math.random() - 0.5) * 0.4;
        } else {
          x = Math.random() * 2 - 1;
          y = Math.random() * 2 - 1;
        }
        const storeNode = stable.get(id) ?? pending.get(id);
        const nodeRole = storeNode?.nodeRole;
        const description = storeNode?.description;
        const sizeMult = nodeRole ? (ROLE_SIZE_MULT[nodeRole] ?? 1) : 1;
        g.addNode(id, { label: d.label, size: d.size * sizeMult, color: nodeStateColor(d.state), x, y, state: d.state, freq: d.freq, nodeRole, description });
        louvainNeeded = true;
      } else {
        // 更新现有节点属性（不动坐标，让 FA2 自然收敛）
        const storeNodeU = stable.get(id) ?? pending.get(id);
        const nodeRoleU = storeNodeU?.nodeRole;
        const sizeMult = nodeRoleU ? (ROLE_SIZE_MULT[nodeRoleU] ?? 1) : 1;
        g.setNodeAttribute(id, 'size', d.size * sizeMult);
        g.setNodeAttribute(id, 'nodeRole', nodeRoleU ?? null);
        g.setNodeAttribute(id, 'description', storeNodeU?.description ?? null);
        if (g.getNodeAttribute(id, 'state') !== d.state) {
          g.setNodeAttribute(id, 'state', d.state);
          if (d.state !== 'stable') g.setNodeAttribute(id, 'color', nodeStateColor(d.state));
          if (d.state === 'stable') louvainNeeded = true;
        }
        g.setNodeAttribute(id, 'freq', d.freq);
      }
    });

    // 3. 同步边
    const desiredEdgeIds = new Set<string>();
    stableEdges.forEach(edge => {
      if (!g.hasNode(edge.source) || !g.hasNode(edge.target)) return;
      desiredEdgeIds.add(edge.id);
      const { color, size } = edgeVisual(edge);
      const hasEdge = g.hasEdge(edge.source, edge.target);
      if (!hasEdge) {
        try {
          g.addEdge(edge.source, edge.target, { _key: edge.id, weight: edge.weight, color, size, relType: edge.relType });
        } catch (_) {}
      } else {
        try {
          const eid = g.edge(edge.source, edge.target);
          if (eid) { g.setEdgeAttribute(eid, 'color', color); g.setEdgeAttribute(eid, 'size', size); }
        } catch (_) {}
      }
    });

    // 删除多余边
    g.edges().forEach(eid => {
      const key = g.getEdgeAttribute(eid, '_key') as string | undefined;
      if (!key || !desiredEdgeIds.has(key)) { try { g.dropEdge(eid); } catch (_) {} }
    });

    // 4. Louvain 社区着色（仅 stable 节点）
    if (louvainNeeded && stable.size > 1 && g.size > 0) {
      try {
        const communities = louvain(g);
        g.forEachNode((id, attrs) => {
          if (attrs.state === 'stable') {
            g.setNodeAttribute(id, 'color', communityColor((communities as any)[id] ?? 0));
          }
        });
      } catch (_) {}
    }

  }, [streaming, pending, stable, stableEdges, deprecated]);

  const isEmpty = stable.size === 0 && pending.size === 0 && streaming.size === 0;

  // ── 悬停节点描述 Tooltip ──────────────────────────────────────────────────
  const hoveredDescription = hoveredNode
    ? (graphRef.current?.getNodeAttribute(hoveredNode, 'description') as string | null)
    : null;
  const hoveredLabel = hoveredNode
    ? (graphRef.current?.getNodeAttribute(hoveredNode, 'label') as string | null)
    : null;
  const hoveredRole = hoveredNode
    ? (graphRef.current?.getNodeAttribute(hoveredNode, 'nodeRole') as NodeRole | null)
    : null;
  const tooltipColor = hoveredRole ? ROLE_COLOR[hoveredRole] : undefined;

  return (
    <div className={`relative w-full h-full bg-[var(--canvas-bg)] ${className}`}>
      {/* Sigma 容器 */}
      <div ref={containerRef} className="w-full h-full" />
      {/* Canvas2D 渐变边覆盖层（pointer-events-none 不拦截交互） */}
      <canvas ref={overlayCanvasRef} className="absolute inset-0 pointer-events-none" style={{ width: '100%', height: '100%' }} />

      {/* 选中节点提示条 */}
      {selectedNode && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 pointer-events-none">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] text-slate-300"
            style={{ background: 'rgba(15,23,42,0.85)', border: '1px solid rgba(148,163,184,0.25)' }}>
            <span className="w-1.5 h-1.5 rounded-full bg-white inline-block" />
            {graphRef.current?.getNodeAttribute(selectedNode, 'label') ?? selectedNode}
            <span className="text-slate-500 ml-0.5">· 点击空白取消</span>
          </span>
        </div>
      )}

      {/* Observer 节点悬停 Tooltip */}
      {hoveredNode && hoveredDescription && (
        <div
          className="absolute top-3 right-3 z-20 max-w-[220px] rounded-lg px-3 py-2 shadow-lg pointer-events-none"
          style={{ background: 'rgba(15,23,42,0.92)', border: `1px solid ${tooltipColor ?? '#334155'}` }}
        >
          {hoveredLabel && (
            <div className="text-[11px] font-semibold mb-0.5" style={{ color: tooltipColor ?? '#e2e8f0' }}>
              {hoveredLabel}
            </div>
          )}
          {hoveredRole && (
            <div className="text-[9px] uppercase tracking-widest mb-1 opacity-60 text-slate-400">
              {hoveredRole}
            </div>
          )}
          <div className="text-[11px] text-slate-300 leading-relaxed">
            {hoveredDescription}
          </div>
        </div>
      )}

      {/* 空状态提示 */}
      {isEmpty && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 pointer-events-none">
          <svg viewBox="0 0 96 64" className="w-20 h-14 opacity-10" fill="none">
            <circle cx="48" cy="10" r="6"  stroke="#94a3b8" strokeWidth="1.5" />
            <circle cx="10" cy="54" r="6"  stroke="#94a3b8" strokeWidth="1.5" />
            <circle cx="86" cy="54" r="6"  stroke="#94a3b8" strokeWidth="1.5" />
            <line x1="48" y1="16" x2="10" y2="48" stroke="#94a3b8" strokeWidth="1.5" />
            <line x1="48" y1="16" x2="86" y2="48" stroke="#94a3b8" strokeWidth="1.5" />
            <line x1="16" y1="54" x2="80" y2="54" stroke="#94a3b8" strokeWidth="1" strokeDasharray="4 3" />
          </svg>
          <p className="text-[11px] text-slate-500 text-center leading-relaxed">
            对话推进后<br />概念与关系自动生成
          </p>
        </div>
      )}

      {/* 图例 */}
      {!isEmpty && (
        <div className="absolute bottom-3 left-3 z-10 pointer-events-none flex flex-col gap-1">
          {/* 边类型图例 */}
          <div className="flex flex-col gap-0.5 mb-1">
            <EdgeLegend color="rgba(96,165,250,0.85)"  label="因果" />
            <EdgeLegend color="rgba(251,146,60,0.85)"  label="层次" />
            <EdgeLegend color="rgba(239,68,68,0.85)"   label="矛盾" />
            <EdgeLegend color="rgba(148,163,184,0.55)" label="关联" dashed />
          </div>
          {/* 节点状态图例 */}
          <div className="flex flex-wrap gap-x-3 gap-y-0.5">
            {stable.size     > 0 && <NodeLegend label={`确认 ${stable.size}`}   alpha={1} />}
            {pending.size    > 0 && <NodeLegend label={`待确认 ${pending.size}`} alpha={0.4} dashed />}
            {streaming.size  > 0 && <NodeLegend label="分析中" alpha={0.35} pulsing />}
            {deprecated.size > 0 && <NodeLegend label={`排除 ${deprecated.size}`} color="#1e293b" alpha={1} />}
          </div>
        </div>
      )}
    </div>
  );
}

// ── 辅助图例组件 ──────────────────────────────────────────────────────────────
function EdgeLegend({ color, label, dashed = false }: { color: string; label: string; dashed?: boolean }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="inline-block w-5 h-[2px]" style={{ background: dashed ? 'none' : color, border: dashed ? `1px dashed ${color}` : 'none' }} />
      <span className="text-[10px] text-slate-400">{label}</span>
    </span>
  );
}

function NodeLegend({ label, alpha = 1, color = '#94a3b8', dashed = false, pulsing = false }:
  { label: string; alpha?: number; color?: string; dashed?: boolean; pulsing?: boolean }) {
  return (
    <span className="flex items-center gap-1">
      <span
        className={`inline-block w-2 h-2 rounded-full border ${pulsing ? 'animate-pulse' : ''}`}
        style={{
          backgroundColor: hexToRgba(color, alpha * 0.8),
          borderColor:     hexToRgba(color, alpha),
          borderStyle:     dashed ? 'dashed' : 'solid',
        }}
      />
      <span className="text-[10px] text-slate-500">{label}</span>
    </span>
  );
}

