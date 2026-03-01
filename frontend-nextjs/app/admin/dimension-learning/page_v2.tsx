'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface Stats {
  overview: {
    total_types: number;
    by_tier: {
      core: number;
      extended: number;
      emerging: number;
    };
    activity_stats: {
      discoveries_total: number;
      extended_types: number;
      emerging_types: number;
    };
  };
}

interface EmergingType {
  dimension: string;
  label_zh: string;
  label_en: string;
  case_count: number;
  success_count: number;
  success_rate: number;
  confidence_score: number;
  promotion_progress: number;
  source: string;
}

interface Discovery {
  concept_cluster: string;
  keywords: string[];
  occurrence_count: number;
  confidence: number;
  suggested_dimension: string;
}

interface LearningCurve {
  curve_data: Array<{
    date: string;
    discoveries: number;
    promotions: number;
  }>;
  summary: {
    total_extended: number;
    total_emerging: number;
    total_discoveries: number;
    period_days: number;
  };
}

export default function DimensionLearningDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [emergingTypes, setEmergingTypes] = useState<EmergingType[]>([]);
  const [discoveries, setDiscoveries] = useState<Discovery[]>([]);
  const [learningCurve, setLearningCurve] = useState<LearningCurve | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('wp_jwt_token');
      const headers = { 'Authorization': `Bearer ${token}` };

      // 并行获取所有数据
      const [statsRes, emergingRes, discoveryRes, curveRes] = await Promise.all([
        axios.get('/api/admin/dimension-learning/stats', { headers }),
        axios.get('/api/admin/dimension-learning/emerging-types?limit=10', { headers }),
        axios.get('/api/admin/dimension-learning/discoveries?limit=10', { headers }),
        axios.get('/api/admin/dimension-learning/learning-curve?days=30', { headers }),
      ]);

      setStats(statsRes.data);
      setEmergingTypes(emergingRes.data.items || []);
      setDiscoveries(discoveryRes.data.items || []);
      setLearningCurve(curveRes.data);
    } catch (error) {
      console.error('获取学习数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000); // 每分钟刷新
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载学习数据...</p>
        </div>
      </div>
    );
  }

  const overview = stats?.overview;

  return (
    <div className="space-y-6 p-6 bg-gray-50 min-h-screen">
      {/* 标题 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">🧠 维度学习系统</h1>
        <p className="text-gray-600">自动从用户输入中学习新的设计概念，持续扩展分类体系</p>
      </div>

      {/* 核心指标卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">核心标签</p>
              <p className="text-3xl font-bold text-gray-900">{overview?.by_tier.core || 92}</p>
            </div>
            <div className="bg-blue-100 p-3 rounded-full">
              <span className="text-2xl">🎯</span>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-2">手动维护的基础分类</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">扩展标签</p>
              <p className="text-3xl font-bold text-green-600">{overview?.by_tier.extended || 0}</p>
            </div>
            <div className="bg-green-100 p-3 rounded-full">
              <span className="text-2xl">✨</span>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-2">已验证晋升的标签</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">新兴候选</p>
              <p className="text-3xl font-bold text-orange-600">{overview?.by_tier.emerging || 0}</p>
            </div>
            <div className="bg-orange-100 p-3 rounded-full">
              <span className="text-2xl">🌱</span>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-2">待验证的新概念</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 mb-1">概念发现</p>
              <p className="text-3xl font-bold text-purple-600">{overview?.activity_stats.discoveries_total || 0}</p>
            </div>
            <div className="bg-purple-100 p-3 rounded-full">
              <span className="text-2xl">💡</span>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-2">LLM提取的原始概念</p>
        </div>
      </div>

      {/* 学习曲线图表 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">📈 学习曲线（近30天）</h2>
        {learningCurve && learningCurve.curve_data.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={learningCurve.curve_data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => {
                  const date = new Date(value);
                  return `${date.getMonth() + 1}/${date.getDate()}`;
                }}
              />
              <YAxis />
              <Tooltip
                labelFormatter={(value) => `日期: ${value}`}
                formatter={(value: any) => [value, '']}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="discoveries"
                stroke="#8b5cf6"
                name="新概念发现"
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="promotions"
                stroke="#10b981"
                name="标签晋升"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-center text-gray-500 py-12">
            暂无学习曲线数据
          </div>
        )}
      </div>

      {/* 新兴标签列表 */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900">🌱 新兴标签（待验证）</h2>
          <span className="text-sm text-gray-500">晋升条件：8次使用 + 80%成功率</span>
        </div>
        {emergingTypes.length > 0 ? (
          <div className="space-y-3">
            {emergingTypes.map((type, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-bold text-lg text-gray-900">{type.label_zh}</h3>
                      <span className="text-sm text-gray-500">({type.label_en})</span>
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        type.source === 'llm_discover'
                          ? 'bg-purple-100 text-purple-700'
                          : 'bg-blue-100 text-blue-700'
                      }`}>
                        {type.source === 'llm_discover' ? 'LLM发现' : '用户建议'}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-600 mb-2">
                      <span>📊 使用 {type.case_count} 次</span>
                      <span>✅ 成功率 {(type.success_rate * 100).toFixed(0)}%</span>
                      <span>🎯 置信度 {(type.confidence_score * 100).toFixed(0)}%</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all ${
                            type.promotion_progress >= 1
                              ? 'bg-green-500'
                              : type.promotion_progress >= 0.7
                              ? 'bg-yellow-500'
                              : 'bg-gray-400'
                          }`}
                          style={{ width: `${Math.min(type.promotion_progress * 100, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 min-w-[60px]">
                        {Math.min(type.promotion_progress * 100, 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center text-gray-500 py-12">
            暂无新兴标签数据
          </div>
        )}
      </div>

      {/* 概念发现列表 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">💡 最新概念发现</h2>
        {discoveries.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {discoveries.map((disc, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-bold text-gray-900">{disc.concept_cluster}</h3>
                  <span className="text-sm text-gray-500">×{disc.occurrence_count}</span>
                </div>
                <div className="flex flex-wrap gap-1 mb-2">
                  {disc.keywords.slice(0, 5).map((kw, kwIndex) => (
                    <span key={kwIndex} className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded">
                      {kw}
                    </span>
                  ))}
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">
                    {disc.suggested_dimension && `→ ${disc.suggested_dimension}`}
                  </span>
                  <span className="text-gray-500">
                    置信度 {(disc.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center text-gray-500 py-12">
            暂无概念发现数据
          </div>
        )}
      </div>

      {/* 系统说明 */}
      <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg shadow p-6 border border-blue-200">
        <h2 className="text-lg font-bold text-gray-900 mb-3">📖 系统工作原理</h2>
        <div className="space-y-2 text-sm text-gray-700">
          <p className="flex items-start gap-2">
            <span className="font-bold text-purple-600">1.</span>
            <span><strong>概念提取</strong>：LLM自动从用户输入中提取设计概念和关键词</span>
          </p>
          <p className="flex items-start gap-2">
            <span className="font-bold text-purple-600">2.</span>
            <span><strong>概念聚类</strong>：相似概念自动聚合，形成候选标签</span>
          </p>
          <p className="flex items-start gap-2">
            <span className="font-bold text-purple-600">3.</span>
            <span><strong>频次统计</strong>：记录每个概念的出现次数和成功率</span>
          </p>
          <p className="flex items-start gap-2">
            <span className="font-bold text-purple-600">4.</span>
            <span><strong>自动晋升</strong>：达到阈值（8次使用、80%成功率）的标签自动晋升为扩展标签</span>
          </p>
          <p className="flex items-start gap-2">
            <span className="font-bold text-purple-600">5.</span>
            <span><strong>持续演进</strong>：系统不断学习，分类体系自主扩展</span>
          </p>
        </div>
      </div>
    </div>
  );
}
