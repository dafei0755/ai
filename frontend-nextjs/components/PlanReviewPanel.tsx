// components/PlanReviewPanel.tsx
// v15.0: DWP 任务优先审核面板 — 在 RoleTaskReviewModal 内嵌入
// 以"用户核心任务"为主键展示交付物工作包，替代纯角色视图
// v15.1: 支持 DWP 内联编辑（增删改）

'use client';

import { useState, useMemo, useCallback } from 'react';
import {
 CheckCircle2,
 AlertCircle,
 Package,
 User,
 ArrowRight,
 ChevronDown,
 ChevronUp,
 Target,
 Pencil,
 Trash2,
 Plus,
 X,
 Search,
} from 'lucide-react';

// ============================================================================
// Types
// ============================================================================

export interface DWP {
 dwp_id: string;
 name: string;
 description: string;
 deliverable_type: string;
 format: string;
 source_task_ids: string[];
 owner_role_id: string;
 contributor_role_ids: string[];
 depends_on: string[];
 priority: string;
 success_criteria: string[];
 constraints: string[];
 require_search: boolean;
 status: string;
 assigned_batch?: number | null;
}

interface TaskRef {
 task_id: string;
 title: string;
}

interface CoverageReport {
 covered: boolean;
 coverage_rate: number;
 covered_task_ids: string[];
 uncovered_task_ids: string[];
 details: string;
}

export interface PlanViewData {
 work_packages: DWP[];
 coverage: CoverageReport | null;
 confirmed_tasks: TaskRef[];
 view_mode: string;
}

interface PlanReviewPanelProps {
 planView: PlanViewData | null;
 /** 是否处于编辑模式 */
 isEditing?: boolean;
 /** 编辑后保存回调，传回完整的 DWP 列表 */
 onSaveEdits?: (editedDwps: DWP[]) => void;
 /** 取消编辑回调 */
 onCancelEdit?: () => void;
 /** 请求进入编辑模式 */
 onRequestEdit?: () => void;
}

// ============================================================================
// Helper: group DWPs by source task
// ============================================================================

function groupByTask(
 tasks: TaskRef[],
 dwps: DWP[]
): { task: TaskRef; dwps: DWP[] }[] {
 const groups: { task: TaskRef; dwps: DWP[] }[] = [];

 for (const task of tasks) {
 const matched = dwps.filter((d) =>
 d.source_task_ids?.includes(task.task_id)
 );
 groups.push({ task, dwps: matched });
 }

 // Unlinked DWPs (source_task_ids = ["UNLINKED"] or not matching any task)
 const allLinkedIds = new Set(tasks.map((t) => t.task_id));
 const unlinked = dwps.filter(
 (d) =>
 !d.source_task_ids?.some((id) => allLinkedIds.has(id)) ||
 d.source_task_ids?.includes('UNLINKED')
 );
 if (unlinked.length > 0) {
 groups.push({
 task: { task_id: 'UNLINKED', title: '未关联任务的交付物' },
 dwps: unlinked,
 });
 }

 return groups;
}

