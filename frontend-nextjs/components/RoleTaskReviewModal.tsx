// components/RoleTaskReviewModal.tsx
// 角色任务审核 Modal 组件

'use client';

import { useState, useEffect } from 'react';
import { CheckCircle2, Edit2, Save, X, Users, ListTodo, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';

interface RoleData {
	role_id: string;
	role_name: string;
	dynamic_role_name?: string;
	tasks: string[];
	focus_areas?: string[];
	expected_output?: string;
	dependencies?: string[];
	task_count?: number;
}

interface RoleTaskReviewModalProps {
	isOpen: boolean;
	data: any; // role_and_task_unified_review interrupt_data
	onConfirm: (action: string, modifications?: any) => void;
}

export function RoleTaskReviewModal({ isOpen, data, onConfirm }: RoleTaskReviewModalProps) {
	const [editedRoles, setEditedRoles] = useState<RoleData[]>([]);
	const [expandedRoles, setExpandedRoles] = useState<Set<string>>(new Set());
	const [isEditing, setIsEditing] = useState(false);
	const [selectedAction, setSelectedAction] = useState<'approve' | 'modify_roles' | 'modify_tasks' | null>(null);

	useEffect(() => {
		if (isOpen && data) {
			// 从 role_selection.selected_roles 或 task_assignment.task_list 提取角色数据
			let roles: RoleData[] = [];

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
					task_count: role.task_count
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
					dependencies: role.dependencies || []
				}));
			}

			setEditedRoles(JSON.parse(JSON.stringify(roles)));
			// 默认全部展开
			setExpandedRoles(new Set(roles.map((r) => r.role_id)));
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

	const totalTasks = editedRoles.reduce((sum, role) => sum + role.tasks.length, 0);
	const rolesWithTasks = editedRoles.filter((role) => role.tasks.length > 0).length;

	return (
		<div className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
			<div className="bg-white dark:bg-[var(--card-bg)] rounded-xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col shadow-2xl border border-gray-200 dark:border-[var(--border-color)]">
				{/* Header */}
				<div className="border-b border-gray-200 dark:border-[var(--border-color)] px-6 py-5 bg-gray-50 dark:bg-gray-800/50">
					<div className="flex items-center justify-between">
						<div className="flex-1">
							<h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
								<Users className="w-5 h-5" />
								任务审批
							</h2>
							<p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{data.message || '请审批项目拆分和任务分配方案'}</p>
						</div>
					</div>

					{/* 统计信息 */}
					<div className="mt-4 flex items-center gap-6 text-sm">
						<div className="flex items-center gap-2">
							<Users className="w-4 h-4 text-blue-600" />
							<span className="text-gray-600 dark:text-gray-400">
								共 <span className="font-semibold text-gray-900 dark:text-gray-100">{editedRoles.length}</span> 个角色
							</span>
						</div>
						<div className="flex items-center gap-2">
							<ListTodo className="w-4 h-4 text-green-600" />
							<span className="text-gray-600 dark:text-gray-400">
								共 <span className="font-semibold text-gray-900 dark:text-gray-100">{totalTasks}</span> 个任务
							</span>
						</div>
						<div className="flex items-center gap-2">
							<CheckCircle2 className="w-4 h-4 text-purple-600" />
							<span className="text-gray-600 dark:text-gray-400">
								<span className="font-semibold text-gray-900 dark:text-gray-100">{rolesWithTasks}</span> 个角色已分配任务
							</span>
						</div>
					</div>
				</div>

				{/* Content */}
				<div className="flex-1 overflow-y-auto px-6 py-6">
					<div className="space-y-4">
						{editedRoles.map((role, roleIndex) => {
							const isExpanded = expandedRoles.has(role.role_id);
							const canEdit = isEditing && selectedAction === 'modify_tasks';

							return (
								<div
									key={role.role_id}
									className="bg-gray-50 dark:bg-gray-800/30 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
								>
									{/* 角色头部 */}
									<div
										className="p-4 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800/50 transition"
										onClick={() => toggleRole(role.role_id)}
									>
										<div className="flex items-start justify-between">
											<div className="flex-1">
												<div className="flex items-center gap-2">
													<span className="text-xs font-medium text-gray-500 dark:text-gray-400 bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded">
														{role.role_id}
													</span>
													<h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">{role.role_name}</h3>
													<span className="text-xs text-gray-500 dark:text-gray-400">({role.tasks.length} 个任务)</span>
												</div>
												{role.focus_areas && role.focus_areas.length > 0 && (
													<div className="mt-2 flex flex-wrap gap-2">
														{role.focus_areas.map((area, i) => (
															<span
																key={i}
																className="text-xs text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/30 px-2 py-1 rounded"
															>
																{area}
															</span>
														))}
													</div>
												)}
											</div>
											<button className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
												{isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
											</button>
										</div>
									</div>

									{/* 角色详情（展开时显示） */}
									{isExpanded && (
										<div className="px-4 pb-4 border-t border-gray-200 dark:border-gray-700">
											{/* 任务列表 */}
											<div className="mt-4">
												<div className="flex items-center justify-between mb-3">
													<h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">任务列表</h4>
													{canEdit && (
														<button
															onClick={() => handleAddTask(role.role_id)}
															className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
														>
															+ 添加任务
														</button>
													)}
												</div>
												<div className="space-y-2">
													{role.tasks.map((task, taskIndex) => (
														<div key={taskIndex} className="flex items-start gap-2">
															<span className="flex-shrink-0 w-6 h-6 bg-gray-300 dark:bg-gray-600 rounded text-gray-700 dark:text-gray-300 flex items-center justify-center text-xs font-medium mt-1">
																{taskIndex + 1}
															</span>
															{canEdit ? (
																<div className="flex-1 flex items-start gap-2">
																	<textarea
																		value={task}
																		onChange={(e) => handleTaskEdit(role.role_id, taskIndex, e.target.value)}
																		className="flex-1 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none min-h-[60px] resize-y"
																		placeholder="输入任务描述..."
																	/>
																	<button
																		onClick={() => handleDeleteTask(role.role_id, taskIndex)}
																		className="flex-shrink-0 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 mt-2"
																		title="删除任务"
																	>
																		<X className="w-4 h-4" />
																	</button>
																</div>
															) : (
																<p className="flex-1 text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{task}</p>
															)}
														</div>
													))}
													{role.tasks.length === 0 && (
														<div className="text-sm text-gray-500 dark:text-gray-400 italic">暂无任务</div>
													)}
												</div>
											</div>

											{/* 预期输出 */}
											{role.expected_output && (
												<div className="mt-4">
													<h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">预期输出</h4>
													<p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{role.expected_output}</p>
												</div>
											)}

											{/* 依赖关系 */}
											{role.dependencies && role.dependencies.length > 0 && (
												<div className="mt-4">
													<h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">依赖角色</h4>
													<div className="flex flex-wrap gap-2">
														{role.dependencies.map((dep, i) => (
															<span
																key={i}
																className="text-xs text-purple-700 dark:text-purple-300 bg-purple-100 dark:bg-purple-900/30 px-2 py-1 rounded"
															>
																{dep}
															</span>
														))}
													</div>
												</div>
											)}
										</div>
									)}
								</div>
							);
						})}
					</div>

					{/* 编辑提示 */}
					{isEditing && selectedAction === 'modify_tasks' && (
						<div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg flex items-start gap-3">
							<AlertCircle className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
							<div className="flex-1">
								<p className="text-sm text-blue-800 dark:text-blue-200 font-medium mb-1">编辑模式</p>
								<p className="text-sm text-blue-700 dark:text-blue-300">您可以修改、添加或删除任务。点击"保存并继续"提交修改。</p>
							</div>
						</div>
					)}
				</div>

				{/* Footer Actions */}
				<div className="border-t border-gray-200 dark:border-[var(--border-color)] px-6 py-4 bg-gray-50 dark:bg-gray-800/50">
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
								className="px-4 py-2 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition"
							>
								取消
							</button>
							<button
								onClick={handleConfirm}
								className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition flex items-center gap-2"
							>
								<Save className="w-4 h-4" />
								保存并继续
							</button>
						</div>
					) : (
						<div className="flex items-center justify-end gap-3">
							<button
								onClick={() => {
									setIsEditing(true);
									setSelectedAction('modify_tasks');
								}}
								className="px-4 py-2 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-600 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 transition flex items-center gap-2"
							>
								<Edit2 className="w-4 h-4" />
								修改任务
							</button>
							<button
								onClick={() => {
									setSelectedAction('approve');
									handleConfirm();
								}}
								className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition flex items-center gap-2"
							>
								<CheckCircle2 className="w-4 h-4" />
								执行
							</button>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
