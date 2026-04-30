import { promises as fs } from 'fs';
import path from 'path';
import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

const PICTURE_DIRECTORIES = {
	default: 'C:\\Users\\Public\\Pictures',
	'advisor-avatar': 'D:\\1 方案高参\\头像',
	'furniture-1': 'D:\\1 方案高参\\家具1',
	'furniture-2': 'D:\\1 方案高参\\家具2',
} as const;
const ALLOWED_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif']);

const getMimeType = (extension: string) => {
	if (extension === '.jpg' || extension === '.jpeg') return 'image/jpeg';
	if (extension === '.png') return 'image/png';
	if (extension === '.webp') return 'image/webp';
	if (extension === '.bmp') return 'image/bmp';
	if (extension === '.gif') return 'image/gif';
	return 'application/octet-stream';
};

const getDirectoryPath = (collection: string | null) => {
	if (!collection || collection === 'default') return PICTURE_DIRECTORIES.default;
	if (collection === 'advisor-avatar') return PICTURE_DIRECTORIES['advisor-avatar'];
	if (collection === 'furniture-1') return PICTURE_DIRECTORIES['furniture-1'];
	if (collection === 'furniture-2') return PICTURE_DIRECTORIES['furniture-2'];
	return null;
};

const getPictureNames = async (directoryPath: string) => {
	const entries = await fs.readdir(directoryPath, { withFileTypes: true });

	return entries
		.filter((entry) => entry.isFile())
		.map((entry) => entry.name)
		.filter((name) => ALLOWED_EXTENSIONS.has(path.extname(name).toLowerCase()))
		.sort((a, b) => a.localeCompare(b, 'zh-CN'));
};

export async function GET(request: NextRequest) {
	try {
		const name = request.nextUrl.searchParams.get('name');
		const collection = request.nextUrl.searchParams.get('collection');
		const directoryPath = getDirectoryPath(collection);

		if (!directoryPath) {
			return NextResponse.json({ error: 'Unsupported picture collection.' }, { status: 400 });
		}

		if (!name) {
			const files = await getPictureNames(directoryPath);
			return NextResponse.json({ files });
		}

		const safeName = path.basename(name);
		if (safeName !== name) {
			return NextResponse.json({ error: 'Invalid file name.' }, { status: 400 });
		}

		const extension = path.extname(safeName).toLowerCase();
		if (!ALLOWED_EXTENSIONS.has(extension)) {
			return NextResponse.json({ error: 'Unsupported image type.' }, { status: 400 });
		}

		const filePath = path.join(directoryPath, safeName);
		const buffer = await fs.readFile(filePath);

		return new NextResponse(buffer, {
			headers: {
				'Content-Type': getMimeType(extension),
				'Cache-Control': 'public, max-age=3600',
			},
		});
	} catch (error) {
		console.error('[public-pictures] failed to serve image(s):', error);
		return NextResponse.json({ error: 'Failed to read public pictures.' }, { status: 500 });
	}
}
