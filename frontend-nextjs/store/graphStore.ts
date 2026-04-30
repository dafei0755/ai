// store/graphStore.ts
// 方案图谱  四态节点状态管理 + 词频/共现边累积 + Observer Intelligence Layer
// Copilot 生成 2026-03-15（v3：Observer LLM 结构化节点注入）

import { create } from 'zustand';
import { ingestText as extractFromText, termId, extractConceptsFromInterruptData, type ConceptNode, type CooccurrenceEdge, type EdgeRelType } from '@/lib/conceptExtractor';

// ── Observer Intelligence Layer 数据模型 ──────────────────────────────────────
/** 节点语义角色（由 Observer LLM 分配） */
export type NodeRole =
  | 'purpose'      // 项目真正意图
  | 'tension'      // 核心矛盾张力
  | 'strategy'     // 策略/解法
  | 'stakeholder'  // 人群/利益相关方
  | 'constraint'   // 约束条件
  | 'gap'          // 盲区/缺口
  | 'factor'       // 关键因素
  | 'insight'      // 穿透性洞察
  | 'deliverable'  // 落地载体
  | 'word';        // 普通词频节点（默认）

export interface ObserverNode {
  id: string;
  label: string;
  nodeType: NodeRole;
  description: string;
  confidence: number;
}

export interface ObserverEdge {
  source: string;
  target: string;
  relType: string;
  label: string;
  reasoning: string;
}

export interface ObserverResult {
  nodes: ObserverNode[];
  edges: ObserverEdge[];
  main_insight: string;
  key_contradictions: string[];
  blind_spots: string[];
  stage: string;
}

/** NodeRole 优先级（高优先级不被低优先级覆盖） */
const ROLE_PRIORITY: Record<string, number> = {
  purpose: 9, insight: 8, tension: 7, strategy: 6,
  stakeholder: 5, constraint: 5, deliverable: 4,
  factor: 3, gap: 2, word: 0,
};

export type { ConceptNode, CooccurrenceEdge };

export interface GraphNode {
  id: string;
  label: string;
  cluster: string;
  freq: number;
  size?: number;
  addedAt: number;
  deprecatedReason?: string;
  /** 锚点节点：永不裁剪，size 额外加权 */
  pinned?: boolean;
  /** 桥接节点：跨社区连通的中枢，由 SchemeGraph 计算后写入 */
  isBridge?: boolean;
  /** Observer LLM 分配的语义角色 */
  nodeRole?: NodeRole;
  /** Observer LLM 生成的节点描述（hover tooltip 使用） */
  description?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  weight: number;
  isConflict: boolean;
  relType: EdgeRelType;
}

const REL_PRIORITY: Record<string, number> = { conflict: 3, causal: 2, hierarchical: 1, association: 0 };

export interface GraphHint {
  node_id: string;
  label: string;
  stability: 'streaming' | 'pending' | 'stable' | 'deprecated';
  cluster?: string;
  deprecated_reason?: string;
}

interface GraphState {
  // 四态集合
  streaming: Set<string>;
  pending: Map<string, GraphNode>;
  stable: Map<string, GraphNode>;
  stableEdges: Map<string, GraphEdge>;
  deprecated: Map<string, GraphNode>;
  /** 累积 ingestText 调用次数（剪枝阈值判断） */
  ingestCount: number;
  /** 绑定的 sessionId，切换时自动 reset */
  boundSessionId: string | null;

  // 核心增量摄入（替代旧 loadConceptsFromInput）
  ingestText: (text: string) => void;

  // session 切换时重置图谱
  resetForSession: (sessionId: string) => void;

  // 四态迁移
  addStreaming: (nodeId: string, label: string) => void;
  promoteToPending: (nodeId: string, data: Omit<GraphNode, 'addedAt'>) => void;
  promoteToStable: (nodeId: string) => void;
  promoteAllPendingToStable: () => void;
  markDeprecated: (nodeId: string, reason: string) => void;

  // WS graph_hint
  applyGraphHint: (hint: GraphHint) => void;

  // 锚定节点（永不被裁剪，size 加权）
  anchorNode: (nodeId: string, label: string) => void;
  markBridge: (nodeId: string) => void;

