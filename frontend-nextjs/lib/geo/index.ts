/**
 * GeoProvider 工厂
 *
 * 用法：import { getGeoProvider } from '@/lib/geo'
 *
 * 未来扩展：读取 process.env.GEO_PROVIDER 动态切换腾讯/Mapbox
 */
import type { GeoProvider } from '@/types/geo';
import { AmapProvider } from './amap-provider';

let _provider: GeoProvider | null = null;

export function getGeoProvider(): GeoProvider {
  if (!_provider) {
    _provider = new AmapProvider();
  }
  return _provider;
}

export { AmapProvider };
export type { GeoProvider };
