/**
 * 知识图谱模拟数据生成器
 * 生成类似 infranodus 风格的节点和连线数据
 */

export interface GraphNode {
	id: string;
	label: string;
	color: string;
	size: number;
	category: 'core' | 'concept' | 'method' | 'tool' | 'outcome';
	cluster?: string;
}

export interface GraphEdge {
	source: string;
	target: string;
	weight: number;
	label?: string;
}

export interface GraphData {
	nodes: GraphNode[];
	edges: GraphEdge[];
}

function createSeededRandom(seed = 20260330) {
	let state = seed >>> 0;
	return () => {
		state = (state * 1664525 + 1013904223) >>> 0;
		return state / 4294967296;
	};
}

// 颜色定义（类似 infranodus 的彩虹色系）
const CATEGORY_COLORS: Record<GraphNode['category'], string> = {
	core: '#FF6B9D', // 粉红
	concept: '#C44569', // 红
	method: '#F8B500', // 金黄
	tool: '#4DB6AC', // 青绿
	outcome: '#7986CB', // 紫蓝
};

const CORE_NODES = [
	'生活方式设计',
	'可持续发展',
	'文化创意',
	'建筑美学',
	'社区建设',
];

const CONCEPT_NODES = [
	'创新',
	'和谐',
	'文明',
	'生态',
	'人文',
	'艺术',
	'设计思维',
	'跨界融合',
	'传统与现代',
	'审美',
	'生态平衡',
	'社会责任',
	'文化特性',
	'品质生活',
	'空间体验',
	'共享经济',
	'数字赋能',
	'系统思维',
	'时间维度',
	'全球视野',
];

const METHOD_NODES = [
	'需求分析',
	'系统规划',
	'方案设计',
	'迭代优化',
	'用户研究',
	'数据分析',
	'模式识别',
	'关键路径法',
	'敏捷开发',
	'价值评估',
];

const TOOL_NODES = [
	'设计工具',
	'数据可视化',
	'协作平台',
	'原型工具',
	'分析框架',
	'评估体系',
];

const OUTCOME_NODES = [
	'战略方案',
	'落地路线图',
	'价值模型',
	'创新产品',
	'生态系统',
	'标准体系',
];

/**
 * 生成模拟的知识图谱数据
 */
export function generateMockGraphData(): GraphData {
	const nodes: GraphNode[] = [];
	let nodeId = 0;

	// 添加核心节点
	CORE_NODES.forEach((label) => {
		nodes.push({
			id: `node-${nodeId++}`,
			label,
			color: CATEGORY_COLORS.core,
			size: 35,
			category: 'core',
		});
	});

	const coreNodeCount = nodes.length;

	// 添加概念节点
	CONCEPT_NODES.forEach((label) => {
		nodes.push({
			id: `node-${nodeId++}`,
			label,
			color: CATEGORY_COLORS.concept,
			size: Math.random() * 15 + 8,
			category: 'concept',
		});
	});

	// 添加方法节点
	METHOD_NODES.forEach((label) => {
		nodes.push({
			id: `node-${nodeId++}`,
			label,
			color: CATEGORY_COLORS.method,
			size: Math.random() * 12 + 6,
			category: 'method',
		});
	});

	// 添加工具节点
	TOOL_NODES.forEach((label) => {
		nodes.push({
			id: `node-${nodeId++}`,
			label,
			color: CATEGORY_COLORS.tool,
			size: Math.random() * 12 + 6,
			category: 'tool',
		});
	});

	// 添加结果节点
	OUTCOME_NODES.forEach((label) => {
		nodes.push({
			id: `node-${nodeId++}`,
			label,
			color: CATEGORY_COLORS.outcome,
			size: Math.random() * 14 + 8,
			category: 'outcome',
		});
	});

	// 生成连线
	const edges: GraphEdge[] = [];

	// 核心节点间的连接
	for (let i = 0; i < coreNodeCount; i++) {
		for (let j = i + 1; j < coreNodeCount; j++) {
			if (Math.random() > 0.4) {
				edges.push({
					source: nodes[i].id,
					target: nodes[j].id,
					weight: Math.random() * 0.8 + 0.3,
				});
			}
		}
	}

	// 核心节点到其他节点的连接
	nodes.forEach((node, idx) => {
		if (node.category !== 'core') {
			// 每个非核心节点连接到 1-3 个核心节点
			const coreConnections = Math.floor(Math.random() * 3) + 1;
			for (let i = 0; i < coreConnections; i++) {
				const coreIdx = Math.floor(Math.random() * coreNodeCount);
				edges.push({
					source: nodes[coreIdx].id,
					target: node.id,
					weight: Math.random() * 0.7 + 0.2,
				});
			}

			// 连接到相同或相邻类别的节点
			const otherNodes = nodes.filter((n, i) => i !== idx && n.category === node.category);
			const sameCategory = Math.floor(Math.random() * 2);
			for (let i = 0; i < sameCategory && otherNodes.length > 0; i++) {
				const targetIdx = Math.floor(Math.random() * otherNodes.length);
				const targetNode = otherNodes[targetIdx];
				edges.push({
					source: node.id,
					target: targetNode.id,
					weight: Math.random() * 0.5 + 0.1,
				});
			}
		}
	});

	// 移除重复的边
	const edgeSet = new Set<string>();
	const uniqueEdges = edges.filter((edge) => {
		const key = [edge.source, edge.target].sort().join('-');
		if (edgeSet.has(key)) {
			return false;
		}
		edgeSet.add(key);
		return true;
	});

	return {
		nodes,
		edges: uniqueEdges,
	};
}

