'use client';

/**
 * MapEngineClient — 高德地图实例（纯客户端，可拖动大头针模式）
 *
 * 交互逻辑：
 *  • 橙色大头针可直接拖拽到精确位置
 *  • 地图仍可平移（用于导航浏览）
 *  • 拖拽结束后通过 onPositionChange 上报坐标
 *  • forwardRef 暴露 moveTo(lat, lng) 供搜索功能程序化移动大头针
 */
import { useEffect, useRef, forwardRef, useImperativeHandle } from 'react';

export interface MapEngineRef {
  moveTo: (lat: number, lng: number) => void;
  /** 仅平移地图视野，不移动大头针 */
  panTo: (lat: number, lng: number) => void;
  /** 显示一批 POI 小圆点标记（蓝色），自动清除上一批 */
  showPoiMarkers: (pois: Array<{ lat: number; lng: number; name: string }>) => void;
  /** 清除所有 POI 标记 */
  clearPoiMarkers: () => void;
  /** 切换底图：'normal' = 标准图，'satellite' = 卫星图 */
  setStyle: (style: 'normal' | 'satellite') => void;
  /** 切换路网图层显示 */
  setRoadNet: (show: boolean) => void;
  /** 切换室内地图（需放大至 17 级以上，且建筑有室内数据） */
  toggleIndoorMap: (show: boolean) => void;
}

interface MapEngineProps {
  initialLat?: number;
  initialLng?: number;
  onPositionChange?: (lat: number, lng: number) => void;
  /** 是否允许拖动大头针，默认 true */
  draggable?: boolean;
  onMarkerClick?: (e: any) => void;
  onMapInteract?: () => void;
}

declare global {
  interface Window {
    AMap?: any;
    _amapLoading?: boolean;
    _amapReady?: boolean;
  }
}

