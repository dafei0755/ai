'use client';

/**
 * GeoCanvasView — 地理工作台画布（嵌入式，替代 analysis page 左侧画布）
 *
 * 布局：
 *  ┌───────────────────────────┬──────────────────┐
 *  │   地图（MapEngineClient）  │  L1 场所信息面板  │
 *  │   搜索框覆盖在地图左上角    │  坐标 / 行政区划  │
 *  │   图层切换按钮             │  周边 POI 分析    │
 *  └───────────────────────────┴──────────────────┘
 *
 * 组件职责：
 *  1. 展示当前 geoAnchor 对应地图位置（只读，不可拖拽大头针）
 *  2. 提供图层切换（标准/卫星/路网）
 *  3. 展示周边 POI 分析（SurroundingPanel 同款）
 *  4. 入口按钮打开 GeoPickerModal（编辑选址）
 *  5. 「注入高参」按钮 → 把地理上下文发送给右侧对话
 */

import { useState, useCallback, useRef, useEffect, Suspense, lazy } from 'react';
import {
  X,
  Radar,
  Map,
  MapPin,
  Layers,
  RefreshCw,
  Navigation,
  Phone,
  Clock,
  Copy,
  Check,
  Loader2,
  Edit2,
  ChevronRight,
  SendHorizontal,
  Search,
  Activity,
  Route,
  Sun,
  Mountain,
  Play
} from 'lucide-react';
import { MapEngineClient } from './MapEngineClient';
import type { MapEngineRef } from './MapEngineClient';
import { useGeoStore } from '@/store/useGeoStore';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

const GeoPickerModal = lazy(() =>
  import('./GeoPickerModal').then((m) => ({ default: m.GeoPickerModal })),
);

// ── 周边分析分类 ────────────────────────────────────────────────────────────
import { GeoScorePanel } from './GeoScorePanel';
import { GeoThesisCard } from './GeoThesisCard';
import type { GeoThesis } from '@/types/geo';

const NEARBY_CATEGORIES = [
  { key: 'dining',     name: '餐饮',   types: '050000',        color: 'bg-orange-100 text-orange-700' },
  { key: 'shopping',   name: '购物',   types: '060000',        color: 'bg-blue-100 text-blue-700' },
  { key: 'hotel',      name: '住宿',   types: '100000',        color: 'bg-purple-100 text-purple-700' },
  { key: 'medical',    name: '医疗',   types: '090000',        color: 'bg-red-100 text-red-700' },
  { key: 'education',  name: '教育',   types: '140000',        color: 'bg-green-100 text-green-700' },
  { key: 'transport',  name: '交通',   types: '150000',        color: 'bg-gray-100 text-gray-700' },
  { key: 'scenery',    name: '景区',   types: '110000',        color: 'bg-emerald-100 text-emerald-700' },
  { key: 'recreation', name: '休闲',   types: '080000',        color: 'bg-pink-100 text-pink-700' },
  { key: 'finance',    name: '金融',   types: '160000',        color: 'bg-yellow-100 text-yellow-700' },
  { key: 'office',     name: '商务',   types: '120000|170000', color: 'bg-slate-100 text-slate-700' },
] as const;

interface NearbyItem {
  name: string;
  address: string;
  distance: string;
  typecode: string;
  type?: string;
  tel?: string;
  opentime?: string;
  lat?: number;
  lng?: number;
}

interface CapturedPoi {
  name: string;
  category: string;
  address: string;
  distance: string;
  tel?: string;
  lat?: number;
  lng?: number;
}

