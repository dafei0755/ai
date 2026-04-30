import { promises as fs } from 'fs';
import path from 'path';
import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

const STORE_DIR = path.join(process.cwd(), '.uploads', 'plan-topics');

const sanitizeSegment = (value: string) =>
	value
		.replace(/[^\w\u4e00-\u9fa5.-]+/g, '-')
		.replace(/-+/g, '-')
		.slice(0, 80) || 'session';

const resolveTopicFile = (sessionId: string) => {
	const safeSessionId = sanitizeSegment(sessionId);
	return path.join(STORE_DIR, `${safeSessionId}.json`);
};

export async function GET(request: NextRequest) {
	try {
		const sessionId = String(request.nextUrl.searchParams.get('sessionId') ?? '').trim();
		if (!sessionId) {
			return NextResponse.json({ error: 'Missing sessionId.' }, { status: 400 });
		}

		const filePath = resolveTopicFile(sessionId);
		const exists = await fs
			.access(filePath)
			.then(() => true)
			.catch(() => false);
		if (!exists) {
			return NextResponse.json({ topics: null });
		}

		const raw = await fs.readFile(filePath, 'utf8');
		const parsed = JSON.parse(raw) as { topics?: Record<string, unknown>; updatedAt?: string };
		return NextResponse.json({
			topics: parsed.topics ?? null,
			updatedAt: parsed.updatedAt,
		});
	} catch (error) {
		console.error('[plan-topics] get failed:', error);
		return NextResponse.json({ error: 'Failed to load plan topics.' }, { status: 500 });
	}
}

export async function POST(request: NextRequest) {
	try {
		const body = await request.json() as { sessionId?: string; topics?: Record<string, unknown> };
		const sessionId = String(body.sessionId ?? '').trim();
		const topics = body.topics;
		if (!sessionId) {
			return NextResponse.json({ error: 'Missing sessionId.' }, { status: 400 });
		}
		if (!topics || typeof topics !== 'object') {
			return NextResponse.json({ error: 'Invalid topics payload.' }, { status: 400 });
		}

		await fs.mkdir(STORE_DIR, { recursive: true });
		const filePath = resolveTopicFile(sessionId);
		const tempPath = `${filePath}.tmp`;
		const payload = {
			sessionId,
			topics,
			updatedAt: new Date().toISOString(),
		};

		await fs.writeFile(tempPath, JSON.stringify(payload, null, 2), 'utf8');
		await fs.rename(tempPath, filePath);

		return NextResponse.json({ ok: true, updatedAt: payload.updatedAt });
	} catch (error) {
		console.error('[plan-topics] save failed:', error);
		return NextResponse.json({ error: 'Failed to save plan topics.' }, { status: 500 });
	}
}