/** 异步加载高德 JS API，保证只加载一次 */
function loadAmapScript(key: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window._amapReady) { resolve(); return; }
    if (window._amapLoading) {
      const check = setInterval(() => {
        if (window._amapReady) { clearInterval(check); resolve(); }
      }, 100);
      return;
    }

    window._amapLoading = true;
    const script = document.createElement('script');
    script.type = 'text/javascript';
    // 高德 JS API 2.0 loader
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${key}&plugin=AMap.Geocoder,AMap.PlaceSearch,AMap.IndoorMap`;
    script.onload = () => {
      window._amapReady = true;
      window._amapLoading = false;
      resolve();
    };
    script.onerror = () => {
      window._amapLoading = false;
      reject(new Error('高德地图脚本加载失败'));
    };
    document.head.appendChild(script);
  });
}

export const MapEngineClient = forwardRef<MapEngineRef, MapEngineProps>(
  ({  initialLat = 31.3, initialLng = 110.0, onPositionChange, draggable = true , onMarkerClick, onMapInteract }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const mapRef = useRef<any>(null);
    const markerRef = useRef<any>(null);
    const satelliteLayerRef = useRef<any>(null);
    const roadNetLayerRef = useRef<any>(null);
    const indoorMapRef = useRef<any>(null);
    // POI 标记数组
    const poiMarkersRef = useRef<any[]>([]);
    // 用 ref 存 callback，避免 effect 重新初始化
    const callbackRef = useRef(onPositionChange);
    callbackRef.current = onPositionChange;

    // 暴露程序化移动方法 + 切换底图样式
    useImperativeHandle(ref, () => ({
      panTo: (lat: number, lng: number) => {
        if (!mapRef.current) return;
        mapRef.current.setCenter([lng, lat], false);
      },
      showPoiMarkers: (pois: Array<{ lat: number; lng: number; name: string }>) => {
        if (!mapRef.current || !window.AMap) return;
        // 清除旧标记
        poiMarkersRef.current.forEach((m) => mapRef.current?.remove(m));
        poiMarkersRef.current = [];
        pois.forEach((poi) => {
          const m = new window.AMap.Marker({
            position: [poi.lng, poi.lat],
            content: `<div title="${poi.name}" style="width:10px;height:10px;background:#3b82f6;border:2px solid white;border-radius:50%;box-shadow:0 1px 4px rgba(0,0,0,.4);cursor:pointer;"></div>`,
            offset: new window.AMap.Pixel(-5, -5),
            zIndex: 80,
          });
          mapRef.current.add(m);
          poiMarkersRef.current.push(m);
        });
      },
      clearPoiMarkers: () => {
        poiMarkersRef.current.forEach((m) => mapRef.current?.remove(m));
        poiMarkersRef.current = [];
      },
      moveTo: (lat: number, lng: number) => {
        if (!mapRef.current || !markerRef.current) return;
        const lnglat = [lng, lat];
        mapRef.current.setCenter(lnglat, false);
        markerRef.current.setPosition(lnglat);
        callbackRef.current?.(lat, lng);
      },
      setStyle: (style: 'normal' | 'satellite') => {
        if (!mapRef.current) return;
        if (style === 'satellite') {
          // 不修改 mapStyle（避免与图层冲突），直接叠加卫星瓦片层
          if (!satelliteLayerRef.current) {
            satelliteLayerRef.current = new window.AMap.TileLayer.Satellite({
              zooms: [3, 18],
              zIndex: 2,
            });
          }
          mapRef.current.add(satelliteLayerRef.current);
        } else {
          if (satelliteLayerRef.current) {
            mapRef.current.remove(satelliteLayerRef.current);
          }
          // 恢复 light 样式
          mapRef.current.setMapStyle('amap://styles/light');
        }
      },
      setRoadNet: (show: boolean) => {
        if (!mapRef.current) return;
        if (show) {
          if (!roadNetLayerRef.current) {
            roadNetLayerRef.current = new window.AMap.TileLayer.RoadNet();
          }
          mapRef.current.add(roadNetLayerRef.current);
        } else {
          if (roadNetLayerRef.current) {
            mapRef.current.remove(roadNetLayerRef.current);
          }
        }
      },
      toggleIndoorMap: (show: boolean) => {
        if (!mapRef.current || !window.AMap?.IndoorMap) return;
        if (show) {
          if (!indoorMapRef.current) {
            indoorMapRef.current = new window.AMap.IndoorMap({ zIndex: 9999 });
          }
          mapRef.current.add(indoorMapRef.current);
        } else {
          if (indoorMapRef.current) {
            mapRef.current.remove(indoorMapRef.current);
          }
        }
      },
    }));

    useEffect(() => {
      const key = process.env.NEXT_PUBLIC_AMAP_WEB_KEY;
      if (!key) {
        console.error('[MapEngineClient] NEXT_PUBLIC_AMAP_WEB_KEY 未配置');
        return;
      }

      let isMounted = true;

      loadAmapScript(key)
        .then(() => {
          if (!isMounted || !containerRef.current || !window.AMap) return;

          const map = new window.AMap.Map(containerRef.current, {
            zoom: 14,
            center: [initialLng, initialLat],
            mapStyle: 'amap://styles/light',
          });
          mapRef.current = map;
          map.on('click', () => { if(onMapInteract) onMapInteract(); });
          map.on('dragstart', () => { if(onMapInteract) onMapInteract(); });
          map.on('zoomstart', () => { if(onMapInteract) onMapInteract(); });


          // 橙色大头针（draggable prop 控制是否可拖拽）
          const marker = new window.AMap.Marker({
            position: [initialLng, initialLat],
            draggable: draggable,
            cursor: draggable ? 'grab' : 'default',
            content: `
              <div style="display:flex;flex-direction:column;align-items:center;filter:drop-shadow(0 3px 6px rgba(0,0,0,.35));">
                <div style="width:24px;height:24px;background:#f97316;border-radius:50% 50% 50% 0;transform:rotate(-45deg);border:3px solid white;"></div>
                <div style="width:6px;height:6px;background:#f97316;border-radius:50%;margin-top:1px;opacity:.8;"></div>
              </div>
            `,
            offset: new window.AMap.Pixel(-12, -30),
          });
          marker.setMap(map);
          marker.on('click', (e: any) => {
            if (onMarkerClick) {
              const pixel = map.lngLatToContainer(marker.getPosition());
              onMarkerClick({ x: pixel.x, y: pixel.y });
            }
          });
          markerRef.current = marker;

          // 初始上报
          callbackRef.current?.(initialLat, initialLng);

          if (draggable) {
            // 拖拽中：更改光标样式
            marker.on('dragging', () => {
              if (!isMounted) return;
              marker.setCursor('grabbing');
            });

            // 拖拽结束 → 上报新坐标
            marker.on('dragend', () => {
              if (!isMounted) return;
              marker.setCursor('grab');
              const pos = marker.getPosition();
              callbackRef.current?.(pos.getLat(), pos.getLng());
            });
          }
        })
        .catch((err) => console.error('[MapEngineClient] 初始化失败:', err));

      return () => {
        isMounted = false;
        if (mapRef.current) {
          mapRef.current.destroy();
          mapRef.current = null;
          markerRef.current = null;
          satelliteLayerRef.current = null;
          roadNetLayerRef.current = null;
          indoorMapRef.current = null;
          poiMarkersRef.current = [];
        }
      };
      // 仅初始化一次
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // 监听 draggable prop 变化，动态更新 marker 的拖拽状态
    useEffect(() => {
      const marker = markerRef.current;
      if (!marker) return;
      marker.setDraggable(draggable);
      marker.setCursor(draggable ? 'grab' : 'default');
      if (draggable) {
        marker.on('dragging', () => marker.setCursor('grabbing'));
        marker.on('dragend', () => {
          marker.setCursor('grab');
          const pos = marker.getPosition();
          callbackRef.current?.(pos.getLat(), pos.getLng());
        });
      } else {
        marker.clearEvents('dragging');
        marker.clearEvents('dragend');
      }
    }, [draggable]);

    return (
      <div
        ref={containerRef}
        className="w-full h-full overflow-hidden"
        style={{ minHeight: 320 }}
      />
    );
  },
);

MapEngineClient.displayName = 'MapEngineClient';
