'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';

interface DimensionStats {
  total_feedbacks: number;
  avg_score: number;
  top_dimensions: Array<{
    name: string;
    usage_count: number;
    avg_score: number;
  }>;
}

export default function DimensionLearningPage() {
  const [stats, setStats] = useState<DimensionStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEnabled, setIsEnabled] = useState<boolean | null>(null);

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem('wp_jwt_token');
      const response = await axios.get('/api/admin/dimension-learning/stats', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.data.status === 'success') {
        setStats(response.data.placeholder_data || response.data.stats);
        setIsEnabled(true);
      }
    } catch (error: any) {
      console.error('获取维度学习统计失败:', error);
      if (error.response?.status === 404 || error.response?.data?.detail?.includes('未启用')) {
        setIsEnabled(false);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    // 每 30 秒刷新一次
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载学习数据...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">🧠 维度学习系统</h1>
          <p className="text-sm text-gray-500 mt-1">智能维度推荐与自主学习数据分析</p>
        </div>
        <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
          isEnabled
            ? 'bg-green-100 text-green-800'
            : 'bg-gray-100 text-gray-800'
        }`}>
          <div className={`w-2 h-2 rounded-full ${
            isEnabled ? 'bg-green-600 animate-pulse' : 'bg-gray-600'
          }`} />
          <span className="font-semibold text-sm">
            {isEnabled ? '学习系统已启用' : '学习系统未启用'}
          </span>
        </div>
      </div>

      {/* 功能未启用提示 */}
      {isEnabled === false && (
        <div className="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl shadow-lg border-2 border-yellow-300 p-8">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0">
              <div className="w-16 h-16 bg-yellow-500 rounded-full flex items-center justify-center">
                <span className="text-3xl text-white">⚙️</span>
              </div>
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-yellow-900 mb-3">维度学习系统未启用</h2>
              <p className="text-yellow-800 mb-4 leading-relaxed">
                维度学习系统可以根据用户反馈自动优化维度推荐策略。请按以下步骤启用：
              </p>

              <div className="bg-white rounded-lg p-5 mb-4 border-2 border-yellow-200">
                <h3 className="font-bold text-gray-900 mb-3 flex items-center gap-2">
                  <span className="bg-yellow-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-sm">1</span>
                  编辑 .env 配置文件
                </h3>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-sm font-mono">
{`# 启用维度学习系统
ENABLE_DIMENSION_LEARNING=true

# 可选：自定义配置
DIMENSION_FEEDBACK_SAMPLE_RATE=0.20  # 20%用户反馈抽样率
DIMENSION_LOW_SCORE_THRESHOLD=40.0   # 低效维度阈值`}
                </pre>
              </div>

              <div className="bg-white rounded-lg p-5 mb-4 border-2 border-yellow-200">
                <h3 className="font-bold text-gray-900 mb-3 flex items-center gap-2">
                  <span className="bg-yellow-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-sm">2</span>
                  重启后端服务
                </h3>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-sm font-mono">
{`# Windows
taskkill /F /IM python.exe
python -B scripts\\run_server_production.py

# Linux/Mac
pkill python
python -B scripts/run_server_production.py`}
                </pre>
              </div>

              <div className="bg-white rounded-lg p-5 border-2 border-yellow-200">
                <h3 className="font-bold text-gray-900 mb-3 flex items-center gap-2">
                  <span className="bg-yellow-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-sm">3</span>
                  刷新页面查看数据
                </h3>
                <p className="text-gray-700 mb-3">服务重启后，刷新此页面即可看到学习数据统计。</p>
                <button
                  onClick={() => window.location.reload()}
                  className="px-6 py-3 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-all font-semibold shadow-md"
                >
                  🔄 刷新页面
                </button>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-6 border-t-2 border-yellow-200">
            <details className="text-left">
              <summary className="cursor-pointer font-semibold text-yellow-900 hover:text-yellow-700 transition-colors">
                📖 查看完整文档
              </summary>
              <div className="mt-4 bg-white rounded-lg p-4 border border-yellow-200">
                <p className="text-sm text-gray-700 mb-2">
                  <strong>维度学习系统技术文档：</strong>
                </p>
                <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside">
                  <li>
                    <a href="/docs/DIMENSION_LEARNING_QUICKSTART.md" target="_blank" className="text-blue-600 hover:underline">
                      快速启用指南
                    </a>
                  </li>
                  <li>
                    <a href="/docs/DIMENSION_LEARNING_SYSTEM.md" target="_blank" className="text-blue-600 hover:underline">
                      完整技术文档
                    </a>
                  </li>
                </ul>
              </div>
            </details>
          </div>
        </div>
      )}

      {/* 功能已启用 - 显示统计数据 */}
      {isEnabled && stats && (
        <>
          {/* 核心指标卡片 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl shadow-lg border-2 border-blue-300 p-6">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-bold text-blue-900">📊 反馈总数</h3>
                <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-xl">💬</span>
                </div>
              </div>
              <p className="text-4xl font-bold text-blue-900 mb-1">{stats.total_feedbacks}</p>
              <p className="text-sm text-blue-700">累计用户反馈次数</p>
            </div>

            <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl shadow-lg border-2 border-green-300 p-6">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-bold text-green-900">⭐ 平均评分</h3>
                <div className="w-10 h-10 bg-green-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-xl">📈</span>
                </div>
              </div>
              <p className="text-4xl font-bold text-green-900 mb-1">{stats.avg_score.toFixed(1)}</p>
              <p className="text-sm text-green-700">维度推荐满意度（满分100）</p>
            </div>

            <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl shadow-lg border-2 border-purple-300 p-6">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-bold text-purple-900">🎯 热门维度</h3>
                <div className="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-xl">🔥</span>
                </div>
              </div>
              <p className="text-4xl font-bold text-purple-900 mb-1">{stats.top_dimensions.length}</p>
              <p className="text-sm text-purple-700">高频使用维度数量</p>
            </div>
          </div>

          {/* 热门维度排行 */}
          {stats.top_dimensions.length > 0 && (
            <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
              <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200">
                <h2 className="text-xl font-bold text-gray-900">🏆 热门维度排行榜</h2>
                <p className="text-sm text-gray-600 mt-1">根据使用频率和用户评分综合排名</p>
              </div>
              <div className="p-6">
                <div className="space-y-3">
                  {stats.top_dimensions.map((dim, index) => (
                    <div key={index} className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-white ${
                        index === 0 ? 'bg-yellow-500' :
                        index === 1 ? 'bg-gray-400' :
                        index === 2 ? 'bg-orange-600' : 'bg-gray-300'
                      }`}>
                        {index + 1}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-bold text-gray-900">{dim.name}</h3>
                        <p className="text-sm text-gray-600">使用 {dim.usage_count} 次</p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-green-600">{dim.avg_score.toFixed(1)}</p>
                        <p className="text-xs text-gray-500">平均评分</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 功能说明 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 border-2 border-blue-300 rounded-xl p-5 shadow-md">
              <h3 className="font-bold text-blue-900 mb-3 flex items-center gap-2 text-lg">
                💡 工作原理
              </h3>
              <ul className="text-sm text-blue-800 space-y-2">
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 mt-0.5">▸</span>
                  <span><strong>混合策略</strong>：80% 规则引擎 + 20% 学习优化</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 mt-0.5">▸</span>
                  <span><strong>动态权重</strong>：随数据累积自动调整学习比例</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-600 mt-0.5">▸</span>
                  <span><strong>反馈采样</strong>：收集用户对维度推荐的评分</span>
                </li>
              </ul>
            </div>

            <div className="bg-gradient-to-br from-orange-50 to-orange-100 border-2 border-orange-300 rounded-xl p-5 shadow-md">
              <h3 className="font-bold text-orange-900 mb-3 flex items-center gap-2 text-lg">
                📈 学习阶段
              </h3>
              <ul className="text-sm text-orange-800 space-y-2">
                <li className="flex items-start gap-2">
                  <span className="text-orange-600 mt-0.5">▸</span>
                  <span><strong>0-50 会话</strong>：20% 学习权重（冷启动）</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-orange-600 mt-0.5">▸</span>
                  <span><strong>50-200 会话</strong>：40% 学习权重（成长期）</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-orange-600 mt-0.5">▸</span>
                  <span><strong>200+ 会话</strong>：60-80% 学习权重（成熟期）</span>
                </li>
              </ul>
            </div>
          </div>

          {/* 开发提示 */}
          <div className="bg-gradient-to-r from-gray-50 to-gray-100 border border-gray-300 rounded-xl p-5 shadow-sm">
            <p className="text-sm text-gray-600 flex items-center gap-2">
              <span className="text-xl">🚧</span>
              <span>
                <strong>开发中功能：</strong>
                更详细的维度分析、低效维度识别、学习曲线可视化等功能正在开发中...
              </span>
            </p>
          </div>
        </>
      )}
    </div>
  );
}
