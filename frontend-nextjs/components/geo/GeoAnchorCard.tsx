'use client';

/**
 * GeoAnchorCard — L1 地理锚点信息卡片
 *
 * 两种状态：
 *  • 未设置：橙色警告提示 + 「在地图上选址」按钮
 *  • 已锁定：静态地图缩略图（点击即开查看弹窗）+ 坐标/行政区划信息
 */
import React, { Suspense, lazy } from 'react';
import { MapPin, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useGeoStore } from '@/store/useGeoStore';

// GeoPickerModal 纯客户端，动态导入避免 SSR 错误
const GeoPickerModal = lazy(() =>
  import('./GeoPickerModal').then((m) => ({ default: m.GeoPickerModal })),
);

export function GeoAnchorCard({ className, onOpenGeoWorkspace }: { className?: string; onOpenGeoWorkspace?: () => void }) {
  const { geoAnchor, pickerOpen, pickerMode, openPicker, openViewer, closePicker } = useGeoStore();

  const hasAnchor = geoAnchor !== null;
  const [mapImageLoaded, setMapImageLoaded] = React.useState(false);
  const [mapImageFailed, setMapImageFailed] = React.useState(false);
  const mapThumbSrc = hasAnchor
    ? `/api/geo/staticmap?lng=${geoAnchor!.coordinates.lng}&lat=${geoAnchor!.coordinates.lat}&zoom=14&w=480&h=480`
    : '';

  React.useEffect(() => {
    setMapImageLoaded(false);
    setMapImageFailed(false);
  }, [mapThumbSrc]);

  React.useEffect(() => {
    if (!mapThumbSrc || mapImageLoaded || mapImageFailed) return;
    const timer = window.setTimeout(() => {
      setMapImageFailed(true);
    }, 5200);
    return () => window.clearTimeout(timer);
  }, [mapImageFailed, mapImageLoaded, mapThumbSrc]);

  const handleMapThumbClick = () => {
    if (onOpenGeoWorkspace) {
      onOpenGeoWorkspace();
    } else {
      openViewer();
    }
  };

  return (
    <>
      {/* 信息卡片 */}
      <div
        className={cn(
          'rounded-xl border bg-white shadow-sm p-4 space-y-3 text-sm',
          hasAnchor ? 'border-emerald-200' : 'border-orange-200',
          className,
        )}
      >
        {/* 标题行 */}
        <div className="flex items-center gap-2">
          <MapPin
            className={cn('h-4 w-4 shrink-0', hasAnchor ? 'text-emerald-500' : 'text-orange-400')}
          />
          <span className="font-medium text-gray-700">地理坐标锚点</span>

          {hasAnchor ? (
            <CheckCircle2 className="ml-auto h-4 w-4 text-emerald-500" />
          ) : (
            <AlertTriangle className="ml-auto h-4 w-4 text-orange-400" />
          )}
        </div>

        {/* 内容区 */}
        {hasAnchor ? (
          <>
            {/* 静态地图缩略图 — 点击打开查看弹窗 */}
            <div
              role="button"
              tabIndex={0}
              onClick={handleMapThumbClick}
              onKeyDown={(e) => e.key === 'Enter' && handleMapThumbClick()}
              className="relative w-full aspect-square cursor-pointer overflow-hidden rounded-lg group bg-slate-50 border border-slate-100"
            >
              {!mapImageLoaded && !mapImageFailed && (
                <div className="absolute inset-0 bg-[linear-gradient(90deg,#f8fafc_0%,#eef2f7_48%,#f8fafc_100%)] animate-pulse" />
              )}
              {mapImageFailed ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-50 text-slate-500">
                  <div className="relative h-24 w-24 rounded-full border border-slate-200 bg-white shadow-sm">
                    <div className="absolute left-1/2 top-0 h-full w-px bg-slate-100" />
                    <div className="absolute left-0 top-1/2 h-px w-full bg-slate-100" />
                    <MapPin className="absolute left-1/2 top-1/2 h-7 w-7 -translate-x-1/2 -translate-y-1/2 text-orange-500" />
                  </div>
                  <span className="mt-3 text-xs font-medium text-slate-700">地图预览加载失败</span>
                  <span className="mt-1 font-mono text-[10px] text-slate-400">
                    {geoAnchor!.coordinates.lat.toFixed(4)}, {geoAnchor!.coordinates.lng.toFixed(4)}
                  </span>
                </div>
              ) : (
                <img
                  src={mapThumbSrc}
                  alt="位置预览"
                  className={cn('w-full h-full object-cover transition-opacity duration-200', mapImageLoaded ? 'opacity-100' : 'opacity-0')}
                  loading="lazy"
                  onLoad={() => setMapImageLoaded(true)}
                  onError={() => {
                    setMapImageLoaded(false);
                    setMapImageFailed(true);
                  }}
                />
              )}
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/25 transition-colors flex items-center justify-center">
                <span className="opacity-0 group-hover:opacity-100 transition-opacity bg-black/65 text-white text-[10px] rounded-full px-2.5 py-1">
                  点击查看地图
                </span>
              </div>
            </div>
            <LockedState />
          </>
        ) : (
          <UnsetState />
        )}

        {/* 操作按钮 — 仅未设置时显示 */}
        {!hasAnchor && (
          <button
            type="button"
            onClick={openPicker}
            className="w-full flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors bg-orange-50 text-orange-600 hover:bg-orange-100 border border-orange-200"
          >
            <MapPin className="h-3 w-3" />
            在地图上选址
          </button>
        )}
      </div>

      {/* 地图选点弹窗（懒加载，避免 SSR） */}
      {pickerOpen && (
        <Suspense fallback={null}>
          <GeoPickerModal open={pickerOpen} onClose={closePicker} readOnly={pickerMode === 'view'} />
        </Suspense>
      )}
    </>
  );
}

