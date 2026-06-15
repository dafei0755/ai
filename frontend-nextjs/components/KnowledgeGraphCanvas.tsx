/**
 * 知识图谱画布组件
 * 使用 Canvas 绘制自定义网络图谱（类似 infranodus）
 */
'use client';

import { useEffect, useRef, useMemo, useState } from 'react';
import { generateClusteredGraphData } from '@/lib/mockGraphData';

export interface KnowledgeGraphCanvasProps {
	className?: string;
	onNodeClick?: (nodeId: string, label: string) => void;
}

interface NodePosition {
	x: number;
	y: number;
}

interface LabelCandidate {
	text: string;
	x: number;
	y: number;
	nodeX: number;
	nodeY: number;
	radius: number;
	font: string;
	fillStyle: string;
	strokeStyle: string;
	lineWidth: number;
	textAlign: CanvasTextAlign;
	textBaseline: CanvasTextBaseline;
	shadowColor: string;
	shadowBlur: number;
	priority: number;
	preferCentered: boolean;
}

interface ViewState {
	zoom: number;
	pan: {
		x: number;
		y: number;
	};
}

const MIN_ZOOM = 0.55;
const MAX_ZOOM = 10;
const INITIAL_FIT_PADDING_RATIO = 0.08;

function hexToRgba(hex: string, alpha: number) {
	const h = hex.replace('#', '');
	const normalized = h.length === 3 ? h.split('').map((ch) => ch + ch).join('') : h;
	const r = parseInt(normalized.substring(0, 2), 16);
	const g = parseInt(normalized.substring(2, 4), 16);
	const b = parseInt(normalized.substring(4, 6), 16);
	return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function clamp(num: number, min: number, max: number) {
	return Math.max(min, Math.min(max, num));
}

function rectsOverlap(
	a: { left: number; top: number; right: number; bottom: number },
	b: { left: number; top: number; right: number; bottom: number }
) {
	return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
}

function getLabelBounds(
	x: number,
	y: number,
	width: number,
	height: number,
	textAlign: CanvasTextAlign,
	paddingX: number,
	paddingY: number
) {
	const left =
		textAlign === 'center'
			? x - width / 2 - paddingX
			: textAlign === 'right'
			? x - width - paddingX
			: x - paddingX;
	const right =
		textAlign === 'center'
			? x + width / 2 + paddingX
			: textAlign === 'right'
			? x + paddingX
			: x + width + paddingX;
	return {
		left,
		top: y - height / 2 - paddingY,
		right,
		bottom: y + height / 2 + paddingY,
	};
}

function getLabelPlacementOptions(candidate: LabelCandidate) {
	const baseOffset = candidate.radius + 8;
	const steps = [0, 12, 24, 40, 60];

	if (candidate.preferCentered) {
		return [
			{ dx: 0, dy: 0, textAlign: 'center' as CanvasTextAlign },
			...steps.flatMap((extra) => [
				{ dx: 0, dy: -(baseOffset + extra), textAlign: 'center' as CanvasTextAlign },
				{ dx: 0, dy: baseOffset + extra, textAlign: 'center' as CanvasTextAlign },
				{ dx: baseOffset + extra, dy: 0, textAlign: 'left' as CanvasTextAlign },
				{ dx: -(baseOffset + extra), dy: 0, textAlign: 'right' as CanvasTextAlign },
				{ dx: baseOffset + extra, dy: -(baseOffset * 0.42 + extra * 0.35), textAlign: 'left' as CanvasTextAlign },
				{ dx: baseOffset + extra, dy: baseOffset * 0.42 + extra * 0.35, textAlign: 'left' as CanvasTextAlign },
				{ dx: -(baseOffset + extra), dy: -(baseOffset * 0.42 + extra * 0.35), textAlign: 'right' as CanvasTextAlign },
				{ dx: -(baseOffset + extra), dy: baseOffset * 0.42 + extra * 0.35, textAlign: 'right' as CanvasTextAlign },
			]),
		];
	}

	return steps.flatMap((extra) => [
		{ dx: baseOffset + extra, dy: 0, textAlign: 'left' as CanvasTextAlign },
		{ dx: baseOffset + extra, dy: -(baseOffset * 0.5 + extra * 0.35), textAlign: 'left' as CanvasTextAlign },
		{ dx: baseOffset + extra, dy: baseOffset * 0.5 + extra * 0.35, textAlign: 'left' as CanvasTextAlign },
		{ dx: 0, dy: -(baseOffset + extra), textAlign: 'center' as CanvasTextAlign },
		{ dx: 0, dy: baseOffset + extra, textAlign: 'center' as CanvasTextAlign },
		{ dx: -(baseOffset + extra), dy: 0, textAlign: 'right' as CanvasTextAlign },
		{ dx: -(baseOffset + extra), dy: -(baseOffset * 0.5 + extra * 0.35), textAlign: 'right' as CanvasTextAlign },
		{ dx: -(baseOffset + extra), dy: baseOffset * 0.5 + extra * 0.35, textAlign: 'right' as CanvasTextAlign },
	]);
}

function zoomAroundPoint(
	view: ViewState,
	pointerX: number,
	pointerY: number,
	factor: number,
	viewportWidth: number,
	viewportHeight: number
): ViewState {
	const nextZoom = clamp(view.zoom * factor, MIN_ZOOM, MAX_ZOOM);
	if (nextZoom === view.zoom) return view;

	const centerX = viewportWidth / 2;
	const centerY = viewportHeight / 2;
	const worldX = (pointerX - centerX - view.pan.x) / view.zoom;
	const worldY = (pointerY - centerY - view.pan.y) / view.zoom;

	return {
		zoom: nextZoom,
		pan: {
			x: pointerX - centerX - worldX * nextZoom,
			y: pointerY - centerY - worldY * nextZoom,
		},
	};
}

function getInitialFittedView(
	nodePositions: Record<string, NodePosition>,
	viewportWidth: number,
	viewportHeight: number
): ViewState {
	const positions = Object.values(nodePositions);
	if (positions.length === 0) {
		return {
			zoom: 1,
			pan: { x: 0, y: 0 },
		};
	}

	let minX = Infinity;
	let maxX = -Infinity;
	let minY = Infinity;
	let maxY = -Infinity;

	positions.forEach(({ x, y }) => {
		if (x < minX) minX = x;
		if (x > maxX) maxX = x;
		if (y < minY) minY = y;
		if (y > maxY) maxY = y;
	});

	const graphWidth = Math.max(1, maxX - minX);
	const graphHeight = Math.max(1, maxY - minY);
	const paddedWidth = Math.max(1, viewportWidth * (1 - INITIAL_FIT_PADDING_RATIO * 2));
	const paddedHeight = Math.max(1, viewportHeight * (1 - INITIAL_FIT_PADDING_RATIO * 2));
	const nextZoom = clamp(Math.min(paddedWidth / graphWidth, paddedHeight / graphHeight), MIN_ZOOM, MAX_ZOOM);
	const graphCenterX = (minX + maxX) / 2;
	const graphCenterY = (minY + maxY) / 2;

	return {
		zoom: nextZoom,
		pan: {
			x: -graphCenterX * nextZoom,
			y: -graphCenterY * nextZoom,
		},
	};
}

export function KnowledgeGraphCanvas({
	className = '',
	onNodeClick,
}: KnowledgeGraphCanvasProps) {
	const containerRef = useRef<HTMLDivElement>(null);
	const canvasRef = useRef<HTMLCanvasElement>(null);
	const hasInitializedViewRef = useRef(false);
	const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
	const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
	const [viewState, setViewState] = useState<ViewState>({
		zoom: 1,
		pan: { x: 0, y: 0 },
	});
	const dragRef = useRef<{ active: boolean; x: number; y: number }>({
		active: false,
		x: 0,
		y: 0,
	});
	const { zoom, pan } = viewState;

	// 生成并初始化图数据
	const graphData = useMemo(() => generateClusteredGraphData(), []);

	// 计算节点位置（力导向布局的简化版本）
	const nodePositions = useMemo(() => {
		const positions: Record<string, NodePosition> = {};
		const spacing = 108;
		const clusterKeys = Array.from(
			new Set(
				graphData.nodes
					.filter((n) => (n.cluster ?? '') !== 'bridge')
					.map((n) => n.cluster ?? n.color)
			)
		).sort();
		const clusterAnchors = new Map<string, NodePosition>();
		const ringRadius = 175;

		clusterKeys.forEach((key, idx) => {
			const angle = (idx / Math.max(clusterKeys.length, 1)) * Math.PI * 2;
			clusterAnchors.set(key, {
				x: Math.cos(angle) * ringRadius,
				y: Math.sin(angle) * ringRadius,
			});
		});

		// 初始化随机位置
		graphData.nodes.forEach((node) => {
			const clusterKey = node.cluster ?? node.color;
			const isBridge = clusterKey === 'bridge';
			const anchor = isBridge
				? { x: 0, y: 0 }
				: clusterAnchors.get(clusterKey) ?? { x: 0, y: 0 };
			const jitter = isBridge ? 95 : node.category === 'core' ? 92 : 165;
			positions[node.id] = {
				x: anchor.x + (Math.random() * 2 - 1) * jitter,
				y: anchor.y + (Math.random() * 2 - 1) * jitter,
			};
		});

		// 迭代松弛布局
		for (let iteration = 0; iteration < 42; iteration++) {
			graphData.nodes.forEach((node) => {
				let forceX = 0;
				let forceY = 0;
				const clusterKey = node.cluster ?? node.color;
				const isBridge = clusterKey === 'bridge';
				const anchor = isBridge
					? { x: 0, y: 0 }
					: clusterAnchors.get(clusterKey) ?? { x: 0, y: 0 };

				// 节点间斥力
				graphData.nodes.forEach((otherNode) => {
					if (node.id === otherNode.id) return;
					const dx = positions[otherNode.id].x - positions[node.id].x;
					const dy = positions[otherNode.id].y - positions[node.id].y;
					const dist = Math.sqrt(dx * dx + dy * dy) || 1;
					const repulsion = -(spacing * 0.66) / dist;
					forceX += (dx / dist) * repulsion;
					forceY += (dy / dist) * repulsion;
				});

				// 连接吸引力
				graphData.edges.forEach((edge) => {
					if (edge.source === node.id) {
						const dx = positions[edge.target].x - positions[node.id].x;
						const dy = positions[edge.target].y - positions[node.id].y;
						const dist = Math.sqrt(dx * dx + dy * dy) || 1;
						const attraction = dist * 0.072;
						forceX += (dx / dist) * attraction;
						forceY += (dy / dist) * attraction;
					} else if (edge.target === node.id) {
						const dx = positions[edge.source].x - positions[node.id].x;
						const dy = positions[edge.source].y - positions[node.id].y;
						const dist = Math.sqrt(dx * dx + dy * dy) || 1;
						const attraction = dist * 0.072;
						forceX += (dx / dist) * attraction;
						forceY += (dy / dist) * attraction;
					}
				});

				// 应用力
				forceX += (anchor.x - positions[node.id].x) * (isBridge ? 0.016 : 0.0065);
				forceY += (anchor.y - positions[node.id].y) * (isBridge ? 0.016 : 0.0065);

				// 全局向心力：避免分裂成多个孤立团块，形成连续网络
				forceX += -positions[node.id].x * 0.0082;
				forceY += -positions[node.id].y * 0.0082;

				positions[node.id].x += forceX * 0.032;
				positions[node.id].y += forceY * 0.032;
			});
		}

		return positions;
	}, [graphData]);

	useEffect(() => {
		if (hasInitializedViewRef.current || !containerRef.current) return;
		const rect = containerRef.current.getBoundingClientRect();
		if (!rect.width || !rect.height) return;

		setViewState(getInitialFittedView(nodePositions, rect.width, rect.height));
		hasInitializedViewRef.current = true;
	}, [nodePositions]);

	useEffect(() => {
		if (!canvasRef.current || !containerRef.current) return;

		const canvas = canvasRef.current;
		const ctx = canvas.getContext('2d');
		if (!ctx) return;

		// 设置 canvas 大小
		const rect = containerRef.current.getBoundingClientRect();
		canvas.width = rect.width;
		canvas.height = rect.height;

		const width = canvas.width;
		const height = canvas.height;
		const centerX = width / 2;
		const centerY = height / 2;

		const adjacency = new Map<string, Set<string>>();
		graphData.nodes.forEach((n) => adjacency.set(n.id, new Set<string>()));
		graphData.edges.forEach((e) => {
			adjacency.get(e.source)?.add(e.target);
			adjacency.get(e.target)?.add(e.source);
		});
		const nodeMap = new Map(graphData.nodes.map((n) => [n.id, n]));

		const worldToScreen = (p: NodePosition) => ({
			x: centerX + p.x * zoom + pan.x,
			y: centerY + p.y * zoom + pan.y,
		});

		// 清空背景
		ctx.fillStyle = '#020403';
		ctx.fillRect(0, 0, width, height);

		const selectedSet = new Set(selectedNodeIds);
		const activeSet = new Set<string>(selectedSet);
		const labelCandidates: LabelCandidate[] = [];
		selectedNodeIds.forEach((sid) => {
			adjacency.get(sid)?.forEach((nid) => activeSet.add(nid));
		});
		const hasSelection = selectedSet.size > 0;
		const isNodeActive = (id: string) => !hasSelection || activeSet.has(id);

		// 绘制边
		graphData.edges.forEach((edge) => {
			const source = nodePositions[edge.source];
			const target = nodePositions[edge.target];
			if (source && target) {
				const s = worldToScreen(source);
				const t = worldToScreen(target);
				const sourceNode = nodeMap.get(edge.source);
				const targetNode = nodeMap.get(edge.target);
				const sourceColor = sourceNode?.color ?? '#6b7280';
				const targetColor = targetNode?.color ?? '#6b7280';
				const edgeIsActive =
					!hasSelection ||
					(selectedSet.has(edge.source) && activeSet.has(edge.target)) ||
					(selectedSet.has(edge.target) && activeSet.has(edge.source)) ||
					(selectedSet.has(edge.source) && selectedSet.has(edge.target));
				const lineWidthBase = edgeIsActive
					? clamp(0.8 + edge.weight * 1.8, 0.8, 3)
					: clamp(0.5 + edge.weight * 1.1, 0.5, 1.8);
				const lineWidth = lineWidthBase * 0.5;

				const dx = t.x - s.x;
				const dy = t.y - s.y;
				const dist = Math.hypot(dx, dy) || 1;
				const nx = -dy / dist;
				const ny = dx / dist;
				const direction = edge.source < edge.target ? 1 : -1;
				const curve = clamp(dist * 0.16, 12, 52) * direction;
				const cx = (s.x + t.x) / 2 + nx * curve;
				const cy = (s.y + t.y) / 2 + ny * curve;

				const gradient = ctx.createLinearGradient(s.x, s.y, t.x, t.y);
				if (edgeIsActive) {
					gradient.addColorStop(0, sourceColor);
					gradient.addColorStop(0.5, sourceColor);
					gradient.addColorStop(1, targetColor);
				} else {
					gradient.addColorStop(0, '#2b2e34');
					gradient.addColorStop(1, '#2b2e34');
				}

				ctx.strokeStyle = gradient;
				ctx.lineWidth = lineWidth;
				ctx.shadowBlur = 0;
				ctx.beginPath();
				ctx.moveTo(s.x, s.y);
				ctx.quadraticCurveTo(cx, cy, t.x, t.y);
				ctx.stroke();
			}
		});

		// 绘制节点
		graphData.nodes.forEach((node) => {
			const pos = nodePositions[node.id];
			if (!pos) return;

			const { x, y } = worldToScreen(pos);
			const isSelected = selectedSet.has(node.id);
			const isSelectedNeighbor =
				!isSelected && selectedNodeIds.some((sid) => adjacency.get(sid)?.has(node.id));
			const nodeIsActive = isNodeActive(node.id);
			const radiusBase = clamp(node.size * 0.88, 6, 28);
			const radius = isSelected
				? radiusBase * 1.24
				: isSelectedNeighbor
				? radiusBase * 1.08
				: radiusBase;

			// 节点圆形
			ctx.fillStyle = nodeIsActive ? node.color : '#272a2f';
			ctx.beginPath();
			ctx.arc(x, y, radius, 0, Math.PI * 2);
			ctx.fill();

			// 标签
			const showLabel =
				isSelected ||
				Boolean(isSelectedNeighbor) ||
				node.category === 'core' ||
				node.size >= 13 ||
				zoom > 0.95;
			if (showLabel) {
				const labelSize = node.category === 'core'
					? clamp(17 + zoom * 1.2, 17, 26)
					: clamp(10 + zoom * 0.8, 10, 18);
				const font = `${node.category === 'core' ? '700' : nodeIsActive ? '500' : '400'} ${labelSize}px sans-serif`;
				const textAlign = node.category === 'core' ? 'center' : 'left';
				const maxChars = zoom >= 2 ? 999 : node.category === 'core' ? 10 : 6;
				const label = node.label.length > maxChars ? node.label.substring(0, maxChars) + '…' : node.label;
				const labelX = node.category === 'core' ? x : x + radius + 4;
				const labelY = node.category === 'core' ? y : y - radius * 0.08;
				const priority =
					(isSelected ? 4000 : 0) +
					(isSelectedNeighbor ? 2000 : 0) +
					(node.category === 'core' ? 1000 : 0) +
					Math.round(radius * 10);
				labelCandidates.push({
					text: label,
					x: labelX,
					y: labelY,
					nodeX: x,
					nodeY: y,
					radius,
					font,
					fillStyle: nodeIsActive ? '#ffffff' : '#a7adb7',
					strokeStyle: nodeIsActive ? 'rgba(0,0,0,0.39)' : 'rgba(0,0,0,0.18)',
					lineWidth: node.category === 'core' ? 1.5 : 1,
					textAlign,
					textBaseline: 'middle',
					shadowColor: 'rgba(0, 0, 0, 0.6)',
					shadowBlur: 4,
					priority,
					preferCentered: node.category === 'core',
				});
			}
		});

		labelCandidates
			.sort((a, b) => b.priority - a.priority)
			.reduce<Array<{ left: number; top: number; right: number; bottom: number }>>((placed, candidate) => {
				ctx.font = candidate.font;
				const metrics = ctx.measureText(candidate.text);
				const width = metrics.width;
				const fontSize = Number.parseFloat(candidate.font.match(/(\d+(?:\.\d+)?)px/)?.[1] ?? '12');
				const paddingX = 4;
				const paddingY = 2;
				const placementOptions = getLabelPlacementOptions(candidate);

				for (const option of placementOptions) {
					const drawX = candidate.nodeX + option.dx;
					const drawY = candidate.nodeY + option.dy;
					const bounds = getLabelBounds(
						drawX,
						drawY,
						width,
						fontSize,
						option.textAlign,
						paddingX,
						paddingY
					);
					if (placed.some((existing) => rectsOverlap(existing, bounds))) {
						continue;
					}

					ctx.fillStyle = candidate.fillStyle;
					ctx.font = candidate.font;
					ctx.textAlign = option.textAlign;
					ctx.textBaseline = candidate.textBaseline;
					ctx.shadowColor = candidate.shadowColor;
					ctx.shadowBlur = candidate.shadowBlur;
					ctx.strokeStyle = candidate.strokeStyle;
					ctx.lineWidth = candidate.lineWidth;
					ctx.strokeText(candidate.text, drawX, drawY);
					ctx.fillText(candidate.text, drawX, drawY);
					ctx.shadowBlur = 0;
					placed.push(bounds);
					return placed;
				}

				return placed;
			}, []);

		// 点击处理
		const handleClick = (e: MouseEvent) => {
			if (dragRef.current.active) return;
			const additive = e.shiftKey || e.ctrlKey || e.metaKey;
			const rect = canvas.getBoundingClientRect();
			const clickX = e.clientX - rect.left;
			const clickY = e.clientY - rect.top;
			let hitNodeId: string | null = null;

			graphData.nodes.forEach((node) => {
				const pos = nodePositions[node.id];
				if (!pos) return;
				const { x, y } = worldToScreen(pos);
				const radius = clamp(node.size * 0.88, 6, 28);
				const distance = Math.hypot(clickX - x, clickY - y);
				if (distance < radius + 6) {
					hitNodeId = node.id;
					onNodeClick?.(node.id, node.label);
				}
			});

			if (hitNodeId) {
				const picked = hitNodeId;
				setSelectedNodeIds((prev) => {
					if (additive) {
						return prev.includes(picked)
							? prev.filter((id) => id !== picked)
							: [...prev, picked];
					}

					return prev.length === 1 && prev[0] === picked ? [] : [picked];
				});
			} else {
				setSelectedNodeIds([]);
			}
		};

		// 悬停处理
		const handleMouseMove = (e: MouseEvent) => {
			if (dragRef.current.active) {
				const dx = e.clientX - dragRef.current.x;
				const dy = e.clientY - dragRef.current.y;
				dragRef.current.x = e.clientX;
				dragRef.current.y = e.clientY;
				setViewState((prev) => ({
					...prev,
					pan: { x: prev.pan.x + dx, y: prev.pan.y + dy },
				}));
				return;
			}

			const rect = canvas.getBoundingClientRect();
			const moveX = e.clientX - rect.left;
			const moveY = e.clientY - rect.top;

			let hovered: string | null = null;
			graphData.nodes.forEach((node) => {
				const pos = nodePositions[node.id];
				if (!pos) return;
				const { x, y } = worldToScreen(pos);
				const radius = clamp(node.size * 0.88, 6, 28);
				const distance = Math.hypot(moveX - x, moveY - y);
				if (distance < radius + 8) {
					hovered = node.id;
				}
			});

			if (hovered !== hoveredNodeId) {
				setHoveredNodeId(hovered);
				canvas.style.cursor = hovered ? 'pointer' : 'default';
			}
		};

		const handleMouseLeave = () => {
			setHoveredNodeId(null);
			canvas.style.cursor = 'default';
			dragRef.current.active = false;
		};

		const handleMouseDown = (e: MouseEvent) => {
			dragRef.current = { active: true, x: e.clientX, y: e.clientY };
			canvas.style.cursor = 'grabbing';
		};

		const handleMouseUp = () => {
			dragRef.current.active = false;
			canvas.style.cursor = hoveredNodeId ? 'pointer' : 'default';
		};

		const handleWheel = (e: WheelEvent) => {
			e.preventDefault();
			const rect = canvas.getBoundingClientRect();
			const pointerX = e.clientX - rect.left;
			const pointerY = e.clientY - rect.top;
			const factor = Math.exp(-e.deltaY * 0.0015);
			setViewState((prev) => zoomAroundPoint(prev, pointerX, pointerY, factor, rect.width, rect.height));
		};

		canvas.addEventListener('click', handleClick);
		canvas.addEventListener('mousemove', handleMouseMove);
		canvas.addEventListener('mouseleave', handleMouseLeave);
		canvas.addEventListener('mousedown', handleMouseDown);
		window.addEventListener('mouseup', handleMouseUp);
		canvas.addEventListener('wheel', handleWheel, { passive: false });

		return () => {
			canvas.removeEventListener('click', handleClick);
			canvas.removeEventListener('mousemove', handleMouseMove);
			canvas.removeEventListener('mouseleave', handleMouseLeave);
			canvas.removeEventListener('mousedown', handleMouseDown);
			window.removeEventListener('mouseup', handleMouseUp);
			canvas.removeEventListener('wheel', handleWheel);
		};
	}, [graphData, hoveredNodeId, nodePositions, onNodeClick, pan.x, pan.y, selectedNodeIds, zoom]);

	// 监听容器大小变化
	useEffect(() => {
		const handleResize = () => {
			if (canvasRef.current && containerRef.current) {
				const rect = containerRef.current.getBoundingClientRect();
				canvasRef.current.width = rect.width;
				canvasRef.current.height = rect.height;
			}
		};

		window.addEventListener('resize', handleResize);
		return () => window.removeEventListener('resize', handleResize);
	}, []);

	return (
		<div
			ref={containerRef}
			className={`w-full h-full bg-[var(--canvas-bg)] relative overflow-hidden ${className}`}
			style={{ backgroundColor: 'var(--canvas-bg)' }}
		>
			<canvas
				ref={canvasRef}
				className="absolute inset-0 w-full h-full"
				style={{ display: 'block' }}
			/>

			<div className="absolute left-3 bottom-3 z-20 rounded-md border border-white/10 bg-black/55 px-2.5 py-1.5 text-[11px] text-white/75">
				滚轮缩放 · 拖拽平移 · Shift/Ctrl/Cmd 可加选 · 当前 {zoom.toFixed(2)}x
			</div>
		</div>
	);
}


