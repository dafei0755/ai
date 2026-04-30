// components/RoleTaskReviewModal.tsx
// 角色任务审核 Modal 组件

'use client';

import { useState, useEffect } from 'react';
import { CheckCircle2, Edit2, Save, X, Users, ListTodo, AlertCircle, ChevronDown, ChevronUp, Package, RefreshCw, XCircle } from 'lucide-react';
import { PlanReviewPanel } from './PlanReviewPanel';
import type { DWP } from './PlanReviewPanel';

interface RoleData {
	role_id: string;
	role_name: string;
	dynamic_role_name?: string;
	tasks: string[];
	focus_areas?: string[];
	expected_output?: string;
	dependencies?: string[];
	task_count?: number;
	// 🆕 v7.129: 工具权限
	tool_settings?: {
		enable_search?: boolean;
		available_tools?: string[];
		recommended?: string[];
	};
}

interface RoleTaskReviewModalProps {
	isOpen: boolean;
	data: any; // role_and_task_unified_review interrupt_data
	onConfirm: (action: string, modifications?: any) => void;
	inline?: boolean;
}

export function RoleTaskReviewModal({ isOpen, data, onConfirm, inline = false }: RoleTaskReviewModalProps) {
	const [editedRoles, setEditedRoles] = useState<RoleData[]>([]);
	const [expandedRoles, setExpandedRoles] = useState<Set<string>>(new Set());
	const [isEditing, setIsEditing] = useState(false);
	const [selectedAction, setSelectedAction] = useState<'approve' | 'modify_roles' | 'modify_tasks' | 'reject' | null>(null);
	const [isEditingDwp, setIsEditingDwp] = useState(false);
	const [showRejectConfirm, setShowRejectConfirm] = useState(false);

	useEffect(() => {
		if (isOpen && data) {
			// 从 role_selection.selected_roles 或 task_assignment.task_list 提取角色数据
			let roles: RoleData[] = [];

			// 🆕 v7.129: 提取工具设置
			const toolSettings = data.tool_settings || {};

			if (data.task_assignment?.task_list) {
				// 使用 task_list（包含完整任务信息）
				roles = data.task_assignment.task_list.map((role: any) => ({
					role_id: role.role_id,
					role_name: role.dynamic_role_name || role.role_name || role.static_role_name,
					dynamic_role_name: role.dynamic_role_name,
					tasks: role.tasks?.map((t: any) => (typeof t === 'string' ? t : t.description)) || [],
					focus_areas: role.focus_areas || [],
					expected_output: role.expected_output || '',
					dependencies: role.dependencies || [],
					task_count: role.task_count,
					// 🆕 v7.129: 添加工具设置
					tool_settings: toolSettings[role.role_id]
				}));
			} else if (data.role_selection?.selected_roles) {
				// 备用：使用 selected_roles
				roles = data.role_selection.selected_roles.map((role: any) => ({
					role_id: role.role_id,
					role_name: role.dynamic_role_name || role.role_name,
					dynamic_role_name: role.dynamic_role_name,
					tasks: role.tasks || [],
					focus_areas: role.focus_areas || [],
					expected_output: role.expected_output || '',
					dependencies: role.dependencies || [],
					// 🆕 v7.129: 添加工具设置
					tool_settings: toolSettings[role.role_id]
				}));
			}

			setEditedRoles(JSON.parse(JSON.stringify(roles)));
			// 默认全部展开
			setExpandedRoles(new Set(roles.map((r) => r.role_id)));
			setIsEditingDwp(false);
		}
	}, [isOpen, data]);

	if (!isOpen || !data) return null;

	const toggleRole = (roleId: string) => {
		setExpandedRoles((prev) => {
			const newSet = new Set(prev);
			if (newSet.has(roleId)) {
				newSet.delete(roleId);
			} else {
				newSet.add(roleId);
			}
			return newSet;
		});
	};

	const handleTaskEdit = (roleId: string, taskIndex: number, newValue: string) => {
		setEditedRoles((prev) => {
			const newRoles = [...prev];
			const roleIndex = newRoles.findIndex((r) => r.role_id === roleId);
			if (roleIndex !== -1) {
				const newTasks = [...newRoles[roleIndex].tasks];
				newTasks[taskIndex] = newValue;
				newRoles[roleIndex] = { ...newRoles[roleIndex], tasks: newTasks };
			}
			return newRoles;
		});
	};

	const handleAddTask = (roleId: string) => {
		setEditedRoles((prev) => {
			const newRoles = [...prev];
			const roleIndex = newRoles.findIndex((r) => r.role_id === roleId);
			if (roleIndex !== -1) {
				const newTasks = [...newRoles[roleIndex].tasks, ''];
				newRoles[roleIndex] = { ...newRoles[roleIndex], tasks: newTasks };
			}
			return newRoles;
		});
	};

	const handleDeleteTask = (roleId: string, taskIndex: number) => {
		setEditedRoles((prev) => {
			const newRoles = [...prev];
			const roleIndex = newRoles.findIndex((r) => r.role_id === roleId);
			if (roleIndex !== -1) {
				const newTasks = newRoles[roleIndex].tasks.filter((_, i) => i !== taskIndex);
				newRoles[roleIndex] = { ...newRoles[roleIndex], tasks: newTasks };
			}
			return newRoles;
		});
	};

	const handleConfirm = () => {
		if (selectedAction === 'modify_tasks' && isEditing) {
			// 提交任务修改
			const modifications: Record<string, string[]> = {};
			const originalRoles = data.task_assignment?.task_list || data.role_selection?.selected_roles || [];

			editedRoles.forEach((editedRole, index) => {
				const originalRole = originalRoles[index];
				const originalTasks = originalRole?.tasks?.map((t: any) => (typeof t === 'string' ? t : t.description)) || [];
				const editedTasks = editedRole.tasks.filter((t) => t.trim() !== ''); // 移除空任务

				// 检查任务是否有变化
				const hasChanges =
					editedTasks.length !== originalTasks.length ||
					editedTasks.some((task, i) => task.trim() !== (originalTasks[i] || '').trim());

				if (hasChanges) {
					modifications[editedRole.role_id] = editedTasks;
				}
			});

			if (Object.keys(modifications).length > 0) {
				console.log('📝 提交任务修改:', modifications);
				onConfirm('modify_tasks', modifications);
			} else {
				console.log('✅ 未检测到任务修改，批准执行');
				onConfirm('approve');
			}
		} else if (selectedAction === 'modify_roles') {
			// 请求重新拆分项目
			console.log('🔄 请求重新拆分项目');
			onConfirm('modify_roles');
		} else {
			// 直接批准
			console.log('✅ 批准项目拆分和任务分配');
			onConfirm('approve');
		}
	};

	const handleDwpSave = (editedDwps: DWP[]) => {
		console.log('📦 提交交付物工作包编辑:', editedDwps.length, '个');
		onConfirm('edit_deliverables', editedDwps);
	};

	const totalTasks = editedRoles.reduce((sum, role) => sum + role.tasks.length, 0);
	const rolesWithTasks = editedRoles.filter((role) => role.tasks.length > 0).length;

	const _outerCls = inline
		? 'h-full flex flex-col overflow-hidden'
		: 'fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4';
	const _innerCls = inline
		? 'bg-white w-full h-full overflow-hidden flex flex-col'
		: 'ui-card-shell ui-card-shell-strong bg-white rounded-2xl max-w-6xl w-full h-[85vh] overflow-hidden flex flex-col';
	return (
		<div className={_outerCls}>
			<div className={_innerCls}>
				{/* Header */}
				<div className="border-b border-gray-200 bg-white px-10 py-5">
					<div className="flex items-center justify-between">
						<div className="flex-1">
							<h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
								<Users className="w-5 h-5 text-blue-600" />
								统一审核（角色/任务/交付物）
							</h2>
							<p className="text-sm text-gray-500 mt-1">{data.message || '项目总监已完成角色选择和任务分派，请审核并确认：'}</p>
						</div>
					</div>

					{/* 占位数据异常检测 */}
					{editedRoles.length > 0 && editedRoles.every((r) => r.role_id.startsWith('REQ-')) && (
						<div className="mt-3 flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
							<AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
							<p className="text-xs text-amber-800">
								检测到占位角色数据（REQ-* 前缀），当前为预规划视图。建议直接确认，项目总监将生成正式角色分配。
							</p>
						</div>
					)}

					{/* 统计信息 */}
					<div className="mt-3 flex items-center gap-6 text-sm">
						<div className="flex items-center gap-1.5">
							<Users className="w-4 h-4 text-blue-500" />
							<span className="text-gray-600">
								共 <span className="font-semibold text-gray-800">{editedRoles.length}</span> 个角色
							</span>
						</div>
						<div className="flex items-center gap-1.5">
							<ListTodo className="w-4 h-4 text-green-500" />
							<span className="text-gray-600">
								共 <span className="font-semibold text-gray-800">{totalTasks}</span> 个任务
							</span>
						</div>
						<div className="flex items-center gap-1.5">
							<CheckCircle2 className="w-4 h-4 text-blue-500" />
							<span className="text-gray-600">
								<span className="font-semibold text-gray-800">{rolesWithTasks}</span> 个角色已分配任务
							</span>
						</div>
					</div>
				</div>

				{/* Content */}
				<div className="flex-1 overflow-y-auto px-10 py-6 bg-[#f5f5f7]">
					{/* v15.0: DWP 任务优先视图（如果有 plan_view 数据） */}
					{data.plan_view?.work_packages?.length > 0 && (
						<div className="mb-6">
							<PlanReviewPanel
								planView={data.plan_view}
								isEditing={isEditingDwp}
								onRequestEdit={() => setIsEditingDwp(true)}
								onCancelEdit={() => setIsEditingDwp(false)}
								onSaveEdits={handleDwpSave}
							/>
						</div>
					)}

					<div className="space-y-4">
						{editedRoles.map((role, roleIndex) => {
							const isExpanded = expandedRoles.has(role.role_id);
							const canEdit = isEditing && selectedAction === 'modify_tasks';

							return (
								<div
									key={role.role_id}
									className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm"
								>
									{/* 角色头部 */}
									<div
										className="p-4 cursor-pointer hover:bg-gray-50 transition"
										onClick={() => toggleRole(role.role_id)}
									>
										<div className="flex items-start justify-between">
											<div className="flex-1">
												<div className="flex items-center gap-2">
													<span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded">
														{role.role_id}
													</span>
													<h3 className="text-base font-semibold text-gray-800">{role.role_name}</h3>
													<span className="text-xs text-gray-500">({role.tasks.length} 个任务)</span>
												</div>
												{role.focus_areas && role.focus_areas.length > 0 && (
													<div className="mt-2 flex flex-wrap gap-2">
														{role.focus_areas.map((area, i) => (
															<span
																key={i}
																className="badge-gray"
															>
																{area}
															</span>
														))}
													</div>
												)}
											</div>
											<button className="text-gray-400 hover:text-gray-600">
												{isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
											</button>
										</div>
									</div>

									{/* 角色详情（展开时显示） */}
									{isExpanded && (
										<div className="px-4 pb-4 border-t border-gray-100">
											{/* 任务列表 */}
											<div className="mt-4">
												<div className="flex items-center justify-between mb-3">
														<h4 className="text-sm font-semibold text-gray-700">任务列表</h4>
														{canEdit && (
															<button
																onClick={() => handleAddTask(role.role_id)}
																className="text-xs text-blue-600 hover:text-blue-700 font-medium"
														>
															+ 添加任务
														</button>
													)}
												</div>
												<div className="space-y-2">
													{role.tasks.map((task, taskIndex) => (
														<div key={taskIndex} className="flex items-start gap-2">
																	<span className="flex-shrink-0 w-6 h-6 bg-gray-200 rounded-full text-gray-600 flex items-center justify-center text-xs font-medium mt-1">
																{taskIndex + 1}
															</span>
															{canEdit ? (
																<div className="flex-1 flex items-start gap-2">
																	<textarea
																		value={task}
																		onChange={(e) => handleTaskEdit(role.role_id, taskIndex, e.target.value)}
																				className="flex-1 px-3 py-2 text-sm text-gray-800 bg-white border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none min-h-[60px] resize-y"
																		placeholder="输入任务描述..."
																	/>
																	<button
																		onClick={() => handleDeleteTask(role.role_id, taskIndex)}
																				className="flex-shrink-0 text-red-500 hover:text-red-600 mt-2"
																		title="删除任务"
																	>
																		<X className="w-4 h-4" />
																	</button>
																</div>
															) : (
																	<p className="flex-1 text-sm text-gray-700 leading-relaxed">{task}</p>
															)}
														</div>
													))}
													{role.tasks.length === 0 && (
																<div className="text-sm text-gray-400 italic">暂无任务</div>
													)}
												</div>
											</div>

											{/* 预期输出 */}
											{role.expected_output && (
												<div className="mt-4">
													<h4 className="text-sm font-semibold text-gray-700 mb-2">预期输出</h4>
													<p className="text-sm text-gray-600 leading-relaxed">{role.expected_output}</p>
												</div>
											)}

											{/* 依赖关系 */}
											{role.dependencies && role.dependencies.length > 0 && (
												<div className="mt-4">
													<h4 className="text-sm font-semibold text-gray-700 mb-2">依赖角色</h4>
													<div className="flex flex-wrap gap-2">
														{role.dependencies.map((dep, i) => (
															<span
																key={i}
																className="text-xs text-blue-700 bg-blue-50 px-2 py-1 rounded-full"
															>
																{dep}
															</span>
														))}
													</div>
												</div>
											)}

											{/* 🆕 v7.129: 工具权限 */}
											{role.tool_settings && (
												<div className="mt-4">
														<h4 className="text-sm font-semibold text-gray-700 mb-2">工具权限</h4>
													<div className="space-y-2">
														{/* 搜索工具状态 */}
														<div className="flex items-center gap-2">
																<span className="text-sm text-gray-600">搜索工具:</span>
																{role.tool_settings.enable_search ? (
																	<span className="text-xs font-medium text-green-700 bg-green-50 px-2 py-1 rounded-full">
																		已启用
																	</span>
																) : (
																	<span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
																	已禁用
																</span>
															)}
														</div>

														{/* 可用工具列表 */}
														{role.tool_settings.available_tools && role.tool_settings.available_tools.length > 0 && (
															<div>
																	<span className="text-sm text-gray-600">可用工具:</span>
																<div className="flex flex-wrap gap-1 mt-1">
																	{role.tool_settings.available_tools.map((tool, i) => {
																		const isRecommended = role.tool_settings?.recommended?.includes(tool);
																		return (
																			<span
																				key={i}
																				className={`text-xs px-2 py-1 rounded-full ${
																					isRecommended
																						? 'text-gray-700 bg-gray-200 font-medium'
																						: 'text-gray-500 bg-gray-100'
																				}`}
																			>
																				{tool}
																				{isRecommended && ' ✓'}
																			</span>
																		);
																	})}
																</div>
															</div>
														)}

														{/* 推荐工具提示 */}
														{role.tool_settings.recommended && role.tool_settings.recommended.length > 0 && (
																<p className="text-xs text-blue-600 italic">
																✓ = 推荐使用
															</p>
														)}

														{/* V2角色特殊提示 */}
														{role.role_id.startsWith('V2') || role.role_id.startsWith('2-') && !role.tool_settings.enable_search && (
																<div className="flex items-start gap-2 p-2 bg-amber-50 border border-amber-200 rounded-lg">
																	<AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
																	<p className="text-xs text-amber-800">
																	设计总监角色仅允许使用内部知识库，避免外部搜索干扰创意判断
																</p>
															</div>
														)}
													</div>
												</div>
											)}
										</div>
									)}
								</div>
							);
						})}
					</div>

					{/* 预期交付物（来自 unified_review.deliverables） */}
					{data.unified_review?.deliverables && data.unified_review.deliverables.length > 0 && (
						<div className="mt-6 bg-white rounded-xl border border-purple-100 p-5 shadow-sm">
							<h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
								<Package className="w-4 h-4 text-purple-500" />
								预期交付物（草稿）
							</h3>
							<div className="space-y-2">
								{data.unified_review.deliverables.map((d: string, i: number) => (
									<div key={i} className="flex items-start gap-2 text-sm text-gray-700">
										<span className="flex-shrink-0 w-5 h-5 rounded-full bg-purple-50 text-purple-600 flex items-center justify-center text-xs font-medium mt-0.5">
											{i + 1}
										</span>
										<span className="leading-relaxed">{d}</span>
									</div>
								))}
							</div>
						</div>
					)}

					{/* 编辑提示 */}
					{isEditing && selectedAction === 'modify_tasks' && (
					<div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-start gap-3">
						<AlertCircle className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
						<div className="flex-1">
							<p className="text-sm text-gray-800 font-medium mb-1">编辑模式</p>
							<p className="text-sm text-gray-600">您可以修改、添加或删除任务。点击&ldquo;保存并继续&rdquo;提交修改。</p>
							</div>
						</div>
					)}
				</div>

				{/* Footer Actions */}
				<div className="px-10 py-4 bg-white flex items-center justify-end">
					{isEditing && selectedAction === 'modify_tasks' ? (
						<div className="flex items-center justify-end gap-3">
							<button
								onClick={() => {
									setIsEditing(false);
									setSelectedAction(null);
									// 重置数据
									if (data.task_assignment?.task_list) {
										const roles = data.task_assignment.task_list.map((role: any) => ({
											role_id: role.role_id,
											role_name: role.dynamic_role_name || role.role_name || role.static_role_name,
											dynamic_role_name: role.dynamic_role_name,
											tasks: role.tasks?.map((t: any) => (typeof t === 'string' ? t : t.description)) || [],
											focus_areas: role.focus_areas || [],
											expected_output: role.expected_output || '',
											dependencies: role.dependencies || [],
											task_count: role.task_count
										}));
										setEditedRoles(JSON.parse(JSON.stringify(roles)));
									}
								}}
								className="px-5 py-2.5 text-gray-600 border border-gray-300 rounded-full hover:bg-gray-50 transition text-sm"
							>
								取消
							</button>
							<button
								onClick={handleConfirm}
								className="btn-primary-lg flex items-center gap-2"
							>
								<Save className="w-4 h-4" />
								保存并继续
							</button>
						</div>
					) : (
						<div className="flex items-center justify-between w-full">
							{/* Left: destructive actions */}
							<div className="flex items-center gap-2">
								{!showRejectConfirm ? (
									<button
										onClick={() => setShowRejectConfirm(true)}
										className="px-4 py-2 text-red-500 border border-red-200 rounded-full hover:bg-red-50 transition flex items-center gap-1.5 text-sm"
									>
										<XCircle className="w-3.5 h-3.5" />
										拒绝
									</button>
								) : (
									<div className="flex items-center gap-2">
										<span className="text-sm text-red-500">确认拒绝？</span>
										<button
											onClick={() => {
												setSelectedAction('reject');
												onConfirm('reject', { reason: '用户拒绝当前方案' });
											}}
											className="px-3 py-1.5 bg-red-500 text-white rounded-full hover:bg-red-600 transition text-xs"
										>
											确认
										</button>
										<button
											onClick={() => setShowRejectConfirm(false)}
											className="px-3 py-1.5 text-gray-500 border border-gray-300 rounded-full hover:bg-gray-50 transition text-xs"
										>
											取消
										</button>
									</div>
								)}
							</div>
							{/* Right: primary actions */}
							<div className="flex items-center gap-3">
								<button
									onClick={() => {
										setSelectedAction('modify_roles');
										onConfirm('modify_roles');
									}}
									className="px-5 py-2.5 text-blue-600 border border-blue-200 rounded-full hover:bg-blue-50 transition flex items-center gap-2 text-sm"
								>
									<RefreshCw className="w-4 h-4" />
									重新选角
								</button>
								<button
									onClick={() => {
										setIsEditing(true);
										setSelectedAction('modify_tasks');
									}}
									className="px-5 py-2.5 text-gray-600 border border-gray-300 rounded-full hover:bg-gray-50 transition flex items-center gap-2 text-sm"
								>
									<Edit2 className="w-4 h-4" />
									修改任务
								</button>
								<button
									onClick={() => {
										setSelectedAction('approve');
										handleConfirm();
									}}
									className="btn-primary-lg flex items-center gap-2"
								>
									<CheckCircle2 className="w-4 h-4" />
									执行
								</button>
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
