/**
 * 问卷加载骨架屏组件
 * 用于问卷确认过程中的过渡加载动画
 * 支持任务列表和雷达图两种骨架屏类型
 */

import React from 'react';

interface QuestionnaireSkeletonLoaderProps {
	type: 'tasks' | 'radar' | 'both';
	message?: string;
}

const QuestionnaireSkeletonLoader: React.FC<QuestionnaireSkeletonLoaderProps> = ({
	type,
	message = 'AI 正在智能分析...'
}) => {
	return (
		<div className="w-full space-y-4 animate-fade-in">
			{/* 加载提示文案 */}
			<div className="flex items-center justify-center py-3">
				<div className="flex items-center space-x-2">
					<svg
						className="animate-spin h-5 w-5 text-blue-500"
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
					>
						<circle
							className="opacity-25"
							cx="12"
							cy="12"
							r="10"
							stroke="currentColor"
							strokeWidth="4"
						/>
						<path
							className="opacity-75"
							fill="currentColor"
							d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
						/>
					</svg>
					<span className="text-gray-600 text-sm font-medium">{message}</span>
				</div>
			</div>

			{/* 任务列表骨架屏 */}
			{(type === 'tasks' || type === 'both') && (
				<div className="space-y-3">
					<div className="h-4 bg-gray-200 rounded animate-pulse w-1/4" />
					{[1, 2, 3, 4].map((index) => (
						<div
							key={index}
							className="border border-gray-200 rounded-lg p-4 space-y-3 animate-pulse"
							style={{ animationDelay: `${index * 100}ms` }}
						>
							<div className="flex items-center space-x-3">
								<div className="h-5 w-5 bg-gray-200 rounded" />
								<div className="h-4 bg-gray-200 rounded flex-1" />
							</div>
							<div className="h-3 bg-gray-100 rounded w-3/4" />
							<div className="h-3 bg-gray-100 rounded w-1/2" />
						</div>
					))}
				</div>
			)}

			{/* 雷达图骨架屏 */}
			{(type === 'radar' || type === 'both') && (
				<div className="space-y-3">
					<div className="h-4 bg-gray-200 rounded animate-pulse w-1/3" />
					<div className="flex justify-center items-center py-8">
						<div className="relative w-64 h-64">
							{/* 中心圆形 */}
							<div className="absolute inset-0 flex items-center justify-center">
								<div className="w-48 h-48 bg-gray-200 rounded-full animate-pulse" />
							</div>
							{/* 周围维度标签 */}
							{[0, 1, 2, 3, 4, 5].map((index) => {
								const angle = (index * 60 - 90) * (Math.PI / 180);
								const x = 50 + 45 * Math.cos(angle);
								const y = 50 + 45 * Math.sin(angle);
								return (
									<div
										key={index}
										className="absolute w-16 h-4 bg-gray-200 rounded animate-pulse"
										style={{
											left: `${x}%`,
											top: `${y}%`,
											transform: 'translate(-50%, -50%)',
											animationDelay: `${index * 150}ms`
										}}
									/>
								);
							})}
						</div>
					</div>
					{/* 维度列表 */}
					<div className="space-y-2">
						{[1, 2, 3].map((index) => (
							<div
								key={index}
								className="flex items-center space-x-3 animate-pulse"
								style={{ animationDelay: `${index * 100}ms` }}
							>
								<div className="h-3 w-3 bg-gray-200 rounded-full" />
								<div className="h-3 bg-gray-200 rounded flex-1" />
							</div>
						))}
					</div>
				</div>
			)}
		</div>
	);
};

export default QuestionnaireSkeletonLoader;