  // Observer Intelligence Layer
  observerResult: ObserverResult | null;
  ingestObserverResult: (result: ObserverResult) => void;

  // TTL 清理
  pruneExpiredStreaming: () => void;

  // 序列化
  toGraphologyData: () => { nodes: GraphNode[]; edges: GraphEdge[] };

  // 兼容旧调用（用 ingestText 实现）
  loadConceptsFromInput: (userInput: string) => void;

  // 模拟数据（仅供开发调试）
  loadMockData: () => void;

  // 跨窗口同步：直接替换 stable/stableEdges（观察屏 BroadcastChannel 专用）
  setStableState: (nodes: GraphNode[], edges: GraphEdge[]) => void;
}

const STREAMING_TTL_MS = 30_000;
/** stable 节点上限：超过此值按词频裁剪，保持图的可读性 */
const MAX_STABLE_NODES = 80;
/** 词频下限：仅在 ingest 次数足够多之后启用，避免首次摄入即清空 */
const MIN_FREQ = 2;
/** 至少摄入多少次文本后才启用 MIN_FREQ 剪枝（每次 node_update 算一次） */
const MIN_INGEST_COUNT = 8;

// ── sessionStorage 持久化：图谱数据刷新后自动恢复 ─────────────────────────────
const GRAPH_STORAGE_PREFIX = 'graph_state_';
const GRAPH_STORAGE_TTL_MS = 2 * 60 * 60 * 1000; // 2小时 TTL

function _saveGraphToStorage(
  sessionId: string | null,
  stable: Map<string, GraphNode>,
  stableEdges: Map<string, GraphEdge>,
  ingestCount: number,
): void {
  if (!sessionId || typeof sessionStorage === 'undefined') return;
  try {
    sessionStorage.setItem(
      `${GRAPH_STORAGE_PREFIX}${sessionId}`,
      JSON.stringify({
        nodes: [...stable.values()],
        edges: [...stableEdges.values()],
        ingestCount,
        savedAt: Date.now(),
      }),
    );
  } catch {
    // sessionStorage 满或不可用时静默失败
  }
}

function _loadGraphFromStorage(sessionId: string): {
  nodes: GraphNode[];
  edges: GraphEdge[];
  ingestCount: number;
} | null {
  if (typeof sessionStorage === 'undefined') return null;
  try {
    const raw = sessionStorage.getItem(`${GRAPH_STORAGE_PREFIX}${sessionId}`);
    if (!raw) return null;
    const data = JSON.parse(raw) as { nodes: GraphNode[]; edges: GraphEdge[]; ingestCount: number; savedAt: number };
    if (Date.now() - data.savedAt > GRAPH_STORAGE_TTL_MS) {
      sessionStorage.removeItem(`${GRAPH_STORAGE_PREFIX}${sessionId}`);
      return null;
    }
    return data;
  } catch {
    return null;
  }
}