// ── 周边分析面板 ─────────────────────────────────────────────────────────────
function SurroundingPanel({
  lat,
  lng,
  mapRef,
}: {
  lat: number;
  lng: number;
  mapRef: React.RefObject<MapEngineRef | null>;
}) {
  const [radius, setRadius] = useState(1000);
  const [results, setResults] = useState<Record<string, { total: number; items: NearbyItem[] }>>({});
  const [loading, setLoading] = useState(false);
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const [selectedPoi, setSelectedPoi] = useState<{ catKey: string; index: number } | null>(null);
  const [capturedPois, setCapturedPois] = useState<CapturedPoi[]>([]);
  const [copied, setCopied] = useState(false);
  const [showCaptured, setShowCaptured] = useState(false);

  const load = useCallback(
    async (searchRadius: number) => {
      setLoading(true);
      setResults({});
      setExpandedKey(null);
      setSelectedPoi(null);
      mapRef.current?.clearPoiMarkers();
      try {
        const fetches = NEARBY_CATEGORIES.map((cat) =>
          fetch(
            `/api/geo/nearby?lng=${lng}&lat=${lat}&radius=${searchRadius}&types=${encodeURIComponent(cat.types)}`,
          )
            .then((r) => r.json())
            .then((data: { total: number; items: NearbyItem[] }) => ({ key: cat.key, data }))
            .catch(() => ({ key: cat.key, data: { total: 0, items: [] as NearbyItem[] } })),
        );
        const all = await Promise.all(fetches);
        const mapped: Record<string, { total: number; items: NearbyItem[] }> = {};
        for (const entry of all) mapped[entry.key] = entry.data;
        setResults(mapped);
      } finally {
        setLoading(false);
      }
    },
    [lat, lng, mapRef],
  );

  useEffect(() => {
    load(radius);
  }, [load, radius]);

  const handleExpandCat = useCallback(
    (catKey: string) => {
      const next = expandedKey === catKey ? null : catKey;
      setExpandedKey(next);
      setSelectedPoi(null);
      if (next) {
        const items = results[next]?.items ?? [];
        const pois = items
          .filter((it) => it.lat !== undefined && it.lng !== undefined)
          .map((it) => ({ lat: it.lat!, lng: it.lng!, name: it.name }));
        mapRef.current?.showPoiMarkers(pois);
      } else {
        mapRef.current?.clearPoiMarkers();
      }
    },
    [expandedKey, results, mapRef],
  );

  const handlePoiClick = useCallback(
    (catKey: string, index: number, item: NearbyItem) => {
      const isSame = selectedPoi?.catKey === catKey && selectedPoi?.index === index;
      setSelectedPoi(isSame ? null : { catKey, index });
      if (!isSame && item.lat !== undefined && item.lng !== undefined) {
        mapRef.current?.panTo(item.lat, item.lng);
      }
    },
    [selectedPoi, mapRef],
  );

  const handleCapture = useCallback(
    (catKey: string, item: NearbyItem, e: React.MouseEvent) => {
      e.stopPropagation();
      const cat = NEARBY_CATEGORIES.find((c) => c.key === catKey);
      setCapturedPois((prev) => {
        if (prev.some((p) => p.name === item.name && p.address === item.address)) return prev;
        return [
          ...prev,
          {
            name: item.name,
            category: cat?.name ?? '',
            address: item.address,
            distance: item.distance,
            tel: item.tel || undefined,
            lat: item.lat,
            lng: item.lng,
          },
        ];
      });
    },
    [],
  );

  const handleCopyAll = useCallback(async () => {
    const text = capturedPois
      .map(
        (p, i) =>
          `${i + 1}. 【${p.category}】${p.name}｜${p.distance ? p.distance + 'm' : ''}｜${p.address}${p.tel ? '｜☎' + p.tel : ''}`,
      )
      .join('\n');
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [capturedPois]);

  return (
    <div className="flex-1 overflow-y-auto flex flex-col gap-0 min-h-0">
      {capturedPois.length > 0 && (
        <div className="shrink-0 border-b border-orange-100 bg-orange-50">
          <button
            type="button"
            onClick={() => setShowCaptured((v) => !v)}
            className="w-full flex items-center justify-between px-3 py-2 text-left"
          >
            <span className="text-[11px] font-semibold text-orange-600">
              📌 已抓取 {capturedPois.length} 项
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); void handleCopyAll(); }}
                className="flex items-center gap-1 text-[10px] text-orange-500 hover:text-orange-700 transition-colors"
              >
                {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                {copied ? '已复制' : '复制全部'}
              </button>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setCapturedPois([]); setShowCaptured(false); }}
                className="text-[10px] text-gray-400 hover:text-red-500 transition-colors"
              >
                清空
              </button>
            </div>
          </button>
          {showCaptured && (
            <div className="px-3 pb-2 space-y-1">
              {capturedPois.map((p, i) => (
                <div key={i} className="flex items-start gap-1.5 text-[10px] text-gray-600">
                  <span className="text-orange-400 shrink-0">{i + 1}.</span>
                  <span>
                    <span className="font-medium text-gray-700">{p.name}</span>
                    {p.distance && <span className="text-gray-400 ml-1">{p.distance}m</span>}
                    {p.tel && <span className="text-gray-400 ml-1">· {p.tel}</span>}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto flex flex-col gap-3 p-3">
        <div>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide mb-1.5">搜索半径</p>
          <div className="flex gap-1">
            {([500, 1000, 3000] as const).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRadius(r)}
                className={`flex-1 py-1 rounded text-[10px] font-medium transition-colors ${
                  radius === r
                    ? 'bg-orange-500 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {r >= 1000 ? `${r / 1000}km` : `${r}m`}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8 gap-2 text-gray-400 text-xs">
            <Loader2 className="h-4 w-4 animate-spin" />
            加载中…
          </div>
        ) : (
          <div className="space-y-1">
            {NEARBY_CATEGORIES.map((cat) => {
              const result = results[cat.key];
              const count = result?.total ?? 0;
              const items = result?.items ?? [];
              const isExpanded = expandedKey === cat.key;

              return (
                <div key={cat.key}>
                  <button
                    type="button"
                    onClick={() => handleExpandCat(cat.key)}
                    className={`w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-left transition-colors ${
                      isExpanded
                        ? 'bg-orange-50 border border-orange-200'
                        : 'bg-gray-50 hover:bg-gray-100 border border-transparent'
                    }`}
                  >
                    <span className="text-xs text-gray-700 font-medium">{cat.name}</span>
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${cat.color}`}>
                      {count >= 20 ? '20+' : count}
                    </span>
                  </button>

                  {isExpanded && (
                    <div className="ml-2 mt-0.5 space-y-0.5">
                      {items.length > 0 ? (
                        items.slice(0, 10).map((item, i) => {
                          const isSelected =
                            selectedPoi?.catKey === cat.key && selectedPoi?.index === i;
                          const isAlreadyCaptured = capturedPois.some(
                            (p) => p.name === item.name && p.address === item.address,
                          );
                          return (
                            <div key={i}>
                              <div
                                className={`flex items-center gap-1.5 py-1.5 px-1 rounded-lg cursor-pointer transition-colors group ${
                                  isSelected
                                    ? 'bg-blue-50 border border-blue-200'
                                    : 'hover:bg-gray-50 border border-transparent'
                                }`}
                                onClick={() => handlePoiClick(cat.key, i, item)}
                              >
                                <span className="text-[10px] text-gray-400 shrink-0 w-4 text-right">{i + 1}.</span>
                                <div className="flex-1 min-w-0">
                                  <p className="text-[11px] font-medium text-gray-700 truncate">{item.name}</p>
                                  <div className="flex items-center gap-2 mt-0.5">
                                    {item.distance && (
                                      <span className="text-[9px] text-blue-400 flex items-center gap-0.5">
                                        <Navigation className="h-2.5 w-2.5" />
                                        {item.distance}m
                                      </span>
                                    )}
                                    {item.tel && (
                                      <span className="text-[9px] text-gray-400 flex items-center gap-0.5 truncate">
                                        <Phone className="h-2.5 w-2.5" />
                                        {item.tel}
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <button
                                  type="button"
                                  title="抓取此 POI 信息"
                                  onClick={(e) => handleCapture(cat.key, item, e)}
                                  className={`shrink-0 p-1 rounded transition-colors ${
                                    isAlreadyCaptured
                                      ? 'text-orange-400'
                                      : 'text-gray-300 hover:text-orange-400 opacity-0 group-hover:opacity-100'
                                  }`}
                                >
                                  {isAlreadyCaptured ? (
                                    <Check className="h-3 w-3" />
                                  ) : (
                                    <Copy className="h-3 w-3" />
                                  )}
                                </button>
                              </div>

                              {isSelected && (
                                <div className="ml-5 mr-1 mb-1 p-2 bg-blue-50 rounded-lg border border-blue-100 space-y-1">
                                  {item.address && (
                                    <p className="text-[10px] text-gray-500 leading-relaxed">
                                      📍 {item.address}
                                    </p>
                                  )}
                                  {item.opentime && (
                                    <p className="text-[10px] text-gray-500 flex items-start gap-1">
                                      <Clock className="h-2.5 w-2.5 mt-0.5 shrink-0 text-gray-400" />
                                      {item.opentime}
                                    </p>
                                  )}
                                  {item.lat && item.lng && (
                                    <p className="text-[9px] text-gray-400 font-mono">
                                      {item.lat.toFixed(5)}, {item.lng.toFixed(5)}
                                    </p>
                                  )}
                                  <button
                                    type="button"
                                    onClick={(e) => handleCapture(cat.key, item, e)}
                                    className={`mt-1 w-full flex items-center justify-center gap-1 py-1 rounded text-[10px] font-medium transition-colors ${
                                      isAlreadyCaptured
                                        ? 'bg-orange-100 text-orange-600'
                                        : 'bg-white border border-gray-200 text-gray-600 hover:bg-orange-50 hover:border-orange-300 hover:text-orange-600'
                                    }`}
                                  >
                                    {isAlreadyCaptured ? (
                                      <><Check className="h-3 w-3" /> 已抓取</>
                                    ) : (
                                      <><Copy className="h-3 w-3" /> 抓取此地点</>
                                    )}
                                  </button>
                                </div>
                              )}
                            </div>
                          );
                        })
                      ) : (
                        <p className="text-[10px] text-gray-400 py-1 ml-1">该半径内暂无数据</p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ── 主组件 ───────────────────────────────────────────────────────────────────

export interface GeoCanvasViewProps {
  /** 点击「注入高参」时触发，传递格式化的地理上下文文本 */
  onInjectToAdvisor?: (text: string) => void;
  className?: string;
}

export function GeoCanvasView({ onInjectToAdvisor, className }: GeoCanvasViewProps) {
  const { 
    geoAnchor, openPicker, openViewer, pickerOpen, pickerMode, closePicker,
    geoThesis, thesisLoading, setGeoThesis, setThesisLoading
  } = useGeoStore();
  const [activeWhiteboardTab, setActiveWhiteboardTab] = useState<'l1' | 'g3'>('l1');
  const [markerMenuPos, setMarkerMenuPos] = useState<{x: number, y: number} | null>(null);

  const handleMarkerClick = useCallback((pos: {x: number, y: number}) => {
    setMarkerMenuPos(pos);
  }, []);

  const handleMapInteract = useCallback(() => {
    if (markerMenuPos) setMarkerMenuPos(null);
  }, [markerMenuPos]);


  const handleSimulateAI = async () => {
    if (!geoAnchor) {
      alert("请先锁定地理位置(GeoAnchor)");
      return;
    }
    setThesisLoading(true);
    
    try {
      const data = await api.getGeoThesis({
        lat: geoAnchor.coordinates.lat,
        lng: geoAnchor.coordinates.lng,
        user_id: "demo_user",
        context: geoAnchor
      });
      setGeoThesis(data);
      setActiveWhiteboardTab('g3');
    } catch (err) {
      console.error("生成商业地理推演失败", err);
      alert("生成商业地理推演失败，请检查控制台并在 8000 端口启动后端服务。");
    } finally {
      setThesisLoading(false);
    }
  };

  const mapRef = useRef<MapEngineRef>(null);
  const [mapStyle, setMapStyle] = useState<'normal' | 'satellite'>('normal');
  const [showRoadNet, setShowRoadNet] = useState(false);

  const handleToggleStyle = useCallback(() => {
    const next: 'normal' | 'satellite' = mapStyle === 'normal' ? 'satellite' : 'normal';
    setMapStyle(next);
    mapRef.current?.setStyle(next);
  }, [mapStyle]);

  const handleToggleRoadNet = useCallback(() => {
    const next = !showRoadNet;
    setShowRoadNet(next);
    mapRef.current?.setRoadNet(next);
  }, [showRoadNet]);

  // 构建 L1 场所上下文文本并注入高参
  const handleInjectContext = useCallback(() => {
    if (!geoAnchor || !onInjectToAdvisor) return;
    const { coordinates, administrative } = geoAnchor;
    const text = [
      `【地理工作台 · L1 场所上下文】`,
      ``,
      `📍 地址：${administrative.manual_override ?? administrative.formatted_address}`,
      `🗺 行政区划：${administrative.province}${administrative.city}${administrative.district}${administrative.township ? ' · ' + administrative.township : ''}`,
      `📌 坐标（GCJ-02）：${coordinates.lat.toFixed(6)}, ${coordinates.lng.toFixed(6)}`,
      ``,
      `请基于以上地理位置，生成该地块的 L1 场所要素清单，涵盖：`,
      `1. 自然禀赋（地形 / 气候 / 景观面 / 生态边界）`,
      `2. 在地文化与历史脉络`,
      `3. 市场机会与竞品格局`,
      `4. 交通可达性与客源结构`,
      `5. 约束性条件（政策 / 地质 / 基础设施）`,
      `6. 业态选型建议与经营模型推导`,
    ].join('\n');
    onInjectToAdvisor(text);
  }, [geoAnchor, onInjectToAdvisor]);

  // 未设置锚点
  if (!geoAnchor) {
    return (
      <div className={cn('w-full h-full flex overflow-hidden bg-[#f5f5f7]', className)}>
        <div className="project-workspace-main-column project-workspace-canvas-column relative flex-1 min-w-0 h-full overflow-hidden flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-center px-8">
            <div className="w-14 h-14 rounded-full bg-orange-100 flex items-center justify-center">
              <MapPin className="h-7 w-7 text-orange-400" />
            </div>
            <p className="text-sm font-medium text-gray-700">尚未设置地理坐标锚点</p>
            <p className="text-xs text-gray-400 leading-relaxed">
              地理工作台是 L1 场所内容的生产车间。<br />
              先在地图上锁定项目坐标，才能推导场所要素。
            </p>
            <button
              type="button"
              onClick={openPicker}
              className="mt-2 flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-500 text-white text-sm font-medium hover:bg-orange-600 transition-colors shadow-sm"
            >
              <MapPin className="h-4 w-4" />
              在地图上选址
            </button>
          </div>
        </div>

        <div className="workspace-info-panel project-workspace-middle-column flex cursor-default flex-col border-l border-gray-100 bg-white text-slate-900">
          <div className="border-b border-gray-100 info-panel-px py-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">Information Board</p>
            <h3 className="mt-1 text-base font-bold text-slate-900">信息白板 · 地理</h3>
            <p className="mt-1 text-xs leading-5 text-slate-500">等待坐标锚点后生成 L1 场所信息。</p>
          </div>
          <div className="flex-1 bg-[#f7f8fa]" />
        </div>

        {pickerOpen && (
          <Suspense fallback={null}>
            <GeoPickerModal open={pickerOpen} onClose={closePicker} readOnly={pickerMode === 'view'} />
          </Suspense>
        )}
      </div>
    );
  }

  const { coordinates, administrative } = geoAnchor;

  return (
    <div className={cn('w-full h-full flex overflow-hidden', className)}>
      {/* 左侧：地图区域 */}
      <div className="project-workspace-main-column project-workspace-canvas-column relative flex-1 min-w-0 h-full overflow-hidden">
        <MapEngineClient
          ref={mapRef}
          initialLat={coordinates.lat}
          initialLng={coordinates.lng}
          draggable={false}
          onMarkerClick={handleMarkerClick}
          onMapInteract={handleMapInteract}
        />


        {/* 地块分析指令菜单 */}
        {markerMenuPos && (
          <div
            className="absolute z-50 bg-white rounded-xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] overflow-hidden border border-gray-100 w-60 flex flex-col animate-in fade-in zoom-in duration-200"
            style={{
              left: markerMenuPos.x + 20,
              top: markerMenuPos.y - 60,
            }}
          >
            <div className="px-3 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-medium text-[12px] flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Radar className="w-3.5 h-3.5 text-white/90" />
                <span>地块可交互入口</span>
              </div>
              <button onClick={() => setMarkerMenuPos(null)} className="hover:bg-white/20 p-0.5 rounded transition">
                <X className="w-3.5 h-3.5 text-white"/>
              </button>
            </div>
            <div className="p-1.5 flex flex-col gap-0.5">
              <button
                onClick={() => {
                  setMarkerMenuPos(null);
                  setActiveWhiteboardTab('g3');
                  handleSimulateAI();
                }}
                className="flex flex-col gap-0.5 px-2.5 py-2 text-[12px] text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 rounded transition-colors text-left group"
              >
                <div className="flex items-center gap-1.5 font-semibold">
                  <Radar className="w-3.5 h-3.5 group-hover:text-indigo-600 transition-colors" />
                  启动商业地理推演
                </div>
                <span className="text-[10px] text-gray-400 pl-5">生成 G3-G4 智能分析报告</span>
              </button>
              
              <button
                onClick={() => {
                  setMarkerMenuPos(null);
                  setActiveWhiteboardTab('l1');
                }}
                className="flex flex-col gap-0.5 px-2.5 py-2 text-[12px] text-gray-700 hover:bg-gray-50 rounded transition-colors text-left mt-0.5"
              >
                <div className="flex items-center gap-1.5 font-medium">
                  <Map className="w-3.5 h-3.5 text-emerald-500" />
                  查看基础底盘数据
                </div>
                <span className="text-[10px] text-gray-400 pl-5">展开 L1 地点信息面板</span>
              </button>
              <div className="h-px bg-gray-100 my-1 mx-2"></div>
              
              <button
                onClick={() => {
                  setMarkerMenuPos(null);
                  alert("正在对接等高线地形库... (功能建设中)");
                }}
                className="flex flex-col gap-0.5 px-2.5 py-1.5 text-[12px] text-gray-700 hover:bg-gray-50 rounded transition-colors text-left"
              >
                <div className="flex items-center gap-1.5 font-medium">
                  <Mountain className="w-3.5 h-3.5 text-slate-500" />
                  地形与等高线高程抓取
                </div>
              </button>

              <button
                onClick={() => {
                  setMarkerMenuPos(null);
                  alert("正在计算交通物流覆盖半径... (功能建设中)");
                }}
                className="flex flex-col gap-0.5 px-2.5 py-1.5 text-[12px] text-gray-700 hover:bg-gray-50 rounded transition-colors text-left"
              >
                <div className="flex items-center gap-1.5 font-medium">
                  <Route className="w-3.5 h-3.5 text-blue-500" />
                  交通接驳与物流限制评估
                </div>
              </button>

              <button
                onClick={() => {
                  setMarkerMenuPos(null);
                  alert("正在抓取该维度微气候与光照数据... (功能建设中)");
                }}
                className="flex flex-col gap-0.5 px-2.5 py-1.5 text-[12px] text-gray-700 hover:bg-gray-50 rounded transition-colors text-left"
              >
                <div className="flex items-center gap-1.5 font-medium">
                  <Sun className="w-3.5 h-3.5 text-orange-500" />
                  日照视线与微气候提取
                </div>
              </button>
              
              <button
                onClick={() => {
                  setMarkerMenuPos(null);
                  setActiveWhiteboardTab('l1');
                }}
                className="flex flex-col gap-0.5 px-2.5 py-1.5 text-[12px] text-gray-700 hover:bg-gray-50 rounded transition-colors text-left"
              >
                <div className="flex items-center gap-1.5 font-medium">
                  <Activity className="w-3.5 h-3.5 text-rose-500" />
                  生成竞品分布光谱扫描
                </div>
              </button>

            </div>
          </div>
        )}

        {/* 图层控制浮层（右下，位于修改选址上方） */}
        <div className="absolute bottom-12 right-3 z-10 flex flex-col gap-1.5">
          <button
            type="button"
            onClick={handleToggleStyle}
            title={mapStyle === 'normal' ? '切换卫星图' : '切换标准图'}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium shadow-md backdrop-blur-sm transition-colors ${
              mapStyle === 'satellite'
                ? 'bg-blue-600/90 text-white'
                : 'bg-white/90 text-gray-700 hover:bg-white'
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            {mapStyle === 'satellite' ? '卫星图' : '标准图'}
          </button>
          <button
            type="button"
            onClick={handleToggleRoadNet}
            title={showRoadNet ? '隐藏路网' : '显示路网'}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium shadow-md backdrop-blur-sm transition-colors ${
              showRoadNet
                ? 'bg-blue-600/90 text-white'
                : 'bg-white/90 text-gray-700 hover:bg-white'
            }`}
          >
            <Navigation className="h-3.5 w-3.5" />
            路网
          </button>
        </div>

        {/* 编辑入口（右下） */}
        <button
          type="button"
          onClick={openPicker}
          className="absolute bottom-3 right-3 z-10 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/90 backdrop-blur-sm text-[11px] font-medium text-gray-700 shadow-md hover:bg-white transition-colors"
        >
          <Edit2 className="h-3.5 w-3.5" />
          修改选址
        </button>
      </div>

      {/* 统一右侧面板：信息白板 & 推演 */}
      <div className="workspace-info-panel project-workspace-middle-column flex cursor-default flex-col bg-white border-l border-gray-100 overflow-hidden z-20 shadow-[-4px_0_12px_rgba(0,0,0,0.03)]">
        {/* 面板标题 & Tabs */}
        <div className="shrink-0 bg-white border-b border-gray-200 flex flex-col">
          <div className="grid grid-cols-2 pt-2 info-panel-px text-[11px] font-medium">
            <button 
              onClick={() => setActiveWhiteboardTab('l1')}
              className={cn("flex-1 py-1.5 text-center border-b-2 transition-colors", activeWhiteboardTab === 'l1' ? "border-sky-500 text-sky-600 font-bold" : "border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50")}
            >
              L1 基础底盘
            </button>
            <button 
              onClick={() => setActiveWhiteboardTab('g3')}
              className={cn("flex-1 py-1.5 text-center border-b-2 transition-colors relative", activeWhiteboardTab === 'g3' ? "border-indigo-500 text-indigo-600 font-bold" : "border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50")}
            >
              G3-G4 商业推演
              {geoThesis && activeWhiteboardTab !== 'g3' && <span className="absolute top-1.5 right-2 w-1.5 h-1.5 rounded-full bg-indigo-500 inline-block animate-pulse"></span>}
            </button>
          </div>
        </div>

        {/* Tab 1: L1 基础底盘 */}
        <div className={cn("flex-1 overflow-hidden flex flex-col relative", activeWhiteboardTab === 'l1' ? 'flex' : 'hidden')}>
          {/* 地址信息头部 */}
          <div className="shrink-0 info-panel-px py-3 border-b border-gray-100 space-y-1.5 bg-white">
            <div className="flex items-start gap-1.5">
              <MapPin className="h-3.5 w-3.5 text-emerald-500 mt-0.5 shrink-0" />
              <p className="text-[11px] font-semibold text-gray-800 leading-snug">
                {administrative.manual_override ?? administrative.district}
              </p>
            </div>
            <p className="text-[10px] text-gray-400 leading-relaxed line-clamp-2 pl-5">
              {administrative.formatted_address}
            </p>
            <div className="pl-5 flex flex-wrap gap-x-2 text-[10px] text-gray-400">
              <span>{administrative.province}{administrative.city}</span>
              {administrative.township && <span>· {administrative.township}</span>}
            </div>
            <p className="pl-5 text-[9px] text-gray-300 font-mono">
              {coordinates.lat.toFixed(6)}, {coordinates.lng.toFixed(6)}
            </p>
          </div>

          {/* 周边分析标题 */}
          <div className="shrink-0 info-panel-px py-2 border-b border-gray-100 flex items-center justify-between bg-white">
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">周边分析</span>
            <ChevronRight className="h-3 w-3 text-gray-300" />
          </div>

          <div className="flex-1 overflow-hidden flex flex-col pb-14">
            <SurroundingPanel lat={coordinates.lat} lng={coordinates.lng} mapRef={mapRef} />
          </div>

          {/* 注入高参按钮 */}
          {onInjectToAdvisor && (
            <div className="absolute bottom-0 left-0 w-full shrink-0 p-3 border-t border-gray-100 bg-white/90 backdrop-blur z-10 shadow-[0_-4px_10px_rgba(0,0,0,0.03)]">
              <button
                type="button"
                onClick={handleInjectContext}
                className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg bg-sky-500 text-white text-[11px] font-semibold hover:bg-sky-600 transition-colors shadow-sm"
              >
                <SendHorizontal className="h-3.5 w-3.5" />
                注入高参·生成 L1 场所清单
              </button>
            </div>
          )}
        </div>

        {/* Tab 2: G3-G4 商业智能 */}
        <div className={cn("flex-1 overflow-y-auto info-panel-px py-4 space-y-4 bg-[#f4f5f8] leading-loose relative", activeWhiteboardTab === 'g3' ? 'block' : 'hidden')}>
            {!geoThesis && !thesisLoading && (
              <div className="flex flex-col items-center justify-center text-center h-full gap-3 opacity-60 pb-10">
                <Layers className="w-8 h-8 text-indigo-400" />
                <p className="text-[11px] text-gray-500 font-medium">点击右上角「运行推演」<br/>基于当前地理底盘生成<br/>商业套利分析及建筑指令</p>
              </div>
            )}
            
            {thesisLoading && !geoThesis && (
              <div className="flex flex-col gap-4">
                <GeoScorePanel scores={null as any} loading={true} />
                <GeoThesisCard thesis={null as any} loading={true} />
              </div>
            )}
            
            {geoThesis && (
               <div className="flex flex-col gap-4 animate-in fade-in slide-in-from-bottom-2 duration-500 pb-10">
                <GeoScorePanel scores={geoThesis.scores} loading={thesisLoading} />
                <GeoThesisCard thesis={geoThesis} loading={thesisLoading} />
               </div>
            )}
        </div>
      </div>

      {/* 选址弹窗 */}
      {pickerOpen && (
        <Suspense fallback={null}>
          <GeoPickerModal open={pickerOpen} onClose={closePicker} readOnly={pickerMode === 'view'} />
        </Suspense>
      )}
    </div>
  );
}
