import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8001';

export async function POST(request: NextRequest) {
	try {
		const body = await request.json();
		const response = await fetch(`${API_BASE}/api/v1/floor-plan/generate-variants`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body),
			cache: 'no-store',
		});
		const payload = await response.json().catch(() => ({}));
		if (!response.ok) {
			return NextResponse.json(
				{ error: payload?.detail ?? payload?.error ?? 'Failed to generate floor-plan variants.' },
				{ status: response.status }
			);
		}
		return NextResponse.json(payload);
	} catch (error) {
		console.error('[floor-plan/generate-variants] proxy failed:', error);
		const message = error instanceof Error ? error.message : 'Failed to generate floor-plan variants.';
		return NextResponse.json({ error: message }, { status: 500 });
	}
}
