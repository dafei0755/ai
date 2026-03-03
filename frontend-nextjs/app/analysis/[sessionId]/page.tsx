'use client';

import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
	Loader2,
	WifiOff,
	X,
	PanelLeft,
	Plus,
	CheckCircle2,
	AlertCircle,
	MoreVertical,
	Edit2,
	Pin,
	Share2,
	Trash2,
	ArrowLeft
} from 'lucide-react';
import { api } from '@/lib/api';
import { WebSocketClient, type WebSocketMessage } from '@/lib/websocket';
import { QuestionnaireModal } from '@/components/QuestionnaireModal';
import { ConfirmationModal } from '@/components/ConfirmationModal';
import {
	OutputIntentConfirmationModal,
	type OutputIntentConfirmPayload
} from '@/components/OutputIntentConfirmationModal';
import { RoleTaskReviewModal } from '@/components/RoleTaskReviewModal';
import { UserQuestionModal } from '@/components/UserQuestionModal';
import { UnifiedProgressiveQuestionnaireModal } from '@/components/UnifiedProgressiveQuestionnaireModal';
import { QualityPreflightModal } from '@/components/QualityPreflightModal';
import { UserQuestionCard } from '@/components/UserQuestionCard';
import type { AnalysisStatus, SessionStatus } from '@/types';
import type { NodeStatus } from '@/types/workflow';
// v7.290: 分析页面改为独立体验，移除侧边栏组件

// 节点名称中文映射
const NODE_NAME_MAP: Record<string, string> = {
	// 输入验证阶段
	input_guard: '安全内容检测',
	unified_input_validator_initial: '初始输入验证',
	unified_input_validator_secondary: '二次输入验证',
	domain_validator: '领域适配性验证',

	// 需求分析阶段
	requirements_analyst: '用户需求分析',
	requirement_collection: '需求信息收集',
	feasibility_analyst: '可行性分析',
	calibration_questionnaire: '战略校准问卷',
	requirements_confirmation: '需求确认 (已废弃 v7.151)',  // 🔧 仅用于旧会话显示
	requirement_confirmation: '需求确认 (已废弃 v7.151)',   // 别名兼容

	// 任务规划阶段
	role_task_unified_review: '任务审批',
	quality_preflight: '质量预检',
	project_director: '项目拆分',
	strategic_analysis: '战略分析',

	// 专家执行阶段
	batch_execution: '专家团队分析',
	batch_executor: '准备专家分析',
	agent_executor: '专家分析执行中',
	batch_router: '分析进度汇总',
	batch_aggregator: '专家成果整合',
	batch_strategy_review: '方案策略评审',
	parallel_analysis: '专家并行分析',

	// 审核阶段
	result_aggregator: '生成分析报告',
	result_aggregation: '结果聚合',
	analysis_review: '质量审核',
	manual_review: '人工审核',
	conduct_red_review: '红队审核',
	conduct_blue_review: '蓝队审核',
	conduct_judge_review: '评委裁决',
	conduct_client_review: '甲方审核',
	detect_challenges: '挑战检测',
	final_review: '最终审核',
	result_review: '结果审核',
	report_guard: '报告安全审核',  // 🔥 v7.21: 添加缺失的节点

	// 完成阶段
	pdf_generator: '生成PDF文档',
	pdf_generation: 'PDF生成中',
	user_question: '解答用户追问',
	interrupt: '等待用户输入',
	completed: '分析已完成',
	waiting_for_input: '等待用户输入',

	// 🔥 v7.7: 状态值映射
	init: '初始化中',
	error: '发生错误',
	running: '运行中',
	processing: '处理中',
	failed: '执行失败',

	// 英文描述映射（后端可能返回的英文描述）
	'Initial input validation': '初始输入验证',
	'Secondary input validation': '二次输入验证',
	'Domain validation': '领域验证',
	'Requirements analysis': '需求分析',
	'Feasibility analysis': '可行性分析',
	'Calibration questionnaire': '战略校准问卷',
	'Requirements confirmation': '需求确认',
	'Project director': '项目拆分',
	'Quality preflight': '质量预检',
	'Batch execution': '批次执行',
	'Result aggregation': '结果聚合',
	'PDF generation': 'PDF生成',
	'Completed': '已完成',
	'Waiting for input': '等待输入',
	'User requirements analysis': '用户需求分析'
};

// 格式化节点名称：优先使用中文映射，支持模糊匹配
const formatNodeName = (nodeName: string | undefined): string => {
	if (!nodeName) return '准备中...';

	// 1. 精确匹配
	if (NODE_NAME_MAP[nodeName]) {
		return NODE_NAME_MAP[nodeName];
	}

	// 2. 小写匹配
	const lowerName = nodeName.toLowerCase();
	if (NODE_NAME_MAP[lowerName]) {
		return NODE_NAME_MAP[lowerName];
	}

	// 3. 下划线转换匹配（如 requirement_collection -> RequirementCollection）
	for (const [key, value] of Object.entries(NODE_NAME_MAP)) {
		if (key.toLowerCase() === lowerName ||
		    key.toLowerCase().replace(/_/g, '') === lowerName.replace(/_/g, '').replace(/ /g, '')) {
			return value;
		}
	}

	// 4. 如果还是英文，尝试返回一个友好的格式
	// 将 snake_case 转换为标题格式，但标记为未翻译
	if (/^[a-z_]+$/.test(nodeName)) {
		console.warn(`[formatNodeName] 未映射的英文节点名: ${nodeName}`);
	}

	return NODE_NAME_MAP[nodeName] || nodeName;
};

const STEP_LABEL_MAP: Record<string, string> = {
	step1_core_task: '任务梳理',
	step2_info_gap: '信息补全',
	step3_radar: '偏好雷达图',
	requirements_insight: '需求洞察',
	output_intent_confirmation: '输出意图确认'
};

const INTERACTION_STEP_ID_MAP: Record<string, string> = {
	progressive_questionnaire_step1: 'step1_core_task',
	progressive_questionnaire_step2: 'step2_info_gap',
	progressive_questionnaire_step3: 'step3_radar',
	progressive_questionnaire_step4: 'requirements_insight',
	requirements_insight: 'requirements_insight'
};

const formatActiveStep = (stepId: string): string => STEP_LABEL_MAP[stepId] || stepId;

