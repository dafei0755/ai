/**
 * useReverseGeocode — 坐标反解析 hook
 *
 * 调用 /api/geo/reverse，返回 GeoAdministrative 数据。
 * 内置防抖（500ms），避免地图拖拽时频繁触发。
 */
import { useState, useEffect, useRef } from 'react';
import type { GeoAdministrative } from '@/types/geo';

interface UseReverseGeocodeResult {
  data: (GeoAdministrative & { poi_name?: string }) | null;
  loading: boolean;
  error: string | null;
}

export function useReverseGeocode(
  lat: number | null,
  lng: number | null,
  debounceMs = 500,
): UseReverseGeocodeResult {
  const [data, setData] = useState<UseReverseGeocodeResult['data']>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (lat === null || lng === null) return;

    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/geo/reverse?lat=${lat}&lng=${lng}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setData({
          country: json.country,
          province: json.province,
          city: json.city,
          district: json.district,
          township: json.township,
          formatted_address: json.formatted_address,
          poi_name: json.poi_name,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : '解析失败');
      } finally {
        setLoading(false);
      }
    }, debounceMs);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [lat, lng, debounceMs]);

  return { data, loading, error };
}
