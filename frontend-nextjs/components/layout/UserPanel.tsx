'use client';

/**
 * 左下角用户面板
 * v7.10.1: 仿照 DeepSeek 界面设计
 * 包含：通用设置（主题）、账号管理（会员信息）、服务协议
 */

import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import {
  User,
  LogOut,
  ChevronUp,
  Palette,
  Shield,
  Crown
} from 'lucide-react';
import { MembershipCard } from './MembershipCard';

export function UserPanel() {
  const { user, logout } = useAuth();
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

  // 未登录状态显示登录提示
  if (!user) {
    return (
      <div className="px-3 py-2.5 bg-[var(--card-bg)] rounded-lg border border-[var(--border-color)]">
        <div className="flex items-center space-x-3 mb-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
            <User className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-[var(--foreground)]">未登录</p>
            <p className="text-xs text-[var(--foreground-secondary)]">请先登录</p>
          </div>
        </div>
        <button
          onClick={() => {
            // 跳转到 WordPress 登录页面
            const wordpressEmbedUrl = process.env.NEXT_PUBLIC_WORDPRESS_EMBED_URL || 'https://www.ucppt.com/nextjs';
            window.location.href = wordpressEmbedUrl;
          }}
          className="w-full px-3 py-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white text-sm font-medium rounded-lg transition-all"
        >
          前往登录
        </button>
      </div>
    );
  }

  // 获取用户显示名称和邮箱/网站
  const displayName = user.display_name || user.name || user.username;
  const subtitle = user.email || 'ucppt.com';

  // 获取头像（使用 Gravatar 或默认头像）
  const avatarUrl = user.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(displayName)}&background=4F46E5&color=fff&size=128`;

  // 头像加载失败时的回退处理
  const handleAvatarError = (e: React.SyntheticEvent<HTMLImageElement>) => {
    console.log('[UserPanel] 头像加载失败，使用默认头像');
    e.currentTarget.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(displayName)}&background=4F46E5&color=fff&size=128`;
  };

  return (
    <div className="relative" ref={menuRef}>
      {/* 弹出菜单 */}
      {isMenuOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-64 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg shadow-xl overflow-hidden">
          {/* 用户信息头部 */}
          <div className="px-4 py-3 border-b border-[var(--border-color)]">
            <div className="flex items-center space-x-3">
              <img
                src={avatarUrl}
                alt={displayName}
                className="w-10 h-10 rounded-full"
                onError={handleAvatarError}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--foreground)] truncate">
                  {displayName}
                </p>
                <p className="text-xs text-[var(--foreground-secondary)] truncate">
                  {subtitle}
                </p>
              </div>
            </div>
          </div>

          {/* 🎨 通用设置 - 主题切换 */}
          <div className="px-3 py-2 border-b border-[var(--border-color)]">
            <div className="flex items-center space-x-2 px-1 py-1.5">
              <Palette className="w-4 h-4 text-[var(--foreground-secondary)]" />
              <span className="text-xs font-medium text-[var(--foreground-secondary)]">通用设置</span>
            </div>
            <div className="px-1 py-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--foreground)]">主题外观</span>
                <select
                  value={theme}
                  onChange={(e) => setTheme(e.target.value as 'light' | 'dark' | 'system')}
                  className="text-xs px-2 py-1 bg-[var(--background)] border border-[var(--border-color)] rounded text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                >
                  <option value="light">浅色</option>
                  <option value="dark">深色</option>
                  <option value="system">跟随系统</option>
                </select>
              </div>
            </div>
          </div>

          {/* 👤 账号管理 - 会员信息 */}
          <div className="border-b border-[var(--border-color)]">
            <div className="px-3 py-2">
              <div className="flex items-center space-x-2 px-1 py-1.5">
                <Crown className="w-4 h-4 text-[var(--foreground-secondary)]" />
                <span className="text-xs font-medium text-[var(--foreground-secondary)]">账号管理</span>
              </div>
            </div>
            <MembershipCard />
          </div>

          {/* 📋 服务协议 */}
          <div className="px-3 py-2 border-b border-[var(--border-color)]">
            <div className="flex items-center space-x-2 px-1 py-1.5 mb-2">
              <Shield className="w-4 h-4 text-[var(--foreground-secondary)]" />
              <span className="text-xs font-medium text-[var(--foreground-secondary)]">服务协议</span>
            </div>
            <div className="space-y-1">
              <a
                href="https://www.ucppt.com/terms"
                target="_blank"
                rel="noopener noreferrer"
                className="block px-1 py-1.5 text-xs text-[var(--foreground)] hover:text-blue-500 transition-colors"
              >
                服务条款
              </a>
              <a
                href="https://www.ucppt.com/privacy"
                target="_blank"
                rel="noopener noreferrer"
                className="block px-1 py-1.5 text-xs text-[var(--foreground)] hover:text-blue-500 transition-colors"
              >
                隐私政策
              </a>
            </div>
          </div>

          {/* 🔧 其他功能 - 已移除下载手机应用和联系我们 */}

          {/* 🚪 退出登录（iframe 模式下隐藏，使用 WordPress 的退出按钮） */}
          {!isInIframe && (
            <>
              <div className="border-t border-[var(--border-color)]"></div>
              <div className="py-1">
                <button
                  onClick={() => {
                    setIsMenuOpen(false);
                    if (confirm('确定要退出登录吗？')) {
                      logout();
                    }
                  }}
                  className="w-full px-4 py-2.5 text-left text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors flex items-center space-x-3"
                >
                  <LogOut className="w-4 h-4" />
                  <span>退出登录</span>
                </button>
              </div>
            </>
          )}
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
          {/* 头像 */}
          <img
            src={avatarUrl}
            alt={displayName}
            className="w-8 h-8 rounded-full flex-shrink-0"
            onError={handleAvatarError}
          />

          {/* 用户信息 */}
          <div className="flex-1 min-w-0 text-left">
            <p className="text-sm font-medium text-[var(--foreground)] truncate">
              {displayName}
            </p>
            <p className="text-xs text-[var(--foreground-secondary)] truncate">
              {subtitle}
            </p>
          </div>

          {/* 箭头图标 */}
          <ChevronUp
            className={`w-4 h-4 text-[var(--foreground-secondary)] transition-transform ${
              isMenuOpen ? 'rotate-180' : ''
            }`}
          />
        </div>
      </button>
    </div>
  );
}
