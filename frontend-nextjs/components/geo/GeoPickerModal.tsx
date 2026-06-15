'use client';

/**
 * GeoPickerModal — 全屏地图选点弹窗
 *
 * 布局：
 *  ┌─────────────────────────────┬──────────────────┐
 *  │  地图（MapEngineClient）     │   信息面板        │
 *  │  搜索框覆盖在地图左上角       │  经纬度 / 地址    │
 *  │  拖拽中心即是选点坐标         │  自定义地名       │
 *  │                             │  [锁定坐标]按钮   │
 *  └─────────────────────────────┴──────────────────┘
 *
 * 该组件只应通过 next/dynamic + ssr:false 加载！
 * 在 GeoAnchorCard 中已通过 React.lazy 保证客户端加载。
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, Loader2, MapPin, Lock, RefreshCw, Copy, Check, Phone, Clock, Navigation } from 'lucide-react';
import { MapEngineClient } from './MapEngineClient';
import type { MapEngineRef } from './MapEngineClient';
import { GeoPickerSkeleton } from './GeoPickerSkeleton';
import { useReverseGeocode } from './hooks/useReverseGeocode';
import { useGeoStore } from '@/store/useGeoStore';
import type { GeoAnchor } from '@/types/geo';
import { cn } from '@/lib/utils';

// ── 周边分析：分类配置 ──────────────────────────────────────────────────────
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

  // 展开分类 → 把该类 POI 打点到地图
  const handleExpandCat = useCallback(
    (catKey: string) => {
      const next = expandedKey === catKey ? null : catKey;
      setExpandedKey(next);
      setSelectedPoi(null);
      if (next) {
        const items = results[next]?.items ?? [];
        const pois = items
          .filter((it) => it.lat !== undefined && it.lng !== undefined)
          .map((it) => ({ lat: it.lat!, lng: it.lng!, name: it.name as string }));
        mapRef.current?.showPoiMarkers(pois);
      } else {
        mapRef.current?.clearPoiMarkers();
      }
    },
    [expandedKey, results, mapRef],
  );

  // 点击某个 POI → 地图飞过去 + 展开详情
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

  // 抓取 POI
  const handleCapture = useCallback(
    (catKey: string, item: NearbyItem, e: React.MouseEvent) => {
      e.stopPropagation();
      const cat = NEARBY_CATEGORIES.find((c) => c.key === catKey);
      setCapturedPois((prev) => {
        if (prev.some((p) => p.name === item.name && p.address === item.address)) return prev;
        return [
          ...prev,
          {
            name: item.name as string,
            category: cat?.name ?? '',
            address: item.address as string,
            distance: item.distance as string,
            tel: item.tel || undefined,
            lat: item.lat,
            lng: item.lng,
          },
        ];
      });
    },
    [],
  );

  // 复制抓取清单
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
      {/* 已抓取条目栏 */}
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
                onClick={(e) => { e.stopPropagation(); handleCopyAll(); }}
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
        {/* 搜索半径 */}
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

        {/* 分类列表 */}
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
                  {/* 分类行 */}
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

                  {/* POI 列表 */}
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
                              {/* POI 行 */}
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
                                  <p className="text-[11px] font-medium text-gray-700 truncate">{item.name as string}</p>
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
                                        {item.tel as string}
                                      </span>
                                    )}
                                  </div>
                                </div>
                                {/* 抓取按钮 */}
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

                              {/* 详情展开 */}
                              {isSelected && (
                                <div className="ml-5 mr-1 mb-1 p-2 bg-blue-50 rounded-lg border border-blue-100 space-y-1">
                                  {item.address && (
                                    <p className="text-[10px] text-gray-500 leading-relaxed">
                                      📍 {item.address as string}
                                    </p>
                                  )}
                                  {item.opentime && (
                                    <p className="text-[10px] text-gray-500 flex items-start gap-1">
                                      <Clock className="h-2.5 w-2.5 mt-0.5 shrink-0 text-gray-400" />
                                      {item.opentime as string}
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

// ───────────────────────────────────────────────────────────────────────────

interface GeoPickerModalProps {
  open: boolean;
  onClose: () => void;
  /** 只读查看模式：不可拖动大头针，不显示锁定按鈕 */
  readOnly?: boolean;
}

export function GeoPickerModal({ open, onClose, readOnly = false }: GeoPickerModalProps) {
  // 当前地图中心坐标（由 MapEngineClient 实时上报）
  const [center, setCenter] = useState<{ lat: number; lng: number } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [customName, setCustomName] = useState('');
  const [mapReady, setMapReady] = useState(false);
  const [isSatellite, setIsSatellite] = useState(false);
  const [showRoadNet, setShowRoadNet] = useState(false);
  const [showLayerPanel, setShowLayerPanel] = useState(false);
  const [activeTab, setActiveTab] = useState<'location' | 'nearby'>('location');
  const [showIndoor, setShowIndoor] = useState(false);

  const { setGeoAnchor, geoAnchor, openPicker } = useGeoStore();

  // 地图引擎 ref，用于程序化移动大头针（搜索功能使用）
  const mapRef = useRef<MapEngineRef>(null);

  // 逆地理编码（防抖 600ms）
  const { data: reverseData, loading: reverseLoading } = useReverseGeocode(
    center?.lat ?? null,
    center?.lng ?? null,
    600,
  );

  const handlePositionChange = useCallback((lat: number, lng: number) => {
    setCenter({ lat, lng });
    if (!mapReady) setMapReady(true);
  }, [mapReady]);

  // POI 搜索 → 通过 ref 移动大头针
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await fetch(`/api/geo/search?q=${encodeURIComponent(searchQuery)}`);
      const data = await res.json();
      if (data.results?.[0]) {
        const { lat, lng } = data.results[0] as { lat: number; lng: number };
        // 移动地图大头针到搜索结果，并同步 center 状态
        mapRef.current?.moveTo(lat, lng);
        setCenter({ lat, lng });
      }
    } finally {
      setSearching(false);
    }
  };

  // 锁定坐标
  const handleLock = async () => {
    if (!center) return;

    const admin = reverseData ?? {
      country: '中国',
      province: '',
      city: '',
      district: '',
      formatted_address: `${center.lat.toFixed(6)}, ${center.lng.toFixed(6)}`,
    };

    // 异步获取海拔
    let elevation: number | undefined;
    try {
      const elevRes = await fetch(
        `/api/geo/elevation?lat=${center.lat}&lng=${center.lng}`,
      );
      if (elevRes.ok) {
        const elevData = await elevRes.json();
        elevation = elevData.elevation;
      }
    } catch {
      // 海拔可选，失败不阻断
    }

    const anchor: GeoAnchor = {
      coordinates: { lat: center.lat, lng: center.lng, elevation },
      administrative: {
        ...admin,
        manual_override: customName.trim() || undefined,
      },
      geo_features: {},
      commercial_context: {},
      meta: {
        set_at: new Date().toISOString(),
        source: 'map_pick',
        confidence: 'confirmed',
      },
    };

    setGeoAnchor(anchor);
    onClose();
  };

  // 用 Portal 挂载到 body，绕过父容器 CSS transform 对 fixed 定位的干扰
  if (!open || typeof document === 'undefined') return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="relative w-full h-full shadow-2xl bg-white flex overflow-hidden">

        {/* 关闭按钮 */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3 right-3 z-20 rounded-full p-1.5 bg-white/80 hover:bg-white shadow text-gray-500 hover:text-gray-800 transition-colors"
          aria-label="关闭"
        >
          <X className="h-4 w-4" />
        </button>

        {/* ── 左侧地图区 ── */}
        <div className="relative flex-1 bg-gray-200">
          {/* 搜索框 - 只在编辑模式显示 */}
          {!readOnly && (
          <div className="absolute top-3 left-3 z-10 flex gap-2 w-72">
            <input
              type="text"
              placeholder="搜索地点…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="flex-1 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 shadow focus:outline-none focus:ring-2 focus:ring-orange-300"
            />
            <button
              type="button"
              onClick={handleSearch}
              disabled={searching}
              className="rounded-lg bg-orange-500 text-white px-3 py-2 text-sm hover:bg-orange-600 disabled:opacity-60 transition-colors shadow"
            >
              {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : '搜索'}
            </button>
          </div>
          )}

          {/* 图层面板入口按鈕 */}
          <button
            type="button"
            onClick={() => setShowLayerPanel(v => !v)}
            className="absolute top-3 right-3 z-20 flex items-center gap-1.5 rounded-lg bg-white/95 hover:bg-white border border-gray-200 px-2.5 py-1.5 text-xs font-medium text-gray-700 shadow transition-colors"
          >
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>
            </svg>
            图层
          </button>

          {/* 图层面板 */}
          {showLayerPanel && (
            <div className="absolute top-11 right-3 z-20 bg-white rounded-xl shadow-xl border border-gray-100 p-3 w-44 space-y-2">
              {/* 底图 */}
              <p className="text-[10px] text-gray-400 font-medium uppercase tracking-wide">底图</p>
              <button
                type="button"
                onClick={() => {
                  setIsSatellite(false);
                  mapRef.current?.setStyle('normal');
                }}
                className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg border transition-colors text-left ${
                  !isSatellite ? 'border-orange-400 bg-orange-50' : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                <div className="w-6 h-6 rounded shrink-0 overflow-hidden">
                  <svg viewBox="0 0 24 24" className="w-full h-full">
                    <rect width="24" height="24" fill="#e8f4e8"/>
                    <rect x="0" y="9" width="24" height="3" fill="#bbb" opacity=".7"/>
                    <rect x="0" y="15" width="24" height="2" fill="#bbb" opacity=".5"/>
                    <rect x="8" y="0" width="3" height="24" fill="#bbb" opacity=".7"/>
                    <rect x="15" y="0" width="2" height="24" fill="#bbb" opacity=".5"/>
                  </svg>
                </div>
                <span className="text-xs text-gray-700">标准地图</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsSatellite(true);
                  mapRef.current?.setStyle('satellite');
                }}
                className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg border transition-colors text-left ${
                  isSatellite ? 'border-orange-400 bg-orange-50' : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                <div className="w-6 h-6 rounded shrink-0 overflow-hidden">
                  <svg viewBox="0 0 24 24" className="w-full h-full">
                    <rect width="24" height="24" fill="#2d4a2d"/>
                    <rect x="0" y="0" width="9" height="9" fill="#1a3a1a"/>
                    <rect x="11" y="3" width="8" height="6" fill="#3d5a3d"/>
                    <rect x="3" y="12" width="12" height="8" fill="#253a25"/>
                    <rect x="17" y="11" width="6" height="10" fill="#1e321e"/>
                  </svg>
                </div>
                <span className="text-xs text-gray-700">卫星地图</span>
              </button>

              {/* 分隔线 */}
              <div className="border-t border-gray-100 pt-2">
                <p className="text-[10px] text-gray-400 font-medium uppercase tracking-wide mb-2">叠加图层</p>

                {/* 路网 */}
                <button
                  type="button"
                  onClick={() => {
                    const next = !showRoadNet;
                    setShowRoadNet(next);
                    mapRef.current?.setRoadNet(next);
                  }}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border mb-1.5 transition-colors ${
                    showRoadNet ? 'border-orange-400 bg-orange-50' : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded shrink-0 overflow-hidden">
                      <svg viewBox="0 0 24 24" className="w-full h-full">
                        <rect width="24" height="24" fill="#e8f4e8"/>
                        <path d="M0 12 Q6 10 12 12 Q18 14 24 12" stroke="#f97316" strokeWidth="2" fill="none"/>
                        <path d="M8 0 Q9 6 8 12 Q7 18 8 24" stroke="#f97316" strokeWidth="1.5" fill="none"/>
                      </svg>
                    </div>
                    <span className="text-xs text-gray-700">路网</span>
                  </div>
                  <span className={`text-[10px] font-medium ${showRoadNet ? 'text-orange-500' : 'text-gray-400'}`}>
                    {showRoadNet ? '开' : '关'}
                  </span>
                </button>

                {/* 室内地图 */}
                <button
                  type="button"
                  onClick={() => {
                    const next = !showIndoor;
                    setShowIndoor(next);
                    mapRef.current?.toggleIndoorMap(next);
                  }}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border transition-colors ${
                    showIndoor ? 'border-orange-400 bg-orange-50' : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded shrink-0 overflow-hidden flex items-center justify-center bg-blue-50">
                      <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="#3b82f6" strokeWidth="1.5">
                        <rect x="3" y="3" width="18" height="18" rx="1"/>
                        <path d="M3 9h18M3 15h18M9 3v18"/>
                      </svg>
                    </div>
                    <span className="text-xs text-gray-700">室内图</span>
                  </div>
                  <span className={`text-[10px] font-medium ${showIndoor ? 'text-orange-500' : 'text-gray-400'}`}>
                    {showIndoor ? '开' : '关'}
                  </span>
                </button>
                <p className="text-[9px] text-gray-400 mt-1 pl-1">室内图需缩放至 17 级以上</p>
              </div>

              {/* 关闭面板 */}
              <button
                type="button"
                onClick={() => setShowLayerPanel(false)}
                className="w-full text-center text-[10px] text-gray-400 hover:text-gray-600 py-1"
              >
                收起
              </button>
            </div>
          )}

          {/* 地图容器 */}
          {!mapReady && <GeoPickerSkeleton />}
          <MapEngineClient
            ref={mapRef}
            initialLat={geoAnchor?.coordinates.lat ?? 31.3}
            initialLng={geoAnchor?.coordinates.lng ?? 110.0}
            onPositionChange={handlePositionChange}
            draggable={!readOnly}
          />
        </div>

        {/* ── 右侧信息面板 ── */}
        <div className="w-64 shrink-0 bg-white border-l border-gray-100 flex flex-col overflow-hidden">
          {/* Tab 导航 */}
          <div className="flex shrink-0 border-b border-gray-100">
            <button
              type="button"
              onClick={() => setActiveTab('location')}
              className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
                activeTab === 'location'
                  ? 'text-orange-500 border-b-2 border-orange-400 -mb-px'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              📍 位置
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('nearby')}
              className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
                activeTab === 'nearby'
                  ? 'text-orange-500 border-b-2 border-orange-400 -mb-px'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              🔍 周边
            </button>
          </div>

          {/* Tab：位置 */}
          {activeTab === 'location' && (
            <div className="flex-1 overflow-y-auto flex flex-col p-4 gap-4">
              <div>
                <h3 className="font-semibold text-gray-800 text-sm flex items-center gap-1.5">
                  <MapPin className="h-4 w-4 text-orange-400" />
                  {readOnly ? '已锁定位置' : '坐标确认'}
                </h3>
              </div>

              {/* 坐标 */}
              <div className="space-y-1">
                <p className="text-[10px] text-gray-400 uppercase tracking-wide">GCJ-02 坐标</p>
                {center ? (
                  <p className="font-mono text-xs text-gray-700">
                    {center.lat.toFixed(6)}, {center.lng.toFixed(6)}
                  </p>
                ) : (
                  <p className="text-xs text-gray-400 italic">等待地图初始化…</p>
                )}
              </div>

              {/* 行政区划 */}
              <div className="space-y-1">
                <p className="text-[10px] text-gray-400 uppercase tracking-wide">行政区划</p>
                {reverseLoading ? (
                  <div className="flex items-center gap-1.5 text-xs text-gray-400">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    解析中…
                  </div>
                ) : reverseData ? (
                  <div className="space-y-0.5 text-xs text-gray-600">
                    <p>{reverseData.province} {reverseData.city}</p>
                    <p>{reverseData.district}{reverseData.township ? ` · ${reverseData.township}` : ''}</p>
                    <p className="text-[10px] text-gray-400 truncate" title={reverseData.formatted_address}>
                      {reverseData.formatted_address}
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-gray-400 italic">{readOnly ? '未有地址信息' : '拖拽地图后自动解析'}</p>
                )}
              </div>

              {/* 自定义地名 - 只在编辑模式显示 */}
              {!readOnly && (
              <div className="space-y-1">
                <p className="text-[10px] text-gray-400 uppercase tracking-wide">自定义地名（可选）</p>
                <input
                  type="text"
                  placeholder="如：七里坪项目地块"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  maxLength={40}
                  className="w-full rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-orange-300"
                />
                <p className="text-[10px] text-gray-400">荒野/未命名地块可在此覆写地址显示</p>
              </div>
              )}

              {/* 锁定按钮 / 关闭按钮 */}
              <div className="mt-auto">
                {readOnly ? (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={openPicker}
                      className="flex-1 flex items-center justify-center gap-1 rounded-lg px-3 py-2 text-xs font-medium bg-orange-500 text-white hover:bg-orange-600 shadow transition-all"
                    >
                      <RefreshCw className="h-3 w-3" />
                      重新选址
                    </button>
                    <button
                      type="button"
                      onClick={onClose}
                      className="flex-1 flex items-center justify-center rounded-lg px-3 py-2 text-xs font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 transition-all"
                    >
                      关闭
                    </button>
                  </div>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={handleLock}
                      disabled={!center}
                      className={cn(
                        'w-full flex items-center justify-center gap-1.5 rounded-lg px-3 py-2',
                        'text-xs font-medium transition-all',
                        center
                          ? 'bg-orange-500 text-white hover:bg-orange-600 shadow hover:shadow-md'
                          : 'bg-gray-100 text-gray-400 cursor-not-allowed',
                      )}
                    >
                      <Lock className="h-3.5 w-3.5" />
                      锁定坐标
                    </button>

                    {center && (
                      <p className="text-center text-[10px] text-gray-400 mt-2">
                        锁定后将写入 L1 项目底盘
                      </p>
                    )}
                  </>
                )}
              </div>
            </div>
          )}

          {/* Tab：周边分析 */}
          {activeTab === 'nearby' && center && (
            <SurroundingPanel lat={center.lat} lng={center.lng} mapRef={mapRef} />
          )}
          {activeTab === 'nearby' && !center && (
            <div className="flex-1 flex items-center justify-center p-4 text-xs text-gray-400 text-center">
              等待地图加载…
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
