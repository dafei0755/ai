// Shared DXF preview parsing utilities used by CockpitPanel and PlanSandboxPanel.

export interface DxfPreviewLine {
	x1: number;
	y1: number;
	x2: number;
	y2: number;
	layer?: string;
	color?: number;
}

export interface DxfPreviewCircle {
	cx: number;
	cy: number;
	r: number;
	layer?: string;
	color?: number;
}

export interface DxfPreviewArc extends DxfPreviewCircle {
	start: number;
	end: number;
}

export interface DxfPreviewText {
	x: number;
	y: number;
	text: string;
	height: number;
	rotation?: number;
	layer?: string;
	color?: number;
}

export interface DxfPreviewFill {
	points: Array<{ x: number; y: number }>;
	layer?: string;
	color?: number;
	source?: 'hatch' | 'solid' | 'polyline';
}

export interface DxfPreviewGeometry {
	lines: DxfPreviewLine[];
	circles: DxfPreviewCircle[];
	arcs: DxfPreviewArc[];
	texts: DxfPreviewText[];
	fills: DxfPreviewFill[];
	width: number;
	height: number;
	entityCount: number;
}

type DxfBlockEntity =
	| { type: 'line'; payload: DxfPreviewLine }
	| { type: 'circle'; payload: DxfPreviewCircle }
	| { type: 'arc'; payload: DxfPreviewArc }
	| { type: 'text'; payload: DxfPreviewText }
	| { type: 'fill'; payload: DxfPreviewFill }
	| {
			type: 'insert';
			payload: {
				name: string;
				x: number;
				y: number;
				scaleX: number;
				scaleY: number;
				rotation: number;
				layer?: string;
				color?: number;
			};
	  };

interface DxfBlockDefinition {
	name: string;
	baseX: number;
	baseY: number;
	entities: DxfBlockEntity[];
}

