/**
 * 高德 GeoProvider 实现
 *
 * 遵循 Adapter 模式：业务代码只依赖 GeoProvider 接口，不直接耦合高德。
 * 所有网络请求都通过 Next.js App Router API 中转（/api/geo/*），
 * 确保 Web 服务 Key 始终留在服务端。
 */
import type {
  GeoProvider,
  GeoSearchResult,
  GeoReverseResult,
  GeoAdministrative,
} from '@/types/geo';

/** 内部工具：构造带 origin 的绝对 URL（支持 SSR 和浏览器两侧调用） */
function apiUrl(path: string, params: Record<string, string>): string {
  const base =
    typeof window !== 'undefined'
      ? window.location.origin
      : process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3000';

  const url = new URL(path, base);
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  return url.toString();
}

export class AmapProvider implements GeoProvider {
  readonly name = 'amap';

  async searchPlace(
    query: string,
    lat?: number,
    lng?: number,
  ): Promise<GeoSearchResult[]> {
    const params: Record<string, string> = { q: query };
    if (lat !== undefined && lng !== undefined) {
      params.lat = String(lat);
      params.lng = String(lng);
    }

    const res = await fetch(apiUrl('/api/geo/search', params));
    if (!res.ok) throw new Error(`searchPlace failed: ${res.status}`);

    const data = await res.json();
    return (data.results ?? []) as GeoSearchResult[];
  }

  async reverseGeocode(lat: number, lng: number): Promise<GeoReverseResult> {
    const res = await fetch(
      apiUrl('/api/geo/reverse', { lat: String(lat), lng: String(lng) }),
    );
    if (!res.ok) throw new Error(`reverseGeocode failed: ${res.status}`);

    const d = await res.json();

    const administrative: GeoAdministrative = {
      country: d.country ?? '中国',
      province: d.province ?? '',
      city: d.city ?? '',
      district: d.district ?? '',
      township: d.township,
      formatted_address: d.formatted_address ?? '',
    };

    return { administrative, poi_name: d.poi_name };
  }

  async getElevation(lat: number, lng: number): Promise<number> {
    const res = await fetch(
      apiUrl('/api/geo/elevation', { lat: String(lat), lng: String(lng) }),
    );
    if (!res.ok) throw new Error(`getElevation failed: ${res.status}`);

    const d = await res.json();
    return typeof d.elevation === 'number' ? d.elevation : 0;
  }
}
