'use client';

/**
 * 开发模式指示器组件
 * 在开发模式下显示一个浮动标识，提醒当前处于开发环境
 *
 * 🆕 v7.277: 新增组件
 */

import React, { useState } from 'react';

// 开发模式配置
const DEV_MODE = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
const DEV_SKIP_AUTH = process.env.NEXT_PUBLIC_DEV_SKIP_AUTH === 'true';

export default function DevModeIndicator() {
  const [isMinimized, setIsMinimized] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  // 非开发模式不显示
  if (!DEV_MODE) {
    return null;
  }

  // 最小化状态
  if (isMinimized) {
    return (
      <div
        className="fixed bottom-4 right-4 z-50 cursor-pointer transition-all duration-200 hover:scale-110"
        onClick={() => setIsMinimized(false)}
        title="点击展开开发模式信息"
      >
        <div className="w-10 h-10 rounded-full bg-orange-500 text-white flex items-center justify-center shadow-lg">
          <span className="text-lg">🔧</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`fixed bottom-4 right-4 z-50 transition-all duration-200 ${
        isHovered ? 'scale-105' : ''
      }`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg shadow-lg px-4 py-2 flex items-center gap-2">
        <span className="text-lg">🔧</span>
        <div className="flex flex-col">
          <span className="font-semibold text-sm">开发模式</span>
          {DEV_SKIP_AUTH && (
            <span className="text-xs text-orange-100">跳过登录验证</span>
          )}
        </div>
        <button
          onClick={() => setIsMinimized(true)}
          className="ml-2 p-1 hover:bg-white/20 rounded-full transition-colors"
          title="最小化"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>
      </div>

      {/* 悬停显示详细信息 */}
      {isHovered && (
        <div className="absolute bottom-full right-0 mb-2 bg-gray-900 text-white text-xs rounded-lg p-3 shadow-lg min-w-[200px]">
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-400">DEV_MODE:</span>
              <span className="text-green-400">✓ enabled</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">SKIP_AUTH:</span>
              <span className={DEV_SKIP_AUTH ? 'text-green-400' : 'text-gray-500'}>
                {DEV_SKIP_AUTH ? '✓ enabled' : '✗ disabled'}
              </span>
            </div>
            <div className="border-t border-gray-700 mt-2 pt-2">
              <span className="text-gray-400">用户:</span>
              <span className="ml-2">{DEV_SKIP_AUTH ? 'dev_user (测试)' : '实际登录'}</span>
            </div>
          </div>
          {/* 小箭头 */}
          <div className="absolute -bottom-1 right-4 w-2 h-2 bg-gray-900 transform rotate-45"></div>
        </div>
      )}
    </div>
  );
}
