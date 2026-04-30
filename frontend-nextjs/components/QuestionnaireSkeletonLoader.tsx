/**
 * 问卷加载骨架屏组件
 * 用于问卷确认过程中的过渡加载动画
 * 支持任务列表和雷达图两种骨架屏类型
 */

import React from 'react';

interface QuestionnaireSkeletonLoaderProps {
	type: 'tasks' | 'radar' | 'both' | 'intent' | 'questions' | 'insights';
	message?: string;
}

const QuestionnaireSkeletonLoader: React.FC<QuestionnaireSkeletonLoaderProps> = ({
	type,
	message = 'AI 正在智能分析...'
}) => {
	return (
		<div className="w-full space-y-4">
			{/* 统一使用 shimmer 进度条，所有类型均不显示 spinner */}
			<div className="space-y-2 px-1">
				<div className="flex items-center justify-between">
					<span className="text-xs text-gray-400 font-medium">{message}</span>
					<span className="text-xs text-blue-400 animate-pulse">••• </span>
				</div>
				{/* 细进度条（shimmer 动画） */}
				<div className="w-full h-1 bg-gray-100 rounded-full overflow-hidden">
					<div
						className="h-full bg-gradient-to-r from-blue-300 via-blue-500 to-blue-300 rounded-full"
						style={{
							width: '40%',
							animation: 'skeletonSlide 1.6s ease-in-out infinite',
						}}
					/>
				</div>
				<style>{`
					@keyframes skeletonSlide {
						0%   { transform: translateX(-100%); }
						100% { transform: translateX(300%); }
					}
				`}</style>
			</div>
		{/* 意图确认骨架屏 */}
		{type === 'intent' && (
			<div className="space-y-4">
				{/* 标题块 */}
				<div className="bg-gray-100 rounded-xl p-4 space-y-2">
					<div className="h-4 bg-gray-200 rounded animate-pulse w-1/3" />
					<div className="h-3 bg-gray-100 rounded animate-pulse w-2/3" />
				</div>
				{/* 交付类型标签 */}
				<div className="space-y-2">
					<div className="h-3 bg-gray-200 rounded animate-pulse w-1/4 mb-3" />
					{[1, 2, 3, 4, 5].map((i) => (
						<div
							key={i}
							className="bg-white border border-gray-200 rounded-xl px-4 py-3 space-y-2 animate-pulse"
							style={{ animationDelay: `${i * 80}ms` }}
						>
							<div className="flex items-center gap-2">
								<div className="w-4 h-4 rounded bg-gray-200 flex-shrink-0" />
								<div className="h-4 bg-gray-200 rounded w-2/5" />
								{i <= 2 && <div className="h-4 w-10 bg-blue-100 rounded-full" />}
							</div>
							<div className="h-3 bg-gray-100 rounded w-3/4 ml-6" />
						</div>
					))}
				</div>
				{/* 体验视角标签 */}
				<div className="space-y-2 pt-2">
					<div className="h-3 bg-gray-200 rounded animate-pulse w-1/4 mb-3" />
					{[1, 2].map((i) => (
						<div
							key={i}
							className="bg-white border border-gray-200 rounded-xl px-4 py-3 space-y-2 animate-pulse"
							style={{ animationDelay: `${(i + 5) * 80}ms` }}
						>
							<div className="flex items-center gap-2">
								<div className="w-4 h-4 rounded bg-gray-200 flex-shrink-0" />
								<div className="h-4 bg-gray-200 rounded w-1/3" />
							</div>
							<div className="h-3 bg-gray-100 rounded w-1/2 ml-6" />
						</div>
					))}
				</div>
			</div>
		)}
			{/* 任务列表骨架屏 */}
			{(type === 'tasks' || type === 'both') && (
				<div className="space-y-3">
					{/* 标题行骨架 */}
					<div className="flex items-center gap-2">
						<div className="h-4 bg-gray-200 rounded animate-pulse w-24" />
						<div className="h-4 bg-gray-100 rounded animate-pulse w-8" />
					</div>
					{[1, 2, 3, 4].map((index) => (
						<div
							key={index}
							className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3"
							style={{ animationDelay: `${index * 80}ms` }}
						>
							{/* 序号 + 标题行 */}
							<div className="flex items-start gap-3">
								<div
									className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-200 animate-pulse"
									style={{ animationDelay: `${index * 80}ms` }}
								/>
								<div className="flex-1 space-y-2">
									<div
										className="h-4 bg-gray-200 rounded-md animate-pulse"
										style={{
											width: `${70 + (index % 3) * 10}%`,
											animationDelay: `${index * 80}ms`,
										}}
									/>
									{/* 描述行 */}
									<div
										className="h-3 bg-gray-100 rounded-md animate-pulse"
										style={{
											width: `${50 + (index % 4) * 8}%`,
											animationDelay: `${index * 80 + 40}ms`,
										}}
									/>
									<div
										className="h-3 bg-gray-100 rounded-md animate-pulse w-2/5"
										style={{ animationDelay: `${index * 80 + 80}ms` }}
									/>
								</div>
								{/* 优先级标签骨架 */}
								<div
									className="flex-shrink-0 h-5 w-12 rounded-full bg-gray-100 animate-pulse"
									style={{ animationDelay: `${index * 80 + 120}ms` }}
								/>
							</div>
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
		{/* 问卷题目骨架屏 */}
		{type === 'questions' && (
			<div className="space-y-4">
				{/* 必填/选填说明行骨架 */}
				<div className="flex items-center gap-3">
					<div className="h-3 bg-blue-100 rounded-full animate-pulse w-16" />
					<div className="h-3 bg-gray-100 rounded-full animate-pulse w-12" />
				</div>
				{/* 题目卡片：交替呈现单选题 / 开放题骨架 */}
				{[1, 2, 3].map((i) => {
					const isOpenEnded = i === 2; // 第 2 题模拟开放题
					return (
						<div
							key={i}
							className={`rounded-xl p-5 space-y-3 ${
								i === 1 ? 'bg-white shadow-sm' : 'bg-[#f5f5f7]'
							}`}
							style={{ animationDelay: `${i * 80}ms` }}
						>
							{/* 题目头部：序号徽章 + 标题 */}
							<div className="flex items-start gap-3">
								<div
									className={`flex-shrink-0 w-7 h-7 rounded-full animate-pulse ${
										i === 1 ? 'bg-blue-200' : 'bg-gray-200'
									}`}
									style={{ animationDelay: `${i * 80}ms` }}
								/>
								<div className="flex-1 space-y-2 pt-0.5">
									{/* 问题标题行 */}
									<div
										className="h-4 bg-gray-200 rounded-md animate-pulse"
										style={{ width: `${68 + i * 6}%`, animationDelay: `${i * 80}ms` }}
									/>
									{/* 上下文说明行（较浅） */}
									<div
										className="h-3 bg-gray-100 rounded-md animate-pulse"
										style={{ width: `${45 + i * 8}%`, animationDelay: `${i * 80 + 40}ms` }}
									/>
								</div>
							</div>
							{/* 选项区域 */}
							{isOpenEnded ? (
								// 开放题：textarea 骨架
								<div
									className="ml-10 h-16 bg-gray-100 rounded-lg animate-pulse"
									style={{ animationDelay: `${i * 80 + 80}ms` }}
								/>
							) : (
								// 单选/多选题：选项行骨架
								<div className="space-y-2 ml-10">
									{[1, 2, 3].map((j) => (
										<div
											key={j}
											className="flex items-center gap-2 p-2"
											style={{ animationDelay: `${i * 80 + j * 40}ms` }}
										>
											<div className="w-4 h-4 rounded-full bg-gray-200 animate-pulse flex-shrink-0" />
											<div
												className="h-3 bg-gray-100 rounded animate-pulse"
												style={{ width: `${42 + j * 14}%`, animationDelay: `${i * 80 + j * 40}ms` }}
											/>
										</div>
									))}
								</div>
							)}
						</div>
					);
				})}
			</div>
		)}

		{/* 需求洞察骨架屏 */}
		{type === 'insights' && (
			<div className="space-y-4">
				{/* 标题块 */}
				<div className="bg-white rounded-xl p-5 space-y-3 animate-pulse">
					<div className="h-4 bg-gray-200 rounded w-1/3" />
					<div className="space-y-2">
						<div className="h-3 bg-gray-100 rounded w-full" />
						<div className="h-3 bg-gray-100 rounded w-5/6" />
						<div className="h-3 bg-gray-100 rounded w-4/6" />
					</div>
				</div>
				{/* 洞察条目 */}
				{[1, 2, 3].map((i) => (
					<div
						key={i}
						className="bg-white rounded-xl p-4 flex items-start gap-3 animate-pulse"
						style={{ animationDelay: `${i * 120}ms` }}
					>
						<div className="w-8 h-8 bg-gray-200 rounded-lg flex-shrink-0" />
						<div className="flex-1 space-y-2">
							<div className="h-4 bg-gray-200 rounded w-2/5" />
							<div className="h-3 bg-gray-100 rounded w-full" />
							<div className="h-3 bg-gray-100 rounded w-3/4" />
						</div>
					</div>
				))}
			</div>
		)}
		</div>
	);
};

export default QuestionnaireSkeletonLoader;
