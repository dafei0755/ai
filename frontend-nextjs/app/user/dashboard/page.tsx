'use client';

/**
 * 用户中心主页面 - v7.141.3
 *
 * 功能模块：
 * 1. 概览 - 会员信息、配额使用情况
 * 2. 知识库管理 - 用户的私有知识库
 * 3. 账户设置 - 个人信息、偏好设置
 * 4. 帮助中心 - 服务条款、隐私政策、使用指南
 */

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import {
  User,
  Database,
  Settings,
  HelpCircle,
  Crown,
  TrendingUp,
  FileText,
  Shield,
  BookOpen
} from 'lucide-react';

type TabType = 'overview' | 'knowledge-base' | 'settings' | 'help';

interface QuotaData {
  user_id: string;
  user_tier: string;
  quota: {
    max_documents: number;
    max_storage_mb: number;
    max_file_size_mb: number;
    document_expiry_days: number;
    allow_sharing: boolean;
    allow_team_kb: boolean;
  };
  usage: {
    document_count: number;
    storage_mb: number;
  };
  remaining: {
    documents: number;
    storage_mb: number;
  };
  warnings: string[];
  quota_exceeded: boolean;
}

export default function UserDashboardPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [quotaData, setQuotaData] = useState<QuotaData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      router.push('/');
      return;
    }

    loadQuotaData();
  }, [user]);

  const loadQuotaData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('jwt_token');

      // TODO: 替换为实际用户ID和会员等级
      const userId = 'user_mock_123';
      const userTier = 'free';

      const response = await fetch(
        `/api/admin/knowledge-quota/quota/${userId}?user_tier=${userTier}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) throw new Error('加载配额数据失败');

      const data = await response.json();
      setQuotaData(data.data);
    } catch (error) {
      console.error('加载配额数据失败:', error);
      toast.error('加载配额数据失败');
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return null;
  }

  const displayName = user.display_name || user.name || user.username || '用户';

  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* 顶部导航栏 */}
      <div className="bg-[var(--card-bg)] border-b border-[var(--border-color)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <User className="w-6 h-6 text-[var(--foreground)]" />
              <h1 className="text-xl font-bold text-[var(--foreground)]">用户中心</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-[var(--foreground-secondary)]">
                欢迎回来，{displayName}
              </span>
              <button
                onClick={() => router.push('/')}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                返回首页
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 主内容区 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* 左侧导航 */}
          <div className="lg:col-span-1">
            <nav className="bg-[var(--card-bg)] rounded-lg border border-[var(--border-color)] p-4 space-y-2">
              <NavItem
                icon={<TrendingUp className="w-5 h-5" />}
                label="概览"
                active={activeTab === 'overview'}
                onClick={() => setActiveTab('overview')}
              />
              <NavItem
                icon={<Database className="w-5 h-5" />}
                label="知识库管理"
                active={activeTab === 'knowledge-base'}
                onClick={() => setActiveTab('knowledge-base')}
              />
              <NavItem
                icon={<Settings className="w-5 h-5" />}
                label="账户设置"
                active={activeTab === 'settings'}
                onClick={() => setActiveTab('settings')}
              />
              <NavItem
                icon={<HelpCircle className="w-5 h-5" />}
                label="帮助中心"
                active={activeTab === 'help'}
                onClick={() => setActiveTab('help')}
              />
            </nav>
          </div>

          {/* 右侧内容 */}
          <div className="lg:col-span-3">
            {activeTab === 'overview' && (
              <OverviewTab quotaData={quotaData} loading={loading} onUpgrade={() => {}} />
            )}
            {activeTab === 'knowledge-base' && (
              <KnowledgeBaseTab />
            )}
            {activeTab === 'settings' && (
              <SettingsTab user={user} />
            )}
            {activeTab === 'help' && (
              <HelpTab />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// 导航项组件
// ============================================================================

function NavItem({ icon, label, active, onClick }: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
        active
          ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400'
          : 'text-[var(--foreground)] hover:bg-[var(--hover-bg)]'
      }`}
    >
      {icon}
      <span className="font-medium">{label}</span>
    </button>
  );
}

