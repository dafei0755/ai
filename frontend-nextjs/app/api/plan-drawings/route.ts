import { promises as fs } from 'fs';
import path from 'path';
import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

const UPLOAD_DIR = path.join(process.cwd(), '.uploads', 'plan-drawings');
const ALLOWED_EXTENSIONS = new Set(['.dwg', '.dxf', '.pdf', '.png', '.jpg', '.jpeg', '.webp']);

const getMimeType = (extension: string) => {
	if (extension === '.jpg' || extension === '.jpeg') return 'image/jpeg';
	if (extension === '.png') return 'image/png';
	if (extension === '.webp') return 'image/webp';
	if (extension === '.pdf') return 'application/pdf';
	if (extension === '.dxf') return 'application/dxf';
	if (extension === '.dwg') return 'application/acad';
	return 'application/octet-stream';
};

const sanitizeSegment = (value: string) =>
	value
		.replace(/[^\w\u4e00-\u9fa5.-]+/g, '-')
		.replace(/-+/g, '-')
		.slice(0, 80) || 'drawing';

const parseDxfSummary = (content: string) => {
	const layers = Array.from(new Set(Array.from(content.matchAll(/\n\s*8\s*\n([^\n\r]+)/g)).map((match) => match[1].trim()).filter(Boolean))).slice(0, 48);
	const entityTypes = ['LINE', 'LWPOLYLINE', 'POLYLINE', 'CIRCLE', 'ARC', 'TEXT', 'MTEXT', 'INSERT', 'HATCH'];
	const entityCounts = entityTypes.reduce<Record<string, number>>((acc, type) => {
		const matches = content.match(new RegExp(`\\n\\s*0\\s*\\n${type}\\s*(\\n|\\r)`, 'g'));
		if (matches?.length) acc[type] = matches.length;
		return acc;
	}, {});

	return {
		status: 'parsed' as const,
		message: `DXF 已解析：${layers.length} 个图层，${Object.values(entityCounts).reduce((sum, count) => sum + count, 0)} 个基础实体。`,
		layers,
		entityCounts,
	};
};

export async function POST(request: NextRequest) {
	try {
		const formData = await request.formData();
		const file = formData.get('file');
		const sessionId = sanitizeSegment(String(formData.get('sessionId') ?? 'global'));
		const space = sanitizeSegment(String(formData.get('space') ?? 'space'));

		if (!(file instanceof File)) {
			return NextResponse.json({ error: 'Missing drawing file.' }, { status: 400 });
		}

		const originalName = path.basename(file.name);
		const extension = path.extname(originalName).toLowerCase();
		if (!ALLOWED_EXTENSIONS.has(extension)) {
			return NextResponse.json({ error: 'Unsupported drawing format.' }, { status: 400 });
		}

		await fs.mkdir(UPLOAD_DIR, { recursive: true });
		const storedName = `${Date.now()}-${sessionId}-${space}-${sanitizeSegment(originalName)}`;
		const filePath = path.join(UPLOAD_DIR, storedName);
		const buffer = Buffer.from(await file.arrayBuffer());
		await fs.writeFile(filePath, buffer);

		let parseResult: {
			status: 'uploaded' | 'parsed' | 'needs_conversion';
			message: string;
			layers?: string[];
			entityCounts?: Record<string, number>;
		};

		if (extension === '.dxf') {
			parseResult = parseDxfSummary(buffer.toString('utf8'));
		} else if (extension === '.dwg') {
			parseResult = {
				status: 'needs_conversion',
				message: 'DWG 已保存。当前版本需要转换为 DXF 后进行图层与实体解析。',
			};
		} else if (extension === '.pdf') {
			parseResult = {
				status: 'uploaded',
				message: 'PDF 已保存，可在图纸查看器中预览；矢量路径解析将在后续接入。',
			};
		} else {
			parseResult = {
				status: 'uploaded',
				message: '图片图纸已保存，可作为分平底图查看与标注。',
			};
		}

		return NextResponse.json({
			id: storedName,
			originalName,
			storedName,
			url: `/api/plan-drawings?file=${encodeURIComponent(storedName)}`,
			extension: extension.slice(1),
			mimeType: getMimeType(extension),
			size: buffer.length,
			parseResult,
		});
	} catch (error) {
		console.error('[plan-drawings] upload failed:', error);
		return NextResponse.json({ error: 'Failed to upload drawing.' }, { status: 500 });
	}
}

export async function GET(request: NextRequest) {
	try {
		const file = request.nextUrl.searchParams.get('file');
		if (!file) return NextResponse.json({ error: 'Missing file.' }, { status: 400 });

		const safeName = path.basename(file);
		if (safeName !== file) return NextResponse.json({ error: 'Invalid file name.' }, { status: 400 });

		const extension = path.extname(safeName).toLowerCase();
		if (!ALLOWED_EXTENSIONS.has(extension)) {
			return NextResponse.json({ error: 'Unsupported drawing format.' }, { status: 400 });
		}

		const buffer = await fs.readFile(path.join(UPLOAD_DIR, safeName));
		return new NextResponse(buffer, {
			headers: {
				'Content-Type': getMimeType(extension),
				'Content-Disposition': `inline; filename="${encodeURIComponent(safeName)}"`,
				'Cache-Control': 'private, max-age=0, must-revalidate',
			},
		});
	} catch (error) {
		console.error('[plan-drawings] read failed:', error);
		return NextResponse.json({ error: 'Failed to read drawing.' }, { status: 404 });
	}
}