export const useGraphStore = create<GraphState>((set, get) => ({
  streaming: new Set(),
  pending: new Map(),
  stable: new Map(),
  stableEdges: new Map(),
  deprecated: new Map(),
  ingestCount: 0,
  boundSessionId: null,
  observerResult: null,

  // session 切换：清空图谱，绑定新 sessionId；优先从 sessionStorage 恢复缓存
  resetForSession: (sessionId: string) => {
    const { boundSessionId } = get();
    if (boundSessionId === sessionId) return; // 同 session 不重置

    const cached = _loadGraphFromStorage(sessionId);
    if (cached && cached.nodes.length > 0) {
      set({
        streaming: new Set(),
        pending: new Map(),
        stable: new Map(cached.nodes.map((n) => [n.id, n])),
        stableEdges: new Map(cached.edges.map((e) => [e.id, e])),
        deprecated: new Map(),
        ingestCount: cached.ingestCount,
        boundSessionId: sessionId,
      });
      return;
    }

    set({
      streaming: new Set(),
      pending: new Map(),
      stable: new Map(),
      stableEdges: new Map(),
      deprecated: new Map(),
      ingestCount: 0,
      boundSessionId: sessionId,
    });
  },
  ingestText: (text: string) => {
    if (!text || text.trim().length < 2) return;
    const { termFreqs, edges } = extractFromText(text);

    set((s) => {
      const nextStable = new Map(s.stable);
      const nextEdges  = new Map(s.stableEdges);
      const nextCount  = s.ingestCount + 1;
      /** 剪枝基准：摄入「前」的库存大小，首次摄入永不触发剪枝 */
      const sizeBeforeIngest = s.stable.size;

      // 词频累积  节点（直接进 stable，无需确认）
      termFreqs.forEach((freq, term) => {
        const id = termId(term);
        const existing = nextStable.get(id);
        if (existing) {
          nextStable.set(id, { ...existing, freq: existing.freq + freq });
        } else {
          nextStable.set(id, {
            id,
            label: term,
            cluster: 'default',   // Louvain 稍后覆写
            freq,
            addedAt: Date.now(),
          });
        }
      });

      // 共现边累积
      edges.forEach((e) => {
        if (!nextStable.has(e.source) || !nextStable.has(e.target)) return;
        const key = `${e.source}|||${e.target}`;
        const existing = nextEdges.get(key);
        if (existing) {
          const newRelType: EdgeRelType =
            (REL_PRIORITY[e.relType ?? 'association'] ?? 0) > (REL_PRIORITY[existing.relType ?? 'association'] ?? 0)
              ? (e.relType ?? 'association')
              : (existing.relType ?? 'association');
          nextEdges.set(key, {
            ...existing,
            weight: existing.weight + e.weight,
            isConflict: existing.isConflict || e.isConflict,
            relType: newRelType,
          });
        } else {
          nextEdges.set(key, {
            id: key,
            source: e.source,
            target: e.target,
            weight: e.weight,
            isConflict: e.isConflict,
            relType: e.relType ?? 'association',
          });
        }
      });

      // ── 剪枝：仅当「摄入前」corpus 已足够大时启用（首次摄入不剪枝）──────────────────────
      if (sizeBeforeIngest > 0 && nextCount >= MIN_INGEST_COUNT) {
        const toPrune = new Set<string>();
        // pinned 节点永不剪枝
        nextStable.forEach((n, id) => { if (!n.pinned && n.freq < MIN_FREQ) toPrune.add(id); });
        toPrune.forEach((id) => nextStable.delete(id));

        if (nextStable.size > MAX_STABLE_NODES) {
          // pinned 优先保留
          const pinned = new Set([...nextStable.entries()].filter(([,n]) => n.pinned).map(([id]) => id));
          const sorted = [...nextStable.entries()].sort((a, b) => b[1].freq - a[1].freq);
          const kept = new Set(
            sorted
              .filter(([id]) => pinned.has(id))
              .concat(sorted.filter(([id]) => !pinned.has(id)))
              .slice(0, MAX_STABLE_NODES)
              .map(([id]) => id)
          );
          nextStable.forEach((_, id) => { if (!kept.has(id)) toPrune.add(id); });
          toPrune.forEach((id) => nextStable.delete(id));
        }

        nextEdges.forEach((_, key) => {
          const [src, tgt] = key.split('|||');
          if (toPrune.has(src) || toPrune.has(tgt)) nextEdges.delete(key);
        });
      }

      return { stable: nextStable, stableEdges: nextEdges, ingestCount: nextCount };
    });
    // 图谱变更后持久化到 sessionStorage（SSR-safe）
    const { boundSessionId, stable, stableEdges, ingestCount } = get();
    _saveGraphToStorage(boundSessionId, stable, stableEdges, ingestCount);
  },

  //  四态迁移 
  addStreaming: (nodeId, label) => {
    set((s) => {
      const next = new Set(s.streaming);
      next.add(nodeId);
      const nextPending = new Map(s.pending);
      if (!nextPending.has(nodeId)) {
        nextPending.set(nodeId, { id: nodeId, label, cluster: 'default', freq: 1, addedAt: Date.now() });
      }
      return { streaming: next, pending: nextPending };
    });
  },

  promoteToPending: (nodeId, data) => {
    set((s) => {
      const nextStreaming = new Set(s.streaming);
      nextStreaming.delete(nodeId);
      const nextPending = new Map(s.pending);
      nextPending.set(nodeId, { ...data, freq: data.freq ?? 1, addedAt: Date.now() });
      return { streaming: nextStreaming, pending: nextPending };
    });
  },

  promoteToStable: (nodeId) => {
    set((s) => {
      const node = s.pending.get(nodeId);
      if (!node) return {};
      const nextPending = new Map(s.pending);
      nextPending.delete(nodeId);
      const nextStable = new Map(s.stable);
      nextStable.set(nodeId, node);
      return { pending: nextPending, stable: nextStable };
    });
  },

  promoteAllPendingToStable: () => {
    set((s) => {
      const nextStable = new Map(s.stable);
      s.pending.forEach((node) => nextStable.set(node.id, node));
      return { pending: new Map(), stable: nextStable };
    });
    const { boundSessionId, stable, stableEdges, ingestCount } = get();
    _saveGraphToStorage(boundSessionId, stable, stableEdges, ingestCount);
  },

  markDeprecated: (nodeId, reason) => {
    set((s) => {
      const nextStreaming = new Set(s.streaming);
      nextStreaming.delete(nodeId);
      const nextPending = new Map(s.pending);
      const nextStable  = new Map(s.stable);
      const sourceNode  = s.pending.get(nodeId) ?? s.stable.get(nodeId)
        ?? { id: nodeId, label: nodeId, cluster: 'default', freq: 1, addedAt: Date.now() };
      nextPending.delete(nodeId);
      nextStable.delete(nodeId);
      const nextDeprecated = new Map(s.deprecated);
      nextDeprecated.set(nodeId, { ...sourceNode, deprecatedReason: reason });
      return { streaming: nextStreaming, pending: nextPending, stable: nextStable, deprecated: nextDeprecated };
    });
  },

  applyGraphHint: (hint) => {
    const { addStreaming, promoteToPending, promoteToStable, markDeprecated } = get();
    const node = { id: hint.node_id, label: hint.label, cluster: hint.cluster ?? 'default', freq: 1 };
    switch (hint.stability) {
      case 'streaming':   addStreaming(hint.node_id, hint.label); break;
      case 'pending':     promoteToPending(hint.node_id, node); break;
      case 'stable':      promoteToPending(hint.node_id, node); promoteToStable(hint.node_id); break;
      case 'deprecated':  markDeprecated(hint.node_id, hint.deprecated_reason ?? '已被否决'); break;
    }
  },

  anchorNode: (nodeId, label) => {
    set(s => {
      const existing = s.stable.get(nodeId);
      if (existing) {
        const next = new Map(s.stable);
        next.set(nodeId, { ...existing, pinned: true, freq: Math.max(existing.freq, 5) });
        return { stable: next };
      }
      // 不在 stable 中则新建
      const next = new Map(s.stable);
      next.set(nodeId, { id: nodeId, label, cluster: 'anchor', freq: 5, addedAt: Date.now(), pinned: true });
      return { stable: next };
    });
  },

  markBridge: (nodeId) => {
    set(s => {
      const existing = s.stable.get(nodeId);
      if (!existing) return {};
      const next = new Map(s.stable);
      next.set(nodeId, { ...existing, isBridge: true });
      return { stable: next };
    });
  },

  pruneExpiredStreaming: () => {
    const now = Date.now();
    set((s) => {
      const expired: string[] = [];
      s.streaming.forEach((id) => {
        const node = s.pending.get(id);
        if (node && now - node.addedAt > STREAMING_TTL_MS) expired.push(id);
      });
      if (expired.length === 0) return {};
      const nextStreaming = new Set(s.streaming);
      const nextPending   = new Map(s.pending);
      expired.forEach((id) => { nextStreaming.delete(id); nextPending.delete(id); });
      return { streaming: nextStreaming, pending: nextPending };
    });
  },

  toGraphologyData: () => {
    const { pending, stable, stableEdges } = get();
    const nodes: GraphNode[] = [...stable.values(), ...pending.values()];
    const edges: GraphEdge[] = [...stableEdges.values()];
    return { nodes, edges };
  },

  loadConceptsFromInput: (userInput: string) => {
    get().ingestText(userInput);
  },

  loadMockData: () => {
    const store = get();
    store.ingestText(
      '蛇口渔村传统文化导致场所认同感，从而吸引香港访客和外籍客群。' +
      '冷链分区包括海鲜区、肉类区、熟食区，属于食品安全保障体系。' +
      '社交空间包括共享厨房、海鲜加工吧、亲子食育角，形成停留理由，从而带来非菜收入。' +
      '老居民效率需求vs游客体验需求，烟火感vs卫生标准，传统vs国际化，存在矛盾张力。' +
      '动线组织分为顾客线、商户线、后勤线，通过三线分流实现空间效率。' +
      '商业模型包括基础摊租、联营、策展市集、社群会员、到家配送，构成五段收入。' +
      '城市更新标杆需要兼顾公益属性和商业可持续，两者构成核心矛盾。'
    );
    // 锚定核心节点
    store.anchorNode('t_蛇口', '蛇口');
    store.anchorNode('t_渔村', '渔村');
    store.anchorNode('t_文化', '文化');
    store.anchorNode('t_冷链', '冷链');
    store.anchorNode('t_动线', '动线');
    store.anchorNode('t_社交', '社交');
    store.anchorNode('t_商业', '商业');
  },

  setStableState: (nodes, edges) => {
    set({
      stable:      new Map(nodes.map((n) => [n.id, n])),
      stableEdges: new Map(edges.map((e) => [e.id, e])),
    });
    const { boundSessionId, stable, stableEdges, ingestCount } = get();
    _saveGraphToStorage(boundSessionId, stable, stableEdges, ingestCount);
  },

  // ── Observer Intelligence Layer ────────────────────────────────────────────
  ingestObserverResult: (result: ObserverResult) => {
    set((s) => {
      const nextStable = new Map(s.stable);
      const nextEdges  = new Map(s.stableEdges);

      // 注入 Observer 节点（merged into stable，pinned 保护）
      result.nodes.forEach((obsNode) => {
        const existing = nextStable.get(obsNode.id);
        const newRole = obsNode.nodeType as NodeRole;
        if (existing) {
          // 只升级 role，不降级；累积 freq
          const existingPriority = ROLE_PRIORITY[existing.nodeRole ?? 'word'] ?? 0;
          const newPriority      = ROLE_PRIORITY[newRole] ?? 0;
          nextStable.set(obsNode.id, {
            ...existing,
            freq:        existing.freq + 2,
            nodeRole:    newPriority > existingPriority ? newRole : (existing.nodeRole ?? 'word'),
            description: obsNode.description || existing.description,
            pinned:      true,
          });
        } else {
          nextStable.set(obsNode.id, {
            id:          obsNode.id,
            label:       obsNode.label,
            cluster:     'default',
            freq:        3,
            addedAt:     Date.now(),
            nodeRole:    newRole,
            description: obsNode.description,
            pinned:      true,
          });
        }
      });

      // 注入 Observer 边
      result.edges.forEach((obsEdge) => {
        if (!nextStable.has(obsEdge.source) || !nextStable.has(obsEdge.target)) return;
        const key = `${obsEdge.source}|||${obsEdge.target}`;
        if (!nextEdges.has(key)) {
          // 将 Observer 边类型映射到 EdgeRelType
          const relTypeMap: Record<string, EdgeRelType> = {
            conflicts:  'conflict',
            resolves:   'causal',
            addresses:  'causal',
            influences: 'causal',
            contains:   'hierarchical',
            depends_on: 'hierarchical',
            constrains: 'hierarchical',
            derives:    'causal',
          };
          const relType: EdgeRelType = relTypeMap[obsEdge.relType] ?? 'association';
          nextEdges.set(key, {
            id:         key,
            source:     obsEdge.source,
            target:     obsEdge.target,
            weight:     3,
            isConflict: obsEdge.relType === 'conflicts',
            relType,
          });
        }
      });

      return {
        stable:       nextStable,
        stableEdges:  nextEdges,
        observerResult: result,
      };
    });
    const { boundSessionId, stable, stableEdges, ingestCount } = get();
    _saveGraphToStorage(boundSessionId, stable, stableEdges, ingestCount);
  },
}));
