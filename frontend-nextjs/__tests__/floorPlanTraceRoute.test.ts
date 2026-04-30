export {};

type RouteModule = {
	POST: (request: any) => Promise<any>;
};

const DXF_MINIMAL = [
	'0', 'SECTION',
	'2', 'ENTITIES',
	'0', 'LINE',
	'8', 'A-WALL',
	'10', '0',
	'20', '0',
	'11', '100',
	'21', '0',
	'0', 'ENDSEC',
	'0', 'EOF',
].join('\n');

const dxfLine = (layer: string, x1: number, y1: number, x2: number, y2: number) => [
	'0', 'LINE',
	'8', layer,
	'10', String(x1),
	'20', String(y1),
	'11', String(x2),
	'21', String(y2),
].join('\n');

const buildClusteredDxf = () => {
	const entities: string[] = [];
	for (let x = 0; x <= 100; x += 4) entities.push(dxfLine('A-WALL', x, 0, x, 100));
	for (let y = 0; y <= 100; y += 4) entities.push(dxfLine('A-WALL', 0, y, 100, y));
	[
		[260, 220, 360, 220],
		[360, 220, 360, 300],
		[360, 300, 260, 300],
		[260, 300, 260, 220],
		[280, 240, 340, 240],
		[280, 260, 340, 260],
		[280, 280, 340, 280],
		[310, 230, 310, 290],
	].forEach(([x1, y1, x2, y2]) => entities.push(dxfLine('A-WALL', x1, y1, x2, y2)));
	return [
		'0', 'SECTION',
		'2', 'ENTITIES',
		...entities,
		'0', 'ENDSEC',
		'0', 'EOF',
	].join('\n');
};

const makeJsonRequest = (body: unknown) =>
	({ json: async () => body });

const makeInvalidJsonRequest = () =>
	({ json: async () => { throw new Error('invalid json'); } });

const loadRoute = async () => {
	jest.resetModules();
	const stat = jest.fn();
	const readFile = jest.fn();
	jest.doMock('fs', () => ({
		promises: { stat, readFile },
	}));
	jest.doMock('next/server', () => ({
		NextResponse: {
			json: (body: unknown, init?: { status?: number }) =>
				({
					status: init?.status ?? 200,
					json: async () => body,
				}),
		},
		NextRequest: class {},
	}));
	const route = (await import('@/app/api/floor-plan/trace/route')) as unknown as RouteModule;
	return { ...route, stat, readFile };
};

describe('API /api/floor-plan/trace', () => {
	it('returns 400 for invalid JSON body', async () => {
		const { POST } = await loadRoute();
		const response = await POST(makeInvalidJsonRequest() as any);
		const payload = await response.json() as { error?: string };
		expect(response.status).toBe(400);
		expect(payload.error).toBe('Invalid JSON body.');
	});

	it('returns 400 when fileUrl is missing', async () => {
		const { POST } = await loadRoute();
		const response = await POST(makeJsonRequest({}) as any);
		const payload = await response.json() as { error?: string };
		expect(response.status).toBe(400);
		expect(payload.error).toBe('Missing fileUrl.');
	});

	it('returns unsupported payload for non-vector extension without reading file', async () => {
		const { POST, stat, readFile } = await loadRoute();
		const response = await POST(makeJsonRequest({ fileUrl: '/api/plan-drawings?file=sample.png' }) as any);
		const payload = await response.json() as {
			status?: string;
			compilerStatus?: string;
			elements?: unknown[];
		};
		expect(response.status).toBe(200);
		expect(payload.status).toBe('unsupported');
		expect(payload.compilerStatus).toBe('candidate_ready');
		expect(Array.isArray(payload.elements)).toBe(true);
		expect(stat).not.toHaveBeenCalled();
		expect(readFile).not.toHaveBeenCalled();
	});

	it('marks mainPlanBoxSource as fallback when region is omitted', async () => {
		const { POST, stat, readFile } = await loadRoute();
		stat.mockResolvedValue({ size: Buffer.byteLength(DXF_MINIMAL) });
		readFile.mockResolvedValue(Buffer.from(DXF_MINIMAL, 'utf8'));
		const response = await POST(makeJsonRequest({ fileUrl: '/api/plan-drawings?file=sample.dxf' }) as any);
		const payload = await response.json() as { normalization?: { mainPlanBoxSource?: string } };
		expect(response.status).toBe(200);
		expect(payload.normalization?.mainPlanBoxSource).toBe('fallback_recognition_region');
	});

	it('keeps fallback source for explicit full-page region', async () => {
		const { POST, stat, readFile } = await loadRoute();
		stat.mockResolvedValue({ size: Buffer.byteLength(DXF_MINIMAL) });
		readFile.mockResolvedValue(Buffer.from(DXF_MINIMAL, 'utf8'));
		const response = await POST(makeJsonRequest({
			fileUrl: '/api/plan-drawings?file=sample.dxf',
			region: { x: 0, y: 0, w: 1, h: 1 },
		}) as any);
		const payload = await response.json() as { normalization?: { mainPlanBoxSource?: string } };
		expect(response.status).toBe(200);
		expect(payload.normalization?.mainPlanBoxSource).toBe('fallback_recognition_region');
	});

	it('marks mainPlanBoxSource as user_roi for non-default region', async () => {
		const { POST, stat, readFile } = await loadRoute();
		stat.mockResolvedValue({ size: Buffer.byteLength(DXF_MINIMAL) });
		readFile.mockResolvedValue(Buffer.from(DXF_MINIMAL, 'utf8'));
		const response = await POST(makeJsonRequest({
			fileUrl: '/api/plan-drawings?file=sample.dxf',
			region: { x: 0.1, y: 0.1, w: 0.8, h: 0.8 },
		}) as any);
		const payload = await response.json() as { normalization?: { mainPlanBoxSource?: string } };
		expect(response.status).toBe(200);
		expect(payload.normalization?.mainPlanBoxSource).toBe('user_roi');
	});

	it('promotes a detected primary plan cluster to mainPlanBox when no user ROI is provided', async () => {
		const dxf = buildClusteredDxf();
		const { POST, stat, readFile } = await loadRoute();
		stat.mockResolvedValue({ size: Buffer.byteLength(dxf) });
		readFile.mockResolvedValue(Buffer.from(dxf, 'utf8'));
		const response = await POST(makeJsonRequest({ fileUrl: '/api/plan-drawings?file=clustered.dxf' }) as any);
		const payload = await response.json() as {
			normalization?: {
				mainPlanBoxSource?: string;
				focusUsedAsMainPlanBox?: boolean;
				mainPlanBox?: { w: number; h: number };
			};
		};
		expect(response.status).toBe(200);
		expect(payload.normalization?.mainPlanBoxSource).toBe('detected_plan_frame');
		expect(payload.normalization?.focusUsedAsMainPlanBox).toBe(true);
		expect((payload.normalization?.mainPlanBox?.w ?? 1) * (payload.normalization?.mainPlanBox?.h ?? 1)).toBeLessThan(0.9);
	});
});
