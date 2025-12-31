// components/QualityPreflightModal.tsx
// 质量预检高风险警告 Modal 组件

'use client';

import { useState } from 'react';
import { AlertTriangle, CheckCircle2, ArrowLeft, XCircle, Shield, ChevronDown, ChevronUp } from 'lucide-react';
import { RISK_LEVEL_COLORS, getRiskLevelColor } from '@/lib/theme';

interface RiskWarning {
	role_id: string;
	// 🔥 v7.27: 后端发送 dynamic_name，兼容 role_name
	role_name?: string;
	dynamic_name?: string;
	risk_level?: 'high' | 'medium' | 'low';
	risk_score: number;
	// 🔥 v7.27: 后端发送 risk_points，兼容 risk_factors
	risk_factors?: string[];
	risk_points?: string[];
	// 🔥 v7.27: 后端发送 mitigation，兼容 checklist
	checklist?: string[];
	mitigation?: string[];
	// 🔥 v7.27: 添加 tasks 字段，支持编辑
	tasks?: string[];
}

interface QualityPreflightModalProps {
	isOpen: boolean;
	data: {
		interaction_type: string;
		title: string;
		message: string;
		warnings: RiskWarning[];
		allow_edit?: boolean;
		options?: Array<{ value: string; label: string }>;
	} | null;
	// 🔥 v7.27: 支持带任务修改的回调
	onConfirm: (choice: 'continue' | 'continue_with_edits' | 'adjust' | 'cancel', modifiedTasks?: Record<string, string[]>) => void;
}

