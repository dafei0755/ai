'use client';
import React, { useEffect, useState } from 'react';

// ── External selection payload (drives right-panel linkage) ──────────────────
export type SelectionLevel = 'L1' | 'L2' | 'L3';
export interface BubbleAdjacency {
  id: string; name: string; relation: '已确认' | '待定'; bidir: boolean; tag?: string;
}
export interface BubbleZoneRoom {
  label: string; func?: string; texture?: string;
}
export interface BubbleSelectionInfo {
  level:  SelectionLevel | null;
  bubble: { id: string; name: string; area?: string; group: string } | null;
  zone:   { id: string; label: string; sublabel: string; maturity: number; roomCount: number; rooms: BubbleZoneRoom[] } | null;
  room:   { label: string; func?: string; texture?: string } | null;
  adjacencies: BubbleAdjacency[];
  /** Allow breadcrumb / panel to navigate up. roomIdx required to reach L3. */
  navigate: (target: SelectionLevel | null) => void;
}
interface BubbleZoningDiagramProps {
  onSelectionChange?: (info: BubbleSelectionInfo) => void;
  /** Outer-canvas zoom level — used to keep texture patterns at constant pixel size. */
  zoom?: number;
  /** 点击 tile（每个 zone 自己的"平面穿透窗"）→ 打开该 zone 的悬浮工作台。
      与空间泡泡逻辑 1:1 对应，每个 tile 是它自己的 portal。 */
  onOpenPlan?: (ctx: {
    zoneId: string;
    zoneLabel: string;
    sublabel: string;
    maturity: number;
    bindingState: 'unbound' | 'candidate' | 'bound';
  }) => void;
}

// ── Canvas dims ────────────────────────────────────────────────────────────────
const VW             = 860;
const VH_BUBBLE      = 570;
const BUBBLE_INFO_Y  = VH_BUBBLE + 10;
const BUBBLE_INFO_H  = 38;
const FP_HEADER_Y    = BUBBLE_INFO_Y + BUBBLE_INFO_H + 12;
const FP_HEADER_H    = 22;
const FP_TILE_W      = 252;
const FP_TILE_H      = 320;
const FP_ROW_GAP     = 14;
const FP_TILE_GAP    = 14;
const FP_TOP         = FP_HEADER_Y + FP_HEADER_H + 12;
const FP_BOT         = FP_TOP + FP_TILE_H + FP_ROW_GAP + FP_TILE_H;
const ROOM_INFO_Y    = FP_BOT + 14;
const ROOM_INFO_H    = 38;
const VH_TOTAL       = ROOM_INFO_Y + ROOM_INFO_H + 18;
const DATUM_Y        = 262;
const ROOM_SCALE     = 1.55;

// ── Types ─────────────────────────────────────────────────────────────────────
type Texture = 'stipple' | 'hatch' | 'xhatch' | 'hlines' | 'vlines' | 'none';
type Shape   = 'circle' | 'pill-h' | 'pill-v' | 'rect';

interface ProgramNode {
  id: string; name: string; area?: string; group: string;
  shape: Shape; cx: number; cy: number; rx: number; ry: number;
  texture: Texture; strokeW: number;
  labelDir: 'top' | 'bottom' | 'left' | 'right' | 'inside';
}
interface Link {
  a: string; b: string; curve?: number;
  style: 'solid' | 'dashed'; bidir?: boolean; tag?: string;
}
interface FPRoom {
  x: number; y: number; w: number; h: number;
  label: string; func?: string; texture?: Texture; dashed?: boolean;
}
interface FPZone {
  id: string; label: string; sublabel: string;
  rooms: FPRoom[]; maturity: number;
}

// ── PSC Program nodes ──────────────────────────────────────────────────────────
const NODES: ProgramNode[] = [
  { id: 'entry',   name: '到达与入口', area: '主入口',  group: '前场',
    shape: 'circle', cx: 105, cy: DATUM_Y, rx: 52, ry: 52,
    texture: 'stipple', strokeW: 1.6, labelDir: 'left' },
  { id: 'lobby',   name: '大堂楼',   area: '~2,400 ㎡', group: '前场',
    shape: 'rect', cx: 368, cy: DATUM_Y, rx: 128, ry: 88,
    texture: 'xhatch', strokeW: 2.2, labelDir: 'inside' },
  { id: 'dining',  name: '餐饮',     area: '~1,800 ㎡', group: '前场',
    shape: 'pill-h', cx: 645, cy: 164, rx: 92, ry: 50,
    texture: 'hatch', strokeW: 1.6, labelDir: 'top' },
  { id: 'zone_a',  name: '客房组团 A', area: '~3,200 ㎡', group: '前场',
    shape: 'pill-v', cx: 724, cy: 320, rx: 50, ry: 96,
    texture: 'hlines', strokeW: 1.6, labelDir: 'right' },
  { id: 'zone_b',  name: '客房组团 B', area: '~2,800 ㎡', group: '前场',
    shape: 'pill-v', cx: 630, cy: 436, rx: 46, ry: 76,
    texture: 'hlines', strokeW: 1.6, labelDir: 'right' },
  { id: 'service', name: '后勤与服务', area: '服务区', group: '后场',
    shape: 'rect', cx: 338, cy: 108, rx: 72, ry: 34,
    texture: 'vlines', strokeW: 1.2, labelDir: 'top' },
  { id: 'walk',    name: '景观步道',  group: '前场',
    shape: 'pill-h', cx: 385, cy: 500, rx: 188, ry: 22,
    texture: 'none', strokeW: 1.2, labelDir: 'bottom' },
];

const LINKS: Link[] = [
  { a: 'entry',  b: 'lobby',   style: 'solid',  curve: -18 },
  { a: 'lobby',  b: 'dining',  style: 'solid',  bidir: true, curve: 22 },
  { a: 'lobby',  b: 'service', style: 'dashed', curve: 0, tag: '后勤连通' },
  { a: 'lobby',  b: 'zone_a',  style: 'solid',  curve: 18 },
  { a: 'lobby',  b: 'zone_b',  style: 'solid',  curve: -14 },
  { a: 'lobby',  b: 'walk',    style: 'dashed', curve: 0 },
  { a: 'dining', b: 'zone_a',  style: 'solid',  curve: 10 },
];

