import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

const AMAP_BASE = 'https://restapi.amap.com/v3';

// 高德逆地理编码 API 中转
// GET /api/geo/reverse?lng=110.123&lat=30.456
export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const lng = searchParams.get('lng');
  const lat = searchParams.get('lat');

  // 参数校验
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

  const url = new URL(`${AMAP_BASE}/geocode/regeo`);
  url.searchParams.set('key', serverKey);
  url.searchParams.set('location', `${lngNum},${latNum}`);
  url.searchParams.set('extensions', 'all');
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

    const regeo = data.regeocode;
    const ac = regeo?.addressComponent ?? {};

    return NextResponse.json({
      formatted_address: regeo?.formatted_address ?? '',
      country: ac.country ?? '中国',
      province: ac.province ?? '',
      city: typeof ac.city === 'string' ? ac.city : ac.province ?? '',
      district: ac.district ?? '',
      township: ac.township ?? undefined,
      poi_name: regeo?.pois?.[0]?.name ?? undefined,
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Unknown error';
    return NextResponse.json({ error: msg }, { status: 502 });
  }
}