// ============================================================================
// 概览标签页
// ============================================================================

function OverviewTab({ quotaData, loading, onUpgrade }: {
  quotaData: QuotaData | null;
  loading: boolean;
  onUpgrade: () => void;
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!quotaData) {
    return (
      <div className="text-center text-[var(--foreground-secondary)] py-8">
        无法加载配额数据
      </div>
    );
  }

  const tierNames: Record<string, string> = {
    free: '免费版',
    basic: '基础版',
    professional: '专业版',
    enterprise: '企业版'
  };

  const documentUsagePercent = quotaData.quota.max_documents !== -1
    ? (quotaData.usage.document_count / quotaData.quota.max_documents) * 100
    : 0;

  const storageUsagePercent = quotaData.quota.max_storage_mb !== -1
    ? (quotaData.usage.storage_mb / quotaData.quota.max_storage_mb) * 100
    : 0;

  return (
    <div className="space-y-6">
      {/* 会员信息卡片 */}
      <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center space-x-2 mb-2">
              <Crown className="w-6 h-6" />
              <h2 className="text-2xl font-bold">{tierNames[quotaData.user_tier] || quotaData.user_tier}</h2>
            </div>
            <p className="text-blue-100">
              文档有效期: {quotaData.quota.document_expiry_days === -1 ? '永久' : `${quotaData.quota.document_expiry_days} 天`}
            </p>
          </div>
          {quotaData.user_tier !== 'enterprise' && (
            <button
              onClick={onUpgrade}
              className="px-6 py-3 bg-white text-blue-600 rounded-lg font-semibold hover:bg-blue-50 transition-colors"
            >
              升级会员
            </button>
          )}
        </div>
      </div>

      {/* 配额警告 */}
      {quotaData.warnings.length > 0 && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <h3 className="text-yellow-800 dark:text-yellow-400 font-semibold mb-2">⚠️ 配额提醒</h3>
          <ul className="space-y-1">
            {quotaData.warnings.map((warning, index) => (
              <li key={index} className="text-sm text-yellow-700 dark:text-yellow-500">
                • {warning}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 配额超限 */}
      {quotaData.quota_exceeded && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <h3 className="text-red-800 dark:text-red-400 font-semibold mb-2">❌ 配额已满</h3>
          <p className="text-sm text-red-700 dark:text-red-500 mb-3">
            您的配额已用尽，无法上传新文档。请升级会员或清理旧文档。
          </p>
          <button
            onClick={onUpgrade}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            立即升级
          </button>
        </div>
      )}

      {/* 使用情况统计 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 文档数量 */}
        <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg p-6">
          <h3 className="text-sm font-medium text-[var(--foreground-secondary)] mb-4">文档数量</h3>
          <div className="flex items-end justify-between mb-2">
            <div>
              <span className="text-3xl font-bold text-[var(--foreground)]">
                {quotaData.usage.document_count}
              </span>
              <span className="text-sm text-[var(--foreground-secondary)] ml-2">
                / {quotaData.quota.max_documents === -1 ? '∞' : quotaData.quota.max_documents}
              </span>
            </div>
            <span className="text-sm text-[var(--foreground-secondary)]">
              剩余 {quotaData.remaining.documents === -1 ? '∞' : quotaData.remaining.documents}
            </span>
          </div>
          {quotaData.quota.max_documents !== -1 && (
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${
                  documentUsagePercent >= 80 ? 'bg-red-500' : 'bg-blue-500'
                }`}
                style={{ width: `${Math.min(documentUsagePercent, 100)}%` }}
              ></div>
            </div>
          )}
        </div>

        {/* 存储空间 */}
        <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg p-6">
          <h3 className="text-sm font-medium text-[var(--foreground-secondary)] mb-4">存储空间</h3>
          <div className="flex items-end justify-between mb-2">
            <div>
              <span className="text-3xl font-bold text-[var(--foreground)]">
                {quotaData.usage.storage_mb.toFixed(1)}
              </span>
              <span className="text-sm text-[var(--foreground-secondary)] ml-2">
                / {quotaData.quota.max_storage_mb === -1 ? '∞' : quotaData.quota.max_storage_mb} MB
              </span>
            </div>
            <span className="text-sm text-[var(--foreground-secondary)]">
              剩余 {quotaData.remaining.storage_mb === -1 ? '∞' : quotaData.remaining.storage_mb.toFixed(1)} MB
            </span>
          </div>
          {quotaData.quota.max_storage_mb !== -1 && (
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${
                  storageUsagePercent >= 80 ? 'bg-red-500' : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(storageUsagePercent, 100)}%` }}
              ></div>
            </div>
          )}
        </div>
      </div>

      {/* 功能权限 */}
      <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg p-6">
        <h3 className="text-lg font-semibold text-[var(--foreground)] mb-4">功能权限</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FeatureItem
            label="文档共享"
            enabled={quotaData.quota.allow_sharing}
          />
          <FeatureItem
            label="团队知识库"
            enabled={quotaData.quota.allow_team_kb}
          />
          <FeatureItem
            label="单文件大小"
            value={`${quotaData.quota.max_file_size_mb} MB`}
          />
        </div>
      </div>
    </div>
  );
}