// ── Floor plan zone data ──────────────────────────────────────────────────────
const FP_ZONES: FPZone[] = [
  { id: 'entry', label: '到达与入口', sublabel: '主入口广场', maturity: 0.62,
    rooms: [
      { x: 8,  y: 6,   w: 52,  h: 44, label: '落客区',   func: '车行落客 / 即停即走',  texture: 'stipple', dashed: true },
      { x: 8,  y: 56,  w: 52,  h: 58, label: '入口广场', func: '人流集散 / 仪式感',     texture: 'none',    dashed: true },
      { x: 68, y: 6,   w: 62,  h: 42, label: '有盖连廊', func: '雨天保护 / 引导动线',   texture: 'hlines' },
      { x: 68, y: 54,  w: 62,  h: 36, label: '景观前区', func: '前场绿化 / 视线缓冲',   texture: 'none',    dashed: true },
      { x: 8,  y: 122, w: 122, h: 16, label: '主车行道 →', func: '主车行流线',         texture: 'none' },
    ] },
  { id: 'lobby', label: '大堂楼', sublabel: '~2,400 ㎡', maturity: 0.78,
    rooms: [
      { x: 5,   y: 5,   w: 22,  h: 30, label: '前厅',   func: '入口过渡', texture: 'none' },
      { x: 31,  y: 5,   w: 63,  h: 36, label: '总台接待', func: '入住 / 退房 / 礼宾', texture: 'xhatch' },
      { x: 99,  y: 5,   w: 31,  h: 82, label: '电梯厅',  func: '客用垂直交通',     texture: 'vlines' },
      { x: 5,   y: 40,  w: 89,  h: 52, label: '大堂休闲', func: '等候 / 会客 / 工作', texture: 'hatch' },
      { x: 5,   y: 97,  w: 42,  h: 35, label: '咖啡吧',  func: '全日餐饮 / 配套',   texture: 'hlines' },
      { x: 52,  y: 97,  w: 42,  h: 35, label: '精品店',  func: '零售 / 文创',       texture: 'hatch' },
      { x: 5,   y: 137, w: 125, h: 11, label: '— 一层主流线 —', func: '横向交通主轴', texture: 'none' },
    ] },
  { id: 'dining', label: '餐饮楼', sublabel: '~1,800 ㎡', maturity: 0.55,
    rooms: [
      { x: 5,   y: 5,   w: 82,  h: 72, label: '主餐厅',   func: '正餐 / 自助',        texture: 'hatch' },
      { x: 92,  y: 5,   w: 38,  h: 55, label: '外摆露台', func: '户外用餐 / 季节',   texture: 'none', dashed: true },
      { x: 5,   y: 82,  w: 50,  h: 58, label: '厨房',     func: '热厨 / 冷厨 / 备餐', texture: 'vlines' },
      { x: 60,  y: 82,  w: 30,  h: 28, label: '吧台',     func: '酒吧 / 咖啡',        texture: 'xhatch' },
      { x: 60,  y: 115, w: 30,  h: 25, label: '备餐',     func: '出餐准备',           texture: 'vlines' },
      { x: 95,  y: 65,  w: 35,  h: 40, label: '私人包间', func: '宴请 / 商务',        texture: 'hlines' },
      { x: 5,   y: 145, w: 125, h: 11, label: '← 后勤通道', func: '后勤进出流线', texture: 'none' },
    ] },
  { id: 'zone_a', label: '客房组团 A', sublabel: '~3,200 ㎡ · 3F', maturity: 0.66,
    rooms: [
      { x: 5,   y: 68,  w: 125, h: 11, label: '客房走廊', func: '客房水平交通',  texture: 'none' },
      { x: 5,   y: 10,  w: 28,  h: 55, label: '客房',    func: '标间 · 北向',  texture: 'hlines' },
      { x: 36,  y: 10,  w: 28,  h: 55, label: '客房',    func: '标间 · 北向',  texture: 'hlines' },
      { x: 67,  y: 10,  w: 28,  h: 55, label: '景观套',  func: '套房 · 主景观', texture: 'hlines' },
      { x: 98,  y: 10,  w: 32,  h: 55, label: '服务间',  func: '布草 / 客服',  texture: 'vlines' },
      { x: 5,   y: 83,  w: 28,  h: 55, label: '客房',    func: '标间 · 南向',  texture: 'hlines' },
      { x: 36,  y: 83,  w: 28,  h: 55, label: '客房',    func: '标间 · 南向',  texture: 'hlines' },
      { x: 67,  y: 83,  w: 28,  h: 55, label: '家庭房',  func: '家庭套间',     texture: 'hlines' },
      { x: 98,  y: 83,  w: 32,  h: 55, label: '消防楼梯', func: '紧急疏散',    texture: 'vlines' },
      { x: 5,   y: 143, w: 125, h: 11, label: '— 1F 平面示意 —', func: '当前展示楼层', texture: 'none' },
    ] },
  { id: 'service', label: '后勤与服务', sublabel: '服务区', maturity: 0.42,
    rooms: [
      { x: 5,   y: 5,   w: 50,  h: 40, label: '装卸货',  func: '物流进出',        texture: 'stipple' },
      { x: 60,  y: 5,   w: 65,  h: 56, label: '仓储',    func: '物资 / 干仓',     texture: 'vlines' },
      { x: 5,   y: 50,  w: 50,  h: 45, label: '洗衣房',  func: '布草 / 制服',     texture: 'xhatch' },
      { x: 5,   y: 100, w: 50,  h: 42, label: '员工区',  func: '更衣 / 员工餐厅', texture: 'hlines' },
      { x: 60,  y: 66,  w: 65,  h: 76, label: '设备机房', func: '机电 / 强弱电',   texture: 'vlines' },
      { x: 5,   y: 147, w: 120, h: 11, label: '← 服务后廊', func: '后勤水平交通', texture: 'none' },
    ] },
];

