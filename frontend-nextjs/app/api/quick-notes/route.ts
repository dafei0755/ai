import { promises as fs } from 'fs';
import path from 'path';
import { NextRequest, NextResponse } from 'next/server';

import type { QuickNote, QuickNoteSource, QuickNoteStatus, QuickNoteTargetPage } from '@/types/quick_note';

export const runtime = 'nodejs';

const STORE_DIR = path.join(process.cwd(), '.uploads', 'quick-notes');
const STORE_FILE = path.join(STORE_DIR, 'notes.json');
const VALID_SOURCES = new Set<QuickNoteSource>(['web', 'qclaw_wechat', 'mobile']);
const VALID_TARGET_PAGES = new Set<QuickNoteTargetPage>(['草池', '沉淀', '作品', '我']);

const withGovernanceDefaults = (note: QuickNote): QuickNote => ({
	...note,
	original_preserved: note.original_preserved ?? true,
	review_status: note.review_status ?? 'unreviewed',
	promotion_status: note.promotion_status ?? 'not_promoted',
	promoted_object_id: note.promoted_object_id ?? null,
});

type QuickNoteStore = {
	items: QuickNote[];
	updatedAt?: string;
};

const readStore = async (): Promise<QuickNoteStore> => {
	const exists = await fs
		.access(STORE_FILE)
		.then(() => true)
		.catch(() => false);
	if (!exists) return { items: [] };

	const raw = await fs.readFile(STORE_FILE, 'utf8');
	const parsed = JSON.parse(raw) as Partial<QuickNoteStore>;
	return {
		items: Array.isArray(parsed.items) ? parsed.items.map(withGovernanceDefaults) : [],
		updatedAt: parsed.updatedAt,
	};
};

const writeStore = async (store: QuickNoteStore) => {
	await fs.mkdir(STORE_DIR, { recursive: true });
	const tempPath = `${STORE_FILE}.tmp`;
	await fs.writeFile(tempPath, JSON.stringify(store, null, 2), 'utf8');
	await fs.rename(tempPath, STORE_FILE);
};

export async function GET(request: NextRequest) {
	try {
		const hours = Math.max(1, Number(request.nextUrl.searchParams.get('hours') ?? 24) || 24);
		const limit = Math.min(100, Math.max(1, Number(request.nextUrl.searchParams.get('limit') ?? 20) || 20));
		const cutoff = Date.now() - hours * 60 * 60 * 1000;
		const store = await readStore();
		const items = store.items
			.filter((note) => new Date(note.created_at).getTime() >= cutoff)
			.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
			.slice(0, limit);

		return NextResponse.json({ items });
	} catch (error) {
		console.error('[quick-notes] list failed:', error);
		return NextResponse.json({ error: 'Failed to load quick notes.' }, { status: 500 });
	}
}

export async function POST(request: NextRequest) {
	try {
		const body = await request.json() as { raw_text?: unknown; source?: unknown };
		const rawText = String(body.raw_text ?? '').trim();
		if (!rawText) {
			return NextResponse.json({ error: 'raw_text cannot be empty.' }, { status: 400 });
		}

		const requestedSource = String(body.source ?? 'web') as QuickNoteSource;
		const source = VALID_SOURCES.has(requestedSource) ? requestedSource : 'web';
		const now = new Date().toISOString();
		const note: QuickNote = {
			quicknote_id: crypto.randomUUID(),
			raw_text: rawText,
			created_at: now,
			updated_at: now,
			source,
			status: 'raw' satisfies QuickNoteStatus,
			target_page: '草池',
			category: '待分类',
			original_preserved: true,
			review_status: 'unreviewed',
			promotion_status: 'not_promoted',
			promoted_object_id: null,
		};

		const store = await readStore();
		await writeStore({
			items: [note, ...store.items].slice(0, 500),
			updatedAt: now,
		});

		return NextResponse.json(note, { status: 201 });
	} catch (error) {
		console.error('[quick-notes] save failed:', error);
		return NextResponse.json({ error: 'Failed to save quick note.' }, { status: 500 });
	}
}

export async function PATCH(request: NextRequest) {
	try {
		const body = await request.json() as {
			quicknote_id?: unknown;
			raw_text?: unknown;
			target_page?: unknown;
			category?: unknown;
		};
		const noteId = String(body.quicknote_id ?? '').trim();
		if (!noteId) {
			return NextResponse.json({ error: 'quicknote_id is required.' }, { status: 400 });
		}

		const store = await readStore();
		const index = store.items.findIndex((note) => note.quicknote_id === noteId);
		if (index < 0) {
			return NextResponse.json({ error: 'Quick note not found.' }, { status: 404 });
		}

		const current = store.items[index];
		const nextText = body.raw_text === undefined ? current.raw_text : String(body.raw_text).trim();
		if (!nextText) {
			return NextResponse.json({ error: 'raw_text cannot be empty.' }, { status: 400 });
		}

		const requestedTarget = String(body.target_page ?? current.target_page ?? '草池') as QuickNoteTargetPage;
		const targetPage = VALID_TARGET_PAGES.has(requestedTarget) ? requestedTarget : '草池';
		const category = String(body.category ?? current.category ?? '').trim() || (targetPage === '草池' ? '待分类' : '未分类');
		const now = new Date().toISOString();
		const nextNote: QuickNote = {
			...current,
			raw_text: nextText,
			target_page: targetPage,
			category,
			status: targetPage === '草池' ? 'raw' : 'tagged',
			original_preserved: true,
			review_status: targetPage === '草池' ? 'unreviewed' : 'manual_review_required',
			promotion_status: targetPage === '草池' ? 'not_promoted' : 'candidate_routed',
			promoted_object_id: current.promoted_object_id ?? null,
			updated_at: now,
		};

		const items = [...store.items];
		items[index] = nextNote;
		await writeStore({ items, updatedAt: now });

		return NextResponse.json(nextNote);
	} catch (error) {
		console.error('[quick-notes] update failed:', error);
		return NextResponse.json({ error: 'Failed to update quick note.' }, { status: 500 });
	}
}
