import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

const AMAP_BASE = 'https://restapi.amap.com/v3';

// 高德 POI 关键词搜索 API 中转
// GET /api/geo/search?q=七里坪&lng=110.0&lat=31.0
export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const q = searchParams.get('q');
  const lng = searchParams.get('lng');
  const lat = searchParams.get('lat');

  if (!q || q.trim().length === 0) {
    return NextResponse.json({ error: 'Missing query q' }, { status: 400 });
  }

  // 防止查询字符串过长注入
  if (q.length > 100) {
    return NextResponse.json({ error: 'Query too long' }, { status: 400 });
  }

  const serverKey = process.env.AMAP_SERVER_KEY;
  if (!serverKey) {
    return NextResponse.json({ error: 'AMAP_SERVER_KEY not configured' }, { status: 500 });
  }

  const url = new URL(`${AMAP_BASE}/place/text`);
  url.searchParams.set('key', serverKey);
  url.searchParams.set('keywords', q.trim());
  url.searchParams.set('output', 'json');
  url.searchParams.set('offset', '10');
  url.searchParams.set('page', '1');

  // 若提供了中心坐标，则按距离排序
  if (lng && lat) {
    const lngNum = parseFloat(lng);
    const latNum = parseFloat(lat);
    if (!isNaN(lngNum) && !isNaN(latNum)) {
      url.searchParams.set('location', `${lngNum},${latNum}`);
    }
  }

  try {
    const res = await fetch(url.toString(), {
      headers: { 'User-Agent': 'nextjs-geo-proxy/1.0' },
      signal: AbortSignal.timeout(8000),
    });

    if (!res.ok) {
      return NextResponse.json({ error: 'Upstream error', status: res.status }, { status: 502 });
    }

    const data = await res.json();

    if (data.status !== '1') {
      return NextResponse.json(
        { error: `Amap error: ${data.info ?? 'unknown'}`, infocode: data.infocode },
        { status: 502 },
      );
    }

    const pois: Array<{
      name: string;
      address: string;
      lat: number;
      lng: number;
      poi_id: string;
    }> = (data.pois ?? []).map((p: Record<string, unknown>) => {
      const [poiLng, poiLat] = String(p.location ?? '0,0').split(',').map(Number);
      return {
        name: String(p.name ?? ''),
        address: String(p.address ?? ''),
        lat: poiLat,
        lng: poiLng,
        poi_id: String(p.id ?? ''),
      };
    });

    return NextResponse.json({ results: pois });
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