// ── Bubble ↔ Zone mapping ─────────────────────────────────────────────────────
// null = no detailed floor plan tile (will show "暂无明细" placeholder)
const BUBBLE_TO_ZONE: Record<string, string | null> = {
  entry:   'entry',
  lobby:   'lobby',
  dining:  'dining',
  zone_a:  'zone_a',
  zone_b:  null,
  service: 'service',
  walk:    null,
};
const ZONE_TO_BUBBLE: Record<string, string> = {
  entry:   'entry',
  lobby:   'lobby',
  dining:  'dining',
  zone_a:  'zone_a',
  service: 'service',
};

// Tile positions: 3 + 2 layout
const ROW1_MARGIN = (VW - 3 * FP_TILE_W - 2 * FP_TILE_GAP) / 2;
const ROW2_MARGIN = (VW - 2 * FP_TILE_W - FP_TILE_GAP) / 2;
const TILE_POS: { x: number; y: number }[] = [
  { x: ROW1_MARGIN,                                 y: FP_TOP },
  { x: ROW1_MARGIN + (FP_TILE_W + FP_TILE_GAP),     y: FP_TOP },
  { x: ROW1_MARGIN + 2 * (FP_TILE_W + FP_TILE_GAP), y: FP_TOP },
  { x: ROW2_MARGIN,                                 y: FP_TOP + FP_TILE_H + FP_ROW_GAP },
  { x: ROW2_MARGIN + (FP_TILE_W + FP_TILE_GAP),     y: FP_TOP + FP_TILE_H + FP_ROW_GAP },
];

// ── Geometry helpers ──────────────────────────────────────────────────────────
function edgePt(node: ProgramNode, dx: number, dy: number): [number, number] {
  const len = Math.hypot(dx, dy);
  if (len === 0) return [node.cx, node.cy];
  const nx = dx / len, ny = dy / len;
  const denom = Math.sqrt((node.ry * nx) ** 2 + (node.rx * ny) ** 2);
  const r = (node.rx * node.ry) / (denom || 1);
  return [node.cx + r * nx, node.cy + r * ny];
}

function bezierPath(a: ProgramNode, b: ProgramNode, curve = 0): string {
  const dx = b.cx - a.cx, dy = b.cy - a.cy;
  const [sx, sy] = edgePt(a,  dx,  dy);
  const [ex, ey] = edgePt(b, -dx, -dy);
  if (curve === 0) {
    const mx = (sx + ex) / 2, my = (sy + ey) / 2;
    return `M ${sx} ${sy} Q ${mx} ${my} ${ex} ${ey}`;
  }
  const len = Math.hypot(dx, dy);
  const px = -dy / len, py = dx / len;
  const mx = (sx + ex) / 2 + curve * px;
  const my = (sy + ey) / 2 + curve * py;
  return `M ${sx} ${sy} Q ${mx} ${my} ${ex} ${ey}`;
}

function shapePath(n: ProgramNode): string {
  const { shape, cx, cy, rx, ry } = n;
  if (shape === 'circle') {
    return `M ${cx - rx} ${cy} a ${rx} ${ry} 0 1 0 ${rx * 2} 0 a ${rx} ${ry} 0 1 0 ${-rx * 2} 0`;
  }
  const cr = shape === 'pill-h' ? ry : shape === 'pill-v' ? rx : 13;
  const x0 = cx - rx, y0 = cy - ry, x1 = cx + rx, y1 = cy + ry;
  return [
    `M ${x0 + cr} ${y0}`, `L ${x1 - cr} ${y0}`,
    `a ${cr} ${cr} 0 0 1 ${cr} ${cr}`,
    `L ${x1} ${y1 - cr}`,
    `a ${cr} ${cr} 0 0 1 ${-cr} ${cr}`,
    `L ${x0 + cr} ${y1}`,
    `a ${cr} ${cr} 0 0 1 ${-cr} ${-cr}`,
    `L ${x0} ${y0 + cr}`,
    `a ${cr} ${cr} 0 0 1 ${cr} ${-cr} Z`,
  ].join(' ');
}

function labelPos(n: ProgramNode) {
  const g = 16;
  switch (n.labelDir) {
    case 'top':    return { lx: n.cx,        ly: n.cy - n.ry, tx: n.cx,            ty: n.cy - n.ry - g - 8,  anchor: 'middle' };
    case 'bottom': return { lx: n.cx,        ly: n.cy + n.ry, tx: n.cx,            ty: n.cy + n.ry + g + 14, anchor: 'middle' };
    case 'left':   return { lx: n.cx - n.rx, ly: n.cy,        tx: n.cx - n.rx - g, ty: n.cy + 4,             anchor: 'end' };
    case 'right':  return { lx: n.cx + n.rx, ly: n.cy,        tx: n.cx + n.rx + g, ty: n.cy + 4,             anchor: 'start' };
    default:       return { lx: n.cx,        ly: n.cy,        tx: n.cx,            ty: n.cy,                 anchor: 'middle' };
  }
}