export const parseDxfPreviewGeometry = (content: string): DxfPreviewGeometry => {
	const raw = content.split(/\r?\n/).map((line) => line.trim());
	const pairs: Array<[string, string]> = [];
	for (let i = 0; i < raw.length - 1; i += 2) pairs.push([raw[i], raw[i + 1]]);
	const getString = (startIndex: number, code: string) => {
		for (let i = startIndex; i < pairs.length; i += 1) {
			if (pairs[i][0] === '0') break;
			if (pairs[i][0] === code) return pairs[i][1];
		}
		return undefined;
	};
	const getNumber = (startIndex: number, code: string) => {
		const value = getString(startIndex, code);
		const number = Number(value);
		return Number.isFinite(number) ? number : undefined;
	};
	const getStrings = (startIndex: number, code: string) => {
		const result: string[] = [];
		for (let i = startIndex; i < pairs.length; i += 1) {
			if (pairs[i][0] === '0') break;
			if (pairs[i][0] === code) result.push(pairs[i][1]);
		}
		return result;
	};
	const getEntityColor = (startIndex: number) => getNumber(startIndex, '62');
	const lines: DxfPreviewLine[] = [];
	const circles: DxfPreviewCircle[] = [];
	const arcs: DxfPreviewArc[] = [];
	const texts: DxfPreviewText[] = [];
	const fills: DxfPreviewFill[] = [];
	const points: Array<{ x: number; y: number }> = [];
	const corePoints: Array<{ x: number; y: number }> = [];
	const dimensionPoints: Array<{ x: number; y: number }> = [];
	const textPoints: Array<{ x: number; y: number }> = [];
	const blockDefinitions = new Map<string, DxfBlockDefinition>();
	let currentSection = '';
	let currentBlock: DxfBlockDefinition | null = null;
	const dimensionPattern = /dim|尺寸|标注|axis|grid|轴/i;
	const fixturePattern = /door|window|门|窗|furn|家具|fixture|fixed|洁具|cabinet|table|chair|desk|bed|sofa|toilet|wc|卫|柜|桌|椅|床|沙发|ds-fixt|ff-/i;
	const pushPoint = (x?: number, y?: number, layer?: string) => {
		if (typeof x !== 'number' || typeof y !== 'number' || !Number.isFinite(x) || !Number.isFinite(y)) return;
		points.push({ x, y });
		const layerText = layer ?? '';
		if (dimensionPattern.test(layerText)) {
			dimensionPoints.push({ x, y });
			return;
		}
		if (/furn|家具|洁具|plants|ff-furn/i.test(layerText)) return;
		corePoints.push({ x, y });
	};
	const pushLine = (line: DxfPreviewLine) => {
		lines.push(line);
		pushPoint(line.x1, line.y1, line.layer);
		pushPoint(line.x2, line.y2, line.layer);
	};
	const pushText = (text: DxfPreviewText) => {
		if (!text.text.trim()) return;
		texts.push(text);
		textPoints.push({ x: text.x, y: text.y });
		if (dimensionPattern.test(`${text.layer ?? ''} ${text.text}`)) dimensionPoints.push({ x: text.x, y: text.y });
	};
	const pushFill = (fill: DxfPreviewFill) => {
		if (fill.points.length < 3) return;
		// Fills do not participate in viewport bound estimation.
		// Some DXF HATCH entities expose boundary vertices in multiple loops,
		// and including them directly can explode the preview bounds.
		fills.push(fill);
	};
	const polygonArea = (pts: Array<{ x: number; y: number }>) => {
		let sum = 0;
		for (let i = 0; i < pts.length; i += 1) {
			const a = pts[i];
			const b = pts[(i + 1) % pts.length];
			sum += a.x * b.y - b.x * a.y;
		}
		return Math.abs(sum) * 0.5;
	};
	const decodeDxfText = (value: string) =>
		value
			.replace(/\\P/gi, ' ')
			.replace(/\\X/gi, ' ')
			.replace(/\\A\d+;/gi, '')
			.replace(/\\H[^;]+;/gi, '')
			.replace(/\\W[^;]+;/gi, '')
			.replace(/\\F[^;]+;/gi, '')
			.replace(/\\C\d+;/gi, '')
			.replace(/[{}]/g, '')
			.trim();
	const toRadians = (degrees: number) => (degrees * Math.PI) / 180;
	const transformPoint = (
		x: number, y: number,
		baseX: number, baseY: number,
		scaleX: number, scaleY: number,
		rotation: number,
		translateX: number, translateY: number,
	) => {
		const localX = (x - baseX) * scaleX;
		const localY = (y - baseY) * scaleY;
		const rad = toRadians(rotation);
		const cos = Math.cos(rad);
		const sin = Math.sin(rad);
		return {
			x: translateX + localX * cos - localY * sin,
			y: translateY + localX * sin + localY * cos,
		};
	};
	const parseTextEntity = (startIndex: number, type: 'TEXT' | 'MTEXT'): DxfPreviewText | null => {
		const x = getNumber(startIndex, '10');
		const y = getNumber(startIndex, '20');
		const height = getNumber(startIndex, '40') ?? 180;
		const rotation = getNumber(startIndex, '50') ?? 0;
		const layer = getString(startIndex, '8');
		const color = getEntityColor(startIndex);
		const chunks = type === 'MTEXT' ? [...getStrings(startIndex, '1'), ...getStrings(startIndex, '3')] : getStrings(startIndex, '1');
		const text = decodeDxfText(chunks.join(''));
		if (typeof x !== 'number' || typeof y !== 'number' || !text) return null;
		return { x, y, text, height, rotation, layer, color };
	};
	const parseInsertEntity = (startIndex: number) => {
		const name = getString(startIndex, '2');
		const x = getNumber(startIndex, '10');
		const y = getNumber(startIndex, '20');
		if (!name || typeof x !== 'number' || typeof y !== 'number') return null;
		return {
			type: 'insert' as const,
			payload: {
				name,
				x,
				y,
				scaleX: getNumber(startIndex, '41') ?? 1,
				scaleY: getNumber(startIndex, '42') ?? 1,
				rotation: getNumber(startIndex, '50') ?? 0,
				layer: getString(startIndex, '8'),
				color: getEntityColor(startIndex),
			},
		};
	};
	const resolveInheritedLayer = (layer: string | undefined, fallback: string | undefined) => (!layer || layer === '0' ? fallback : layer);
	const resolveInheritedColor = (color: number | undefined, fallback: number | undefined) => (color === undefined || color === 0 ? fallback : color);
	const getBlockEntitySearchText = (entity: DxfBlockEntity) => {
		switch (entity.type) {
			case 'line':
			case 'circle':
			case 'arc':
			case 'fill':
				return `${entity.payload.layer ?? ''}`;
			case 'text':
				return `${entity.payload.layer ?? ''} ${entity.payload.text}`;
			case 'insert':
				return `${entity.payload.layer ?? ''} ${entity.payload.name}`;
		}
	};
	const shouldExplodeTopLevelInsert = (insert: Extract<DxfBlockEntity, { type: 'insert' }>['payload']) => {
		const searchText = `${insert.layer ?? ''} ${insert.name}`;
		if (dimensionPattern.test(searchText) || fixturePattern.test(searchText) || /^\*d\d+$/i.test(insert.name)) return true;
		const block = blockDefinitions.get(insert.name);
		if (!block || block.entities.length === 0 || block.entities.length > 180) return false;
		const blockSearchText = `${block.name} ${block.entities.map(getBlockEntitySearchText).join(' ')}`;
		const looksLikeDimension = /^\*d\d+$/i.test(block.name) || (block.entities.some((entity) => entity.type === 'text') && dimensionPattern.test(blockSearchText));
		const looksLikeFixture = fixturePattern.test(blockSearchText);
		return looksLikeDimension || looksLikeFixture;
	};
	const pushBlockEntity = (entity: DxfBlockEntity | null) => {
		if (!currentBlock || !entity) return;
		currentBlock.entities.push(entity);
	};
	const materializeInsert = (
		insert: Extract<DxfBlockEntity, { type: 'insert' }>['payload'],
		depth = 0,
		visited = new Set<string>()
	) => {
		if (depth > 4 || visited.has(insert.name)) return;
		const block = blockDefinitions.get(insert.name);
		if (!block) return;
		visited.add(insert.name);
		for (const entity of block.entities) {
			if (lines.length + circles.length + arcs.length + texts.length + fills.length >= maxEntities) break;
			if (entity.type === 'line') {
				const p1 = transformPoint(entity.payload.x1, entity.payload.y1, block.baseX, block.baseY, insert.scaleX, insert.scaleY, insert.rotation, insert.x, insert.y);
				const p2 = transformPoint(entity.payload.x2, entity.payload.y2, block.baseX, block.baseY, insert.scaleX, insert.scaleY, insert.rotation, insert.x, insert.y);
				pushLine({
					...entity.payload,
					x1: p1.x,
					y1: p1.y,
					x2: p2.x,
					y2: p2.y,
					layer: resolveInheritedLayer(entity.payload.layer, insert.layer),
					color: resolveInheritedColor(entity.payload.color, insert.color),
				});
			} else if (entity.type === 'circle') {
				const center = transformPoint(entity.payload.cx, entity.payload.cy, block.baseX, block.baseY, insert.scaleX, insert.scaleY, insert.rotation, insert.x, insert.y);
				const radiusScale = (Math.abs(insert.scaleX) + Math.abs(insert.scaleY)) / 2;
				const layer = resolveInheritedLayer(entity.payload.layer, insert.layer);
				circles.push({ ...entity.payload, cx: center.x, cy: center.y, r: entity.payload.r * radiusScale, layer, color: resolveInheritedColor(entity.payload.color, insert.color) });
				pushPoint(center.x - entity.payload.r * radiusScale, center.y - entity.payload.r * radiusScale, layer);
				pushPoint(center.x + entity.payload.r * radiusScale, center.y + entity.payload.r * radiusScale, layer);
			} else if (entity.type === 'arc') {
				const center = transformPoint(entity.payload.cx, entity.payload.cy, block.baseX, block.baseY, insert.scaleX, insert.scaleY, insert.rotation, insert.x, insert.y);
				const radiusScale = (Math.abs(insert.scaleX) + Math.abs(insert.scaleY)) / 2;
				const layer = resolveInheritedLayer(entity.payload.layer, insert.layer);
				arcs.push({
					...entity.payload,
					cx: center.x,
					cy: center.y,
					r: entity.payload.r * radiusScale,
					start: entity.payload.start + insert.rotation,
					end: entity.payload.end + insert.rotation,
					layer,
					color: resolveInheritedColor(entity.payload.color, insert.color),
				});
				pushPoint(center.x - entity.payload.r * radiusScale, center.y - entity.payload.r * radiusScale, layer);
				pushPoint(center.x + entity.payload.r * radiusScale, center.y + entity.payload.r * radiusScale, layer);
			} else if (entity.type === 'text') {
				const point = transformPoint(entity.payload.x, entity.payload.y, block.baseX, block.baseY, insert.scaleX, insert.scaleY, insert.rotation, insert.x, insert.y);
				pushText({
					...entity.payload,
					x: point.x,
					y: point.y,
					height: entity.payload.height * Math.max(Math.abs(insert.scaleY), 0.01),
					rotation: (entity.payload.rotation ?? 0) + insert.rotation,
					layer: resolveInheritedLayer(entity.payload.layer, insert.layer),
					color: resolveInheritedColor(entity.payload.color, insert.color),
				});
			} else if (entity.type === 'insert') {
				const point = transformPoint(entity.payload.x, entity.payload.y, block.baseX, block.baseY, insert.scaleX, insert.scaleY, insert.rotation, insert.x, insert.y);
				materializeInsert(
					{
						...entity.payload,
						x: point.x,
						y: point.y,
						scaleX: entity.payload.scaleX * insert.scaleX,
						scaleY: entity.payload.scaleY * insert.scaleY,
						rotation: entity.payload.rotation + insert.rotation,
						layer: resolveInheritedLayer(entity.payload.layer, insert.layer),
						color: resolveInheritedColor(entity.payload.color, insert.color),
					},
					depth + 1,
					new Set(visited)
				);
			} else if (entity.type === 'fill') {
				const layer = resolveInheritedLayer(entity.payload.layer, insert.layer);
				const color = resolveInheritedColor(entity.payload.color, insert.color);
				const points = entity.payload.points.map((p) =>
					transformPoint(p.x, p.y, block.baseX, block.baseY, insert.scaleX, insert.scaleY, insert.rotation, insert.x, insert.y)
				);
				pushFill({ points, layer, color });
			}
		}
	};
	const maxEntities = 50000;
	for (let i = 0; i < pairs.length && lines.length + circles.length + arcs.length + texts.length + fills.length < maxEntities; i += 1) {
		const [code, value] = pairs[i];
		if (code === '0' && value === 'SECTION') {
			currentSection = pairs[i + 1]?.[0] === '2' ? pairs[i + 1][1].toUpperCase() : '';
			continue;
		}
		if (code === '0' && value === 'ENDSEC') {
			if (currentSection === 'BLOCKS' && currentBlock) {
				blockDefinitions.set(currentBlock.name, currentBlock);
				currentBlock = null;
			}
			currentSection = '';
			continue;
		}
		if (code !== '0') continue;
		if (currentSection === 'BLOCKS') {
			if (value === 'BLOCK') {
				currentBlock = {
					name: getString(i + 1, '2') ?? getString(i + 1, '3') ?? `block-${i}`,
					baseX: getNumber(i + 1, '10') ?? 0,
					baseY: getNumber(i + 1, '20') ?? 0,
					entities: [],
				};
				continue;
			}
			if (value === 'ENDBLK') {
				if (currentBlock) blockDefinitions.set(currentBlock.name, currentBlock);
				currentBlock = null;
				continue;
			}
			if (!currentBlock) continue;
			if (value === 'LINE') {
				const x1 = getNumber(i + 1, '10');
				const y1 = getNumber(i + 1, '20');
				const x2 = getNumber(i + 1, '11');
				const y2 = getNumber(i + 1, '21');
				if ([x1, y1, x2, y2].every((number) => typeof number === 'number')) {
					pushBlockEntity({ type: 'line', payload: { x1: x1!, y1: y1!, x2: x2!, y2: y2!, layer: getString(i + 1, '8'), color: getEntityColor(i + 1) } });
				}
			} else if (value === 'LWPOLYLINE') {
				const layer = getString(i + 1, '8');
				const color = getEntityColor(i + 1);
				const flags = getNumber(i + 1, '70') ?? 0;
				const vertices: Array<{ x: number; y: number }> = [];
				for (let j = i + 1; j < pairs.length && pairs[j][0] !== '0'; j += 1) {
					if (pairs[j][0] === '10') {
						const x = Number(pairs[j][1]);
						const yPair = pairs.slice(j + 1, Math.min(j + 8, pairs.length)).find((pair) => pair[0] === '20');
						const y = yPair ? Number(yPair[1]) : NaN;
						if (Number.isFinite(x) && Number.isFinite(y)) vertices.push({ x, y });
					}
				}
				for (let j = 0; j < vertices.length - 1; j += 1) {
					pushBlockEntity({ type: 'line', payload: { x1: vertices[j].x, y1: vertices[j].y, x2: vertices[j + 1].x, y2: vertices[j + 1].y, layer, color } });
				}
				if ((flags & 1) === 1 && vertices.length > 2) {
					const first = vertices[0];
					const last = vertices[vertices.length - 1];
					pushBlockEntity({ type: 'line', payload: { x1: last.x, y1: last.y, x2: first.x, y2: first.y, layer, color } });
					if (!fixturePattern.test(layer ?? '') && !dimensionPattern.test(layer ?? '')) {
						pushBlockEntity({ type: 'fill', payload: { points: vertices, layer, color, source: 'polyline' } });
					}
				}
			} else if (value === 'POLYLINE') {
				const layer = getString(i + 1, '8');
				const color = getEntityColor(i + 1);
				const flags = getNumber(i + 1, '70') ?? 0;
				const vertices: Array<{ x: number; y: number }> = [];
				let cursor = i + 1;
				while (cursor < pairs.length) {
					const [vertexCode, vertexValue] = pairs[cursor];
					if (vertexCode === '0' && vertexValue === 'SEQEND') {
						i = cursor;
						break;
					}
					if (vertexCode === '0' && vertexValue === 'VERTEX') {
						const x = getNumber(cursor + 1, '10');
						const y = getNumber(cursor + 1, '20');
						if (typeof x === 'number' && typeof y === 'number') vertices.push({ x, y });
					}
					cursor += 1;
				}
				for (let j = 0; j < vertices.length - 1; j += 1) {
					pushBlockEntity({ type: 'line', payload: { x1: vertices[j].x, y1: vertices[j].y, x2: vertices[j + 1].x, y2: vertices[j + 1].y, layer, color } });
				}
				if ((flags & 1) === 1 && vertices.length > 2) {
					const first = vertices[0];
					const last = vertices[vertices.length - 1];
					pushBlockEntity({ type: 'line', payload: { x1: last.x, y1: last.y, x2: first.x, y2: first.y, layer, color } });
					if (!fixturePattern.test(layer ?? '') && !dimensionPattern.test(layer ?? '')) {
						pushBlockEntity({ type: 'fill', payload: { points: vertices, layer, color, source: 'polyline' } });
					}
				}
			} else if (value === 'SOLID') {
				const layer = getString(i + 1, '8');
				const color = getEntityColor(i + 1);
				const p1 = { x: getNumber(i + 1, '10'), y: getNumber(i + 1, '20') };
				const p2 = { x: getNumber(i + 1, '11'), y: getNumber(i + 1, '21') };
				const p3 = { x: getNumber(i + 1, '12'), y: getNumber(i + 1, '22') };
				const p4 = { x: getNumber(i + 1, '13'), y: getNumber(i + 1, '23') };
				const raw = [p1, p2, p3, p4].filter((p) => typeof p.x === 'number' && typeof p.y === 'number') as Array<{ x: number; y: number }>;
				if (raw.length >= 3) pushBlockEntity({ type: 'fill', payload: { points: raw, layer, color, source: 'solid' } });
			} else if (value === 'HATCH') {
				const layer = getString(i + 1, '8');
				const color = getEntityColor(i + 1);
				const xs = getStrings(i + 1, '10').map(Number).filter((v) => Number.isFinite(v));
				const ys = getStrings(i + 1, '20').map(Number).filter((v) => Number.isFinite(v));
				const count = Math.min(xs.length, ys.length);
				const pts: Array<{ x: number; y: number }> = [];
				for (let k = 0; k < count; k += 1) pts.push({ x: xs[k], y: ys[k] });
				// HATCH parsing is conservative to avoid malformed boundary loops exploding geometry.
				if (pts.length >= 3 && pts.length <= 64 && /hatch|填充|solid/i.test(layer ?? '')) {
					pushBlockEntity({ type: 'fill', payload: { points: pts, layer, color, source: 'hatch' } });
				}
			} else if (value === 'CIRCLE') {
				const cx = getNumber(i + 1, '10');
				const cy = getNumber(i + 1, '20');
				const r = getNumber(i + 1, '40');
				if (typeof cx === 'number' && typeof cy === 'number' && typeof r === 'number' && r > 0) {
					pushBlockEntity({ type: 'circle', payload: { cx, cy, r, layer: getString(i + 1, '8'), color: getEntityColor(i + 1) } });
				}
			} else if (value === 'ARC') {
				const cx = getNumber(i + 1, '10');
				const cy = getNumber(i + 1, '20');
				const r = getNumber(i + 1, '40');
				const start = getNumber(i + 1, '50');
				const end = getNumber(i + 1, '51');
				if (typeof cx === 'number' && typeof cy === 'number' && typeof r === 'number' && typeof start === 'number' && typeof end === 'number' && r > 0) {
					pushBlockEntity({ type: 'arc', payload: { cx, cy, r, start, end, layer: getString(i + 1, '8'), color: getEntityColor(i + 1) } });
				}
			} else if (value === 'TEXT' || value === 'MTEXT') {
				pushBlockEntity(parseTextEntity(i + 1, value === 'TEXT' ? 'TEXT' : 'MTEXT') ? { type: 'text', payload: parseTextEntity(i + 1, value === 'TEXT' ? 'TEXT' : 'MTEXT')! } : null);
			} else if (value === 'INSERT') {
				pushBlockEntity(parseInsertEntity(i + 1));
			}
			continue;
		}
		if (currentSection !== 'ENTITIES') continue;
		const spaceFlag = getNumber(i + 1, '67');
		if (spaceFlag === 1) continue;
		if (value === 'LINE') {
			const layer = getString(i + 1, '8');
			const color = getEntityColor(i + 1);
			const x1 = getNumber(i + 1, '10');
			const y1 = getNumber(i + 1, '20');
			const x2 = getNumber(i + 1, '11');
			const y2 = getNumber(i + 1, '21');
			if ([x1, y1, x2, y2].every((number) => typeof number === 'number')) pushLine({ x1: x1!, y1: y1!, x2: x2!, y2: y2!, layer, color });
		} else if (value === 'LWPOLYLINE') {
			const layer = getString(i + 1, '8');
			const color = getEntityColor(i + 1);
			const flags = getNumber(i + 1, '70') ?? 0;
			const vertices: Array<{ x: number; y: number }> = [];
			for (let j = i + 1; j < pairs.length && pairs[j][0] !== '0'; j += 1) {
				if (pairs[j][0] === '10') {
					const x = Number(pairs[j][1]);
					const yPair = pairs.slice(j + 1, Math.min(j + 8, pairs.length)).find((pair) => pair[0] === '20');
					const y = yPair ? Number(yPair[1]) : NaN;
					if (Number.isFinite(x) && Number.isFinite(y)) vertices.push({ x, y });
				}
			}
			for (let j = 0; j < vertices.length - 1; j += 1) pushLine({ x1: vertices[j].x, y1: vertices[j].y, x2: vertices[j + 1].x, y2: vertices[j + 1].y, layer, color });
			if ((flags & 1) === 1 && vertices.length > 2) {
				const first = vertices[0];
				const last = vertices[vertices.length - 1];
				pushLine({ x1: last.x, y1: last.y, x2: first.x, y2: first.y, layer, color });
				if (!fixturePattern.test(layer ?? '') && !dimensionPattern.test(layer ?? '')) {
					pushFill({ points: vertices, layer, color, source: 'polyline' });
				}
			}
		} else if (value === 'POLYLINE') {
			const layer = getString(i + 1, '8');
			const color = getEntityColor(i + 1);
			const flags = getNumber(i + 1, '70') ?? 0;
			const vertices: Array<{ x: number; y: number }> = [];
			let cursor = i + 1;
			while (cursor < pairs.length) {
				const [vertexCode, vertexValue] = pairs[cursor];
				if (vertexCode === '0' && vertexValue === 'SEQEND') {
					i = cursor;
					break;
				}
				if (vertexCode === '0' && vertexValue === 'VERTEX') {
					const x = getNumber(cursor + 1, '10');
					const y = getNumber(cursor + 1, '20');
					if (typeof x === 'number' && typeof y === 'number') vertices.push({ x, y });
				}
				cursor += 1;
			}
			for (let j = 0; j < vertices.length - 1; j += 1) pushLine({ x1: vertices[j].x, y1: vertices[j].y, x2: vertices[j + 1].x, y2: vertices[j + 1].y, layer, color });
			if ((flags & 1) === 1 && vertices.length > 2) {
				const first = vertices[0];
				const last = vertices[vertices.length - 1];
				pushLine({ x1: last.x, y1: last.y, x2: first.x, y2: first.y, layer, color });
				if (!fixturePattern.test(layer ?? '') && !dimensionPattern.test(layer ?? '')) {
					pushFill({ points: vertices, layer, color, source: 'polyline' });
				}
			}
		} else if (value === 'SOLID') {
			const layer = getString(i + 1, '8');
			const color = getEntityColor(i + 1);
			const p1 = { x: getNumber(i + 1, '10'), y: getNumber(i + 1, '20') };
			const p2 = { x: getNumber(i + 1, '11'), y: getNumber(i + 1, '21') };
			const p3 = { x: getNumber(i + 1, '12'), y: getNumber(i + 1, '22') };
			const p4 = { x: getNumber(i + 1, '13'), y: getNumber(i + 1, '23') };
			const raw = [p1, p2, p3, p4].filter((p) => typeof p.x === 'number' && typeof p.y === 'number') as Array<{ x: number; y: number }>;
			if (raw.length >= 3) pushFill({ points: raw, layer, color, source: 'solid' });
		} else if (value === 'HATCH') {
			const layer = getString(i + 1, '8');
			const color = getEntityColor(i + 1);
			const xs = getStrings(i + 1, '10').map(Number).filter((v) => Number.isFinite(v));
			const ys = getStrings(i + 1, '20').map(Number).filter((v) => Number.isFinite(v));
			const count = Math.min(xs.length, ys.length);
			const pts: Array<{ x: number; y: number }> = [];
			for (let k = 0; k < count; k += 1) pts.push({ x: xs[k], y: ys[k] });
			if (pts.length >= 3 && pts.length <= 64 && /hatch|填充|solid/i.test(layer ?? '')) {
				pushFill({ points: pts, layer, color, source: 'hatch' });
			}
		} else if (value === 'CIRCLE') {
			const layer = getString(i + 1, '8');
			const color = getEntityColor(i + 1);
			const cx = getNumber(i + 1, '10');
			const cy = getNumber(i + 1, '20');
			const r = getNumber(i + 1, '40');
			if (typeof cx === 'number' && typeof cy === 'number' && typeof r === 'number' && r > 0) {
				circles.push({ cx, cy, r, layer, color });
				pushPoint(cx - r, cy - r);
				pushPoint(cx + r, cy + r);
			}
		} else if (value === 'ARC') {
			const layer = getString(i + 1, '8');
			const color = getEntityColor(i + 1);
			const cx = getNumber(i + 1, '10');
			const cy = getNumber(i + 1, '20');
			const r = getNumber(i + 1, '40');
			const start = getNumber(i + 1, '50');
			const end = getNumber(i + 1, '51');
			if (typeof cx === 'number' && typeof cy === 'number' && typeof r === 'number' && typeof start === 'number' && typeof end === 'number' && r > 0) {
				arcs.push({ cx, cy, r, start, end, layer, color });
				pushPoint(cx - r, cy - r, layer);
				pushPoint(cx + r, cy + r, layer);
			}
		} else if (value === 'TEXT' || value === 'MTEXT') {
			const textEntity = parseTextEntity(i + 1, value === 'TEXT' ? 'TEXT' : 'MTEXT');
			if (textEntity) pushText(textEntity);
		} else if (value === 'DIMENSION') {
			const blockName = getString(i + 1, '2');
			if (blockName) {
				materializeInsert({
					name: blockName,
					x: 0,
					y: 0,
					scaleX: 1,
					scaleY: 1,
					rotation: 0,
					layer: getString(i + 1, '8'),
					color: getEntityColor(i + 1),
				});
			}
		} else if (value === 'INSERT') {
			const insertEntity = parseInsertEntity(i + 1);
			if (insertEntity && shouldExplodeTopLevelInsert(insertEntity.payload)) materializeInsert(insertEntity.payload);
		}
	}
	if (points.length === 0 && textPoints.length === 0) return { lines: [], circles: [], arcs: [], texts: [], fills: [], width: 1, height: 1, entityCount: 0 };
	const primaryBoundPoints = corePoints.length > 12 ? corePoints : points.length > 0 ? points : textPoints;
	const primaryX = primaryBoundPoints.map((point) => point.x);
	const primaryY = primaryBoundPoints.map((point) => point.y);
	const baseMinX = Math.min(...primaryX);
	const baseMaxX = Math.max(...primaryX);
	const baseMinY = Math.min(...primaryY);
	const baseMaxY = Math.max(...primaryY);
	const baseWidth = Math.max(1, baseMaxX - baseMinX);
	const baseHeight = Math.max(1, baseMaxY - baseMinY);
	const marginX = baseWidth * 0.22;
	const marginY = baseHeight * 0.22;
	const nearbyPoints = points.filter(
		(point) =>
			point.x >= baseMinX - marginX &&
			point.x <= baseMaxX + marginX &&
			point.y >= baseMinY - marginY &&
			point.y <= baseMaxY + marginY
	);
	const nearbyTextPoints = textPoints.filter(
		(point) =>
			point.x >= baseMinX - marginX &&
			point.x <= baseMaxX + marginX &&
			point.y >= baseMinY - marginY &&
			point.y <= baseMaxY + marginY
	);
	const boundPoints = [...(nearbyPoints.length > 0 ? nearbyPoints : primaryBoundPoints), ...nearbyTextPoints];
	const allX = boundPoints.map((point) => point.x);
	const allY = boundPoints.map((point) => point.y);
	const paddingX = Math.max(baseWidth * 0.04, 120);
	const paddingY = Math.max(baseHeight * 0.06, 120);
	const minX = Math.min(...allX) - paddingX;
	const maxX = Math.max(...allX) + paddingX;
	const minY = Math.min(...allY) - paddingY;
	const maxY = Math.max(...allY) + paddingY;
	const sourceWidth = Math.max(1, maxX - minX);
	const sourceHeight = Math.max(1, maxY - minY);
	const targetWidth = 1400;
	const targetHeight = Math.max(520, targetWidth * (sourceHeight / sourceWidth));
	const intersectsBounds = (left: number, top: number, right: number, bottom: number) =>
		right >= minX && left <= maxX && bottom >= minY && top <= maxY;
	const visibleLines = lines.filter((line) => {
		const left = Math.min(line.x1, line.x2);
		const right = Math.max(line.x1, line.x2);
		const top = Math.min(line.y1, line.y2);
		const bottom = Math.max(line.y1, line.y2);
		if (!intersectsBounds(left, top, right, bottom)) return false;
		return true;
	});
	const visibleCircles = circles.filter((circle) => intersectsBounds(circle.cx - circle.r, circle.cy - circle.r, circle.cx + circle.r, circle.cy + circle.r));
	const visibleArcs = arcs.filter((arc) => intersectsBounds(arc.cx - arc.r, arc.cy - arc.r, arc.cx + arc.r, arc.cy + arc.r));
	const visibleTexts = texts.filter((text) => text.x >= minX && text.x <= maxX && text.y >= minY && text.y <= maxY);
	const visibleFills = fills.filter((fill) => {
		const xs = fill.points.map((p) => p.x);
		const ys = fill.points.map((p) => p.y);
		if (xs.length < 3 || ys.length < 3) return false;
		const left = Math.min(...xs);
		const right = Math.max(...xs);
		const top = Math.min(...ys);
		const bottom = Math.max(...ys);
		if (!intersectsBounds(left, top, right, bottom)) return false;
		const dx = right - left;
		const dy = bottom - top;
		const diag = Math.hypot(sourceWidth, sourceHeight);
		const maxAllowedEdge = diag * 0.55;
		let maxEdge = 0;
		for (let i = 0; i < fill.points.length; i += 1) {
			const a = fill.points[i];
			const b = fill.points[(i + 1) % fill.points.length];
			maxEdge = Math.max(maxEdge, Math.hypot(a.x - b.x, a.y - b.y));
		}
		if (maxEdge > maxAllowedEdge) return false;
		// Reject obviously malformed fills that dwarf the drawing.
		const area = polygonArea(fill.points);
		const drawingArea = sourceWidth * sourceHeight;
		if (!Number.isFinite(area) || area <= 0) return false;
		if (area > drawingArea * 0.2) return false;
		if ((right - left) > sourceWidth * 0.85 && (bottom - top) > sourceHeight * 0.85) return false;
		// HATCH boundaries are noisy in many CAD exports; keep only compact hatch islands.
		if (fill.source === 'hatch' && (dx > sourceWidth * 0.35 || dy > sourceHeight * 0.35)) return false;
		if (fill.source === 'polyline' && fill.points.length > 24) return false;
		return true;
	});
	const normalizeX = (x: number) => ((x - minX) / sourceWidth) * targetWidth;
	const normalizeY = (y: number) => ((maxY - y) / sourceHeight) * targetHeight;
	return {
		lines: visibleLines.map((line) => ({ ...line, x1: normalizeX(line.x1), y1: normalizeY(line.y1), x2: normalizeX(line.x2), y2: normalizeY(line.y2) })),
		circles: visibleCircles.map((circle) => ({ ...circle, cx: normalizeX(circle.cx), cy: normalizeY(circle.cy), r: circle.r * (targetWidth / sourceWidth) })),
		arcs: visibleArcs.map((arc) => ({ ...arc, cx: normalizeX(arc.cx), cy: normalizeY(arc.cy), r: arc.r * (targetWidth / sourceWidth) })),
		texts: visibleTexts.map((text) => ({ ...text, x: normalizeX(text.x), y: normalizeY(text.y), height: text.height * (targetWidth / sourceWidth) })),
		fills: visibleFills.map((fill) => ({ ...fill, points: fill.points.map((p) => ({ x: normalizeX(p.x), y: normalizeY(p.y) })) })),
		width: targetWidth,
		height: targetHeight,
		entityCount: visibleLines.length + visibleCircles.length + visibleArcs.length + visibleTexts.length + visibleFills.length,
	};
};

