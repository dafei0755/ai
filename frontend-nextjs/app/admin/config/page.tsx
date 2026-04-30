'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';

export default function ConfigPage() {
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [editorValue, setEditorValue] = useState<string>('');
  const [isEditing, setIsEditing] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  const fetchConfig = async () => {
    try {
      const token = localStorage.getItem('wp_jwt_token');
      const response = await axios.get('/api/admin/config/current', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setConfig(response.data.config);
      setEditorValue(JSON.stringify(response.data.config, null, 2));
    } catch (error) {
      console.error('获取配置失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleReload = async () => {
    try {
      const token = localStorage.getItem('wp_jwt_token');
      await axios.post('/api/admin/config/reload', {}, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      alert('✅ 配置已重载！');
      fetchConfig();
    } catch (error: any) {
      alert(`❌ 重载失败: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleEditorChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setEditorValue(value);
    setHasChanges(value !== JSON.stringify(config, null, 2));
  };

  const handleSave = () => {
    try {
      const parsed = JSON.parse(editorValue);
      // TODO: 实现保存配置到后端的API
      console.log('保存配置:', parsed);
      alert('⚠️ 配置保存功能待实现（需要后端支持写入.env）');
    } catch (error: any) {
      alert(`❌ JSON格式错误: ${error.message}`);
    }
  };

  const handleCancel = () => {
    setEditorValue(JSON.stringify(config, null, 2));
    setIsEditing(false);
    setHasChanges(false);
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载配置中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">⚙️ 配置管理</h1>
          <p className="text-sm text-gray-500 mt-1">查看和编辑系统运行时配置</p>
        </div>
        <div className="flex gap-3">
          {isEditing ? (
            <>
              <button
                onClick={handleCancel}
                className="px-5 py-2.5 bg-white border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-all font-medium shadow-sm"
              >
                取消
              </button>
              <button
                onClick={handleSave}
                disabled={!hasChanges}
                className="px-5 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium shadow-sm flex items-center gap-2"
              >
                💾 保存修改
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setIsEditing(true)}
                className="px-5 py-2.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-all font-medium shadow-sm flex items-center gap-2"
              >
                ✏️ 编辑配置
              </button>
              <button
                onClick={handleReload}
                className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all font-medium shadow-sm flex items-center gap-2"
              >
                🔄 重载配置
              </button>
            </>
          )}
        </div>
      </div>

      {/* 编辑器区域 */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
        {isEditing ? (
          <div className="border-2 border-purple-400">
            <div className="bg-gradient-to-r from-purple-50 to-purple-100 px-5 py-3 border-b border-purple-200">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-purple-900">
                  ✏️ 编辑模式 - 修改配置后点击&ldquo;保存修改&rdquo;按钮
                </p>
                {hasChanges && (
                  <span className="text-xs px-3 py-1 bg-orange-500 text-white rounded-full font-semibold animate-pulse">
                    ● 有未保存的更改
                  </span>
                )}
              </div>
            </div>
            <textarea
              value={editorValue}
              onChange={handleEditorChange}
              className="w-full h-[600px] p-5 font-mono text-sm text-gray-800 bg-white focus:outline-none focus:ring-2 focus:ring-purple-500 leading-relaxed"
              spellCheck={false}
              placeholder="编辑 JSON 配置..."
            />
          </div>
        ) : (
          <div>
            <div className="bg-gradient-to-r from-gray-50 to-gray-100 px-5 py-3 border-b border-gray-200">
              <p className="text-sm font-semibold text-gray-700">
                👁️ 只读模式 - 点击&ldquo;编辑配置&rdquo;按钮进入编辑模式
              </p>
            </div>
            <pre className="p-5 overflow-auto h-[600px] bg-gray-50 text-sm text-gray-800 leading-relaxed font-mono">
{editorValue}
            </pre>
          </div>
        )}
      </div>

      {/* 帮助信息 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 border-2 border-blue-300 rounded-xl p-5 shadow-md">
          <h3 className="font-bold text-blue-900 mb-3 flex items-center gap-2 text-lg">
            💡 功能说明
          </h3>
          <ul className="text-sm text-blue-800 space-y-2">
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">▸</span>
              <span><strong>编辑配置</strong>：进入编辑模式，修改 JSON 配置内容</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">▸</span>
              <span><strong>保存修改</strong>：将修改保存到 .env 文件（待实现）</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">▸</span>
              <span><strong>重载配置</strong>：从 .env 文件重新加载配置到内存</span>
            </li>
          </ul>
        </div>
        <div className="bg-gradient-to-br from-orange-50 to-orange-100 border-2 border-orange-300 rounded-xl p-5 shadow-md">
          <h3 className="font-bold text-orange-900 mb-3 flex items-center gap-2 text-lg">
            ⚠️ 注意事项
          </h3>
          <ul className="text-sm text-orange-800 space-y-2">
            <li className="flex items-start gap-2">
              <span className="text-orange-600 mt-0.5">▸</span>
              <span>修改配置前请<strong>确保备份</strong>原有配置</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-orange-600 mt-0.5">▸</span>
              <span>敏感信息（API Key）已<strong>脱敏显示</strong></span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-orange-600 mt-0.5">▸</span>
              <span>配置保存后需<strong>重载才能生效</strong></span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
