// components/SettingsModal.tsx
// 设置模态框组件

'use client';

import { X, Sun, Moon, Monitor } from 'lucide-react';
import { useTheme, type Theme } from '@/hooks/useTheme';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const { theme, changeTheme } = useTheme();

  if (!isOpen) return null;

  const themes: { value: Theme; label: string; icon: React.ReactNode }[] = [
    { value: 'light', label: '浅色', icon: <Sun className="w-5 h-5" /> },
    { value: 'dark', label: '深色', icon: <Moon className="w-5 h-5" /> },
    { value: 'system', label: '跟随系统', icon: <Monitor className="w-5 h-5" /> },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-[var(--card-bg)] rounded-2xl border border-[var(--border-color)] shadow-2xl w-full max-w-2xl">
        {/* Header */}
        <div className="p-6 border-b border-[var(--border-color)] flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[var(--foreground)]">系统设置</h2>
          <button
            onClick={onClose}
            className="p-2 text-[var(--foreground-secondary)] hover:text-[var(--foreground)] hover:bg-[var(--sidebar-bg)] rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* 主题设置 */}
          <div>
            <label className="text-sm font-medium text-[var(--foreground-secondary)] mb-3 block">主题</label>
            <div className="grid grid-cols-3 gap-3">
              {themes.map((t) => (
                <button
                  key={t.value}
                  onClick={() => changeTheme(t.value)}
                  className={`
                    flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all
                    ${theme === t.value
                      ? 'bg-[var(--primary)]/10 border-[var(--primary)] text-[var(--foreground)]'
                      : 'bg-[var(--sidebar-bg)] border-[var(--border-color)] text-[var(--foreground-secondary)] hover:border-[var(--foreground-secondary)]'
                    }
                  `}
                >
                  {t.icon}
                  <span className="text-sm font-medium">{t.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-[var(--border-color)] flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2.5 bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white rounded-lg transition-colors font-medium"
          >
            完成
          </button>
        </div>
      </div>
    </div>
  );
}
