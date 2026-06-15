'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import axios from 'axios';

interface SessionDetail {
  session_id: string;
  user_id: string;
  status: string;
  created_at: string;
  updated_at?: string;
  input_text?: string;
  state?: any;
  error?: string;
  analysis_result?: any;
  expert_reports?: any[];
}

export default function SessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [session, setSession] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSession = async () => {
      try {
        const token = localStorage.getItem('app_auth_token');
        if (!token) {
          setError('未登录，请先登录');
          setLoading(false);
          return;
        }

        console.log('🔍 获取会话详情:', sessionId);
        const response = await axios.get(`/api/sessions/${sessionId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });

        console.log('✅ 会话数据:', response.data);
        setSession(response.data);
      } catch (err: any) {
        console.error('❌ 获取会话详情失败:', err);
        setError(err.response?.data?.detail || '无法加载会话详情');
      } finally {
        setLoading(false);
      }
    };

    if (sessionId) {
      fetchSession();
    }
  }, [sessionId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载会话详情...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-red-50 border border-red-200 rounded-lg p-8 max-w-md">
          <h2 className="text-xl font-bold text-red-800 mb-4">❌ 加载失败</h2>
          <p className="text-red-600 mb-4">{error}</p>

          {error.includes('不存在') && (
            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4 text-sm">
              <p className="text-yellow-800 mb-2">💡 <strong>可能的原因：</strong></p>
              <ul className="text-yellow-700 space-y-1 list-disc list-inside">
                <li>会话已过期（Redis TTL）</li>
                <li>会话已被归档到历史记录</li>
                <li>会话ID格式错误</li>
              </ul>
            </div>
          )}

          <div className="flex space-x-3">
            <button
              onClick={() => router.back()}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              返回上一页
            </button>
            <button
              onClick={() => router.push('/admin/sessions')}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
            >
              查看所有会话
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="text-gray-600">会话不存在</p>
          <button
            onClick={() => router.back()}
            className="mt-4 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
          >
            返回
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        {/* 头部导航 */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => router.back()}
              className="text-gray-600 hover:text-gray-800"
            >
              ← 返回
            </button>
            <h1 className="text-2xl font-bold text-gray-800">会话详情</h1>
          </div>
          <span className={`px-4 py-2 rounded-full text-sm font-medium ${
            session.status === 'running' ? 'bg-yellow-100 text-yellow-800' :
            session.status === 'completed' ? 'bg-green-100 text-green-800' :
            session.status === 'error' ? 'bg-red-100 text-red-800' :
            session.status === 'waiting_for_input' ? 'bg-blue-100 text-blue-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {session.status}
          </span>
        </div>

        {/* 基本信息卡片 */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">基本信息</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">会话ID</label>
              <p className="text-sm text-gray-900 font-mono bg-gray-50 p-2 rounded break-all">
                {session.session_id}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">用户ID</label>
              <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{session.user_id}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1">创建时间</label>
              <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">
                {new Date(session.created_at).toLocaleString('zh-CN')}
              </p>
            </div>
            {session.updated_at && (
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">更新时间</label>
                <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">
                  {new Date(session.updated_at).toLocaleString('zh-CN')}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* 会话状态说明 */}
        <div className={`rounded-lg shadow-lg p-6 mb-6 ${
          session.status === 'running' ? 'bg-yellow-50 border border-yellow-200' :
          session.status === 'completed' ? 'bg-green-50 border border-green-200' :
          session.status === 'error' ? 'bg-red-50 border border-red-200' :
          session.status === 'waiting_for_input' ? 'bg-blue-50 border border-blue-200' :
          'bg-gray-50 border border-gray-200'
        }`}>
          <h2 className="text-lg font-semibold text-gray-800 mb-2">当前状态</h2>
          <p className="text-gray-700 mb-2">
            {session.status === 'running' && '🔄 系统正在处理您的需求，专家团队正在分析中...'}
            {session.status === 'completed' && '✅ 分析已完成！您可以查看下方的完整报告。'}
            {session.status === 'error' && '❌ 处理过程中出现错误，请查看错误信息。'}
            {session.status === 'waiting_for_input' && '⏸️ 等待您的输入或确认。'}
            {session.status === 'rejected' && '🚫 需求已被拒绝，可能因为不符合系统处理范围。'}
          </p>
          {session.status === 'waiting_for_input' && (
            <div className="mt-3 p-3 bg-white rounded border">
              <p className="text-sm text-gray-600">
                💡 <strong>提示：</strong>该会话可能正在等待您完成问卷调查或提供更多信息。
                请返回主应用继续操作。
              </p>
            </div>
          )}
          {session.status === 'completed' && (
            <div className="mt-3 flex space-x-3">
              <button
                onClick={() => {
                  // 跳转到报告页面（使用动态路由）
                  window.location.href = `/report/${session.session_id}`;
                }}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
              >
                📄 查看完整报告
              </button>
              <button
                onClick={() => {
                  // 下载报告（如果支持）
                  window.open(`/api/sessions/${session.session_id}/export-pdf`, '_blank');
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
              >
                📥 导出 PDF
              </button>
            </div>
          )}
        </div>

        {/* 用户输入 */}
        {session.input_text && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">用户输入</h2>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-gray-800 whitespace-pre-wrap">{session.input_text}</p>
            </div>
          </div>
        )}

        {/* 分析结果 */}
        {session.analysis_result && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">分析结果概览</h2>
            <div className="prose max-w-none">
              {typeof session.analysis_result === 'string' ? (
                <div className="whitespace-pre-wrap text-gray-700">{session.analysis_result}</div>
              ) : (
                <pre className="bg-gray-50 p-4 rounded-lg text-sm overflow-x-auto">
                  {JSON.stringify(session.analysis_result, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )}

        {/* 报告预览（如果有 final_output） */}
        {session.state?.final_output && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">📋 完整分析报告</h2>
            <div className="prose max-w-none">
              <div
                className="text-gray-700"
                dangerouslySetInnerHTML={{
                  __html: session.state.final_output.replace(/\n/g, '<br/>')
                }}
              />
            </div>
            <div className="mt-4 pt-4 border-t">
              <button
                onClick={() => window.location.href = `/report/${session.session_id}`}
                className="text-blue-600 hover:text-blue-800 font-medium"
              >
                查看完整报告（包含交付物和概念图） →
              </button>
            </div>
          </div>
        )}

        {/* 交付物列表 */}
        {session.state?.deliverables && session.state.deliverables.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">
              🎁 交付物 ({session.state.deliverables.length})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {session.state.deliverables.map((deliverable: any, index: number) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                  <h3 className="font-medium text-gray-800 mb-2">
                    {deliverable.title || `交付物 ${index + 1}`}
                  </h3>
                  <p className="text-sm text-gray-600 mb-3">
                    {deliverable.description || '暂无描述'}
                  </p>
                  {deliverable.image_url && (
                    <img
                      src={deliverable.image_url}
                      alt={deliverable.title}
                      className="w-full h-48 object-cover rounded mb-2"
                    />
                  )}
                  {deliverable.type && (
                    <span className="inline-block px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                      {deliverable.type}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 专家报告 */}
        {session.expert_reports && session.expert_reports.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">
              专家报告 ({session.expert_reports.length})
            </h2>
            <div className="space-y-4">
              {session.expert_reports.map((report: any, index: number) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4">
                  <h3 className="font-medium text-gray-800 mb-2">
                    {report.expert_name || `专家 ${index + 1}`}
                  </h3>
                  <div className="text-sm text-gray-600 whitespace-pre-wrap">
                    {report.content || JSON.stringify(report, null, 2)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 会话完整数据（开发调试用） */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">完整会话数据（调试视图）</h2>
          <details className="cursor-pointer">
            <summary className="text-sm text-blue-600 hover:text-blue-800 mb-2">
              点击展开查看原始 JSON 数据
            </summary>
            <pre className="bg-gray-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto mt-2">
              {JSON.stringify(session, null, 2)}
            </pre>
          </details>
        </div>

        {/* 会话状态 */}
        {session.state && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">会话状态数据</h2>
            <details className="cursor-pointer">
              <summary className="text-sm text-blue-600 hover:text-blue-800 mb-2">
                点击展开查看状态详情
              </summary>
              <pre className="bg-gray-50 border rounded-lg p-4 text-xs overflow-x-auto mt-2">
                {JSON.stringify(session.state, null, 2)}
              </pre>
            </details>
          </div>
        )}

        {/* 错误信息 */}
        {session.error && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-red-800 mb-4">错误信息</h2>
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-800">{session.error}</p>
            </div>
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex justify-center space-x-4">
          <button
            onClick={() => router.push('/analysis')}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            开始新的分析
          </button>
          <button
            onClick={() => router.back()}
            className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 font-medium"
          >
            返回列表
          </button>
        </div>
      </div>
    </div>
  );
}
