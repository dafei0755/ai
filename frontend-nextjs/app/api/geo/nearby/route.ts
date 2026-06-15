import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/geo/nearby
 * 周边 POI 搜索 — 代理高德 /v3/place/around
 *
 * Query params:
 *   lng      经度 (GCJ-02)
 *   lat      纬度 (GCJ-02)
 *   types    POI 类型码，多个用 | 分隔，如 050000|060000（默认 050000）
 *   radius   搜索半径（米），最大 50000（默认 1000）
 */
export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;

  const lng = searchParams.get('lng');
  const lat = searchParams.get('lat');
  const types = searchParams.get('types') ?? '050000';
  const rawRadius = parseInt(searchParams.get('radius') ?? '1000', 10);
  const radius = Math.min(isNaN(rawRadius) ? 1000 : rawRadius, 50000);

  // 只允许数字和 | 分隔符，防止注入
  if (!/^[\d|]+$/.test(types)) {
    return NextResponse.json({ error: 'invalid types parameter' }, { status: 400 });
  }

  const key = process.env.AMAP_SERVER_KEY;
  if (!key) {
    return NextResponse.json({ error: 'server key not configured' }, { status: 500 });
  }

  if (!lng || !lat) {
    return NextResponse.json({ error: 'lng and lat required' }, { status: 400 });
  }

  // 验证坐标格式
  if (!/^-?\d+(\.\d+)?$/.test(lng) || !/^-?\d+(\.\d+)?$/.test(lat)) {
    return NextResponse.json({ error: 'invalid coordinates' }, { status: 400 });
  }

  const amapUrl =
    `https://restapi.amap.com/v3/place/around` +
    `?location=${lng},${lat}` +
    `&radius=${radius}` +
    `&types=${types}` +
    `&key=${key}` +
    `&offset=20&page=1&extensions=all`;

  try {
    const res = await fetch(amapUrl, { signal: AbortSignal.timeout(8000) });
    const data = (await res.json()) as {
      status: string;
      count?: string;
      pois?: Array<Record<string, unknown>>;
    };

    if (data.status !== '1') {
      return NextResponse.json({ total: 0, items: [] });
    }

    const pois = (data.pois ?? []).map((p) => {
      // location 字段格式为 "lng,lat"
      const locStr = String(p.location ?? '');
      const [poiLng, poiLat] = locStr.split(',').map(Number);
      return {
        name: p.name,
        address: p.address || '',
        distance: p.distance,
        typecode: p.typecode,
        type: p.type || '',
        tel: p.tel || '',
        opentime: (p as any).opentime_week || (p as any).opentime || '',
        lat: isNaN(poiLat) ? undefined : poiLat,
        lng: isNaN(poiLng) ? undefined : poiLng,
      };
    });

    return NextResponse.json(
      { total: parseInt(data.count ?? '0', 10), items: pois },
      { headers: { 'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600' } },
    );
  } catch (err) {
    console.error('[geo/nearby]', err);
    return NextResponse.json({ error: 'upstream fetch failed' }, { status: 502 });
  }
}
