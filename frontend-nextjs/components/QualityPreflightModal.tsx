/**
 * 质量预检警告模态框
 * v7.119: 新增 - 用于显示高风险任务警告
 */

'use client';

import { AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';
import { useState } from 'react';

interface RiskWarning {
	role_id: string;
	role_name: string;
	task_summary: string;
	risk_score: number;
	risk_level: string;
	checklist: string[];
}

interface QualityPreflightData {
	interaction_type: 'quality_preflight_warning';
	high_risk_count: number;
	medium_risk_count: number;
	warnings: RiskWarning[];
	summary: string;
}

interface QualityPreflightModalProps {
	isOpen: boolean;
	data: QualityPreflightData | null;
	onConfirm: () => void;
	onCancel: () => void;
}

export function QualityPreflightModal({
	isOpen,
	data,
	onConfirm,
	onCancel
}: QualityPreflightModalProps) {
	const [isSubmitting, setIsSubmitting] = useState(false);

	if (!isOpen || !data) return null;

	const handleConfirm = async () => {
		setIsSubmitting(true);
		try {
			await onConfirm();
		} finally {
			setIsSubmitting(false);
		}
	};

	const getRiskColor = (level: string) => {
		switch (level) {
			case 'high':
				return 'text-red-600 bg-red-50 border-red-200';
			case 'medium':
				return 'text-yellow-600 bg-yellow-50 border-yellow-200';
			default:
				return 'text-gray-600 bg-gray-50 border-gray-200';
		}
	};

	const getRiskLabel = (level: string) => {
		switch (level) {
			case 'high':
				return '高风险';
			case 'medium':
				return '中风险';
			default:
				return '低风险';
		}
	};

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
			<div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col m-4">
				{/* Header */}
				<div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-yellow-50 to-orange-50">
					<div className="flex items-center gap-3">
						<div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
							<AlertTriangle className="w-6 h-6 text-yellow-600" />
						</div>
						<div>
							<h2 className="text-xl font-bold text-gray-900">质量预检警告</h2>
							<p className="text-sm text-gray-600 mt-1">
								发现 {data.high_risk_count} 个高风险任务，需要您的确认
							</p>
						</div>
					</div>
				</div>

				{/* Content */}
				<div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
					{/* 摘要信息 */}
					<div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
						<p className="text-sm text-gray-700">
							{data.summary}
						</p>
						<div className="mt-3 flex items-center gap-4 text-sm">
							<span className="px-3 py-1.5 bg-red-100 text-red-700 rounded-full font-medium">
								高风险：{data.high_risk_count}
							</span>
							<span className="px-3 py-1.5 bg-yellow-100 text-yellow-700 rounded-full font-medium">
								中风险：{data.medium_risk_count}
							</span>
						</div>
					</div>

					{/* 风险警告列表 */}
					<div className="space-y-4">
						{data.warnings.map((warning, index) => (
							<div
								key={index}
								className={`border-2 rounded-xl p-5 transition-all hover:shadow-md ${
									warning.risk_level === 'high'
										? 'border-red-200 bg-red-50/30'
										: 'border-yellow-200 bg-yellow-50/30'
								}`}
							>
								{/* 角色信息 */}
								<div className="flex items-start justify-between mb-4">
									<div className="flex-1">
										<h3 className="font-bold text-gray-900 text-lg">
											{warning.role_name}
										</h3>
										<p className="text-sm text-gray-600 mt-2 leading-relaxed">
											{warning.task_summary}
										</p>
									</div>
									<div className="flex flex-col items-end gap-2 ml-4 flex-shrink-0">
										<span className={`px-4 py-1.5 rounded-full text-xs font-bold border-2 ${getRiskColor(warning.risk_level)}`}>
											{getRiskLabel(warning.risk_level)}
										</span>
										<span className="text-2xl font-bold text-gray-800">
											{warning.risk_score}
											<span className="text-sm text-gray-500">/100</span>
										</span>
									</div>
								</div>

								{/* 风险清单 */}
								<div className="bg-white border border-gray-200 rounded-lg p-4">
									<h4 className="text-sm font-bold text-gray-700 mb-3 flex items-center gap-2">
										<XCircle className="w-4 h-4 text-red-500" />
										风险清单
									</h4>
									<ul className="space-y-2.5">
										{(warning.checklist || []).map((item, idx) => (
											<li key={idx} className="flex items-start gap-3 text-sm text-gray-700">
												<span className="flex-shrink-0 w-5 h-5 bg-red-100 text-red-600 rounded-full flex items-center justify-center text-xs font-bold mt-0.5">
													{idx + 1}
												</span>
												<span className="flex-1">{item}</span>
											</li>
										))}
									</ul>
								</div>
							</div>
						))}
					</div>

					{/* 说明 */}
					<div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-xl p-5">
						<h4 className="font-bold text-blue-900 mb-3 text-lg">💡 温馨提示</h4>
						<ul className="space-y-2.5 text-sm text-blue-800">
							<li className="flex items-start gap-3">
								<CheckCircle2 className="w-5 h-5 mt-0.5 flex-shrink-0 text-blue-600" />
								<span>系统已为每个高风险任务提供详细的风险清单</span>
							</li>
							<li className="flex items-start gap-3">
								<CheckCircle2 className="w-5 h-5 mt-0.5 flex-shrink-0 text-blue-600" />
								<span>专家团队将参考清单进行额外的质量把控</span>
							</li>
							<li className="flex items-start gap-3">
								<CheckCircle2 className="w-5 h-5 mt-0.5 flex-shrink-0 text-blue-600" />
								<span>您可以选择继续执行或取消并修改需求</span>
							</li>
						</ul>
					</div>
				</div>

				{/* Footer */}
				<div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-end gap-3">
					<button
						onClick={onCancel}
						disabled={isSubmitting}
						className="px-6 py-2.5 border-2 border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
					>
						取消并修改需求
					</button>
					<button
						onClick={handleConfirm}
						disabled={isSubmitting}
						className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white font-medium rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
					>
						{isSubmitting ? (
							<>
								<span className="animate-spin">⏳</span>
								确认中...
							</>
						) : (
							<>
								<CheckCircle2 className="w-5 h-5" />
								确认继续执行
							</>
						)}
					</button>
				</div>
			</div>
		</div>
	);
}