export default function AnalysisPage() {
	const params = useParams();
	const router = useRouter();
	const sessionId = params.sessionId as string;

	const [status, setStatus] = useState<AnalysisStatus | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [wsConnected, setWsConnected] = useState<boolean>(false);
	const [userInput, setUserInput] = useState<string>(''); // v7.290: 用户输入（用于显示用户问题卡片）
	const [nodeHistory, setNodeHistory] = useState<Array<{ node: string; detail: string; time: string }>>([]);
	const [nodeDetails, setNodeDetails] = useState<Record<string, { status: NodeStatus; detail?: string }>>({});

	// 问卷状态
	const [showQuestionnaire, setShowQuestionnaire] = useState<boolean>(false);
	const [questionnaireData, setQuestionnaireData] = useState<any>(null);

	// 需求确认状态
	const [showConfirmation, setShowConfirmation] = useState<boolean>(false);
	const [confirmationData, setConfirmationData] = useState<any>(null);
	const [showOutputIntentModal, setShowOutputIntentModal] = useState<boolean>(false);
	const [outputIntentData, setOutputIntentData] = useState<any>(null);

	// 用户追问状态
	const [showUserQuestion, setShowUserQuestion] = useState<boolean>(false);
	const [userQuestionData, setUserQuestionData] = useState<any>(null);
	const [userQuestionSubmitting, setUserQuestionSubmitting] = useState<boolean>(false);

	// 角色任务审核状态
	const [roleTaskReviewData, setRoleTaskReviewData] = useState<any>(null);
	const [showRoleTaskReview, setShowRoleTaskReview] = useState(false);

	// 🆕 v7.130: 三步递进式问卷 - 统一状态管理
	// currentProgressiveStep: 0=关闭, 1=任务梳理, 2=信息补全, 3=雷达图
	const [currentProgressiveStep, setCurrentProgressiveStep] = useState<number>(0);
	const [progressiveStepData, setProgressiveStepData] = useState<any>(null);

	// 🆕 v7.119: 质量预检警告状态
	const [qualityPreflightData, setQualityPreflightData] = useState<any>(null);
	const [showQualityPreflight, setShowQualityPreflight] = useState(false);

	// 节点详情面板状态
	const [selectedNode, setSelectedNode] = useState<string | null>(null);

	// v7.290: 移除侧边栏状态，独立分析体验

	const wsClientRef = useRef<WebSocketClient | null>(null);
	const hasRedirectedRef = useRef<boolean>(false);

	const activeProgressiveSteps = useMemo(() => {
		const fromStatus = status?.active_steps;
		if (!fromStatus || fromStatus.length === 0) {
			return ['step1_core_task', 'step2_info_gap', 'step3_radar', 'requirements_insight'];
		}
		return fromStatus;
	}, [status?.active_steps]);

	const resolveProgressiveStepNumber = useCallback((interactionType: string): number => {
		const stepId = INTERACTION_STEP_ID_MAP[interactionType];
		if (stepId) {
			const idx = activeProgressiveSteps.indexOf(stepId);
			if (idx >= 0) {
				return idx + 1;
			}
		}

		if (interactionType === 'progressive_questionnaire_step1') return 1;
		if (interactionType === 'progressive_questionnaire_step2') return 2;
		if (interactionType === 'progressive_questionnaire_step3') return 3;
		if (interactionType === 'progressive_questionnaire_step4' || interactionType === 'requirements_insight') return 4;

		return 0;
	}, [activeProgressiveSteps]);

	const navigateToReport = useCallback(() => {
		if (hasRedirectedRef.current) {
			return;
		}
		hasRedirectedRef.current = true;
		router.push(`/report/${sessionId}`);
	}, [router, sessionId]);

	const applyInterruptDispatch = useCallback((interruptData: any) => {
		if (!interruptData) {
			return;
		}

		const interactionType = interruptData.interaction_type;
		const dynamicStepNumber = resolveProgressiveStepNumber(interactionType);

		if (interactionType === 'calibration_questionnaire') {
			setQuestionnaireData(interruptData.questionnaire);
			setShowQuestionnaire(true);
			console.log('📋 检测到待处理的问卷');
		} else if (interactionType === 'role_and_task_unified_review') {
			if (interruptData.close_previous_modal) {
				console.log('🔧 [v7.153] 收到 close_previous_modal 指令，关闭 progressive questionnaire');
				setCurrentProgressiveStep(0);
				setProgressiveStepData(null);
			}
			setRoleTaskReviewData(interruptData);
			setShowRoleTaskReview(true);
			console.log('📋 检测到待审核的角色任务');
		} else if (interactionType === 'user_question') {
			setUserQuestionData(interruptData);
			setShowUserQuestion(true);
			console.log('📋 检测到待处理的用户追问');
		} else if (interactionType === 'batch_confirmation') {
			console.log('📦 收到批次确认请求，自动批准执行');
			console.log(`  批次 ${interruptData.current_batch}/${interruptData.total_batches}: ${interruptData.agents_in_batch?.join(', ')}`);
			api.resumeAnalysis(sessionId, 'approve').catch((err: any) => {
				console.error('❌ 自动批准批次失败:', err);
			});
		} else if (interactionType === 'progressive_questionnaire_step1') {
			setProgressiveStepData(interruptData);
			setCurrentProgressiveStep(dynamicStepNumber || 1);
			console.log('📋 检测到待处理的第1步 - 任务梳理');
		} else if (interactionType === 'progressive_questionnaire_step2') {
			setProgressiveStepData(interruptData);
			setCurrentProgressiveStep(dynamicStepNumber || 2);
			console.log('📋 检测到待处理的第2步 - 信息补全');
		} else if (interactionType === 'progressive_questionnaire_step3') {
			console.log('📋 检测到待处理的第3步 - 雷达图维度选择');
			console.log('🔍 [Step3] dimensions 类型:', typeof interruptData.dimensions);
			console.log('🔍 [Step3] dimensions 是否为数组:', Array.isArray(interruptData.dimensions));
			if (interruptData.dimensions) {
				console.log('🔍 [Step3] dimensions 数量:', Array.isArray(interruptData.dimensions) ? interruptData.dimensions.length : 'N/A');
			}
			setProgressiveStepData(interruptData);
			setCurrentProgressiveStep(dynamicStepNumber || 3);
		} else if (interactionType === 'progressive_questionnaire_step4' || interactionType === 'requirements_insight') {
			console.log('📋 检测到待处理的第4步 - 需求洞察');
			console.log('🔍 [Step4] restructured_requirements:', interruptData.restructured_requirements ? '已包含' : '缺失');
			console.log('🔍 [Step4] project_essence:', interruptData.project_essence ? '已包含' : '缺失');
			setProgressiveStepData(interruptData);
			setCurrentProgressiveStep(dynamicStepNumber || 4);
		} else if (interactionType === 'quality_preflight_warning') {
			setQualityPreflightData(interruptData);
			setShowQualityPreflight(true);
			console.log('⚠️ 检测到质量预检警告');
		} else if (interactionType === 'output_intent_confirmation') {
			setOutputIntentData(interruptData);
			setShowOutputIntentModal(true);
			console.log('🎯 检测到输出意图确认');
		} else {
			setConfirmationData(interruptData);
			setShowConfirmation(true);
		}
	}, [resolveProgressiveStepNumber, sessionId]);

	// 使用 WebSocket 实时更新状态
	useEffect(() => {
		const fetchInitialStatus = async (retryCount = 0) => {
			try {
				console.log(`🔍 开始获取初始状态 (尝试 ${retryCount + 1}/3), sessionId:`, sessionId);
				const data = await api.getStatus(sessionId);
				console.log('✅ 获取初始状态成功:', data);

				// 🆕 v7.290: 从 localStorage 加载用户输入（用于显示用户问题卡片）
				const userInputsJson = localStorage.getItem('analysis_user_inputs');
				if (userInputsJson) {
					const userInputs: Record<string, string> = JSON.parse(userInputsJson);
					if (userInputs[sessionId]) {
						setUserInput(userInputs[sessionId]);
						console.log('📝 加载用户输入:', userInputs[sessionId]);
					}
				}

				// 🆕 v7.290: 检测是否为旧的未完成会话
				// 从 localStorage 获取最近创建的会话记录
				const recentSessionsJson = localStorage.getItem('recent_analysis_sessions');
				const recentSessions: Record<string, number> = recentSessionsJson ? JSON.parse(recentSessionsJson) : {};
				const sessionCreatedAt = recentSessions[sessionId];
				const now = Date.now();

				// 如果会话不在最近记录中，或创建时间超过1分钟，且状态为运行中/等待输入，则认为是旧会话
				const isOldSession = !sessionCreatedAt || (now - sessionCreatedAt > 60000);
				const isIncompleteStatus = data.status === 'running' || data.status === 'waiting_for_input';

				if (isOldSession && isIncompleteStatus) {
					console.warn('⚠️ 检测到旧的未完成会话:', { sessionId, sessionCreatedAt, status: data.status });
					// 显示友好提示，而不是自动恢复
					setError('此分析会话可能已中断。您可以尝试重新加载以继续执行，或返回首页开始新的分析。');
					return;
				}
				setStatus(data);

				if (data.history && data.history.length > 0) {
					console.log('📜 恢复执行历史:', data.history);
					setNodeHistory(data.history);

					const details: Record<string, { status: NodeStatus; detail?: string }> = {};
					data.history.forEach((entry) => {
						details[entry.node] = {
							status: 'completed',
							detail: entry.detail
						};
					});

					if (data.current_stage && (data.status === 'running' || data.status === 'waiting_for_input')) {
						details[data.current_stage] = {
							status: 'running',
							detail: data.detail
						};
					}

					setNodeDetails((prev) => ({ ...prev, ...details }));
				}

				if (data.status === 'waiting_for_input' && data.interrupt_data) {
					applyInterruptDispatch(data.interrupt_data);
				}

					if (data.status === 'completed') {
						console.log('✅ 检测到会话已完成，跳转至报告页面');
						navigateToReport();
					}
				} catch (err: any) {
					// 🔥 检测是否为追问会话
					const isFollowupSession = sessionId.includes('-followup-');
					console.error(`获取初始状态失败 (尝试 ${retryCount + 1}/3):`, err);				// 🔧 修复：对于 404 错误，如果是追问会话且重试次数少于3，则重试
				if (err?.response?.status === 404 && sessionId.includes('-followup-') && retryCount < 2) {
					console.log(`⏳ 追问会话可能还在创建中，2秒后重试...`);
					setTimeout(() => {
						fetchInitialStatus(retryCount + 1);
					}, 2000);
					return;
				}

				if (err?.response?.status === 404) {
					setError('会话已过期或不存在，请重新开始分析');
				} else if (err?.response?.status === 410) {
					setError('工作流已失效，请重新开始分析');
				} else if (err?.response?.status === 500) {
					setError('服务器内部错误，请稍后重试');
				} else if (err?.message?.includes('Network Error') || err?.message?.includes('timeout')) {
					setError('网络连接失败，请检查后端服务是否运行');
				} else {
					setError(err?.response?.data?.detail || err.message || '获取会话状态失败');
				}
			}
		};

		fetchInitialStatus();

		// 🔥 检测是否为追问会话（用于显示友好文案）
		const isFollowupSession = sessionId.includes('-followup-');

		const wsUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
		console.log('🔌 准备连接 WebSocket:', { wsUrl, sessionId, isFollowup: isFollowupSession });

		wsClientRef.current = new WebSocketClient({
			url: wsUrl,
			sessionId,
			onOpen: async () => {
				// 🔧 v7.118: 重连后同步最新状态
				console.log('✅ WebSocket 已连接，同步最新状态...');
				try {
					const response = await api.getStatus(sessionId);
					if (response) {
						setStatus({
							session_id: sessionId,
							status: response.status,
							progress: response.progress ?? 0,
							error: response.error,
							current_stage: response.current_stage,
							detail: response.detail
						});
						console.log('✅ 状态同步完成:', response);
					}
				} catch (error) {
					console.error('⚠️ 状态同步失败:', error);
				}
			},
			onMessage: (message: WebSocketMessage) => {
				console.log('📩 收到 WebSocket 消息 [' + message.type + ']:', message);				switch (message.type) {
					case 'initial_status':
						setStatus((prev) => ({
							...prev!,
							status: message.status as SessionStatus,
							progress: message.progress,
							current_stage: message.current_node || prev?.current_stage,
							detail: message.detail || prev?.detail
						}));
						setWsConnected(true);
						break;

					case 'status_update':
						console.log('📨 收到状态更新:', message);
						setStatus((prev) => {
							// 🔥 防止进度回退：只有新进度 ≥ 旧进度时才更新
							const newProgress = message.progress;
							const oldProgress = prev?.progress ?? 0;
							const validatedProgress = newProgress !== undefined && newProgress >= oldProgress
								? newProgress
								: oldProgress;

							if (newProgress !== undefined && newProgress < oldProgress) {
								console.warn(`⚠️ [status_update] 检测到进度回退: ${Math.round(oldProgress * 100)}% → ${Math.round(newProgress * 100)}%，已忽略`);
							}

							return {
								...prev!,
								status: message.status as SessionStatus,
								progress: validatedProgress,
								error: message.error,
								rejection_message: message.rejection_message,
								final_report: message.final_report,
								current_stage: message.current_node || prev?.current_stage,
								detail: message.detail ?? prev?.detail
							};
						});

						if (message.current_node) {
							const currentNode = message.current_node;
							setNodeDetails((prev) => {
								const updated = { ...prev };
								Object.keys(updated).forEach((key) => {
									if (key !== currentNode && updated[key].status === 'running') {
										updated[key] = { ...updated[key], status: 'completed' };
									}
								});

							const previousDetail = updated[currentNode]?.detail;
							updated[currentNode] = {
								status: message.status === 'completed' ? 'completed' : 'running',
								detail: message.detail ?? previousDetail
							};
							return updated;
						});

						setNodeHistory((prev) => {
							const lastEntry = prev[prev.length - 1];
							if (lastEntry?.node === currentNode) {
								return prev;
							}
							// 🆕 P3修复: 限制历史记录最多100条，避免内存溢出
							const newHistory = [
								...prev,
								{
									node: currentNode,
									detail: message.detail || '',
									time: new Date().toLocaleTimeString()
								}
							];
							return newHistory.length > 100 ? newHistory.slice(-100) : newHistory;
						});
					}

						if (message.status === 'completed') {
							console.log('✅ 分析完成！');
							setStatus((prev) => ({
								...prev!,
								current_stage: 'completed',
								detail: '分析完成'
							}));

							setNodeDetails((prev) => {
								const updated = { ...prev };
								Object.keys(updated).forEach((key) => {
									updated[key] = { ...updated[key], status: 'completed' };
								});
								return updated;
							});

							navigateToReport();
						}

						if (message.status === 'failed') {
							console.error('❌ 分析失败:', message.error);
						}
						break;

					case 'status':
					console.log('📨 收到 status 消息:', message);
					setStatus((prev) => {
						// 防止进度回退：只有新进度≥旧进度时才更新
						const newProgress = (message as any).progress;
						const oldProgress = prev?.progress ?? 0;
						const validatedProgress = newProgress !== undefined && newProgress >= oldProgress
							? newProgress
							: oldProgress;

						if (newProgress !== undefined && newProgress < oldProgress) {
							console.warn(`⚠️ 检测到进度回退: ${oldProgress} → ${newProgress}，已忽略`);
						}

						return {
							...prev!,
							status: (message as any).status as SessionStatus,
							progress: validatedProgress,
							error: (message as any).error,
							final_report: (message as any).final_report
						};
					});						if ((message as any).status === 'completed') {
							console.log('✅ 分析完成！进度 100%');
							setStatus((prev) => ({
								...prev!,
								progress: 1.0,
								current_stage: 'completed',
								detail: '分析完成'
							}));

							navigateToReport();
						}
						break;

					case 'node_update':
						// ✅ 统一使用 current_node 字段，兼容旧的 node_name
						const nodeName = message.current_node || message.node_name;
						if (!nodeName) {
							console.warn('⚠️ 节点更新缺少节点名称，已忽略');
							break;
						}
						console.log('📊 节点更新:', nodeName, '-', message.detail);
						setStatus((prev) => ({
							...prev!,
							current_stage: nodeName,
							detail: message.detail,
							status: 'running'
						}));

						setNodeDetails((prev) => {
							const updated = { ...prev };
							Object.keys(updated).forEach((key) => {
								if (key !== nodeName && updated[key].status === 'running') {
									updated[key] = { ...updated[key], status: 'completed' };
								}
							});

							const previousDetail = updated[nodeName]?.detail;
							updated[nodeName] = {
								status: 'running',
								detail: message.detail || previousDetail
							};

							return updated;
						});

						setNodeHistory((prev) => [
							...prev,
							{
								node: nodeName,
								detail: message.detail,
								time: new Date(message.timestamp).toLocaleTimeString()
							}
						]);
						break;

					case 'interrupt':
						setStatus((prev) => ({
							...prev!,
							status: message.status as SessionStatus,
							interrupt_data: message.interrupt_data
						}));

						applyInterruptDispatch(message.interrupt_data);
						break;

					case 'tool_permissions_initialized':
						// 🆕 v7.129 Week2 P1: 工具权限初始化通知
						console.log('🔧 收到工具权限初始化消息:', message);

						// 显示toast通知用户工具权限已配置
						import('sonner').then(({ toast }) => {
							// 统计启用搜索的角色数量
							const toolSettings = message.tool_settings || {};
							const rolesWithSearch = Object.entries(toolSettings)
								.filter(([_, settings]: [string, any]) => settings.enable_search)
								.map(([roleType, _]) => roleType);

							const allRoles = Object.keys(toolSettings);

							toast.success(
								`工具权限系统已初始化`,
								{
									description: `已配置 ${allRoles.length} 个角色，其中 ${rolesWithSearch.length} 个角色启用搜索工具 (${rolesWithSearch.join(', ')})`,
									duration: 5000,
								}
							);

							console.log('📡 工具权限配置:', {
								allRoles,
								rolesWithSearch,
								settings: toolSettings
							});
						});
						break;
				}
			},
			onError: (event) => {
				console.error('❌ WebSocket 错误:', event);
				setWsConnected(false);
			},
			onClose: () => {
				console.log('🔌 WebSocket 连接关闭');
				setWsConnected(false);
			}
		});

		wsClientRef.current.connect();

		return () => {
			wsClientRef.current?.close();
		};
	}, [applyInterruptDispatch, navigateToReport, sessionId]);

	const handleNodeClick = (nodeId: string) => {
		setSelectedNode(nodeId);
	};

	const closeNodeDetail = () => {
		setSelectedNode(null);
	};

	const handleQuestionnaireSubmit = async (answers: any) => {
		try {
			await api.resumeAnalysis(sessionId, JSON.stringify(answers));
			setShowQuestionnaire(false);
			setQuestionnaireData(null);
			console.log('✅ 问卷已提交');
		} catch (err: any) {
			console.error('❌ 问卷提交失败:', err);
			if (err?.response?.status === 410) {
				alert('工作流已失效，请重新开始分析');
				router.push('/');
			} else {
				alert('问卷提交失败,请重试');
			}
		}
	};

	const handleQuestionnaireSkip = async () => {
		try {
			await api.resumeAnalysis(sessionId, 'skip');
			setShowQuestionnaire(false);
			setQuestionnaireData(null);
			console.log('⏭️ 已跳过问卷');
		} catch (err: any) {
			console.error('❌ 跳过问卷失败:', err);
			if (err?.response?.status === 410) {
				alert('工作流已失效，请重新开始分析');
				router.push('/');
			} else {
				alert('操作失败,请重试');
			}
		}
	};

	const handleConfirmation = async (editedData?: any) => {
		try {
			console.log('🚀 开始提交确认...', editedData);

			let payload: any;

			if (editedData && Array.isArray(editedData)) {
				const modifications: Record<string, string> = {};
				const originalSummary = confirmationData?.requirements_summary || [];

				editedData.forEach((editedItem: any, index: number) => {
					const originalItem = originalSummary[index];
					if (originalItem) {
						if (editedItem.label !== originalItem.label) {
							console.log(`📝 检测到标签修改: ${originalItem.key}`);
						}
						const originalContent = (originalItem.content || '').trim();
						const editedContent = (editedItem.content || '').trim();
						if (editedContent !== originalContent) {
							modifications[editedItem.key || originalItem.key] = editedContent;
							console.log(`📝 检测到内容修改: ${editedItem.key || originalItem.key}`);
						}
					}
				});

				if (Object.keys(modifications).length > 0) {
					payload = {
						intent: 'approve',
						modifications
					};
					console.log(`📝 提交 ${Object.keys(modifications).length} 个字段修改`);
				} else {
					payload = 'confirm';
					console.log('✅ 未检测到修改，直接确认');
				}
			} else {
				payload = 'confirm';
			}

			await api.resumeAnalysis(sessionId, payload);
			setShowConfirmation(false);
			setConfirmationData(null);

			const lastNode = nodeHistory.length > 0 ? nodeHistory[nodeHistory.length - 1].node : null;
			const processingText = lastNode ? `${formatNodeName(lastNode)} (处理中...)` : '工作流继续执行中...';

			setStatus((prev) => ({
				...prev!,
				status: 'running' as SessionStatus,
				detail: payload !== 'confirm' ? '正在根据您的修改重新分析...' : processingText
			}));

			console.log('✅ 确认完成,工作流继续执行');
		} catch (err) {
			console.error('❌ 确认失败:', err);
			alert('确认失败,请重试');
		}
	};

	const handleOutputIntentConfirm = async (payload: OutputIntentConfirmPayload) => {
		try {
			await api.resumeAnalysis(sessionId, payload);
			setShowOutputIntentModal(false);
			setOutputIntentData(null);
			setStatus((prev) => (prev ? { ...prev, status: 'running' as SessionStatus, detail: '正在继续分析...' } : prev));
			console.log('✅ 输出意图确认已提交');
		} catch (err) {
			console.error('❌ 输出意图确认提交失败:', err);
			alert('提交失败，请重试');
		}
	};

	const handleRoleTaskReview = async (action: string, modifications?: any) => {
		try {
			console.log('🚀 开始提交任务审批...', { action, modifications });

			let payload: any;

			if (action === 'modify_tasks' && modifications && Object.keys(modifications).length > 0) {
				// 修改任务分配
				payload = {
					action: 'modify_tasks',
					modifications
				};
				console.log(`📝 提交 ${Object.keys(modifications).length} 个角色的任务修改`);
			} else if (action === 'modify_roles') {
				// 请求重新拆分项目
				payload = {
					action: 'modify_roles'
				};
				console.log('🔄 请求重新拆分项目');
			} else if (action === 'approve') {
				// 直接批准，无修改
				payload = {
					action: 'approve'
				};
				console.log('✅ 批准项目拆分和任务分配');
			} else {
				// 其他动作
				payload = { action };
				console.log(`📤 提交动作: ${action}`);
			}

			await api.resumeAnalysis(sessionId, payload);
			setShowRoleTaskReview(false);
			setRoleTaskReviewData(null);

			const lastNode = nodeHistory.length > 0 ? nodeHistory[nodeHistory.length - 1].node : null;
			const processingText =
				action === 'modify_roles'
					? '正在重新拆分项目...'
					: action === 'modify_tasks'
					? '正在根据您的修改重新分配任务...'
					: lastNode
					? `${formatNodeName(lastNode)} (处理中...)`
					: '工作流继续执行中...';

			setStatus((prev) => ({
				...prev!,
				status: 'running' as SessionStatus,
				detail: processingText
			}));

			console.log('✅ 任务审批完成,工作流继续执行');
		} catch (err) {
			console.error('❌ 任务审批失败:', err);
			alert('审批失败,请重试');
		}
	};

	const handleUserQuestionSubmit = async ({ question, requiresAnalysis }: { question: string; requiresAnalysis: boolean }) => {
		try {
			setUserQuestionSubmitting(true);
			const payload = {
				question: question.trim(),
				requires_analysis: requiresAnalysis
			};
			await api.resumeAnalysis(sessionId, payload);
			setShowUserQuestion(false);
			setUserQuestionData(null);
			setStatus((prev) => (prev
				? {
						...prev,
						status: 'running' as SessionStatus,
						detail: '继续处理用户追问...',
						interrupt_data: null
				  }
				: null
			));
			console.log('✅ 用户追问提交成功');
		} catch (err) {
			console.error('❌ 追问提交失败:', err);
			alert('提交失败，请重试');
		} finally {
			setUserQuestionSubmitting(false);
		}
	};

	const handleUserQuestionSkip = async () => {
		try {
			await api.resumeAnalysis(sessionId, { skip: true });
			setShowUserQuestion(false);
			setUserQuestionData(null);
			setStatus((prev) => (prev ? { ...prev, status: 'running' as SessionStatus } : null));
			console.log('✅ 跳过用户追问');
		} catch (err) {
			console.error('❌ 跳过失败:', err);
			alert('跳过失败，请重试');
		}
	};

	// 🆕 v7.119: 质量预检处理函数
	const handleQualityPreflightConfirm = async () => {
		try {
			console.log('✅ 用户确认继续执行高风险任务');
			await api.resumeAnalysis(sessionId, { action: 'approve' });
			setShowQualityPreflight(false);
			setQualityPreflightData(null);

			setStatus((prev) => ({
				...prev!,
				status: 'running' as SessionStatus,
				detail: '专家团队开始执行分析...'
			}));

			console.log('✅ 质量预检确认完成，工作流继续执行');
		} catch (err) {
			console.error('❌ 质量预检确认失败:', err);
			alert('确认失败，请重试');
		}
	};

	const handleQualityPreflightCancel = async () => {
		try {
			console.log('❌ 用户取消执行，请求修改需求');
			await api.resumeAnalysis(sessionId, { action: 'reject_and_revise' });
			setShowQualityPreflight(false);
			setQualityPreflightData(null);

			setStatus((prev) => ({
				...prev!,
				status: 'running' as SessionStatus,
				detail: '正在重新分析需求...'
			}));

			console.log('✅ 用户取消，工作流重新开始');
		} catch (err) {
			console.error('❌ 取消失败:', err);
			alert('取消失败，请重试');
		}
	};

	// 🆕 v7.130: 统一问卷处理函数
	const handleProgressiveStepConfirm = async (stepData?: any) => {
		const step = currentProgressiveStep;
		try {
			console.log(`✅ 第${step}步 - 用户确认:`, stepData);

			let payload: any = { action: 'confirm' };
			if (step === 1 && stepData?.extracted_tasks) {
				payload.confirmed_tasks = stepData.extracted_tasks;
			} else if (step === 2 && stepData?.answers) {
				payload.answers = stepData.answers;
			} else if (step === 3 && stepData?.dimension_values) {
				payload.selected_dimensions = stepData.dimension_values;
			}

			// 🆕 v7.400: Step 1确认后立即显示Step 2加载状态（极致用户体验优化）
			if (step === 1) {
				console.log('🚀 [UX优化] Step 1确认，立即显示Step 2加载状态');
				setCurrentProgressiveStep(2);
				setProgressiveStepData({
					isLoading: true,
					interaction_type: 'progressive_questionnaire_step2',
					step: 2,
					total_steps: 3,
					title: '信息补全',
					message: '正在理解您的需求并进行深度分析...'
				});
			}

			await api.resumeAnalysis(sessionId, payload);

			// 🔧 v7.130: 不关闭 Modal，让 WebSocket 消息自动触发下一步
			setStatus((prev) => ({
				...prev!,
				status: 'running' as SessionStatus,
				detail: step === 3 ? '正在生成分析报告...' : '正在处理您的输入...'
			}));

			// 🔧 v7.153: Step 3（雷达图）或 Step 4（需求洞察）完成后，关闭问卷
			if (step === 3 || step === 4) {
				setCurrentProgressiveStep(0);
				setProgressiveStepData(null);
			}

			console.log(`✅ 第${step}步确认完成`);
		} catch (err) {
			console.error(`❌ 第${step}步确认失败:`, err);
			alert('确认失败,请重试');
			// 🆕 v7.400: 如果API调用失败，清除loading状态
			if (step === 1) {
				setCurrentProgressiveStep(1);
				setProgressiveStepData((prev: any) => ({ ...prev, isLoading: false }));
			}
		}
	};

	const handleProgressiveStepSkip = async () => {
		const step = currentProgressiveStep;
		try {
			console.log(`⏭️ 第${step}步 - 用户选择跳过问卷`);
			await api.resumeAnalysis(sessionId, { action: 'skip' });
			setCurrentProgressiveStep(0);
			setProgressiveStepData(null);
			setStatus((prev) => ({
				...prev!,
				status: 'running' as SessionStatus,
				detail: '跳过问卷，继续分析流程...'
			}));
			console.log(`⏭️ 第${step}步跳过成功`);
		} catch (err) {
			console.error(`❌ 第${step}步跳过失败:`, err);
			alert('操作失败,请重试');
		}
	};

	// v7.290: 移除侧边栏，独立分析体验

	const selectedNodeData = selectedNode ? nodeHistory.filter((h) => h.node === selectedNode) : [];

	return (
		<div className="flex h-screen bg-[var(--background)] text-[var(--foreground)] overflow-hidden relative">
			{/* v7.290: 独立分析页面，无侧边栏 */}
			<div className="flex-1 flex flex-col relative h-full overflow-hidden w-full">
{/* v7.290.1: 顶部导航栏 - 统一体验 */}
		<header className="sticky top-0 z-10 bg-[var(--sidebar-bg)] border-b border-[var(--border-color)]">
			<div className="flex items-center justify-between px-4 py-3">
				<div className="flex items-center gap-3">
					<button
						onClick={() => router.push('/')}
						className="p-2 text-[var(--foreground-secondary)] hover:text-[var(--foreground)] hover:bg-[var(--card-bg)] rounded-lg transition-colors"
						title="返回首页"
					>
						<ArrowLeft className="w-5 h-5" />
					</button>
					<h1 className="text-lg font-semibold">
						{sessionId.includes('-followup-') ? '💬 追问分析中...' : '方案高参'}
					</h1>
				</div>

				{!wsConnected && (
					<div className="flex items-center gap-2 px-3 py-1.5 bg-red-900/20 text-red-400 rounded-full text-xs border border-red-900/30">
						<WifiOff className="w-3 h-3" />
						<span>网络异常，正在重连...</span>
					</div>
				)}
			</div>
		</header>

				<div className="flex-1 overflow-y-auto p-6">
					<div className={`max-w-6xl mx-auto ${status?.status === 'completed' ? 'h-full flex items-center justify-center' : 'space-y-6'}`}>
						{/* 🆕 v7.290: 用户问题卡片 - 使用公共组件 */}
						{(error || status) && <UserQuestionCard question={userInput} className="mb-6" />}

						{error ? (
							<div className="max-w-2xl mx-auto">
								<div className="bg-red-900/20 border border-red-900/50 rounded-lg p-6">
									<div className="flex items-start gap-3 mb-4">
										<AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0 mt-0.5" />
										<div className="flex-1">
											{error && error.includes('LLM服务连接异常') ? (
												<>
													<h3 className="text-lg font-semibold text-red-400 mb-2">AI分析服务连接异常</h3>
													<p className="text-red-300 mb-2">AI分析服务暂时不可用，请刷新页面后继续，您的进度已自动保存，无需重头开始。</p>
													<p className="text-xs text-gray-400">如多次遇到该问题，请联系管理员。</p>
												</>
											) : (
												<>
													<h3 className="text-lg font-semibold text-red-400 mb-2">加载失败</h3>
													<p className="text-red-300">{error}</p>
												</>
											)}
										</div>
									</div>
									<div className="flex gap-3">
										<button
											onClick={() => router.push('/')}
											className="px-4 py-2 bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white rounded-lg transition-colors font-medium"
										>
											返回首页
										</button>
										<button
											onClick={() => window.location.reload()}
											className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
										>
											{error && error.includes('LLM服务连接异常')
												? '刷新后继续'
												: error && error.includes('会话可能已中断')
												? '尝试继续执行'
												: '重新加载'}
										</button>
									</div>
								</div>
							</div>
						) : !status ? (
							<div className="flex flex-col items-center justify-center h-64 text-gray-400 gap-4">
								<Loader2 className="w-8 h-8 animate-spin text-[var(--primary)]" />
								<p>{sessionId.includes('-followup-') ? '💬 正在基于原报告分析您的追问...' : '正在初始化分析环境...'}</p>
							</div>
						) : status.status === 'rejected' ? (
							<div className="w-full max-w-2xl space-y-6">
								<div className="bg-[var(--card-bg)] rounded-xl border border-red-900/50 p-8">
									<div className="flex justify-center mb-4">
										<AlertCircle className="w-16 h-16 text-red-400" />
									</div>
									<div className="text-2xl font-semibold mb-2 text-center text-red-400">输入被拒绝</div>

									{status.rejection_reason && (
										<div className="text-sm text-gray-400 text-center mb-6">
											拒绝原因: {status.rejection_reason === 'content_safety_violation' ? '内容安全违规' : status.rejection_reason === 'not_design_related' ? '非设计领域问题' : status.rejection_reason}
										</div>
									)}

									{status.rejection_message && (
										<div className="bg-[var(--sidebar-bg)] rounded-lg p-6 mb-6 text-sm text-gray-300 whitespace-pre-wrap border border-[var(--border-color)]">
											{status.rejection_message}
										</div>
									)}

									{status.progress !== undefined && (
										<div className="space-y-2 mb-6">
											<div className="flex justify-between text-sm">
												<span className="text-gray-400">总体进度</span>
												<span className="text-red-400 font-medium">{Math.round(status.progress * 100)}%</span>
											</div>
											<div className="w-full bg-[var(--sidebar-bg)] rounded-full h-2 overflow-hidden">
												<div
													className="bg-red-500 h-full rounded-full transition-all duration-500 ease-out"
													style={{ width: `${status.progress * 100}%` }}
												/>
											</div>
										</div>
									)}

									<div className="space-y-3">
										<button
											onClick={() => router.push('/')}
											className="w-full px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white rounded-lg transition-colors font-medium shadow-lg"
										>
											🏠 返回首页重新开始
										</button>
									</div>
								</div>
							</div>
						) : status.status === 'completed' ? (
							<div className="w-full max-w-2xl space-y-6">
								<div className="bg-[var(--card-bg)] rounded-xl border border-[var(--border-color)] p-8 text-center">
									<div className="flex justify-center mb-4">
										<CheckCircle2 className="w-16 h-16 text-green-500" />
									</div>
									<div className="text-2xl font-semibold mb-2">已完成</div>
									<div className="text-gray-400 mb-6">分析完成</div>
									{status.progress !== undefined && (
										<div className="space-y-2 mb-6">
											<div className="flex justify-between text-sm">
												<span className="text-gray-400">总体进度</span>
												<span className="text-[var(--primary)] font-medium">{Math.round(status.progress * 100)}%</span>
											</div>
											<div className="w-full bg-[var(--sidebar-bg)] rounded-full h-2 overflow-hidden">
												<div
													className="bg-[var(--primary)] h-full rounded-full transition-all duration-500 ease-out"
													style={{ width: `${status.progress * 100}%` }}
												/>
											</div>
										</div>
									)}

									<div className="space-y-3">
										<button
											onClick={() => router.push(`/report/${sessionId}`)}
											className="w-full px-6 py-3 bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white rounded-lg transition-colors font-medium shadow-lg"
										>
											📊 查看分析报告
										</button>
										<button
											onClick={() => router.push('/')}
											className="w-full px-6 py-3 bg-[var(--card-bg)] hover:bg-[var(--sidebar-bg)] text-[var(--foreground)] border border-[var(--border-color)] rounded-lg transition-colors font-medium"
										>
											返回首页
										</button>
									</div>
								</div>
							</div>
						) : (
							<>
								<div className="bg-[var(--card-bg)] rounded-xl border border-[var(--border-color)] p-6">
									<div className="flex items-center justify-between mb-6">
										<div className="space-y-1 flex-1">
											<div className="text-sm text-gray-400">当前阶段</div>
											<div className="text-xl font-semibold flex items-center gap-2">
												{/* 🔥 v7.7: 优先翻译 detail，然后翻译 current_stage */}
												{formatNodeName(status.detail) !== status.detail
													? formatNodeName(status.detail)
													: formatNodeName(status.current_stage)}
												{status.status === 'running' && <Loader2 className="w-4 h-4 animate-spin text-[var(--primary)]" />}
											</div>
										</div>
										{(['completed', 'failed', 'waiting_for_input'] as Array<string | SessionStatus>).includes(status.status as any) && (
											<div
												className={`px-3 py-1 rounded-full text-sm font-medium border ${
													(status.status as any) === 'completed'
														? 'bg-green-900/20 text-green-400 border-green-900/30'
														: status.status === 'failed'
														? 'bg-red-900/20 text-red-400 border-red-900/30'
														: 'bg-yellow-900/20 text-yellow-400 border-yellow-900/30'
												}`}
											>
												{(status.status as any) === 'completed' ? '已完成' : status.status === 'failed' ? '失败' : '等待输入'}
											</div>
										)}
									</div>

									{status.progress !== undefined && (
										<div className="space-y-2">
											<div className="flex justify-between text-sm">
												<span className="text-gray-400">总体进度</span>
												<span className="text-[var(--primary)] font-medium">{Math.round(status.progress * 100)}%</span>
											</div>
											<div className="w-full bg-[var(--sidebar-bg)] rounded-full h-2 overflow-hidden">
												<div
													className="bg-[var(--primary)] h-full rounded-full transition-all duration-500 ease-out"
													style={{ width: `${status.progress * 100}%` }}
												/>
											</div>
										</div>
									)}

									{status.active_steps && status.active_steps.length > 0 && (
										<div className="mt-4 pt-4 border-t border-[var(--border-color)]">
											<div className="text-xs text-gray-400 mb-2">当前激活步骤（后端驱动）</div>
											<div className="flex flex-wrap gap-2">
												{status.active_steps.map((step, idx) => (
													<span
														key={`${step}-${idx}`}
														className="px-2 py-1 rounded-md text-xs bg-[var(--sidebar-bg)] border border-[var(--border-color)] text-[var(--foreground-secondary)]"
													>
														{formatActiveStep(step)}
													</span>
												))}
											</div>
										</div>
									)}
								</div>

								{nodeHistory.length > 0 && (
									<div className="bg-[var(--card-bg)] rounded-xl border border-[var(--border-color)] p-6">
										<h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
											<CheckCircle2 className="w-5 h-5 text-green-500" />
											执行历史
											{/* 🆕 P3修复: 显示隐藏记录数量 */}
											{nodeHistory.length > 50 && (
												<span className="text-xs text-gray-500 font-normal ml-auto">
													显示最近50条 / 总计{nodeHistory.length}条
												</span>
											)}
										</h2>
										<div className="space-y-0 relative">
											<div className="absolute left-[5px] top-2 bottom-2 w-0.5 bg-[var(--border-color)]" />

											{/* 🆕 P3修复: 只显示最近50条 */}
											{nodeHistory.slice(-50).map((entry, index) => (
												<div key={index} className="flex gap-3 relative">
													<div className="w-3 h-3 rounded-full bg-[var(--sidebar-bg)] border border-[var(--border-color)] flex items-center justify-center z-10 shrink-0 mt-1.5">
														<div className="w-1 h-1 rounded-full bg-[var(--primary)]" />
													</div>
													<div className="flex-1 pb-6">
														<div className="flex items-center justify-between mb-1">
															<span className="font-medium text-[var(--foreground)]">{formatNodeName(entry.node)}</span>
															<span className="text-xs text-gray-500 font-mono">{entry.time}</span>
														</div>
													</div>
												</div>
											))}
										</div>
									</div>
								)}
							</>
						)}
					</div>
				</div>

				<div
					className={`fixed inset-y-0 right-0 w-96 bg-[var(--card-bg)] border-l border-[var(--border-color)] shadow-2xl transform transition-transform duration-300 ease-in-out z-50 ${
						selectedNode ? 'translate-x-0' : 'translate-x-full'
					}`}
				>
					<div className="h-full flex flex-col">
						<div className="p-4 border-b border-[var(--border-color)] flex items-center justify-between">
							<h3 className="font-semibold text-lg">节点详情</h3>
							<button
								onClick={closeNodeDetail}
								className="p-2 text-gray-400 hover:text-white hover:bg-[var(--sidebar-bg)] rounded-lg"
							>
								<X className="w-5 h-5" />
							</button>
						</div>

						<div className="flex-1 overflow-y-auto p-4 space-y-6">
							<div>
								<div className="text-xs text-gray-500 uppercase tracking-wider mb-1">节点 ID</div>
								<div className="font-mono text-sm bg-[var(--sidebar-bg)] p-2 rounded border border-[var(--border-color)]">
									{selectedNode}
								</div>
							</div>

							{selectedNode && nodeDetails[selectedNode] && (
								<div>
									<div className="text-xs text-gray-500 uppercase tracking-wider mb-1">当前状态</div>
									<div
										className={`inline-flex px-2 py-1 rounded text-xs font-medium border ${
											nodeDetails[selectedNode].status === 'completed'
												? 'bg-green-900/20 text-green-400 border-green-900/30'
												: nodeDetails[selectedNode].status === 'running'
												? 'bg-blue-900/20 text-blue-400 border-blue-900/30'
												: nodeDetails[selectedNode].status === 'error'
												? 'bg-red-900/20 text-red-400 border-red-900/30'
												: 'bg-gray-800 text-gray-400 border-gray-700'
										}`}
									>
										{nodeDetails[selectedNode].status}
									</div>
								</div>
							)}

							{selectedNodeData.length > 0 && (
								<div>
									<div className="text-xs text-gray-500 uppercase tracking-wider mb-2">执行记录</div>
									<div className="space-y-3">
										{selectedNodeData.map((record, index) => (
											<div key={index} className="bg-[var(--sidebar-bg)] rounded-lg p-3 border border-[var(--border-color)]">
												<div className="text-xs text-gray-500 mb-1 font-mono">{record.time}</div>
												<div className="text-sm text-gray-300">{record.detail || '无详细信息'}</div>
											</div>
										))}
									</div>
								</div>
							)}
						</div>
					</div>
				</div>

				{selectedNode && (
					<div
						className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
						onClick={closeNodeDetail}
					/>
				)}
			</div>

			<QuestionnaireModal
				isOpen={showQuestionnaire}
				questionnaire={questionnaireData}
				onSubmit={handleQuestionnaireSubmit}
				onSkip={handleQuestionnaireSkip}
			/>

			{/* 🆕 v7.151: ConfirmationModal 不再用于 requirements_confirmation（已合并到 questionnaire_summary） */}
			<ConfirmationModal
				isOpen={
					showConfirmation &&
					confirmationData?.interaction_type !== 'role_and_task_unified_review' &&
					confirmationData?.interaction_type !== 'output_intent_confirmation'
				}
				title={'确认'}
				message={confirmationData?.message || '请确认以下信息'}
				summary={confirmationData?.requirements_summary || confirmationData}
				onConfirm={handleConfirmation}
			/>

			<OutputIntentConfirmationModal
				isOpen={showOutputIntentModal}
				data={outputIntentData}
				onConfirm={handleOutputIntentConfirm}
				allowSkip={false}
			/>

			<RoleTaskReviewModal isOpen={showRoleTaskReview} data={roleTaskReviewData} onConfirm={handleRoleTaskReview} />

			<UserQuestionModal
				isOpen={showUserQuestion}
				data={userQuestionData}
				onSubmit={handleUserQuestionSubmit}
				onSkip={handleUserQuestionSkip}
				submitting={userQuestionSubmitting}
			/>

			<UnifiedProgressiveQuestionnaireModal
				isOpen={currentProgressiveStep > 0}
				currentStep={currentProgressiveStep}
				stepData={progressiveStepData}
				onConfirm={handleProgressiveStepConfirm}
				onSkip={handleProgressiveStepSkip}
				sessionId={sessionId as string}
			/>

			{/* 🆕 v7.119: 质量预检警告模态框 */}
			<QualityPreflightModal
				isOpen={showQualityPreflight}
				data={qualityPreflightData}
				onConfirm={handleQualityPreflightConfirm}
				onCancel={handleQualityPreflightCancel}
			/>
		</div>
	);
}
