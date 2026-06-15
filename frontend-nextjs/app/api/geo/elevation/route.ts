import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

const AMAP_BASE = 'https://restapi.amap.com/v3';

// 高德高程 API 中转（最多 20 个坐标点/次）
// GET /api/geo/elevation?lng=110.123&lat=30.456
export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const lng = searchParams.get('lng');
  const lat = searchParams.get('lat');

  if (!lng || !lat) {
    return NextResponse.json({ error: 'Missing lng or lat' }, { status: 400 });
  }

  const lngNum = parseFloat(lng);
  const latNum = parseFloat(lat);
  if (
    isNaN(lngNum) || isNaN(latNum) ||
    lngNum < 72 || lngNum > 136 ||
    latNum < 3 || latNum > 54
  ) {
    return NextResponse.json({ error: 'Coordinates out of China bounds' }, { status: 400 });
  }

  const serverKey = process.env.AMAP_SERVER_KEY;
  if (!serverKey) {
    return NextResponse.json({ error: 'AMAP_SERVER_KEY not configured' }, { status: 500 });
  }

  const url = new URL(`${AMAP_BASE}/elevation/detail`);
  url.searchParams.set('key', serverKey);
  url.searchParams.set('locations', `${lngNum},${latNum}`);
  url.searchParams.set('output', 'json');

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

    const elevation = parseFloat(data.results?.[0]?.elevation ?? '0');
    return NextResponse.json({ elevation });
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