/** 生成临时 DWP id */
function generateTempDwpId(): string {
 return `DWP-NEW-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
}

// ============================================================================
// Sub-components
// ============================================================================

function CoverageBadge({ coverage }: { coverage: CoverageReport | null }) {
 if (!coverage) return null;
 const pct = Math.round(coverage.coverage_rate * 100);
 const color =
 pct === 100
 ? 'text-green-600'
 : pct >= 80
 ? 'text-yellow-600'
 : 'text-red-600'

 return (
 <div className="flex items-center gap-2 text-sm">
 {pct === 100 ? (
 <CheckCircle2 className="w-4 h-4 text-green-500" />
 ) : (
 <AlertCircle className="w-4 h-4 text-yellow-500" />
 )}
 <span className={color}>
 任务覆盖率 {pct}%
 </span>
 {coverage.uncovered_task_ids?.length > 0 && (
 <span className="text-xs text-gray-500">
 ({coverage.uncovered_task_ids.length} 个未覆盖)
 </span>
 )}
 </div>
 );
}

const PRIORITY_OPTIONS = ['high', 'medium', 'low'] as const;

const PRIORITY_COLORS: Record<string, string> = {
 high: 'bg-red-100 text-red-700',
 medium: 'bg-yellow-100 text-yellow-700',
 low: 'bg-green-100 text-green-700',
};

const PRIORITY_LABELS: Record<string, string> = {
 high: '高',
 medium: '中',
 low: '低',
};

/** 只读 DWP 卡片 */
function DWPCard({ dwp }: { dwp: DWP }) {
 const [expanded, setExpanded] = useState(false);

 return (
 <div className="bg-[#f5f5f7] rounded-lg p-3 hover:bg-gray-100 transition">
 <div
 className="flex items-start justify-between cursor-pointer"
 onClick={() => setExpanded(!expanded)}
 >
 <div className="flex items-start gap-2 flex-1 min-w-0">
 <Package className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
 <div className="min-w-0">
 <div className="flex items-center gap-2 flex-wrap">
 <span className="font-medium text-sm text-gray-900">
 {dwp.name}
 </span>
 <span className="text-xs text-gray-400">{dwp.dwp_id}</span>
 <span
 className={`text-xs px-1.5 py-0.5 rounded ${PRIORITY_COLORS[dwp.priority] || PRIORITY_COLORS.medium}`}
 >
 {dwp.priority}
 </span>
 </div>
 <p className="text-xs text-gray-600 mt-0.5 line-clamp-2">
 {dwp.description}
 </p>
 </div>
 </div>
 <div className="flex items-center gap-2 flex-shrink-0 ml-2">
 <span className="text-xs text-gray-500 flex items-center gap-1">
 <User className="w-3 h-3" />
 {dwp.owner_role_id}
 </span>
 {expanded ? (
 <ChevronUp className="w-4 h-4 text-gray-400" />
 ) : (
 <ChevronDown className="w-4 h-4 text-gray-400" />
 )}
 </div>
 </div>

 {expanded && (
 <div className="mt-3 pl-6 space-y-2 text-xs">
 {dwp.success_criteria?.length > 0 && (
 <div>
 <span className="text-gray-500 font-medium">验收标准:</span>
 <ul className="list-disc list-inside text-gray-600">
 {dwp.success_criteria.map((c, i) => (
 <li key={i}>{c}</li>
 ))}
 </ul>
 </div>
 )}
 {dwp.depends_on?.length > 0 && (
 <div className="flex items-center gap-1 text-gray-500">
 <ArrowRight className="w-3 h-3" />
 依赖: {dwp.depends_on.join(', ')}
 </div>
 )}
 {dwp.contributor_role_ids?.length > 0 && (
 <div className="text-gray-500">
 协作: {dwp.contributor_role_ids.join(', ')}
 </div>
 )}
 {dwp.require_search && (
 <div className="text-blue-500">需要外部搜索</div>
 )}
 </div>
 )}
 </div>
 );
}

/** 可编辑 DWP 卡片 */
function EditableDWPCard({
 dwp,
 availableTaskIds,
 availableRoleIds,
 allDwpIds,
 onChange,
 onDelete,
}: {
 dwp: DWP;
 availableTaskIds: string[];
 availableRoleIds: string[];
 allDwpIds: string[];
 onChange: (updated: DWP) => void;
 onDelete: () => void;
}) {
 const [expanded, setExpanded] = useState(true);

 const updateField = <K extends keyof DWP>(key: K, value: DWP[K]) => {
 onChange({ ...dwp, [key]: value });
 };

 const updateCriteria = (index: number, value: string) => {
 const next = [...dwp.success_criteria];
 next[index] = value;
 onChange({ ...dwp, success_criteria: next });
 };

 const addCriteria = () => {
 onChange({ ...dwp, success_criteria: [...(dwp.success_criteria || []), ''] });
 };

 const removeCriteria = (index: number) => {
 onChange({
 ...dwp,
 success_criteria: dwp.success_criteria.filter((_, i) => i !== index),
 });
 };

 const toggleTaskId = (taskId: string) => {
 const current = dwp.source_task_ids || [];
 const next = current.includes(taskId)
 ? current.filter((id) => id !== taskId)
 : [...current.filter((id) => id !== 'UNLINKED'), taskId];
 updateField('source_task_ids', next.length > 0 ? next : ['UNLINKED']);
 };

 const toggleDependency = (depId: string) => {
 const current = dwp.depends_on || [];
 const next = current.includes(depId)
 ? current.filter((id) => id !== depId)
 : [...current, depId];
 updateField('depends_on', next);
 };

 return (
 <div className="border-2 border-blue-300 rounded-lg p-3 bg-blue-50/30 transition">
 {/* Header row */}
 <div className="flex items-start justify-between">
 <div
 className="flex items-start gap-2 flex-1 min-w-0 cursor-pointer"
 onClick={() => setExpanded(!expanded)}
 >
 <Pencil className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
 <div className="min-w-0 flex-1">
 <div className="flex items-center gap-2 flex-wrap">
 <span className="text-xs text-gray-400 font-mono">{dwp.dwp_id}</span>
 {expanded ? (
 <ChevronUp className="w-3 h-3 text-gray-400" />
 ) : (
 <ChevronDown className="w-3 h-3 text-gray-400" />
 )}
 </div>
 </div>
 </div>
 <button
 onClick={onDelete}
 className="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-100 transition"
 title="删除此交付物"
 >
 <Trash2 className="w-4 h-4" />
 </button>
 </div>

 {expanded && (
 <div className="mt-3 space-y-3">
 {/* Name */}
 <div>
 <label className="text-xs font-medium text-gray-600 block mb-1">
 名称
 </label>
 <input
 type="text"
 value={dwp.name}
 onChange={(e) => updateField('name', e.target.value)}
 className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
 placeholder="交付物名称"
 />
 </div>

 {/* Description */}
 <div>
 <label className="text-xs font-medium text-gray-600 block mb-1">
 描述
 </label>
 <textarea
 value={dwp.description}
 onChange={(e) => updateField('description', e.target.value)}
 className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-y min-h-[50px]"
 rows={2}
 placeholder="交付物描述"
 />
 </div>

 {/* Priority + Owner row */}
 <div className="grid grid-cols-2 gap-3">
 <div>
 <label className="text-xs font-medium text-gray-600 block mb-1">
 优先级
 </label>
 <select
 value={dwp.priority}
 onChange={(e) => updateField('priority', e.target.value)}
 className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
 >
 {PRIORITY_OPTIONS.map((p) => (
 <option key={p} value={p}>
 {PRIORITY_LABELS[p]}
 </option>
 ))}
 </select>
 </div>
 <div>
 <label className="text-xs font-medium text-gray-600 block mb-1">
 负责角色
 </label>
 {availableRoleIds.length > 0 ? (
 <select
 value={dwp.owner_role_id}
 onChange={(e) => updateField('owner_role_id', e.target.value)}
 className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
 >
 {availableRoleIds.map((rid) => (
 <option key={rid} value={rid}>
 {rid}
 </option>
 ))}
 </select>
 ) : (
 <input
 type="text"
 value={dwp.owner_role_id}
 onChange={(e) => updateField('owner_role_id', e.target.value)}
 className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
 placeholder="角色 ID"
 />
 )}
 </div>
 </div>

 {/* Format + Type row */}
 <div className="grid grid-cols-2 gap-3">
 <div>
 <label className="text-xs font-medium text-gray-600 block mb-1">
 交付类型
 </label>
 <input
 type="text"
 value={dwp.deliverable_type}
 onChange={(e) => updateField('deliverable_type', e.target.value)}
 className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
 placeholder="如: report, plan, drawing"
 />
 </div>
 <div>
 <label className="text-xs font-medium text-gray-600 block mb-1">
 格式
 </label>
 <input
 type="text"
 value={dwp.format}
 onChange={(e) => updateField('format', e.target.value)}
 className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
 placeholder="如: markdown, pdf"
 />
 </div>
 </div>

 {/* Source task IDs (multi-select chips) */}
 <div>
 <label className="text-xs font-medium text-gray-600 block mb-1">
 关联任务
 </label>
 <div className="flex flex-wrap gap-1.5">
 {availableTaskIds.map((tid) => {
 const isSelected = dwp.source_task_ids?.includes(tid);
 return (
 <button
 key={tid}
 type="button"
 onClick={() => toggleTaskId(tid)}
 className={`text-xs px-2 py-1 rounded-full border transition ${
 isSelected
 ? 'bg-blue-100 border-blue-300 text-blue-700'
 : 'bg-gray-100 border-gray-300 text-gray-500 hover:border-blue-300 hover:text-blue-600'
 }`}
 >
 {tid}
 </button>
 );
 })}
 </div>
 </div>

 {/* Dependencies (multi-select chips among other DWPs) */}
 {allDwpIds.filter((id) => id !== dwp.dwp_id).length > 0 && (
 <div>
 <label className="text-xs font-medium text-gray-600 block mb-1">
 依赖的工作包
 </label>
 <div className="flex flex-wrap gap-1.5">
 {allDwpIds
 .filter((id) => id !== dwp.dwp_id)
 .map((depId) => {
 const isSelected = dwp.depends_on?.includes(depId);
 return (
 <button
 key={depId}
 type="button"
 onClick={() => toggleDependency(depId)}
 className={`text-xs px-2 py-1 rounded-full border transition ${
 isSelected
 ? 'bg-orange-100 border-orange-300 text-orange-700'
 : 'bg-gray-100 border-gray-300 text-gray-500 hover:border-orange-300 hover:text-orange-600'
 }`}
 >
 {depId}
 </button>
 );
 })}
 </div>
 </div>
 )}

 {/* Require search toggle */}
 <div className="flex items-center gap-2">
 <label className="relative inline-flex items-center cursor-pointer">
 <input
 type="checkbox"
 checked={dwp.require_search ?? false}
 onChange={(e) => updateField('require_search', e.target.checked)}
 className="sr-only peer"
 />
 <div className="w-8 h-4 bg-gray-300 peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-blue-500"></div>
 </label>
 <span className="text-xs text-gray-600 flex items-center gap-1">
 <Search className="w-3 h-3" />
 需要外部搜索
 </span>
 </div>

 {/* Success criteria (editable list) */}
 <div>
 <div className="flex items-center justify-between mb-1">
 <label className="text-xs font-medium text-gray-600">
 验收标准
 </label>
 <button
 type="button"
 onClick={addCriteria}
 className="text-xs text-blue-600 hover:text-blue-700 font-medium"
 >
 + 添加
 </button>
 </div>
 <div className="space-y-1.5">
 {(dwp.success_criteria || []).map((c, i) => (
 <div key={i} className="flex items-center gap-1.5">
 <span className="text-xs text-gray-400 w-4 text-right flex-shrink-0">
 {i + 1}.
 </span>
 <input
 type="text"
 value={c}
 onChange={(e) => updateCriteria(i, e.target.value)}
 className="flex-1 px-2 py-1 text-xs border border-gray-300 rounded bg-white text-gray-900 focus:ring-1 focus:ring-blue-500 outline-none"
 placeholder="输入验收标准..."
 />
 <button
 type="button"
 onClick={() => removeCriteria(i)}
 className="text-red-400 hover:text-red-600 flex-shrink-0"
 >
 <X className="w-3.5 h-3.5" />
 </button>
 </div>
 ))}
 {(!dwp.success_criteria || dwp.success_criteria.length === 0) && (
 <p className="text-xs text-gray-400 italic">暂无验收标准</p>
 )}
 </div>
 </div>
 </div>
 )}
 </div>
 );
}

// ============================================================================
// Main Component
// ============================================================================

export function PlanReviewPanel({
 planView,
 isEditing = false,
 onSaveEdits,
 onCancelEdit,
 onRequestEdit,
}: PlanReviewPanelProps) {
 const originalDwps = useMemo(
 () => planView?.work_packages ?? [],
 [planView?.work_packages]
 );
 const coverage = planView?.coverage ?? null;
 const tasks = useMemo(
 () => planView?.confirmed_tasks ?? [],
 [planView?.confirmed_tasks]
 );

 // Editing state — deep copy for mutation safety
 const [editedDwps, setEditedDwps] = useState<DWP[]>([]);

 // Initialize/reset edited list when entering edit mode
 const prevIsEditing = useState(false);
 if (isEditing && !prevIsEditing[0]) {
 setEditedDwps(JSON.parse(JSON.stringify(originalDwps)));
 }
 prevIsEditing[0] = isEditing;

 const activeDwps = isEditing ? editedDwps : originalDwps;

 const groups = useMemo(
 () => groupByTask(tasks || [], activeDwps),
 [tasks, activeDwps]
 );

 // All unique role IDs for select dropdown
 const availableRoleIds = useMemo(() => {
 const s = new Set<string>();
 for (const d of originalDwps) {
 if (d.owner_role_id) s.add(d.owner_role_id);
 for (const c of d.contributor_role_ids || []) s.add(c);
 }
 return Array.from(s).sort();
 }, [originalDwps]);

 const availableTaskIds = useMemo(
 () => tasks.map((t) => t.task_id),
 [tasks]
 );

 const allDwpIds = useMemo(
 () => activeDwps.map((d) => d.dwp_id),
 [activeDwps]
 );

 // Role load summary
 const roleSummary = useMemo(() => {
 const map: Record<string, number> = {};
 for (const dwp of activeDwps) {
 map[dwp.owner_role_id] = (map[dwp.owner_role_id] || 0) + 1;
 }
 return Object.entries(map).sort((a, b) => b[1] - a[1]);
 }, [activeDwps]);

 // Edit handlers
 const handleDwpChange = useCallback((index: number, updated: DWP) => {
 setEditedDwps((prev) => {
 const next = [...prev];
 next[index] = updated;
 return next;
 });
 }, []);

 const handleDwpDelete = useCallback((index: number) => {
 setEditedDwps((prev) => prev.filter((_, i) => i !== index));
 }, []);

 const handleAddDwp = useCallback(() => {
 const newDwp: DWP = {
 dwp_id: generateTempDwpId(),
 name: '',
 description: '',
 deliverable_type: 'report',
 format: 'markdown',
 source_task_ids: availableTaskIds.length > 0 ? [availableTaskIds[0]] : ['UNLINKED'],
 owner_role_id: availableRoleIds.length > 0 ? availableRoleIds[0] : '',
 contributor_role_ids: [],
 depends_on: [],
 priority: 'medium',
 success_criteria: [],
 constraints: [],
 require_search: false,
 status: 'pending',
 assigned_batch: null,
 };
 setEditedDwps((prev) => [...prev, newDwp]);
 }, [availableTaskIds, availableRoleIds]);

 const handleSave = useCallback(() => {
 // Filter out empty-named DWPs
 const cleaned = editedDwps.filter((d) => d.name.trim() !== '');
 onSaveEdits?.(cleaned);
 }, [editedDwps, onSaveEdits]);

 if (!planView || originalDwps.length === 0) {
 return null;
 }

 // ----------- EDIT MODE -----------
 if (isEditing) {
 return (
 <div className="space-y-4">
 {/* Header */}
 <div className="flex items-center justify-between">
 <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
 <Pencil className="w-4 h-4 text-blue-500" />
 编辑交付物工作包
 </h3>
 <span className="text-xs text-gray-500">
 {editedDwps.length} 个工作包
 </span>
 </div>

 {/* Flat editable list (simpler than grouped view in edit mode) */}
 <div className="space-y-3">
 {editedDwps.map((dwp, idx) => (
 <EditableDWPCard
 key={dwp.dwp_id}
 dwp={dwp}
 availableTaskIds={availableTaskIds}
 availableRoleIds={availableRoleIds}
 allDwpIds={allDwpIds}
 onChange={(updated) => handleDwpChange(idx, updated)}
 onDelete={() => handleDwpDelete(idx)}
 />
 ))}
 </div>

 {/* Add new DWP */}
 <button
 type="button"
 onClick={handleAddDwp}
 className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 transition flex items-center justify-center gap-2"
 >
 <Plus className="w-4 h-4" />
 添加交付物工作包
 </button>

 {/* Save / Cancel */}
 <div className="flex items-center justify-end gap-3 pt-2">
 <button
 type="button"
 onClick={onCancelEdit}
 className="px-5 py-2 text-sm text-gray-600 border border-gray-300 rounded-full hover:bg-gray-50 transition"
 >
 取消
 </button>
 <button
 type="button"
 onClick={handleSave}
 className="px-5 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-full transition flex items-center gap-1.5"
 >
 <CheckCircle2 className="w-3.5 h-3.5" />
 保存交付物
 </button>
 </div>
 </div>
 );
 }

 // ----------- READ-ONLY MODE -----------
 return (
 <div className="space-y-4">
 {/* Header + Role Summary Card */}
 <div className="bg-white rounded-xl shadow-sm p-4">
 <div className="flex items-center justify-between">
 <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
 <Target className="w-4 h-4 text-blue-500" />
 交付物工作包计划
 </h3>
 <div className="flex items-center gap-3">
 <CoverageBadge coverage={coverage} />
 {onRequestEdit && (
 <button
 type="button"
 onClick={onRequestEdit}
 className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1 transition"
 >
 <Pencil className="w-3 h-3" />
 编辑
 </button>
 )}
 </div>
 </div>

 {/* Role Load Summary */}
 {roleSummary.length > 0 && (
 <div className="mt-3 flex flex-wrap gap-2">
 {roleSummary.map(([roleId, count]) => (
 <span
 key={roleId}
 className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-blue-50 text-blue-700"
 >
 <User className="w-3 h-3" />
 {roleId}: {count} 个交付物
 </span>
 ))}
 </div>
 )}
 </div>

 {/* Task-grouped DWP List — each group is its own card */}
{groups.map(({ task, dwps: groupDwps }, groupIndex) => (
 <div key={`${task.task_id}-${groupIndex}`} className="bg-white rounded-xl shadow-sm overflow-hidden">
 {/* Task group header */}
 <div className="px-4 pt-4 pb-2 flex items-center gap-2">
 <span
 className={`text-xs font-mono px-1.5 py-0.5 rounded ${
 task.task_id === 'UNLINKED'
 ? 'bg-gray-200 text-gray-600'
 : 'bg-blue-100 text-blue-700'
 }`}
 >
 {task.task_id}
 </span>
 <span className="text-sm font-medium text-gray-800">
 {task.title}
 </span>
 <span className="text-xs text-gray-500">
 ({groupDwps.length} 个交付物)
 </span>
 </div>
 {/* DWP cards within this task group */}
 <div className="px-4 pb-4 space-y-2">
 {groupDwps.length > 0 ? (
 groupDwps.map((dwp) => <DWPCard key={dwp.dwp_id} dwp={dwp} />)
 ) : (
 <div className="text-xs text-amber-600 py-1">
 无关联交付物 — 此任务可能未被覆盖
 </div>
 )}
 </div>
 </div>
 ))}
 </div>
 );
}