/**
 * 生成具有集群结构的图数据（更像 infranodus）
 */
export function generateClusteredGraphData(): GraphData {
	const nodes: GraphNode[] = [];
	const edges: GraphEdge[] = [];
	let nodeId = 0;
	const rand = createSeededRandom(2511180444);

	const clusters = [
		{
			name: '自然生态',
			color: '#8BC34A',
			concepts: ['山地', '溪谷', '森林', '雾气', '光影', '气候', '雨季', '季风', '石材', '木作', '苔藓', '生态', '生境', '海拔', '土壤', '坡地'],
		},
		{
			name: '文化叙事',
			color: '#B388FF',
			concepts: ['在地', '手工', '纹样', '民俗', '仪式', '语境', '记忆', '故事', '历史', '节庆', '传承', '地域性', '语义', '符号', '叙述', '文脉'],
		},
		{
			name: '空间体验',
			color: '#FF80AB',
			concepts: ['动线', '停留', '开合', '尺度', '界面', '转场', '序列', '视线', '私密', '共享', '社交', '休憩', '归属', '沉浸', '松弛', '漫游'],
		},
		{
			name: '品牌表达',
			color: '#40C4FF',
			concepts: ['年轻', '克制', '功能主义', '辨识度', '视觉系统', '品牌语气', '一致性', '记忆点', '调性', '场景化', '标签', '审美', '风格', '表达', '形象', '口碑'],
		},
		{
			name: '材料工艺',
			color: '#FFD54F',
			concepts: ['木饰面', '石材', '金属', '织物', '漆面', '构造', '节点', '触感', '耐久', '维护', '预算', '替代', '工法', '样板', '细部', '收口'],
		},
		{
			name: '运营策略',
			color: '#FFAB40',
			concepts: ['客群', '收益', '转化', '复购', '入住率', '淡旺季', '服务', '效率', '成本', '定价', '套餐', '营销', '渠道', '活动', '体验包', '社媒'],
		},
		{
			name: '智能系统',
			color: '#64FFDA',
			concepts: ['传感器', '照明控制', '能耗', '安防', '数据看板', '自动化', '联动', 'AI助手', '预测', '维护计划', '可视化', '监测', '反馈', '调优', '告警', '流程'],
		},
		{
			name: '设计方法',
			color: '#F06292',
			concepts: ['调研', '共创', '原型', '迭代', '评审', '验证', '复盘', '对标', '拆解', '推演', '决策', '优先级', '路线图', '里程碑', '风险', '假设'],
		},
	] as const;

	const clusterCenters: Record<string, string> = {};
	const clusterConceptMap: Record<string, string[]> = {};

	clusters.forEach((cluster, clusterIndex) => {
		const centerId = `node-${nodeId++}`;
		clusterCenters[cluster.name] = centerId;
		clusterConceptMap[cluster.name] = [];

		nodes.push({
			id: centerId,
			label: cluster.name,
			color: cluster.color,
			size: 20 + Math.floor(rand() * 8),
			category: 'core',
			cluster: cluster.name,
		});

		cluster.concepts.forEach((concept, idx) => {
			const conceptId = `node-${nodeId++}`;
			clusterConceptMap[cluster.name].push(conceptId);
			const category: GraphNode['category'] =
				idx % 5 === 0 ? 'method' : idx % 4 === 0 ? 'tool' : idx % 3 === 0 ? 'outcome' : 'concept';

			nodes.push({
				id: conceptId,
				label: concept,
				color: cluster.color,
				size: 8 + Math.floor(rand() * 8),
				category,
				cluster: cluster.name,
			});

			edges.push({
				source: centerId,
				target: conceptId,
				weight: 0.42 + rand() * 0.48,
			});

			if (idx > 0) {
				const prevId = clusterConceptMap[cluster.name][idx - 1];
				edges.push({
					source: conceptId,
					target: prevId,
					weight: 0.24 + rand() * 0.42,
				});
			}

			if (idx > 2 && rand() > 0.2) {
				const randomPeer = clusterConceptMap[cluster.name][Math.floor(rand() * idx)];
				edges.push({
					source: conceptId,
					target: randomPeer,
					weight: 0.26 + rand() * 0.4,
				});
			}

			if (idx > 4) {
				const ringTarget = clusterConceptMap[cluster.name][idx - 4];
				edges.push({
					source: conceptId,
					target: ringTarget,
					weight: 0.2 + rand() * 0.35,
				});
			}
		});
	});

	const bridgeNodes = [
		{ label: '塔莎框架', color: '#1EA7FD', size: 24, links: ['文化叙事', '空间体验', '品牌表达', '设计方法'] },
		{ label: '生活', color: '#35D07F', size: 22, links: ['自然生态', '空间体验', '运营策略'] },
		{ label: '哲学', color: '#BADA55', size: 20, links: ['文化叙事', '设计方法', '品牌表达'] },
	] as const;

	const bridgeIds: string[] = [];
	bridgeNodes.forEach((hub) => {
		const id = `node-${nodeId++}`;
		bridgeIds.push(id);
		nodes.push({
			id,
			label: hub.label,
			color: hub.color,
			size: hub.size,
			category: 'core',
			cluster: 'bridge',
		});

		hub.links.forEach((clusterName) => {
			edges.push({
				source: id,
				target: clusterCenters[clusterName],
				weight: 0.56 + rand() * 0.28,
			});

			const concepts = clusterConceptMap[clusterName];
			for (let i = 0; i < 3; i++) {
				const target = concepts[Math.floor(rand() * concepts.length)];
				edges.push({ source: id, target, weight: 0.34 + rand() * 0.26 });
			}
		});
	});

	const relationGraph: Array<[string, string, number]> = [
		['自然生态', '材料工艺', 0.68],
		['自然生态', '空间体验', 0.62],
		['文化叙事', '品牌表达', 0.66],
		['文化叙事', '空间体验', 0.58],
		['空间体验', '运营策略', 0.64],
		['品牌表达', '运营策略', 0.61],
		['材料工艺', '智能系统', 0.56],
		['设计方法', '品牌表达', 0.59],
		['设计方法', '智能系统', 0.57],
		['智能系统', '运营策略', 0.54],
	];

	relationGraph.forEach(([a, b, w]) => {
		edges.push({ source: clusterCenters[a], target: clusterCenters[b], weight: w });

		const aConcepts = clusterConceptMap[a];
		const bConcepts = clusterConceptMap[b];
		const bridgeCount = 2 + Math.floor(rand() * 2);
		for (let i = 0; i < bridgeCount; i++) {
			edges.push({
				source: aConcepts[Math.floor(rand() * aConcepts.length)],
				target: bConcepts[Math.floor(rand() * bConcepts.length)],
				weight: 0.24 + rand() * 0.24,
			});
		}
	});

	const bridgeTerms = [
		{ term: '年轻', clusters: ['品牌表达', '文化叙事'] },
		{ term: '克制', clusters: ['品牌表达', '空间体验'] },
		{ term: '功能主义', clusters: ['品牌表达', '设计方法', '材料工艺'] },
		{ term: '山地民宿', clusters: ['自然生态', '空间体验', '运营策略'] },
		{ term: '自然景观', clusters: ['自然生态', '空间体验'] },
		{ term: '轻度度假', clusters: ['运营策略', '空间体验'] },
		{ term: '品牌辨识', clusters: ['品牌表达', '文化叙事'] },
		{ term: '公共社交', clusters: ['空间体验', '运营策略'] },
		{ term: '客房体验', clusters: ['空间体验', '材料工艺'] },
		{ term: '可持续', clusters: ['自然生态', '材料工艺', '智能系统'] },
	] as const;

	const bridgeTermIds: string[] = [];
	bridgeTerms.forEach((item, idx) => {
		const id = `node-${nodeId++}`;
		bridgeTermIds.push(id);
		nodes.push({
			id,
			label: item.term,
			color: idx % 2 === 0 ? '#F48FB1' : '#AED581',
			size: 11 + Math.floor(rand() * 7),
			category: idx % 3 === 0 ? 'outcome' : 'method',
			cluster: 'bridge',
		});

		item.clusters.forEach((clusterName) => {
			edges.push({ source: id, target: clusterCenters[clusterName], weight: 0.35 + rand() * 0.3 });
			const concepts = clusterConceptMap[clusterName];
			edges.push({ source: id, target: concepts[Math.floor(rand() * concepts.length)], weight: 0.24 + rand() * 0.22 });
		});

		edges.push({ source: id, target: bridgeIds[Math.floor(rand() * bridgeIds.length)], weight: 0.4 + rand() * 0.2 });
	});

	for (let i = 0; i < bridgeTermIds.length - 1; i++) {
		if (rand() > 0.45) {
			edges.push({ source: bridgeTermIds[i], target: bridgeTermIds[i + 1], weight: 0.22 + rand() * 0.2 });
		}
	}

	const edgeSet = new Set<string>();
	const uniqueEdges = edges.filter((edge) => {
		if (edge.source === edge.target) return false;
		const key = [edge.source, edge.target].sort().join('__');
		if (edgeSet.has(key)) return false;
		edgeSet.add(key);
		return true;
	});

	return { nodes, edges: uniqueEdges };
}
