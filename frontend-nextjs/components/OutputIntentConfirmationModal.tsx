/**
 * 输出意图确认弹窗
 * 用于让用户确认交付类型和身份视角，支持 output_intent_confirmation interrupt 类型
 */

'use client';

import { useState } from 'react';
import { CheckCircle2 } from 'lucide-react';

interface DeliveryOption {
	id: string;
	label: string;
	desc: string;
	recommended: boolean;
	evidence?: string[];
}

interface IdentityModeOption {
	id: string;
	label: string;
	spatial_need?: string;
	recommended: boolean;
	evidence_sources?: string[];
}

interface DeliveryTypesConfig {
	message: string;
	options: DeliveryOption[];
	max_select: number;
}

interface IdentityModesConfig {
	message: string;
	options: IdentityModeOption[];
}

export interface OutputIntentConfirmationData {
	interaction_type: 'output_intent_confirmation';
	title?: string;
	delivery_types?: DeliveryTypesConfig;
	identity_modes?: IdentityModesConfig;
}

export interface OutputIntentConfirmPayload {
	selected_deliveries: string[];
	selected_modes: string[];
}

interface OutputIntentConfirmationModalProps {
	isOpen: boolean;
	data: OutputIntentConfirmationData | null;
	onConfirm: (payload: OutputIntentConfirmPayload) => void;
	onSkip: () => void;
}

export function OutputIntentConfirmationModal({
	isOpen,
	data,
	onConfirm,
	onSkip
}: OutputIntentConfirmationModalProps) {
	const deliveryOptions: DeliveryOption[] = data?.delivery_types?.options ?? [];
	const maxSelect: number = data?.delivery_types?.max_select ?? 3;
	const identityOptions: IdentityModeOption[] = data?.identity_modes?.options ?? [];

	// 默认预选 recommended=true 的项
	const [selectedDeliveries, setSelectedDeliveries] = useState<string[]>(
		() => deliveryOptions.filter((o) => o.recommended).map((o) => o.id)
	);
	const [selectedModes, setSelectedModes] = useState<string[]>(
		() => identityOptions.filter((o) => o.recommended).map((o) => o.id)
	);
	const [isSubmitting, setIsSubmitting] = useState(false);

	if (!isOpen || !data) return null;

	const toggleDelivery = (id: string) => {
		setSelectedDeliveries((prev) => {
			if (prev.includes(id)) {
				return prev.filter((x) => x !== id);
			}
			if (prev.length >= maxSelect) {
				return prev; // 达到上限，不允许再选
			}
			return [...prev, id];
		});
	};

	const toggleMode = (id: string) => {
		setSelectedModes((prev) =>
			prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
		);
	};

	const handleConfirm = async () => {
		setIsSubmitting(true);
		try {
			const payload: OutputIntentConfirmPayload = {
				selected_deliveries: selectedDeliveries.length > 0
					? selectedDeliveries
					: deliveryOptions.filter((o) => o.recommended).map((o) => o.id),
				selected_modes: selectedModes.length > 0
					? selectedModes
					: identityOptions.filter((o) => o.recommended).map((o) => o.id),
			};
			await onConfirm(payload);
		} finally {
			setIsSubmitting(false);
		}
	};

	const isDeliveryLimitReached = selectedDeliveries.length >= maxSelect;

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
			<div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col m-4">
				{/* Header */}
				<div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
					<h2 className="text-lg font-semibold text-gray-800">
						{data.title ?? '输出意图确认'}
					</h2>
				</div>

				{/* Body */}
				<div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
					{/* 交付类型 */}
					{data.delivery_types && (
						<div>
							<div className="text-sm font-medium text-gray-700 mb-1">
								{data.delivery_types.message}
							</div>
							<div className="text-xs text-gray-400 mb-3">
								最多选择 {maxSelect} 项
								{isDeliveryLimitReached && (
									<span className="text-orange-500 ml-2">已达上限</span>
								)}
							</div>
							<div className="space-y-2">
								{deliveryOptions.map((option) => {
									const isSelected = selectedDeliveries.includes(option.id);
									const isDisabled = !isSelected && isDeliveryLimitReached;
									return (
										<button
											key={option.id}
											onClick={() => !isDisabled && toggleDelivery(option.id)}
											disabled={isDisabled}
											className={`w-full text-left rounded-xl border px-4 py-3 transition-all ${
												isSelected
													? 'border-blue-500 bg-blue-50 ring-1 ring-blue-300'
													: isDisabled
													? 'border-gray-200 bg-gray-50 opacity-50 cursor-not-allowed'
													: 'border-gray-200 hover:border-blue-300 hover:bg-blue-50/30 cursor-pointer'
											}`}
										>
											<div className="flex items-center justify-between">
												<div className="flex items-center gap-2">
													<div className={`w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 ${
														isSelected ? 'border-blue-500 bg-blue-500' : 'border-gray-300'
													}`}>
														{isSelected && (
															<svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 12 12">
																<path d="M10 3L5 8.5 2 5.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
															</svg>
														)}
													</div>
													<span className="text-sm font-medium text-gray-800">{option.label}</span>
													{option.recommended && (
														<span className="text-xs px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-600 font-medium">推荐</span>
													)}
												</div>
											</div>
											<p className="text-xs text-gray-500 mt-1 ml-6">{option.desc}</p>
										</button>
									);
								})}
							</div>
						</div>
					)}

					{/* 身份视角 */}
					{data.identity_modes && identityOptions.length > 0 && (
						<div>
							<div className="text-sm font-medium text-gray-700 mb-3">
								{data.identity_modes.message}
							</div>
							<div className="space-y-2">
								{identityOptions.map((option) => {
									const isSelected = selectedModes.includes(option.id);
									return (
										<button
											key={option.id}
											onClick={() => toggleMode(option.id)}
											className={`w-full text-left rounded-xl border px-4 py-3 transition-all ${
												isSelected
													? 'border-indigo-500 bg-indigo-50 ring-1 ring-indigo-300'
													: 'border-gray-200 hover:border-indigo-300 hover:bg-indigo-50/30 cursor-pointer'
											}`}
										>
											<div className="flex items-center gap-2">
												<div className={`w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 ${
													isSelected ? 'border-indigo-500 bg-indigo-500' : 'border-gray-300'
												}`}>
													{isSelected && (
														<svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 12 12">
															<path d="M10 3L5 8.5 2 5.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
														</svg>
													)}
												</div>
												<span className="text-sm font-medium text-gray-800">{option.label}</span>
												{option.recommended && (
													<span className="text-xs px-1.5 py-0.5 rounded-full bg-indigo-100 text-indigo-600 font-medium">推荐</span>
												)}
											</div>
											{option.spatial_need && (
												<p className="text-xs text-gray-500 mt-1 ml-6">{option.spatial_need}</p>
											)}
										</button>
									);
								})}
							</div>
						</div>
					)}
				</div>

				{/* Footer */}
				<div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between gap-3">
					<button
						onClick={onSkip}
						disabled={isSubmitting}
						className="text-sm text-gray-500 hover:text-gray-700 underline underline-offset-2 disabled:opacity-50"
					>
						跳过，使用推荐配置
					</button>
					<button
						onClick={handleConfirm}
						disabled={isSubmitting || selectedDeliveries.length === 0}
						className="flex items-center gap-2 px-5 py-2 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
					>
						{isSubmitting ? (
							<>
								<span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
								提交中...
							</>
						) : (
							<>
								<CheckCircle2 className="w-4 h-4" />
								确认并继续
							</>
						)}
					</button>
				</div>
			</div>
		</div>
	);
}
