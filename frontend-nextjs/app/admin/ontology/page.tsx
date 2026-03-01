'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
import { ChevronRight, ChevronDown, Search, RefreshCw } from 'lucide-react';

interface Framework {
  id: string;
  name: string;
  categories: string[];
  total_dimensions: number;
}

interface Category {
  id: string;
  name: string;
  dimensions: Dimension[];
}

interface Dimension {
  name: string;
  description: string;
  ask_yourself: string;
  examples: string;
}

interface FrameworkDetail {
  id: string;
  name: string;
  categories: Category[];
}

export default function OntologyBrowserPage() {
  const [frameworks, setFrameworks] = useState<Framework[]>([]);
  const [selectedFramework, setSelectedFramework] = useState<FrameworkDetail | null>(null);
  const [selectedDimension, setSelectedDimension] = useState<Dimension | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [reloading, setReloading] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string>('');

  const token = typeof window !== 'undefined' ? localStorage.getItem('wp_jwt_token') : null;
  const headers = { 'Authorization': `Bearer ${token}` };

  // 加载框架列表
  useEffect(() => {
    fetchFrameworks();
  }, []);

  const fetchFrameworks = async () => {
    try {
      setLoading(true);
      setError('');
      console.log('🔍 正在加载框架列表...');
      const res = await axios.get('/api/admin/ontology/frameworks', { headers });
      console.log('✅ 框架列表加载成功:', res.data);
      setFrameworks(res.data);
    } catch (error: any) {
      console.error('❌ 加载框架列表失败:', error);
      const errorMsg = error.response?.data?.detail || error.message || '未知错误';
      setError(`加载框架列表失败: ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  // 加载框架详情
  const loadFrameworkDetail = async (frameworkId: string) => {
    try {
      setLoadingDetail(true);
      setError('');
      console.log(`🔍 正在加载框架详情: ${frameworkId}`);
      const res = await axios.get(`/api/admin/ontology/framework/${frameworkId}`, { headers });
      console.log('✅ 框架详情加载成功:', res.data);
      setSelectedFramework(res.data);
      setSelectedDimension(null);
      setExpandedCategories(new Set());
    } catch (error: any) {
      console.error('❌ 加载框架详情失败:', error);
      const errorMsg = error.response?.data?.detail || error.message || '未知错误';
      setError(`加载框架详情失败: ${errorMsg}`);
      alert(`加载失败: ${errorMsg}`);
    } finally {
      setLoadingDetail(false);
    }
  };

  // 重新加载本体论
  const handleReload = async () => {
    try {
      setReloading(true);
      await axios.post('/api/admin/ontology/reload', {}, { headers });
      await fetchFrameworks();
      if (selectedFramework) {
        await loadFrameworkDetail(selectedFramework.id);
      }
      alert('本体论已重新加载');
    } catch (error) {
      console.error('重新加载失败:', error);
      alert('重新加载失败');
    } finally {
      setReloading(false);
    }
  };

  // 切换类别展开状态
  const toggleCategory = (categoryId: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(categoryId)) {
      newExpanded.delete(categoryId);
    } else {
      newExpanded.add(categoryId);
    }
    setExpandedCategories(newExpanded);
  };

  // 过滤维度（搜索功能）
  const filteredCategories = selectedFramework?.categories.map(cat => ({
    ...cat,
    dimensions: cat.dimensions.filter(dim =>
      searchQuery === '' ||
      dim.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      dim.description.toLowerCase().includes(searchQuery.toLowerCase())
    )
  })).filter(cat => cat.dimensions.length > 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载本体论框架...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 顶部工具栏 */}
      <div className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">本体论框架浏览器</h1>
          <p className="text-sm text-gray-500 mt-1">
            共 {frameworks.length} 个框架 |
            {selectedFramework && ` ${selectedFramework.categories.reduce((sum, cat) => sum + cat.dimensions.length, 0)} 个维度`}
          </p>
          {error && (
            <p className="text-sm text-red-500 mt-1">
              ⚠️ {error}
            </p>
          )}
        </div>
        <button
          onClick={handleReload}
          disabled={reloading}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${reloading ? 'animate-spin' : ''}`} />
          重新加载
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* 左侧：框架树形导航 */}
        <div className="w-1/3 bg-white border-r overflow-y-auto">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold mb-3">框架列表</h2>
            <div className="space-y-2">
              {frameworks.map(fw => (
                <button
                  key={fw.id}
                  onClick={() => loadFrameworkDetail(fw.id)}
                  disabled={loadingDetail}
                  className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
                    selectedFramework?.id === fw.id
                      ? 'bg-purple-100 text-purple-700 font-medium'
                      : 'hover:bg-gray-100'
                  } disabled:opacity-50 disabled:cursor-wait`}
                >
                  <div className="flex items-center justify-between">
                    <span>{fw.name}</span>
                    <span className="text-xs bg-gray-200 px-2 py-1 rounded">
                      {fw.total_dimensions}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* 类别和维度列表 */}
          {loadingDetail ? (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto mb-2"></div>
              <p className="text-sm text-gray-500">加载中...</p>
            </div>
          ) : selectedFramework ? (
            <div className="p-4">
              <div className="relative mb-4">
                <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="搜索维度..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div className="space-y-2">
                {filteredCategories?.map(category => (
                  <div key={category.id}>
                    <button
                      onClick={() => toggleCategory(category.id)}
                      className="w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-100 rounded-lg text-left"
                    >
                      {expandedCategories.has(category.id) ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                      <span className="font-medium">{category.name}</span>
                      <span className="ml-auto text-xs text-gray-500">
                        {category.dimensions.length}
                      </span>
                    </button>

                    {expandedCategories.has(category.id) && (
                      <div className="ml-6 mt-1 space-y-1">
                        {category.dimensions.map((dim, idx) => (
                          <button
                            key={idx}
                            onClick={() => setSelectedDimension(dim)}
                            className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                              selectedDimension === dim
                                ? 'bg-purple-50 text-purple-700'
                                : 'hover:bg-gray-50'
                            }`}
                          >
                            {dim.name}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        {/* 右侧：维度详情 */}
        <div className="flex-1 overflow-y-auto p-6">
          {selectedDimension ? (
            <div className="max-w-3xl mx-auto">
              <div className="bg-white rounded-lg shadow-sm p-6 space-y-6">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">
                    {selectedDimension.name}
                  </h2>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">
                    描述 (Description)
                  </h3>
                  <p className="text-gray-600 leading-relaxed">
                    {selectedDimension.description}
                  </p>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">
                    引导性问题 (Ask Yourself)
                  </h3>
                  <p className="text-gray-600 leading-relaxed italic">
                    {selectedDimension.ask_yourself}
                  </p>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase mb-2">
                    示例 (Examples)
                  </h3>
                  <p className="text-gray-600 leading-relaxed">
                    {selectedDimension.examples}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center">
                <Search className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg">选择一个维度查看详情</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