function FeatureItem({ label, enabled, value }: {
  label: string;
  enabled?: boolean;
  value?: string;
}) {
  return (
    <div className="flex items-center justify-between p-3 bg-[var(--background)] rounded-lg">
      <span className="text-sm text-[var(--foreground)]">{label}</span>
      {enabled !== undefined ? (
        <span className={`text-sm font-semibold ${enabled ? 'text-green-600' : 'text-gray-400'}`}>
          {enabled ? '✅ 已启用' : '❌ 未启用'}
        </span>
      ) : (
        <span className="text-sm font-semibold text-[var(--foreground)]">{value}</span>
      )}
    </div>
  );
}

// ============================================================================
// 知识库管理标签页
// ============================================================================

function KnowledgeBaseTab() {
  return (
    <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-[var(--foreground)]">我的知识库</h2>
        <button
          onClick={() => window.location.href = '/admin/knowledge-base'}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          管理知识库
        </button>
      </div>
      <p className="text-[var(--foreground-secondary)]">
        在这里您可以查看和管理您的私有知识库文档。
      </p>
    </div>
  );
}

// ============================================================================
// 账户设置标签页
// ============================================================================

function SettingsTab({ user }: { user: any }) {
  return (
    <div className="space-y-6">
      <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg p-6">
        <h2 className="text-xl font-bold text-[var(--foreground)] mb-6">账户信息</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--foreground-secondary)] mb-1">
              用户名
            </label>
            <div className="text-[var(--foreground)]">
              {user.username || user.name || '未设置'}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--foreground-secondary)] mb-1">
              邮箱
            </label>
            <div className="text-[var(--foreground)]">
              {user.email || '未设置'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// 帮助中心标签页
// ============================================================================

function HelpTab() {
  return (
    <div className="space-y-4">
      <HelpCard
        icon={<Shield className="w-8 h-8" />}
        title="服务条款"
        description="了解我们的服务条款和使用规则"
        link="https://www.ucppt.com/terms"
      />
      <HelpCard
        icon={<Shield className="w-8 h-8" />}
        title="隐私政策"
        description="查看我们如何保护您的隐私"
        link="https://www.ucppt.com/privacy"
      />
      <HelpCard
        icon={<BookOpen className="w-8 h-8" />}
        title="使用指南"
        description="学习如何使用知识库功能"
        link="/help/guide"
      />
    </div>
  );
}

function HelpCard({ icon, title, description, link }: {
  icon: React.ReactNode;
  title: string;
  description: string;
  link: string;
}) {
  return (
    <a
      href={link}
      target="_blank"
      rel="noopener noreferrer"
      className="block bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg p-6 hover:border-blue-500 transition-colors"
    >
      <div className="flex items-start space-x-4">
        <div className="text-blue-600">{icon}</div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-[var(--foreground)] mb-1">{title}</h3>
          <p className="text-sm text-[var(--foreground-secondary)]">{description}</p>
        </div>
        <svg className="w-5 h-5 text-[var(--foreground-secondary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </a>
  );
}