// ── Layer toggle button ───────────────────────────────────────────────────────
function LayerBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      style={{
        fontSize: 10,
        fontFamily: "'Courier New', monospace",
        letterSpacing: '0.08em',
        padding: '2px 9px',
        borderRadius: 0,
        border: `1px solid ${active ? 'rgba(255,255,255,0.42)' : 'rgba(255,255,255,0.14)'}`,
        background: active ? 'rgba(255,255,255,0.09)' : 'transparent',
        color: active ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.28)',
        cursor: 'pointer',
        userSelect: 'none',
      }}
    >
      {children}
    </button>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function BubbleZoningDiagram({ onSelectionChange, zoom = 1, onOpenPlan }: BubbleZoningDiagramProps = {}) {
  // Counter-scale pattern transform to keep textures crisp at all zoom levels
  const patScale = `scale(${1 / Math.max(zoom, 0.1)})`;
  // selBubble — selected bubble node id (drives cross-layer linkage)
  // selRoom   — selected room within a tile { zoneId, idx }
  // selLevel  — which level was explicitly clicked (drives panel detail card)
  const [selBubble, setSelBubble] = useState<string | null>(null);
  const [selRoom, setSelRoom]     = useState<{ zoneId: string; idx: number } | null>(null);
  const [selLevel, setSelLevel]   = useState<SelectionLevel | null>(null);

  const [showFlow, setFlow]   = useState(true);
  const [showArea, setArea]   = useState(true);
  const [showNotes, setNotes] = useState(true);
  const [showFloor, setFloor] = useState(true);

  const byId = (id: string) => NODES.find(n => n.id === id)!;
  const TEX: Record<Texture, string> = {
    stipple: 'url(#bz-stipple)',
    hatch:   'url(#bz-hatch)',
    xhatch:  'url(#bz-xhatch)',
    hlines:  'url(#bz-hlines)',
    vlines:  'url(#bz-vlines)',
    none:    'transparent',
  };

  const selNode    = selBubble ? NODES.find(n => n.id === selBubble) ?? null : null;
  const selZoneId  = selBubble ? BUBBLE_TO_ZONE[selBubble] ?? null : null;
  const selZone    = selZoneId ? FP_ZONES.find(z => z.id === selZoneId) ?? null : null;
  const selRoomObj = selRoom && selZone ? selZone.rooms[selRoom.idx] ?? null : null;

  // ── Push selection upward so the right-panel can render linked detail ────
  useEffect(() => {
    if (!onSelectionChange) return;
    const adjacencies: BubbleAdjacency[] = selNode
      ? LINKS.filter(lk => lk.a === selNode.id || lk.b === selNode.id).map(lk => {
          const otherId = lk.a === selNode.id ? lk.b : lk.a;
          const other = NODES.find(n => n.id === otherId);
          return {
            id: otherId,
            name: other?.name ?? otherId,
            relation: lk.style === 'solid' ? '已确认' : '待定',
            bidir: !!lk.bidir,
            tag: lk.tag,
          };
        })
      : [];
    onSelectionChange({
      level: selLevel,
      bubble: selNode
        ? { id: selNode.id, name: selNode.name, area: selNode.area, group: selNode.group }
        : null,
      zone: selZone
        ? {
            id: selZone.id, label: selZone.label, sublabel: selZone.sublabel,
            maturity: selZone.maturity, roomCount: selZone.rooms.length,
            rooms: selZone.rooms.map(r => ({ label: r.label, func: r.func, texture: r.texture })),
          }
        : null,
      room: selRoomObj
        ? { label: selRoomObj.label, func: selRoomObj.func, texture: selRoomObj.texture }
        : null,
      adjacencies,
      navigate,
    });
    // navigate is intentionally omitted from deps — its closures are stable for this purpose
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selBubble, selRoom, selLevel, selNode, selZone, selRoomObj, onSelectionChange]);

  // Click handlers (cross-layer linkage + level tracking)
  const onBubbleClick = (id: string) => {
    if (selBubble === id && selLevel === 'L1') {
      setSelBubble(null); setSelRoom(null); setSelLevel(null);
    } else {
      setSelBubble(id); setSelRoom(null); setSelLevel('L1');
    }
  };
  const onTileClick = (zoneId: string) => {
    // 点击 tile = 该 zone 自己的"平面穿透窗"被点击 → 选中 L2 + 打开悬浮工作台
    const bubble = ZONE_TO_BUBBLE[zoneId];
    setSelBubble(bubble); setSelRoom(null); setSelLevel('L2');
    const z = FP_ZONES.find(fz => fz.id === zoneId);
    if (z && onOpenPlan) {
      onOpenPlan({
        zoneId: z.id,
        zoneLabel: z.label,
        sublabel: z.sublabel,
        maturity: z.maturity,
        bindingState: z.maturity < 0.50 ? 'candidate' : 'bound',
      });
    }
  };
  const onRoomClick = (zoneId: string, idx: number) => {
    const bubble = ZONE_TO_BUBBLE[zoneId];
    const isSame = selRoom?.zoneId === zoneId && selRoom.idx === idx && selLevel === 'L3';
    if (isSame) {
      // Re-clicking selected room steps back to L2
      setSelLevel('L2'); setSelRoom(null);
    } else {
      setSelBubble(bubble); setSelRoom({ zoneId, idx }); setSelLevel('L3');
    }
  };
  // Breadcrumb / panel navigation up
  const navigate = (target: SelectionLevel | null) => {
    if (target === null) {
      setSelBubble(null); setSelRoom(null); setSelLevel(null);
    } else if (target === 'L1') {
      setSelRoom(null); setSelLevel('L1');
    } else if (target === 'L2' && selBubble) {
      setSelRoom(null); setSelLevel('L2');
    } else if (target === 'L3' && selRoom) {
      setSelLevel('L3');
    }
  };

  // Adaptive canvas height
  const canvasH = showFloor
    ? VH_TOTAL
    : BUBBLE_INFO_Y + BUBBLE_INFO_H + 18;

  return (
    <div style={{ width: '100%', background: '#0d1117', overflow: 'hidden' }}>

      {/* ── Layer control toolbar ────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 7,
        padding: '6px 14px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        background: 'rgba(0,0,0,0.22)',
      }}>
        <span style={{
          fontSize: 10, fontFamily: "'Courier New', monospace",
          letterSpacing: '0.10em', color: 'rgba(255,255,255,0.32)',
          marginRight: 3, userSelect: 'none',
        }}>
          图层
        </span>
        <LayerBtn active={showFlow}  onClick={() => setFlow(v => !v)}>动线</LayerBtn>
        <LayerBtn active={showArea}  onClick={() => setArea(v => !v)}>面积标注</LayerBtn>
        <LayerBtn active={showNotes} onClick={() => setNotes(v => !v)}>空间注释</LayerBtn>
        <LayerBtn active={showFloor} onClick={() => setFloor(v => !v)}>平面逻辑</LayerBtn>
      </div>

      <svg viewBox={`0 0 ${VW} ${canvasH}`} width="100%" style={{ display: 'block' }}>
        <defs>
          <pattern id="bz-grid" width="28" height="28" patternUnits="userSpaceOnUse" patternTransform={patScale}>
            <circle cx="0" cy="0" r="0.85" fill="rgba(255,255,255,0.055)" />
          </pattern>
          <pattern id="bz-stipple" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform={patScale}>
            <circle cx="3.5" cy="3.5" r="1.1" fill="rgba(255,255,255,0.36)" />
          </pattern>
          <pattern id="bz-hatch" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform={patScale}>
            <line x1="0" y1="9" x2="9" y2="0" stroke="rgba(255,255,255,0.32)" strokeWidth="1.1" />
          </pattern>
          <pattern id="bz-xhatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform={patScale}>
            <line x1="0" y1="10" x2="10" y2="0" stroke="rgba(255,255,255,0.22)" strokeWidth="1" />
            <line x1="0" y1="0"  x2="10" y2="10" stroke="rgba(255,255,255,0.22)" strokeWidth="1" />
          </pattern>
          <pattern id="bz-hlines" width="8" height="7" patternUnits="userSpaceOnUse" patternTransform={patScale}>
            <line x1="0" y1="3.5" x2="8" y2="3.5" stroke="rgba(255,255,255,0.28)" strokeWidth="0.95" />
          </pattern>
          <pattern id="bz-vlines" width="7" height="8" patternUnits="userSpaceOnUse" patternTransform={patScale}>
            <line x1="3.5" y1="0" x2="3.5" y2="8" stroke="rgba(255,255,255,0.28)" strokeWidth="0.95" />
          </pattern>
          <marker id="bz-arr" markerWidth="9" markerHeight="8" refX="8" refY="4" orient="auto">
            <path d="M0,0.5 L8.5,4 L0,7.5 L2.2,4 Z" fill="rgba(255,255,255,0.82)" />
          </marker>
          <marker id="bz-arr-rev" markerWidth="9" markerHeight="8" refX="1" refY="4" orient="auto-start-reverse">
            <path d="M9,0.5 L0.5,4 L9,7.5 L6.8,4 Z" fill="rgba(255,255,255,0.82)" />
          </marker>
          <marker id="bz-arr-dim" markerWidth="9" markerHeight="8" refX="8" refY="4" orient="auto">
            <path d="M0,0.5 L8.5,4 L0,7.5 L2.2,4 Z" fill="rgba(255,255,255,0.36)" />
          </marker>
          {/* Outer-glow only: subtract the source shape from the blur so the
              halo lives strictly outside the path — prevents the selected
              bubble's interior from looking smudged. */}
          <filter id="bz-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="b" />
            <feComposite in="b" in2="SourceGraphic" operator="out" result="outer" />
            <feMerge><feMergeNode in="outer"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>

        {/* Background — bubble dark, info & floor plan lighter.
            Background rects carry the click-to-clear handler so clicks on
            decorations (lines, labels, arrows) do nothing — only true empty
            background clicks deselect. */}
        <rect width={VW} height={VH_BUBBLE} fill="#0d1117"
          onClick={() => navigate(null)} />
        <rect y={VH_BUBBLE} width={VW} height={canvasH - VH_BUBBLE} fill="#171d23"
          onClick={() => navigate(null)} />
        <rect width={VW} height={VH_BUBBLE} fill="url(#bz-grid)"
          onClick={() => navigate(null)} />

        {/* Top title */}
        <text x="22" y="28" fontSize="9" fill="rgba(255,255,255,0.50)"
          fontFamily="'Courier New',monospace" letterSpacing="0.08em">
          泡泡逻辑预演 / 一层概念
        </text>

        {/* ─── BUBBLE DIAGRAM (y: 0 to VH_BUBBLE) ─────────────────────────── */}

        {showNotes && (
          <>
            <text x={VW - 22} y={DATUM_Y - 10} fontSize="9" textAnchor="end"
              fill="rgba(255,255,255,0.32)" fontFamily="'Courier New',monospace" letterSpacing="0.06em">
              前场 / 客用
            </text>
            <text x={VW - 22} y={DATUM_Y + 20} fontSize="9" textAnchor="end"
              fill="rgba(255,255,255,0.32)" fontFamily="'Courier New',monospace" letterSpacing="0.06em">
              后场 / 后勤
            </text>
          </>
        )}

        {showFlow && (
          <path
            d={`M 57 ${DATUM_Y + 12} Q 200 ${VH_BUBBLE - 70} 385 500`}
            fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="1.8"
            markerEnd="url(#bz-arr-dim)"
          />
        )}

        {/* Program shapes — clickable, parent of cross-layer linkage */}
        {NODES.map(node => {
          const isSel = selBubble === node.id;
          const isDim = selBubble !== null && !isSel;
          const d = shapePath(node);
          return (
            <g key={node.id}
              onClick={(e) => { e.stopPropagation(); onBubbleClick(node.id); }}
              style={{ cursor: 'pointer' }}
              filter={isSel ? 'url(#bz-glow)' : undefined}
              opacity={isDim ? 0.45 : 1}
            >
              <path d={d} fill="rgba(13,17,23,0.90)" />
              <path d={d} fill={TEX[node.texture]} />
              <path d={d} fill="none"
                stroke={isSel
                  ? 'rgba(255,255,255,0.98)'
                  : node.texture === 'none'
                    ? 'rgba(255,255,255,0.38)'
                    : 'rgba(255,255,255,0.82)'}
                strokeWidth={isSel ? node.strokeW + 0.8 : node.strokeW}
              />
              {node.labelDir === 'inside' && (
                <>
                  <text x={node.cx} y={node.cy - 4} textAnchor="middle"
                    fontSize="11" fill="rgba(255,255,255,0.82)"
                    fontFamily="'Courier New',monospace" letterSpacing="0.07em"
                    style={{ pointerEvents: 'none' }}>
                    {node.name}
                  </text>
                  {showArea && node.area && (
                    <text x={node.cx} y={node.cy + 11} textAnchor="middle"
                      fontSize="8.5" fill="rgba(255,255,255,0.38)"
                      fontFamily="'Courier New',monospace"
                      style={{ pointerEvents: 'none' }}>
                      {node.area}
                    </text>
                  )}
                </>
              )}
            </g>
          );
        })}

        {/* Datum line */}
        <line x1="28" y1={DATUM_Y} x2={VW - 28} y2={DATUM_Y}
          stroke="rgba(255,255,255,0.86)" strokeWidth="2.2" />
        {showNotes && (
          <text x="32" y={DATUM_Y - 7} fontSize="7"
            fill="rgba(255,255,255,0.32)" fontFamily="'Courier New',monospace" letterSpacing="0.10em">
            主轴 / 一层地面
          </text>
        )}

        {/* Connections */}
        {showFlow && LINKS.map((lk, i) => {
          const na = byId(lk.a), nb = byId(lk.b);
          const d = bezierPath(na, nb, lk.curve ?? 0);
          const isDash = lk.style === 'dashed';
          const involves = selBubble && (selBubble === lk.a || selBubble === lk.b);
          const isDim = selBubble !== null && !involves;
          const mx = (na.cx + nb.cx) / 2 + (lk.curve ?? 0) * 0.5;
          const my = (na.cy + nb.cy) / 2;
          return (
            <g key={i} opacity={isDim ? 0.25 : 1}>
              <path d={d} fill="none"
                stroke={involves
                  ? 'rgba(255,255,255,0.95)'
                  : isDash ? 'rgba(255,255,255,0.30)' : 'rgba(255,255,255,0.68)'}
                strokeWidth={isDash ? 1 : 1.6}
                strokeDasharray={isDash ? '6 5' : undefined}
                markerEnd={isDash ? 'url(#bz-arr-dim)' : 'url(#bz-arr)'}
                markerStart={lk.bidir ? 'url(#bz-arr-rev)' : undefined}
              />
              {lk.tag && showNotes && (
                <text x={mx + 10} y={my - 6} fontSize="7"
                  fill="rgba(255,255,255,0.32)"
                  fontFamily="'Courier New',monospace" letterSpacing="0.06em">
                  {lk.tag}
                </text>
              )}
            </g>
          );
        })}

        {/* External labels */}
        {NODES.filter(n => n.labelDir !== 'inside').map(node => {
          const { lx, ly, tx, ty, anchor } = labelPos(node);
          const isDim = selBubble !== null && selBubble !== node.id;
          return (
            <g key={`lbl-${node.id}`} opacity={isDim ? 0.45 : 1} style={{ pointerEvents: 'none' }}>
              <line x1={lx} y1={ly} x2={tx} y2={ty}
                stroke="rgba(255,255,255,0.18)" strokeWidth="0.8" />
              <text x={tx} y={ty}
                textAnchor={anchor as React.SVGAttributes<SVGTextElement>['textAnchor']}
                fontSize="9.5" fill="rgba(255,255,255,0.80)"
                fontFamily="'Courier New',monospace" letterSpacing="0.06em">
                {node.name}
              </text>
              {showArea && node.area && (
                <text x={tx} y={ty + 13}
                  textAnchor={anchor as React.SVGAttributes<SVGTextElement>['textAnchor']}
                  fontSize="8" fill="rgba(255,255,255,0.34)"
                  fontFamily="'Courier New',monospace">
                  {node.area}
                </text>
              )}
            </g>
          );
        })}

        {/* Annotations panel */}
        {showNotes && (
          <g transform="translate(668 20)">
            <rect width="178" height="152"
              fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.18)" strokeWidth="0.8" />
            <rect width="178" height="22" fill="rgba(255,255,255,0.07)" />
            <text x="9" y="15" fontSize="8" fill="rgba(255,255,255,0.55)"
              fontFamily="'Courier New',monospace" letterSpacing="0.08em">
              空间逻辑备注
            </text>
            <line x1="0" y1="22" x2="178" y2="22" stroke="rgba(255,255,255,0.10)" strokeWidth="0.6" />
            {([
              ['空间骨架', '已确认 / 草案'],
              ['总面积',   '~13,200 ㎡'],
              ['大堂楼',   '已挂载'],
              ['餐饮楼',   '草案中'],
              ['客房组团', '草案中'],
              ['后勤区',   '待挂载'],
              ['基准轴',   '一层地面层'],
              ['邻接关系', '实线=确认 虚线=待定'],
              ['下游解锁', '→ 生成作用域索引'],
            ] as [string, string][]).map(([k, v], i) => (
              <g key={i} transform={`translate(0 ${27 + i * 13.5})`}>
                <text x="9" fontSize="7" fill="rgba(255,255,255,0.34)"
                  fontFamily="'Courier New',monospace" letterSpacing="0.04em">
                  {k}
                </text>
                <text x="96" fontSize="7" fill="rgba(255,255,255,0.62)"
                  fontFamily="'Courier New',monospace" letterSpacing="0.04em">
                  {v}
                </text>
              </g>
            ))}
          </g>
        )}

        {/* Compass */}
        <g transform={`translate(${VW - 38} ${VH_BUBBLE - 50})`}>
          <path d="M0,-11 L4,4 L0,1 L-4,4 Z" fill="rgba(255,255,255,0.60)" />
          <path d="M0,11 L4,-4 L0,-1 L-4,-4 Z" fill="rgba(255,255,255,0.14)" />
          <text x="0" y="-14" textAnchor="middle" fontSize="7"
            fill="rgba(255,255,255,0.40)" fontFamily="'Courier New',monospace">北</text>
        </g>

        {/* ─── L1 INFO BAR — bubble level summary ─────────────────────────── */}
        <g transform={`translate(0 ${BUBBLE_INFO_Y})`}>
          <rect x="20" y="0" width={VW - 40} height={BUBBLE_INFO_H}
            fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.12)" strokeWidth="0.7" />
          {/* Left tag */}
          <rect x="20" y="0" width="86" height={BUBBLE_INFO_H} fill="rgba(255,255,255,0.05)" />
          <text x="32" y={BUBBLE_INFO_H / 2 + 3.5} fontSize="9.5"
            fill="rgba(255,255,255,0.55)" fontFamily="'Courier New',monospace" letterSpacing="0.08em">
            L1 · 空间索引
          </text>

          {selNode ? (
            <>
              <text x={120} y={15} fontSize="11" fill="rgba(255,255,255,0.92)"
                fontFamily="'Courier New',monospace" fontWeight="700">
                {selNode.name}
              </text>
              <text x={120} y={29} fontSize="8" fill="rgba(255,255,255,0.45)"
                fontFamily="'Courier New',monospace" letterSpacing="0.04em">
                {selNode.group} · {selNode.area ?? '—'} · 关联 {LINKS.filter(l => l.a === selNode.id || l.b === selNode.id).length} 项
              </text>

              {/* Right side: drill-down hint */}
              {selZone ? (
                <text x={VW - 30} y={BUBBLE_INFO_H / 2 + 3.5} textAnchor="end" fontSize="9"
                  fill="rgba(125,211,252,0.82)" fontFamily="'Courier New',monospace" letterSpacing="0.05em">
                  ↓ 已联动平面：{selZone.label} · {Math.round(selZone.maturity * 100)}%
                </text>
              ) : (
                <text x={VW - 30} y={BUBBLE_INFO_H / 2 + 3.5} textAnchor="end" fontSize="9"
                  fill="rgba(255,255,255,0.32)" fontFamily="'Courier New',monospace" letterSpacing="0.05em">
                  ↓ 平面明细：暂无（待补充）
                </text>
              )}
            </>
          ) : (
            <>
              <text x={120} y={15} fontSize="10.5" fill="rgba(255,255,255,0.55)"
                fontFamily="'Courier New',monospace">
                全局视图 · 未选择空间
              </text>
              <text x={120} y={29} fontSize="8" fill="rgba(255,255,255,0.32)"
                fontFamily="'Courier New',monospace" letterSpacing="0.04em">
                共 {NODES.length} 个空间节点 · {LINKS.length} 条邻接关系 · 点击任一空间进入索引
              </text>
            </>
          )}
        </g>

        {/* ─── FLOOR PLAN REGION ─────────────────────────────────────────── */}
        {showFloor && (
          <g>
            {/* Section header */}
            <line x1={28} y1={FP_HEADER_Y} x2={VW - 28} y2={FP_HEADER_Y}
              stroke="rgba(255,255,255,0.10)" strokeWidth="0.7" strokeDasharray="5 4" />
            <text x="32" y={FP_HEADER_Y + 16} fontSize="9"
              fill="rgba(255,255,255,0.42)" fontFamily="'Courier New',monospace" letterSpacing="0.08em">
              L2 · 区域平面逻辑
            </text>
            <text x={VW - 32} y={FP_HEADER_Y + 16} fontSize="8" textAnchor="end"
              fill="rgba(255,255,255,0.22)" fontFamily="'Courier New',monospace" letterSpacing="0.04em">
              示意图 · 非比例 · 点击进入房间索引
            </text>

            {/* Tiles */}
            {FP_ZONES.map((zone, zi) => {
              const { x: tx, y: ty } = TILE_POS[zi];
              const isTileSelected = selZoneId === zone.id;
              const isTileDim = selZoneId !== null && !isTileSelected;
              const matW = Math.round(zone.maturity * (FP_TILE_W - 18));
              const matColor = zone.maturity >= 0.70
                ? 'rgba(52,211,153,0.72)'
                : zone.maturity >= 0.50
                  ? 'rgba(251,191,36,0.72)'
                  : 'rgba(248,113,113,0.60)';
              const planOffsetX = (FP_TILE_W - 130 * ROOM_SCALE) / 2;
              const planOffsetY = 50;

              return (
                <g key={zone.id} transform={`translate(${tx} ${ty})`}
                  opacity={isTileDim ? 0.42 : 1}>
                  {/* Tile background — clickable, 1:1 portal to plan deliberation */}
                  <rect
                    width={FP_TILE_W} height={FP_TILE_H}
                    fill={isTileSelected ? 'rgba(125,211,252,0.05)' : 'transparent'}
                    stroke={isTileSelected ? 'rgba(125,211,252,0.55)' : 'rgba(255,255,255,0.13)'}
                    strokeWidth={isTileSelected ? 1.2 : 0.8}
                    style={{ cursor: 'pointer' }}
                    onClick={(e) => { e.stopPropagation(); onTileClick(zone.id); }}
                  />

                  {/* Portal hint — 提示此 tile 即该 zone 的平面穿透窗 */}
                  <text x={FP_TILE_W - 9} y={14} textAnchor="end"
                    fontSize="7" fill="rgba(125,211,252,0.50)"
                    fontFamily="'Courier New',monospace" letterSpacing="0.06em"
                    style={{ pointerEvents: 'none' }}>
                    点击进入推演 →
                  </text>

                  {/* Header */}
                  <text x={FP_TILE_W / 2} y="22" textAnchor="middle"
                    fontSize="11"
                    fill={isTileSelected ? 'rgba(255,255,255,0.96)' : 'rgba(255,255,255,0.78)'}
                    fontFamily="'Courier New',monospace" letterSpacing="0.04em"
                    style={{ pointerEvents: 'none' }}>
                    {zone.label}
                  </text>
                  <text x={FP_TILE_W / 2} y="36" textAnchor="middle"
                    fontSize="8.5" fill="rgba(255,255,255,0.34)"
                    fontFamily="'Courier New',monospace"
                    style={{ pointerEvents: 'none' }}>
                    {zone.sublabel}
                  </text>
                  <line x1="14" y1="42" x2={FP_TILE_W - 14} y2="42"
                    stroke="rgba(255,255,255,0.10)" strokeWidth="0.6" />

                  {/* Rooms — each one clickable */}
                  <g transform={`translate(${planOffsetX} ${planOffsetY}) scale(${ROOM_SCALE})`}>
                    {zone.rooms.map((room, ri) => {
                      const isRoomSel = selRoom?.zoneId === zone.id && selRoom.idx === ri;
                      return (
                        <g key={ri}
                          onClick={(e) => { e.stopPropagation(); onRoomClick(zone.id, ri); }}
                          style={{ cursor: 'pointer' }}>
                          <rect x={room.x} y={room.y} width={room.w} height={room.h}
                            fill={isRoomSel ? 'rgba(125,211,252,0.18)' : 'rgba(13,17,23,0.88)'}
                            stroke={isRoomSel
                              ? 'rgba(125,211,252,0.95)'
                              : room.dashed ? 'rgba(255,255,255,0.24)' : 'rgba(255,255,255,0.55)'}
                            strokeWidth={isRoomSel ? 1.2 : (room.dashed ? 0.55 : 0.7)}
                            strokeDasharray={!isRoomSel && room.dashed ? '3 2' : undefined}
                            vectorEffect="non-scaling-stroke"
                          />
                          {room.texture && room.texture !== 'none' && !isRoomSel && (
                            <rect x={room.x} y={room.y} width={room.w} height={room.h}
                              fill={TEX[room.texture]} style={{ pointerEvents: 'none' }} />
                          )}
                          <text
                            x={room.x + room.w / 2}
                            y={room.y + room.h / 2 + (room.h > 20 ? 2.5 : 3)}
                            textAnchor="middle"
                            fontSize={room.h <= 14 ? 5.6 : room.h <= 24 ? 6.4 : 7.2}
                            fill={isRoomSel ? 'rgba(255,255,255,0.95)' : 'rgba(255,255,255,0.66)'}
                            fontFamily="'Courier New',monospace"
                            style={{ pointerEvents: 'none' }}
                          >
                            {room.label}
                          </text>
                        </g>
                      );
                    })}
                  </g>

                  {/* Maturity bar */}
                  <g transform={`translate(9 ${FP_TILE_H - 22})`}
                    style={{ pointerEvents: 'none' }}>
                    <text x="0" y="0" fontSize="7" fill="rgba(255,255,255,0.28)"
                      fontFamily="'Courier New',monospace" letterSpacing="0.04em">
                      完善度 {Math.round(zone.maturity * 100)}%
                    </text>
                    <rect x="0" y="6" width={FP_TILE_W - 18} height="3.5"
                      fill="rgba(255,255,255,0.07)" />
                    <rect x="0" y="6" width={matW} height="3.5"
                      fill={matColor} />
                  </g>
                </g>
              );
            })}

            {/* ─── L3 INFO BAR — room-level summary ───────────────────────── */}
            <g transform={`translate(0 ${ROOM_INFO_Y})`}>
              <rect x="20" y="0" width={VW - 40} height={ROOM_INFO_H}
                fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.12)" strokeWidth="0.7" />
              <rect x="20" y="0" width="86" height={ROOM_INFO_H} fill="rgba(255,255,255,0.05)" />
              <text x="32" y={ROOM_INFO_H / 2 + 3.5} fontSize="9.5"
                fill="rgba(255,255,255,0.55)" fontFamily="'Courier New',monospace" letterSpacing="0.08em">
                L3 · 房间索引
              </text>

              {selRoomObj && selZone && selNode ? (
                <>
                  <text x={120} y={15} fontSize="11" fill="rgba(255,255,255,0.92)"
                    fontFamily="'Courier New',monospace" fontWeight="700">
                    {selRoomObj.label}
                  </text>
                  <text x={120} y={29} fontSize="8" fill="rgba(255,255,255,0.50)"
                    fontFamily="'Courier New',monospace" letterSpacing="0.04em">
                    {selNode.name} → {selZone.label} → {selRoomObj.label}
                    {selRoomObj.func ? `   ·   ${selRoomObj.func}` : ''}
                  </text>
                  <text x={VW - 30} y={ROOM_INFO_H / 2 + 3.5} textAnchor="end" fontSize="9"
                    fill="rgba(125,211,252,0.82)" fontFamily="'Courier New',monospace" letterSpacing="0.05em">
                    ↓ 下游：进入平面推演 · 生成作用域
                  </text>
                </>
              ) : selZone ? (
                <>
                  <text x={120} y={15} fontSize="10.5" fill="rgba(255,255,255,0.65)"
                    fontFamily="'Courier New',monospace">
                    {selZone.label} · 共 {selZone.rooms.length} 个房间空间
                  </text>
                  <text x={120} y={29} fontSize="8" fill="rgba(255,255,255,0.32)"
                    fontFamily="'Courier New',monospace" letterSpacing="0.04em">
                    点击 tile 内任一房间查看明细
                  </text>
                </>
              ) : selBubble ? (
                <>
                  <text x={120} y={15} fontSize="10.5" fill="rgba(255,255,255,0.45)"
                    fontFamily="'Courier New',monospace">
                    暂无平面明细
                  </text>
                  <text x={120} y={29} fontSize="8" fill="rgba(255,255,255,0.30)"
                    fontFamily="'Courier New',monospace" letterSpacing="0.04em">
                    {selNode?.name ?? ''} 当前未挂载 FFL，房间数据待补充
                  </text>
                </>
              ) : (
                <>
                  <text x={120} y={15} fontSize="10.5" fill="rgba(255,255,255,0.45)"
                    fontFamily="'Courier New',monospace">
                    未选中房间
                  </text>
                  <text x={120} y={29} fontSize="8" fill="rgba(255,255,255,0.30)"
                    fontFamily="'Courier New',monospace" letterSpacing="0.04em">
                    上一层选中后，可在此查看其房间明细 / 路径索引
                  </text>
                </>
              )}
            </g>
          </g>
        )}
      </svg>
    </div>
  );
}