export const describeArcPath = (arc: DxfPreviewArc): string => {
	const startRad = (-arc.start * Math.PI) / 180;
	const endRad = (-arc.end * Math.PI) / 180;
	const start = { x: arc.cx + arc.r * Math.cos(startRad), y: arc.cy + arc.r * Math.sin(startRad) };
	const end = { x: arc.cx + arc.r * Math.cos(endRad), y: arc.cy + arc.r * Math.sin(endRad) };
	const delta = ((arc.end - arc.start + 360) % 360) || 360;
	const largeArcFlag = delta > 180 ? 1 : 0;
	return `M ${start.x} ${start.y} A ${arc.r} ${arc.r} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`;
};

const ACI_PALETTE: Record<number, string> = {
	1: '#ef4444',
	2: '#facc15',
	3: '#22c55e',
	4: '#06b6d4',
	5: '#3b82f6',
	6: '#a855f7',
	7: '#e5e7eb',
};

const withAlpha = (hexOrColor: string, alpha = 1): string => {
	if (alpha >= 0.999) return hexOrColor;
	const color = hexOrColor.trim();
	if (/^rgba?\(/i.test(color)) return color;
	const m = color.match(/^#([0-9a-f]{6})$/i);
	if (!m) return color;
	const n = parseInt(m[1], 16);
	const r = (n >> 16) & 255;
	const g = (n >> 8) & 255;
	const b = n & 255;
	return `rgba(${r},${g},${b},${Math.max(0, Math.min(1, alpha))})`;
};

export const getDxfStroke = (entity: { color?: number; layer?: string }, alpha = 1): string => {
	const aci = Math.abs(entity.color ?? 0);
	if (ACI_PALETTE[aci]) return withAlpha(ACI_PALETTE[aci], alpha);
	const layer = (entity.layer ?? '').toLowerCase();
	if (/dim|尺寸|标注|axis|grid|轴/.test(layer)) return withAlpha('#a3e635', alpha);
	if (/wall|墙/.test(layer)) return withAlpha('#22d3ee', alpha);
	if (/door|门/.test(layer)) return withAlpha('#f97316', alpha);
	if (/window|窗/.test(layer)) return withAlpha('#60a5fa', alpha);
	if (/hatch|填充/.test(layer)) return withAlpha('#64748b', alpha);
	return withAlpha('#d1d5db', alpha);
};

export const getDxfTextFill = (entity: { color?: number; layer?: string }, alpha = 1): string => {
	const layer = (entity.layer ?? '').toLowerCase();
	if (/dim|尺寸|标注|axis|grid|轴/.test(layer)) return withAlpha('#facc15', alpha);
	return getDxfStroke(entity, alpha);
};

export const getDxfFill = (entity: { color?: number; layer?: string }, alpha = 1): string => {
	const aci = Math.abs(entity.color ?? 0);
	if (ACI_PALETTE[aci]) return withAlpha(ACI_PALETTE[aci], alpha);
	const layer = (entity.layer ?? '').toLowerCase();
	if (/hatch|填充/.test(layer)) return withAlpha('#7c8798', alpha);
	if (/wall|墙/.test(layer)) return withAlpha('#4b5563', alpha);
	return withAlpha('#6b7280', alpha);
};