// ─── 已锁定态 ───────────────────────────────────────────────────────────────

function LockedState() {
  const { geoAnchor } = useGeoStore();
  if (!geoAnchor) return null;

  const { coordinates, administrative } = geoAnchor;

  return (
    <div className="space-y-1.5 text-xs text-gray-600">
      <div className="flex items-center gap-1.5">
        <span className="text-gray-400 w-10 shrink-0">地址</span>
        <span className="font-medium text-gray-800 truncate" title={administrative.formatted_address}>
          {administrative.manual_override ?? administrative.formatted_address}
        </span>
      </div>

      {administrative.township && (
        <div className="flex items-center gap-1.5">
          <span className="text-gray-400 w-10 shrink-0">镇乡</span>
          <span>{administrative.township}</span>
        </div>
      )}

      <div className="flex items-center gap-1.5">
        <span className="text-gray-400 w-10 shrink-0">坐标</span>
        <code className="font-mono text-[10px] text-gray-500">
          {coordinates.lat.toFixed(6)}, {coordinates.lng.toFixed(6)}
        </code>
      </div>

      {coordinates.elevation !== undefined && (
        <div className="flex items-center gap-1.5">
          <span className="text-gray-400 w-10 shrink-0">海拔</span>
          <span>{coordinates.elevation} m</span>
        </div>
      )}

      {/* 来源徽章 */}
      <div className="pt-0.5 flex gap-1.5">
        <span className="inline-flex items-center rounded-full bg-emerald-50 text-emerald-600 border border-emerald-100 px-2 py-0.5 text-[10px]">
          GCJ-02
        </span>
        <span className="inline-flex items-center rounded-full bg-sky-50 text-sky-600 border border-sky-100 px-2 py-0.5 text-[10px]">
          {geoAnchor.meta.source === 'map_pick' ? '地图选点' : '手动输入'}
        </span>
      </div>
    </div>
  );
}

// ─── 未设置态 ───────────────────────────────────────────────────────────────

function UnsetState() {
  return (
    <p className="text-xs text-orange-500 leading-relaxed">
      尚未锁定项目坐标。锚定后 AI 将自动触发气候分析、竞品召回和历史案例匹配。
    </p>
  );
}
