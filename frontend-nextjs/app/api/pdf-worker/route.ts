import { readFile } from 'fs/promises';
import path from 'path';
import { NextResponse } from 'next/server';

export const runtime = 'nodejs';

export async function GET() {
	try {
		const workerPath = path.join(process.cwd(), 'node_modules', 'pdfjs-dist', 'legacy', 'build', 'pdf.worker.js');
		const worker = await readFile(workerPath, 'utf8');
		return new NextResponse(worker, {
			headers: {
				'Content-Type': 'application/javascript; charset=utf-8',
				'Cache-Control': 'public, max-age=31536000, immutable',
			},
		});
	} catch (error) {
		console.error('[pdf-worker] read failed:', error);
		return NextResponse.json({ error: 'Failed to load pdf worker.' }, { status: 500 });
	}
}
