import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /api/geo/staticmap?lng=&lat=&zoom=14&w=600&h=300
 * 高德静态地图中转（使用服务端 Key，不暴露给前端）
 */
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const lng = searchParams.get('lng');
  const lat = searchParams.get('lat');
  const zoom = searchParams.get('zoom') ?? '14';
  const w = searchParams.get('w') ?? '600';
  const h = searchParams.get('h') ?? '300';

  const key = process.env.AMAP_SERVER_KEY;
  if (!key) return NextResponse.json({ error: 'server key not configured' }, { status: 500 });
  if (!lng || !lat) return NextResponse.json({ error: 'lng and lat required' }, { status: 400 });

  const lngN = parseFloat(lng);
  const latN = parseFloat(lat);
  if (isNaN(lngN) || isNaN(latN) || lngN < 72 || lngN > 138 || latN < 3 || latN > 54) {
    return NextResponse.json({ error: 'coordinates out of range' }, { status: 400 });
  }

  // 橙色大头针标记
  const marker = `mid,0xFF6600,:${lng},${lat}`;
  const url = `https://restapi.amap.com/v3/staticmap?location=${lng},${lat}&zoom=${zoom}&size=${w}*${h}&markers=${marker}&key=${key}`;

  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(4500) });
    if (!res.ok) throw new Error(`amap ${res.status}`);
    const contentType = res.headers.get('Content-Type') ?? '';
    if (!contentType.startsWith('image/')) {
      const text = await res.text();
      throw new Error(`amap returned non-image response: ${text.slice(0, 160)}`);
    }
    const buf = await res.arrayBuffer();
    return new NextResponse(buf, {
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=3600',
      },
    });
  } catch (err) {
    console.error('[geo/staticmap]', err);
    return NextResponse.json({ error: 'fetch failed' }, { status: 502 });
  }
}
