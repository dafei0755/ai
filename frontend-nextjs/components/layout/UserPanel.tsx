'use client';

/**
 * 左下角用户面板
 * v7.10.2: 扁平化设计，移除分类标题
 * 包含：主题切换、会员信息、服务协议
 */

import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import {
  User,
  ChevronUp,
  Palette,
  Shield,
  Crown
} from 'lucide-react';
import { MembershipCard } from './MembershipCard';

export function UserPanel() {
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // 检测是否在 iframe 中（WordPress 嵌入模式）
  const isInIframe = typeof window !== 'undefined' && window.self !== window.top;

  // 调试日志：显示用户信息
  useEffect(() => {
    console.log('[UserPanel] 用户状态:', {
      hasUser: !!user,
      user: user,
      isInIframe,
      localStorage_token: typeof window !== 'undefined' ? localStorage.getItem('wp_jwt_token') : null,
      localStorage_user: typeof window !== 'undefined' ? localStorage.getItem('wp_jwt_user') : null,
    });
  }, [user, isInIframe]);

  // 点击外部关闭菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    if (isMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isMenuOpen]);

  // 🔒 v3.0.8: 未登录状态不显示用户面板
  // 用户只能通过 WordPress 右上角的登录/退出按钮控制
  if (!user) {
    return null;
  }

  // 获取用户显示名称和邮箱/网站
  const displayName = user.display_name || user.name || user.username;
  const subtitle = user.email || 'ucppt.com';

  // 🎨 生成首字母头像
  const getInitials = (name: string) => {
    if (!name) return 'U';
    // 如果是中文名，取第一个字
    if (/[\u4e00-\u9fa5]/.test(name)) {
      return name.charAt(0);
    }
    // 如果是英文名，取首字母
    const parts = name.split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.charAt(0).toUpperCase();
  };

  // 🎨 智能截断邮箱（保留前4位+@+域名）
  const truncateEmail = (email: string) => {
    if (!email || email.length <= 20) return email;
    const [local, domain] = email.split('@');
    if (!domain) return email;
    return `${local.substring(0, 4)}...@${domain}`;
  };

  const initials = getInitials(displayName);
  const truncatedEmail = truncateEmail(subtitle);

  return (
    <div className="relative" ref={menuRef}>
      {/* 弹出菜单 */}
      {isMenuOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-64 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg shadow-xl overflow-hidden">
          {/* 用户信息头部 */}
          <div className="px-4 py-3 border-b border-[var(--border-color)]">
            <div className="flex items-center space-x-3">
              {/* 首字母头像 - v7.105.2: 改为灰色与新建按钮一致 */}
              <div className="w-10 h-10 rounded-full ucppt-icon-avatar text-lg flex-shrink-0">
                {initials}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--foreground)] truncate" title={displayName}>
                  {displayName}
                </p>
                <p className="text-xs text-[var(--foreground-secondary)] truncate" title={subtitle}>
                  {truncatedEmail}
                </p>
              </div>
            </div>
          </div>

          {/* 主题切换 */}
          <div className="px-4 py-3 border-b border-[var(--border-color)]">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Palette className="w-4 h-4 text-gray-500" />
                <span className="text-sm text-[var(--foreground)]">主题外观</span>
              </div>
              <select
                value={theme === 'system' ? 'dark' : theme}
                onChange={(e) => setTheme(e.target.value as 'light' | 'dark')}
                className="text-xs px-2 py-1 bg-[var(--background)] border border-[var(--border-color)] rounded text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              >
                <option value="light">浅色</option>
                <option value="dark">深色</option>
              </select>
            </div>
          </div>

          {/* 会员信息 */}
          <MembershipCard />

          {/* 快捷链接 */}
          <div className="px-4 py-3 border-b border-[var(--border-color)] space-y-2">
            {/* 🆕 v7.141.3: 用户中心链接（统一入口） */}
            <a
              href="/user/dashboard"
              className="flex items-center space-x-2 text-sm text-[var(--foreground)] hover:text-blue-500 transition-colors font-semibold"
            >
              <User className="w-4 h-4 text-gray-500" />
              <span>用户中心</span>
              <svg className="w-3 h-3 ml-auto text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </a>
          </div>

          {/* 🔧 其他功能 - 已移除下载手机应用和联系我们 */}

          {/* 🚪 退出登录 - v3.0.23已移除：避免用户误操作导致SSO同步问题 */}
          {/* 用户应该在 WordPress 网站退出登录，而不是在应用内退出 */}
        </div>
      )}

      {/* 用户面板按钮 */}
      <button
        onClick={() => setIsMenuOpen(!isMenuOpen)}
        className={`
          w-full px-3 py-2.5 rounded-lg transition-all
          ${isMenuOpen
            ? 'bg-[var(--hover-bg)] ring-2 ring-blue-500/30'
            : 'hover:bg-[var(--hover-bg)]'
          }
        `}
      >
        <div className="flex items-center space-x-3">
          {/* 首字母头像 - v7.105.2: 改为灰色与新建按钮一致 */}
          <div className="w-8 h-8 rounded-full ucppt-icon-avatar flex-shrink-0">
            {initials}
          </div>

          {/* 用户信息 */}
          <div className="flex-1 min-w-0 text-left">
            <p className="text-sm font-medium text-[var(--foreground)] truncate" title={displayName}>
              {displayName}
            </p>
            <p className="text-xs text-[var(--foreground-secondary)] truncate" title={subtitle}>
              {truncatedEmail}
            </p>
          </div>

          {/* 箭头图标 */}
          <ChevronUp
            className={`w-4 h-4 text-gray-500 transition-transform flex-shrink-0 ${
              isMenuOpen ? 'rotate-180' : ''
            }`}
          />
        </div>
      </button>
    </div>
  );
}
