'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';

interface FilterConfig {
  blacklist: {
    domains: string[];
    patterns: string[];
    regex: string[];
    notes: Record<string, string>;
  };
  whitelist: {
    domains: string[];
    patterns: string[];
    regex: string[];
    boost_score: number;
    notes: Record<string, string>;
  };
  scope: {
    tools: string[];
    enabled: boolean;
    priority: string;
  };
  metadata: {
    version: string;
    last_updated: string;
    updated_by: string;
  };
}

interface Statistics {
  blacklist: {
    domains: number;
    patterns: number;
    regex: number;
    total: number;
  };
  whitelist: {
    domains: number;
    patterns: number;
    regex: number;
    total: number;
  };
  enabled: boolean;
  last_updated: string;
}

// 审核队列项目接口
interface ReviewQueueItem {
  domain: string;
  total_appearances: number;
  avg_quality_score: number;
  avg_relevance_score: number;
  low_score_count: number;
  very_low_score_count: number;
  content_short_count: number;
  review_reason: string;
  review_added_time: string;
  first_seen: string;
  last_seen: string;
  score_history: number[];
}

export default function SearchFiltersPage() {
  const [config, setConfig] = useState<FilterConfig | null>(null);
  const [stats, setStats] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'blacklist' | 'whitelist' | 'review'>('blacklist');
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [newDomain, setNewDomain] = useState('');
  const [newMatchType, setNewMatchType] = useState<'domains' | 'patterns' | 'regex'>('domains');
  const [newNote, setNewNote] = useState('');
  const [testUrl, setTestUrl] = useState('');
  const [testResult, setTestResult] = useState<any>(null);
  // 审核队列状态
  const [reviewQueue, setReviewQueue] = useState<ReviewQueueItem[]>([]);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewCount, setReviewCount] = useState(0);

  useEffect(() => {
    loadConfig();
    loadReviewQueue();
  }, []);

  const loadReviewQueue = async () => {
    try {
      setReviewLoading(true);
      const token = localStorage.getItem('wp_jwt_token');

      const response = await fetch('/api/admin/domain-quality/review-queue', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('加载审核队列失败');

      const data = await response.json();
      setReviewQueue(data.data?.queue || []);
      setReviewCount(data.data?.count || 0);
    } catch (error) {
      console.error('加载审核队列失败:', error);
    } finally {
      setReviewLoading(false);
    }
  };

  const handleReviewAction = async (domain: string, action: 'approve' | 'block' | 'dismiss', addToWhitelist: boolean = false) => {
    try {
      const token = localStorage.getItem('wp_jwt_token');

      const response = await fetch(`/api/admin/domain-quality/${action}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          domain,
          add_to_whitelist: addToWhitelist,
          admin_notes: `通过管理界面${action === 'approve' ? '批准' : action === 'block' ? '屏蔽' : '移除'}`
        })
      });

      if (!response.ok) throw new Error('操作失败');

      const data = await response.json();
      toast.success(data.data?.message || '操作成功');

      // 重新加载
      await loadReviewQueue();
      await loadConfig();
    } catch (error) {
      console.error('操作失败:', error);
      toast.error('操作失败');
    }
  };

  const loadConfig = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('wp_jwt_token');

      const response = await fetch('/api/admin/search-filters', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('加载配置失败');

      const data = await response.json();
      setConfig(data.data);
      setStats(data.data.statistics);
    } catch (error) {
      console.error('加载配置失败:', error);
      toast.error('加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  const addToList = async (listType: 'blacklist' | 'whitelist') => {
    if (!newDomain.trim()) {
      toast.error('请输入域名');
      return;
    }

    try {
      const token = localStorage.getItem('wp_jwt_token');

      const response = await fetch(`/api/admin/search-filters/${listType}?domain=${encodeURIComponent(newDomain)}&match_type=${newMatchType}&note=${encodeURIComponent(newNote || '')}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('添加失败');

      const data = await response.json();
      toast.success(data.message);

      // 重新加载配置
      await loadConfig();

      // 清空表单
      setNewDomain('');
      setNewNote('');
      setAddModalOpen(false);
    } catch (error) {
      console.error('添加失败:', error);
      toast.error('添加失败');
    }
  };

  const removeFromList = async (listType: 'blacklist' | 'whitelist', domain: string, matchType: string) => {
    if (!confirm(`确定要从${listType === 'blacklist' ? '黑名单' : '白名单'}移除 "${domain}" 吗？`)) {
      return;
    }

    try {
      const token = localStorage.getItem('wp_jwt_token');

      const response = await fetch(`/api/admin/search-filters/${listType}?domain=${encodeURIComponent(domain)}&match_type=${matchType}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('移除失败');

      const data = await response.json();
      toast.success(data.message);

      // 重新加载配置
      await loadConfig();
    } catch (error) {
      console.error('移除失败:', error);
      toast.error('移除失败');
    }
  };

  const testFilter = async () => {
    if (!testUrl.trim()) {
      toast.error('请输入测试 URL');
      return;
    }

    try {
      const token = localStorage.getItem('wp_jwt_token');

      const response = await fetch(`/api/admin/search-filters/test?url=${encodeURIComponent(testUrl)}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('测试失败');

      const data = await response.json();
      setTestResult(data.data);
    } catch (error) {
      console.error('测试失败:', error);
      toast.error('测试失败');
    }
  };

  const reloadConfig = async () => {
    try {
      const token = localStorage.getItem('wp_jwt_token');

      const response = await fetch('/api/admin/search-filters/reload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('重载失败');

      toast.success('配置已重载');
      await loadConfig();
    } catch (error) {
      console.error('重载失败:', error);
      toast.error('重载失败');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-red-800 mb-2">⚠️ 配置加载失败</h2>
          <p className="text-red-700 mb-4">无法加载搜索过滤器配置，请检查：</p>
          <ul className="list-disc list-inside text-red-700 mb-4 space-y-1">
            <li>后端服务是否正常运行</li>
            <li>配置文件 config/search_filters.yaml 是否存在</li>
            <li>是否有管理员权限</li>
          </ul>
          <button
            onClick={loadConfig}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            重新加载
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">搜索过滤器管理</h1>
        <p className="text-gray-600 mt-2">管理搜索结果的黑名单和白名单</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">黑名单总数</div>
          <div className="text-2xl font-bold text-red-600">{stats?.blacklist?.total || 0}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">白名单总数</div>
          <div className="text-2xl font-bold text-green-600">{stats?.whitelist?.total || 0}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">过滤器状态</div>
          <div className={`text-2xl font-bold ${config?.scope?.enabled ? 'text-green-600' : 'text-gray-400'}`}>
            {config?.scope?.enabled ? '已启用' : '已禁用'}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">上次更新</div>
          <div className="text-sm font-medium text-gray-900">
            {stats?.last_updated ? new Date(stats.last_updated).toLocaleString('zh-CN') : '-'}
          </div>
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-3 mb-6">
        <button
          onClick={() => setAddModalOpen(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          ➕ 添加规则
        </button>
        <button
          onClick={reloadConfig}
          className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
        >
          🔄 重载配置
        </button>
      </div>

      {/* 标签页切换 */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => setActiveTab('blacklist')}
              className={`py-4 px-6 border-b-2 font-medium text-sm ${
                activeTab === 'blacklist'
                  ? 'border-red-500 text-red-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              🚫 黑名单 ({stats?.blacklist.total || 0})
            </button>
            <button
              onClick={() => setActiveTab('whitelist')}
              className={`py-4 px-6 border-b-2 font-medium text-sm ${
                activeTab === 'whitelist'
                  ? 'border-green-500 text-green-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              ⭐ 白名单 ({stats?.whitelist.total || 0})
            </button>
            <button
              onClick={() => setActiveTab('review')}
              className={`py-4 px-6 border-b-2 font-medium text-sm ${
                activeTab === 'review'
                  ? 'border-orange-500 text-orange-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              ⏳ 待审核 {reviewCount > 0 && (
                <span className="ml-1 px-2 py-0.5 bg-orange-100 text-orange-600 rounded-full text-xs">
                  {reviewCount}
                </span>
              )}
            </button>
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'blacklist' ? (
            <BlacklistContent
              config={config}
              onRemove={(domain, matchType) => removeFromList('blacklist', domain, matchType)}
            />
          ) : activeTab === 'whitelist' ? (
            <WhitelistContent
              config={config}
              onRemove={(domain, matchType) => removeFromList('whitelist', domain, matchType)}
            />
          ) : (
            <ReviewQueueContent
              queue={reviewQueue}
              loading={reviewLoading}
              onAction={handleReviewAction}
              onRefresh={loadReviewQueue}
            />
          )}
        </div>
      </div>

      {/* 测试工具 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-bold mb-4">🧪 测试过滤器</h2>
        <div className="flex gap-3 mb-4">
          <input
            type="text"
            value={testUrl}
            onChange={(e) => setTestUrl(e.target.value)}
            placeholder="输入要测试的 URL (如: https://example.com)"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg"
          />
          <button
            onClick={testFilter}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            测试
          </button>
        </div>

        {testResult && (
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-sm text-gray-600">黑名单状态：</span>
                <span className={`ml-2 font-medium ${testResult.is_blacklisted ? 'text-red-600' : 'text-green-600'}`}>
                  {testResult.is_blacklisted ? '✗ 已屏蔽' : '✓ 未屏蔽'}
                </span>
              </div>
              <div>
                <span className="text-sm text-gray-600">白名单状态：</span>
                <span className={`ml-2 font-medium ${testResult.is_whitelisted ? 'text-green-600' : 'text-gray-600'}`}>
                  {testResult.is_whitelisted ? '✓ 已加入' : '✗ 未加入'}
                </span>
              </div>
              <div>
                <span className="text-sm text-gray-600">是否会被过滤：</span>
                <span className={`ml-2 font-medium ${testResult.will_be_blocked ? 'text-red-600' : 'text-green-600'}`}>
                  {testResult.will_be_blocked ? '是' : '否'}
                </span>
              </div>
              <div>
                <span className="text-sm text-gray-600">白名单加分：</span>
                <span className="ml-2 font-medium text-gray-900">
                  +{testResult.boost_score}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 添加规则模态框 */}
      {addModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-lg font-bold mb-4">添加到 {activeTab === 'blacklist' ? '黑名单' : '白名单'}</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  域名或模式
                </label>
                <input
                  type="text"
                  value={newDomain}
                  onChange={(e) => setNewDomain(e.target.value)}
                  placeholder="example.com 或 *.spam.com"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  匹配类型
                </label>
                <select
                  value={newMatchType}
                  onChange={(e) => setNewMatchType(e.target.value as any)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="domains">完整域名</option>
                  <option value="patterns">通配符（支持 *）</option>
                  <option value="regex">正则表达式</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  备注（可选）
                </label>
                <textarea
                  value={newNote}
                  onChange={(e) => setNewNote(e.target.value)}
                  placeholder="添加原因..."
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => activeTab !== 'review' && addToList(activeTab)}
                disabled={activeTab === 'review'}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                确认添加
              </button>
              <button
                onClick={() => {
                  setAddModalOpen(false);
                  setNewDomain('');
                  setNewNote('');
                }}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function BlacklistContent({ config, onRemove }: { config: FilterConfig; onRemove: (domain: string, matchType: string) => void }) {
  return (
    <div className="space-y-6">
      <RuleSection
        title="完整域名匹配"
        items={config?.blacklist?.domains || []}
        notes={config?.blacklist?.notes || {}}
        matchType="domains"
        onRemove={onRemove}
        color="red"
      />
      <RuleSection
        title="通配符匹配"
        items={config?.blacklist?.patterns || []}
        notes={config?.blacklist?.notes || {}}
        matchType="patterns"
        onRemove={onRemove}
        color="red"
      />
      <RuleSection
        title="正则表达式"
        items={config?.blacklist?.regex || []}
        notes={config?.blacklist?.notes || {}}
        matchType="regex"
        onRemove={onRemove}
        color="red"
      />
    </div>
  );
}

function WhitelistContent({ config, onRemove }: { config: FilterConfig; onRemove: (domain: string, matchType: string) => void }) {
  return (
    <div className="space-y-6">
      <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
        <p className="text-sm text-green-800">
          ⭐ 白名单提升分数：<strong>+{config?.whitelist?.boost_score || 0.3}</strong>
        </p>
      </div>

      <RuleSection
        title="完整域名匹配"
        items={config?.whitelist?.domains || []}
        notes={config?.whitelist?.notes || {}}
        matchType="domains"
        onRemove={onRemove}
        color="green"
      />
      <RuleSection
        title="通配符匹配"
        items={config?.whitelist?.patterns || []}
        notes={config?.whitelist?.notes || {}}
        matchType="patterns"
        onRemove={onRemove}
        color="green"
      />
      <RuleSection
        title="正则表达式"
        items={config?.whitelist?.regex || []}
        notes={config?.whitelist?.notes || {}}
        matchType="regex"
        onRemove={onRemove}
        color="green"
      />
    </div>
  );
}

function RuleSection({
  title,
  items,
  notes,
  matchType,
  onRemove,
  color
}: {
  title: string;
  items: string[];
  notes: Record<string, string>;
  matchType: string;
  onRemove: (domain: string, matchType: string) => void;
  color: 'red' | 'green';
}) {
  if (!items || items.length === 0) {
    return (
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2">{title}</h3>
        <p className="text-sm text-gray-500 italic">暂无规则</p>
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-sm font-medium text-gray-700 mb-2">{title}</h3>
      <div className="space-y-2">
        {items.map((item, index) => (
          <div
            key={index}
            className={`flex items-center justify-between p-3 border rounded-lg ${
              color === 'red' ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'
            }`}
          >
            <div className="flex-1">
              <code className="text-sm font-mono">{item}</code>
              {notes[item] && (
                <p className="text-xs text-gray-600 mt-1">{notes[item]}</p>
              )}
            </div>
            <button
              onClick={() => onRemove(item, matchType)}
              className={`ml-4 px-3 py-1 text-sm rounded ${
                color === 'red'
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'bg-green-600 hover:bg-green-700 text-white'
              }`}
            >
              移除
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// 审核队列组件
function ReviewQueueContent({
  queue,
  loading,
  onAction,
  onRefresh
}: {
  queue: ReviewQueueItem[];
  loading: boolean;
  onAction: (domain: string, action: 'approve' | 'block' | 'dismiss', addToWhitelist?: boolean) => void;
  onRefresh: () => void;
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">加载审核队列...</span>
      </div>
    );
  }

  if (queue.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-6xl mb-4">✅</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">审核队列为空</h3>
        <p className="text-gray-600 mb-4">系统会自动识别低质量域名并加入此队列</p>
        <button
          onClick={onRefresh}
          className="px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg"
        >
          🔄 刷新
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-600">
          共 {queue.length} 个域名待审核，按质量分从低到高排序
        </p>
        <button
          onClick={onRefresh}
          className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded"
        >
          🔄 刷新
        </button>
      </div>

      {queue.map((item, index) => (
        <div key={item.domain} className="bg-orange-50 border border-orange-200 rounded-lg p-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <code className="text-sm font-mono font-bold">{item.domain}</code>
                <span className={`px-2 py-0.5 rounded text-xs ${
                  item.avg_quality_score < 30 
                    ? 'bg-red-100 text-red-600' 
                    : item.avg_quality_score < 50 
                    ? 'bg-orange-100 text-orange-600' 
                    : 'bg-yellow-100 text-yellow-600'
                }`}>
                  质量分: {item.avg_quality_score.toFixed(1)}
                </span>
              </div>

              <p className="text-sm text-orange-700 mb-2">
                ⚠️ {item.review_reason}
              </p>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-gray-600">
                <div>出现次数: <span className="font-medium">{item.total_appearances}</span></div>
                <div>低分次数: <span className="font-medium text-red-600">{item.low_score_count}</span></div>
                <div>极低分次数: <span className="font-medium text-red-700">{item.very_low_score_count}</span></div>
                <div>内容过短: <span className="font-medium">{item.content_short_count}</span></div>
              </div>

              {item.score_history.length > 0 && (
                <div className="mt-2 text-xs text-gray-500">
                  最近分数: {item.score_history.slice(-5).map(s => s.toFixed(0)).join(' → ')}
                </div>
              )}
            </div>

            <div className="flex flex-col gap-2 ml-4">
              <button
                onClick={() => onAction(item.domain, 'block')}
                className="px-3 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                title="加入黑名单"
              >
                🚫 屏蔽
              </button>
              <button
                onClick={() => onAction(item.domain, 'approve')}
                className="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                title="移出队列，正常使用"
              >
                ✓ 批准
              </button>
              <button
                onClick={() => onAction(item.domain, 'approve', true)}
                className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                title="批准并加入白名单"
              >
                ⭐ 白名单
              </button>
              <button
                onClick={() => onAction(item.domain, 'dismiss')}
                className="px-3 py-1.5 bg-gray-500 text-white text-sm rounded hover:bg-gray-600"
                title="移出队列，继续观察"
              >
                ⏭️ 跳过
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
