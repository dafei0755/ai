'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { User, ChevronUp, Palette, LogOut } from 'lucide-react';

export function UserPanel() {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    if (isMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isMenuOpen]);

  if (!user) {
    return null;
  }

  const displayName = user.display_name || user.name || user.username;
  const subtitle = user.email || '方案高参账号';

  const getInitials = (name: string) => {
    if (!name) return 'U';
    if (/[\u4e00-\u9fa5]/.test(name)) return name.charAt(0);
    const parts = name.split(' ');
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.charAt(0).toUpperCase();
  };

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
      {isMenuOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-64 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg shadow-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-[var(--border-color)]">
            <div className="flex items-center space-x-3">
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

          <div className="px-4 py-3 border-b border-[var(--border-color)] space-y-2">
            <a
              href="/user/dashboard"
              className="flex items-center space-x-2 text-sm text-[var(--foreground)] hover:text-blue-500 transition-colors font-semibold"
            >
              <User className="w-4 h-4 text-gray-500" />
              <span>用户中心</span>
            </a>
            <button
              onClick={logout}
              className="flex w-full items-center space-x-2 text-sm text-[var(--foreground)] hover:text-red-500 transition-colors"
            >
              <LogOut className="w-4 h-4 text-gray-500" />
              <span>退出登录</span>
            </button>
          </div>
        </div>
      )}

      <button
        onClick={() => setIsMenuOpen(!isMenuOpen)}
        className={`w-full px-3 py-2.5 rounded-lg transition-all ${
          isMenuOpen ? 'bg-[var(--hover-bg)] ring-2 ring-blue-500/30' : 'hover:bg-[var(--hover-bg)]'
        }`}
      >
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-full ucppt-icon-avatar flex-shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0 text-left">
            <p className="text-sm font-medium text-[var(--foreground)] truncate" title={displayName}>
              {displayName}
            </p>
            <p className="text-xs text-[var(--foreground-secondary)] truncate" title={subtitle}>
              {truncatedEmail}
            </p>
          </div>
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