export function QualityPreflightModal({ isOpen, data, onConfirm }: QualityPreflightModalProps) {
	const [expandedWarnings, setExpandedWarnings] = useState<Set<string>>(new Set());
	const [selectedChoice, setSelectedChoice] = useState<'continue' | 'continue_with_edits' | 'adjust' | 'cancel' | null>(null);
	const [isSubmitting, setIsSubmitting] = useState(false);
	// 🔥 v7.27: 任务编辑状态
	const [editedTasks, setEditedTasks] = useState<Record<string, string[]>>({});
	const [editingRole, setEditingRole] = useState<string | null>(null);

	if (!isOpen || !data) return null;

	const toggleWarning = (roleId: string) => {
		setExpandedWarnings((prev) => {
			const newSet = new Set(prev);
			if (newSet.has(roleId)) {
				newSet.delete(roleId);
			} else {
				newSet.add(roleId);
			}
			return newSet;
		});
	};

	const handleConfirm = async () => {
		if (!selectedChoice) return;
		setIsSubmitting(true);
		try {
			// 🔥 v7.27: 如果有任务编辑，传递修改后的任务
			const hasEdits = Object.keys(editedTasks).length > 0;
			if (hasEdits && selectedChoice === 'continue') {
				// 自动切换为 continue_with_edits
				await onConfirm('continue_with_edits', editedTasks);
			} else if (selectedChoice === 'continue_with_edits') {
				await onConfirm('continue_with_edits', editedTasks);
			} else {
				await onConfirm(selectedChoice);
			}
		} finally {
			setIsSubmitting(false);
		}
	};

	// 🔥 v7.27: 初始化任务编辑状态（使用原始任务）
	const initializeTaskEdit = (roleId: string, tasks: string[]) => {
		if (!editedTasks[roleId]) {
			setEditedTasks(prev => ({
				...prev,
				[roleId]: [...tasks]
			}));
		}
		setEditingRole(roleId);
	};

	// 🔥 v7.27: 更新单个任务
	const updateTask = (roleId: string, taskIndex: number, newValue: string) => {
		setEditedTasks(prev => {
			const currentTasks = prev[roleId] || [];
			const updated = [...currentTasks];
			updated[taskIndex] = newValue;
			return {
				...prev,
				[roleId]: updated
			};
		});
	};

	// 🔥 v7.27: 检查是否有任何编辑
	const hasAnyEdits = Object.keys(editedTasks).length > 0;

	const warnings = data.warnings || [];

	return (
		<div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
			<div className="bg-[var(--card-bg)] rounded-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col shadow-2xl border border-[var(--border-color)]">
				{/* Header */}
				<div className="border-b border-[var(--border-color)] px-6 py-5 bg-amber-500/10">
					<div className="flex items-center gap-3">
						<div className="p-2 bg-amber-500/20 rounded-lg">
							<AlertTriangle className="w-6 h-6 text-amber-400" />
						</div>
						<div>
							<h2 className="text-xl font-semibold text-gray-100">{data.title || '质量预检警告'}</h2>
							<p className="text-sm text-gray-400 mt-1">{data.message}</p>
						</div>
					</div>
				</div>

				{/* Warning List */}
				<div className="flex-1 overflow-y-auto px-6 py-4">
					<div className="space-y-3">
						{warnings.map((warning, index) => {
							// 🔥 v7.27: 从 risk_score 推断 risk_level（后端不发送 risk_level）
							const inferredLevel = warning.risk_level ||
								(warning.risk_score >= 70 ? 'high' : warning.risk_score >= 50 ? 'medium' : 'low');
							const colors = getRiskLevelColor(inferredLevel);
							const isExpanded = expandedWarnings.has(warning.role_id);
							return (
								<div
									key={warning.role_id || index}
									className={`${colors.bg} ${colors.border} border rounded-lg overflow-hidden`}
								>
									{/* Warning Header */}
									<button
										onClick={() => toggleWarning(warning.role_id)}
										className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition"
									>
										<div className="flex items-center gap-3">
											<Shield className={`w-5 h-5 ${colors.text}`} />
											<div className="text-left">
												<span className="font-medium text-gray-200">
												{/* 🔥 v7.27: 兼容 dynamic_name */}
												{warning.dynamic_name || warning.role_name || warning.role_id}
												</span>
												<span className={`ml-2 px-2 py-0.5 text-xs rounded ${colors.badge}`}>
													风险分数: {warning.risk_score}/100
												</span>
											</div>
										</div>
										{isExpanded ? (
											<ChevronUp className="w-5 h-5 text-gray-400" />
										) : (
											<ChevronDown className="w-5 h-5 text-gray-400" />
										)}
									</button>

									{/* Expanded Content */}
									{isExpanded && (
										<div className="px-4 pb-4 space-y-3">
											{/* Risk Factors - 🔥 v7.27: 兼容 risk_points */}
											{(() => {
												const riskItems = warning.risk_factors || warning.risk_points || [];
												return riskItems.length > 0 && (
													<div>
														<h4 className="text-sm font-medium text-gray-300 mb-2">⚠️ 风险因素</h4>
														<ul className="space-y-1">
															{riskItems.map((factor: string, i: number) => (
																<li key={i} className="text-sm text-gray-400 flex items-start gap-2">
																	<span className="text-red-400 mt-1">•</span>
																	<span>{factor}</span>
																</li>
															))}
														</ul>
													</div>
												);
											})()}

											{/* Mitigation Suggestions - 🔥 v7.27: 兼容 mitigation */}
											{(() => {
												const checkItems = warning.checklist || warning.mitigation || [];
												return checkItems.length > 0 && (
													<div>
														<h4 className="text-sm font-medium text-gray-300 mb-2">💡 缓解建议</h4>
														<ul className="space-y-1">
															{checkItems.map((item: string, i: number) => (
																<li key={i} className="text-sm text-gray-400 flex items-start gap-2">
																	<span className="text-blue-400 mt-1">✓</span>
																	<span>{item}</span>
																</li>
															))}
														</ul>
													</div>
												);
											})()}

											{/* 🔥 v7.27: 任务编辑区域 */}
											{warning.tasks && warning.tasks.length > 0 && (
												<div className="border-t border-[var(--border-color)] pt-3 mt-3">
													<div className="flex items-center justify-between mb-2">
														<h4 className="text-sm font-medium text-gray-300">📝 当前任务</h4>
														{editingRole !== warning.role_id ? (
															<button
																onClick={() => initializeTaskEdit(warning.role_id, warning.tasks || [])}
																className="text-xs px-2 py-1 rounded bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition"
															>
																编辑任务
															</button>
														) : (
															<span className="text-xs text-green-400">✓ 编辑中</span>
														)}
													</div>
													
													{editingRole === warning.role_id ? (
														// 编辑模式
														<div className="space-y-2">
															{(editedTasks[warning.role_id] || warning.tasks || []).map((task: string, taskIdx: number) => (
																<div key={taskIdx} className="flex items-start gap-2">
																	<span className="text-gray-500 text-sm mt-2">{taskIdx + 1}.</span>
																	<textarea
																		value={editedTasks[warning.role_id]?.[taskIdx] ?? task}
																		onChange={(e) => updateTask(warning.role_id, taskIdx, e.target.value)}
																		className="flex-1 bg-[var(--input-bg)] border border-[var(--border-color)] rounded px-3 py-2 text-sm text-gray-200 resize-none focus:outline-none focus:border-blue-500"
																		rows={2}
																		placeholder="输入任务描述..."
																	/>
																</div>
															))}
															<p className="text-xs text-gray-500 mt-2">
																💡 提示：修改任务后，选择&ldquo;继续执行&rdquo;将使用修改后的任务
															</p>
														</div>
													) : (
														// 只读模式
														<ul className="space-y-1">
															{warning.tasks.map((task: string, i: number) => (
																<li key={i} className="text-sm text-gray-400 flex items-start gap-2">
																	<span className="text-gray-500">{i + 1}.</span>
																	<span>{task}</span>
																</li>
															))}
														</ul>
													)}
												</div>
											)}
										</div>
									)}
								</div>
							);
						})}
					</div>

					{/* Action Selection */}
					<div className="mt-6 space-y-3">
						<h3 className="text-sm font-medium text-gray-300">请选择操作：</h3>

						<div className="grid grid-cols-1 gap-3">
							{/* Continue Option */}
							<button
								onClick={() => setSelectedChoice('continue')}
								className={`p-4 rounded-lg border transition flex items-start gap-3 text-left ${
									selectedChoice === 'continue'
										? 'border-green-500 bg-green-500/10'
										: 'border-[var(--border-color)] hover:border-green-500/50 hover:bg-green-500/5'
								}`}
							>
								<CheckCircle2
									className={`w-5 h-5 mt-0.5 ${
										selectedChoice === 'continue' ? 'text-green-400' : 'text-gray-500'
									}`}
								/>
								<div>
									<div className={`font-medium ${selectedChoice === 'continue' ? 'text-green-400' : 'text-gray-200'}`}>
										继续执行（已知悉风险）
									</div>
									<p className="text-sm text-gray-400 mt-1">
										我已了解以上风险，继续执行专家分析任务
									</p>
								</div>
							</button>

							{/* Adjust Option */}
							<button
								onClick={() => setSelectedChoice('adjust')}
								className={`p-4 rounded-lg border transition flex items-start gap-3 text-left ${
									selectedChoice === 'adjust'
										? 'border-amber-500 bg-amber-500/10'
										: 'border-[var(--border-color)] hover:border-amber-500/50 hover:bg-amber-500/5'
								}`}
							>
								<ArrowLeft
									className={`w-5 h-5 mt-0.5 ${selectedChoice === 'adjust' ? 'text-amber-400' : 'text-gray-500'}`}
								/>
								<div>
									<div className={`font-medium ${selectedChoice === 'adjust' ? 'text-amber-400' : 'text-gray-200'}`}>
										调整任务分配
									</div>
									<p className="text-sm text-gray-400 mt-1">
										返回上一步，重新调整角色选择和任务分配
									</p>
								</div>
							</button>

							{/* Cancel Option */}
							<button
								onClick={() => setSelectedChoice('cancel')}
								className={`p-4 rounded-lg border transition flex items-start gap-3 text-left ${
									selectedChoice === 'cancel'
										? 'border-red-500 bg-red-500/10'
										: 'border-[var(--border-color)] hover:border-red-500/50 hover:bg-red-500/5'
								}`}
							>
								<XCircle
									className={`w-5 h-5 mt-0.5 ${selectedChoice === 'cancel' ? 'text-red-400' : 'text-gray-500'}`}
								/>
								<div>
									<div className={`font-medium ${selectedChoice === 'cancel' ? 'text-red-400' : 'text-gray-200'}`}>
										取消分析
									</div>
									<p className="text-sm text-gray-400 mt-1">
										终止当前分析流程
									</p>
								</div>
							</button>
						</div>
					</div>
				</div>

				{/* Footer */}
				<div className="border-t border-[var(--border-color)] px-6 py-4 bg-gray-800/30 flex items-center justify-between">
					<div className="text-sm text-gray-400">
						发现 <span className="text-amber-400 font-medium">{warnings.length}</span> 个高风险任务
						{/* 🔥 v7.27: 显示已修改任务数 */}
						{hasAnyEdits && (
							<span className="ml-2 text-green-400">
								• 已修改 {Object.keys(editedTasks).length} 个任务
							</span>
						)}
					</div>
					<button
						onClick={handleConfirm}
						disabled={!selectedChoice || isSubmitting}
						className={`px-6 py-2.5 rounded-lg font-medium transition flex items-center gap-2 ${
							selectedChoice
								? 'bg-blue-600 hover:bg-blue-700 text-white'
								: 'bg-gray-700 text-gray-400 cursor-not-allowed'
						}`}
					>
						{isSubmitting ? (
							<>
								<span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
								处理中...
							</>
						) : hasAnyEdits && selectedChoice === 'continue' ? (
							'确认选择（含任务修改）'
						) : (
							'确认选择'
						)}
					</button>
				</div>
			</div>
		</div>
	);
}
