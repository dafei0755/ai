"use client";

import { useState, useEffect } from 'react';

interface CapabilityViolation {
  id: string;
  timestamp: string;
  node: string;
  original_deliverable: string;
  transformed_deliverable: string;
  user_input: string;
  session_id: string;
  match_score: number;
  transformation_reason: string;
}

interface NodeStats {
  node_name: string;
  total_checks: number;
  violation_count: number;
  violation_rate: number;
  most_common_violations: Array<{
    original: string;
    transformed: string;
    count: number;
  }>;
}

interface TrendData {
  date: string;
  violations: number;
  checks: number;
}

export default function CapabilityBoundaryMonitoring() {
  const [violations, setViolations] = useState<CapabilityViolation[]>([]);
  const [nodeStats, setNodeStats] = useState<NodeStats[]>([]);
  const [trends, setTrends] = useState<TrendData[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('7d');
  const [activeTab, setActiveTab] = useState<'nodes' | 'violations' | 'patterns'>('nodes');

  useEffect(() => {
    fetchCapabilityBoundaryData();
  }, [timeRange]);

  const fetchCapabilityBoundaryData = async () => {
    setLoading(true);
    try {
      // TODO: 实际API调用
      // const response = await fetch(`/api/admin/capability-boundary?range=${timeRange}`);
      // const data = await response.json();

      // 模拟数据
      const mockViolations: CapabilityViolation[] = [
        {
          id: '1',
          timestamp: '2026-01-04T10:30:00Z',
          node: 'progressive_step3_gap_filling',
          original_deliverable: '施工图',
          transformed_deliverable: '设计策略文档',
          user_input: '35岁首套，骑士大华悦，程序员，腾讯上班，年薪120万，约34岁，外企上班，年车20万，深圳购置住宅160平，基于此给出设计计划书。',
          session_id: 'session_123',
          match_score: 0.45,
          transformation_reason: '施工图需要AutoCAD专业工具，超出系统能力边界'
        },
        {
          id: '2',
          timestamp: '2026-01-04T09:15:00Z',
          node: 'progressive_step3_gap_filling',
          original_deliverable: '效果图',
          transformed_deliverable: '空间概念描述',
          user_input: '深圳口岸, 20000平米，菜市场研市，对标苏州白塘菜场，给出方案设计和设计策略',
          session_id: 'session_124',
          match_score: 0.38,
          transformation_reason: '效果图需要3D渲染工具，系统仅提供概念描述'
        },
        {
          id: '3',
          timestamp: '2026-01-04T08:45:00Z',
          node: 'questionnaire_summary',  // 🔧 v7.151: 替换 requirements_confirmation
          original_deliverable: '精确预算清单',
          transformed_deliverable: '预算框架',
          user_input: '150平米住宅，预算30万，现代简约风格，三室两厅',
          session_id: 'session_125',
          match_score: 0.52,
          transformation_reason: '精确预算需要实时市场报价，系统提供预算框架指导'
        }
      ];

      const mockNodeStats: NodeStats[] = [
        {
          node_name: 'progressive_step3_gap_filling',
          total_checks: 156,
          violation_count: 42,
          violation_rate: 0.269,
          most_common_violations: [
            { original: '施工图', transformed: '设计策略文档', count: 18 },
            { original: '效果图', transformed: '空间概念描述', count: 15 },
            { original: '软装清单', transformed: '材料选择指导', count: 9 }
          ]
        },
        {
          node_name: 'questionnaire_summary',  // 🔧 v7.151: 替换 requirements_confirmation
          total_checks: 203,
          violation_count: 28,
          violation_rate: 0.138,
          most_common_violations: [
            { original: '精确预算清单', transformed: '预算框架', count: 16 },
            { original: 'BOM清单', transformed: '材料选择指导', count: 12 }
          ]
        },
        {
          node_name: 'progressive_step1_core_task',
          total_checks: 180,
          violation_count: 12,
          violation_rate: 0.067,
          most_common_violations: [
            { original: '施工图', transformed: '设计策略文档', count: 8 },
            { original: '效果图', transformed: '空间概念描述', count: 4 }
          ]
        }
      ];

      const mockTrends: TrendData[] = [
        { date: '2026-01-01', violations: 8, checks: 45 },
        { date: '2026-01-02', violations: 12, checks: 52 },
        { date: '2026-01-03', violations: 15, checks: 58 },
        { date: '2026-01-04', violations: 10, checks: 48 }
      ];

      setViolations(mockViolations);
      setNodeStats(mockNodeStats);
      setTrends(mockTrends);
    } catch (error) {
      console.error('Failed to fetch capability boundary data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTotalViolations = () => violations.length;
  const getAverageViolationRate = () => {
    if (nodeStats.length === 0) return '0.0';
    const sum = nodeStats.reduce((acc, stat) => acc + stat.violation_rate, 0);
    return (sum / nodeStats.length * 100).toFixed(1);
  };

  const getTrendDirection = () => {
    if (trends.length < 2) return 'stable';
    const recent = trends.slice(-3);
    const recentAvg = recent.reduce((acc, t) => acc + t.violations, 0) / recent.length;
    const older = trends.slice(0, -3);
    if (older.length === 0) return 'stable';
    const olderAvg = older.reduce((acc, t) => acc + t.violations, 0) / older.length;

    if (recentAvg > olderAvg * 1.1) return 'up';
    if (recentAvg < olderAvg * 0.9) return 'down';
    return 'stable';
  };

  const getNodeStatusColor = (rate: number) => {
    if (rate >= 0.3) return 'bg-red-100 text-red-800 border-red-200';
    if (rate >= 0.15) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    return 'bg-green-100 text-green-800 border-green-200';
  };

  const trendDirection = getTrendDirection();

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">能力边界违规监控</h1>
        <p className="text-gray-600">
          监控系统各节点的能力边界检查，统计超出能力的交付物转化情况
        </p>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">总违规次数</h3>
            <span className="text-2xl">⚠️</span>
          </div>
          <div className="text-3xl font-bold text-gray-900">{getTotalViolations()}</div>
          <p className="text-sm text-gray-500 mt-1">
            过去 {timeRange === '24h' ? '24小时' : timeRange === '7d' ? '7天' : '30天'}
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">平均违规率</h3>
            <span className="text-2xl">📊</span>
          </div>
          <div className="text-3xl font-bold text-gray-900">{getAverageViolationRate()}%</div>
          <p className="text-sm text-gray-500 mt-1">所有节点平均值</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">趋势</h3>
            <span className="text-2xl">📈</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">
            {trendDirection === 'up' && <span className="text-red-500">↗ 上升</span>}
            {trendDirection === 'down' && <span className="text-green-500">↘ 下降</span>}
            {trendDirection === 'stable' && <span className="text-gray-500">→ 稳定</span>}
          </div>
          <p className="text-sm text-gray-500 mt-1">
            {trendDirection === 'up' && '违规率上升'}
            {trendDirection === 'down' && '违规率下降'}
            {trendDirection === 'stable' && '违规率稳定'}
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-600">最新检查</h3>
            <span className="text-2xl">🕐</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">
            {violations.length > 0 ? new Date(violations[0].timestamp).toLocaleTimeString('zh-CN') : '--:--'}
          </div>
          <p className="text-sm text-gray-500 mt-1">最近一次转化时间</p>
        </div>
      </div>

      {/* Time Range Selector */}
      <div className="flex items-center space-x-2">
        <span className="text-sm text-gray-600">时间范围:</span>
        <div className="flex space-x-2">
          {(['24h', '7d', '30d'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-4 py-2 text-sm rounded-md transition ${ timeRange === range
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {range === '24h' ? '24小时' : range === '7d' ? '7天' : '30天'}
            </button>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-4 px-6" aria-label="Tabs">
            {(['nodes', 'violations', 'patterns'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 px-2 text-sm font-medium border-b-2 transition ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab === 'nodes' && '节点统计'}
                {tab === 'violations' && '违规记录'}
                {tab === 'patterns' && '转化模式'}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* Node Statistics Tab */}
          {activeTab === 'nodes' && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-blue-800">
                  📋 监控各节点的能力边界检查情况，违规率≥30%为高风险，15%-30%为中风险，&lt;15%为低风险
                </p>
              </div>

              {nodeStats.map((stat) => (
                <div key={stat.node_name} className="border border-gray-200 rounded-lg p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">{stat.node_name}</h3>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getNodeStatusColor(stat.violation_rate)}`}>
                      {(stat.violation_rate * 100).toFixed(1)}% 违规率
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mb-4">
                    总检查: {stat.total_checks} | 违规: {stat.violation_count}
                  </p>
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">常见违规转化:</h4>
                    <div className="space-y-2">
                      {stat.most_common_violations.map((v, idx) => (
                        <div key={idx} className="flex items-center justify-between text-sm bg-gray-50 p-2 rounded">
                          <span className="text-gray-700">
                            {v.original} → {v.transformed}
                          </span>
                          <span className="text-gray-500 bg-white px-2 py-1 rounded border border-gray-200">
                            {v.count}次
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Violation Records Tab */}
          {activeTab === 'violations' && (
            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-4">最近违规记录</h2>
              <p className="text-gray-600 mb-6">系统自动转化的交付物列表</p>

              <div className="space-y-4">
                {violations.map((v) => (
                  <div key={v.id} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className="space-y-2 flex-1">
                        <div className="flex items-center space-x-2">
                          <span className="px-2 py-1 bg-gray-100 rounded text-xs font-medium text-gray-700">
                            {v.node}
                          </span>
                          <span className="text-xs text-gray-500">
                            {new Date(v.timestamp).toLocaleString('zh-CN')}
                          </span>
                        </div>
                        <p className="text-sm font-medium">
                          <span className="text-red-600">{v.original_deliverable}</span>
                          {' → '}
                          <span className="text-green-600">{v.transformed_deliverable}</span>
                        </p>
                        <p className="text-sm text-gray-600">{v.transformation_reason}</p>
                        <p className="text-xs text-gray-500 mt-2">
                          用户输入: {v.user_input.substring(0, 100)}...
                        </p>
                      </div>
                      <span className={`ml-4 px-2 py-1 rounded text-xs font-medium whitespace-nowrap ${
                        v.match_score >= 0.6 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        匹配度: {(v.match_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Transformation Patterns Tab */}
          {activeTab === 'patterns' && (
            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-4">转化模式分析</h2>
              <p className="text-gray-600 mb-6">最常见的交付物转化规则</p>

              <div className="grid md:grid-cols-2 gap-6 mb-8">
                <div className="border border-red-200 rounded-lg p-4 bg-red-50">
                  <h4 className="text-sm font-semibold text-red-800 mb-3">❌ 不支持的交付物</h4>
                  <ul className="text-sm space-y-2 text-gray-700">
                    <li>• CAD施工图 (需要AutoCAD专业工具)</li>
                    <li>• 3D效果图 (需要3ds Max、SketchUp)</li>
                    <li>• 精确材料清单 (需要现场测量)</li>
                    <li>• 精确预算清单 (需要实时报价)</li>
                    <li>• BOM清单 (需要供应商对接)</li>
                  </ul>
                </div>
                <div className="border border-green-200 rounded-lg p-4 bg-green-50">
                  <h4 className="text-sm font-semibold text-green-800 mb-3">✅ 系统支持的交付物</h4>
                  <ul className="text-sm space-y-2 text-gray-700">
                    <li>• 设计策略文档 (策略性指导)</li>
                    <li>• 空间概念描述 (概念性说明)</li>
                    <li>• 材料选择指导 (选型建议)</li>
                    <li>• 预算框架 (预算结构指导)</li>
                    <li>• 分析报告 (需求和可行性分析)</li>
                  </ul>
                </div>
              </div>

              <div className="border border-gray-200 rounded-lg p-6 bg-gray-50">
                <h4 className="text-sm font-semibold text-gray-900 mb-4">转化规则:</h4>
                <div className="space-y-3 text-sm">
                  <div className="flex items-center space-x-2">
                    <span className="text-green-500">✓</span>
                    <span className="text-gray-700">施工图 → 设计策略文档</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-green-500">✓</span>
                    <span className="text-gray-700">效果图 → 空间概念描述</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-green-500">✓</span>
                    <span className="text-gray-700">软装清单/精确材料清单 → 材料选择指导</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-green-500">✓</span>
                    <span className="text-gray-700">精确预算清单 → 预算框架</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
