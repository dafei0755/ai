'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useRouter } from 'next/navigation';

interface Session {
  session_id: string;
  user_id: string;
  status: string;
  created_at: string;
  input_text?: string;
}

export default function SessionsPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const fetchSessions = async () => {
    try {
      const token = localStorage.getItem('wp_jwt_token');
      const response = await axios.get(`/api/admin/sessions?page=${page}&page_size=20`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setSessions(response.data.sessions);
      setTotal(response.data.total);
    } catch (error) {
      console.error('获取会话失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, [page]);

  const handleViewSession = (sessionId: string) => {
    // 直接跳转到报告页面
    router.push(`/report/${sessionId}`);
  };

  if (loading) {
    return <div className="text-center py-8">加载中...</div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">会话管理</h1>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">会话ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">用户</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sessions.map((session) => {
              // 使用后端返回的用户信息
              const username = (session as any).username || session.user_id || '未知';
              const displayName = (session as any).display_name || username;

              // 提取会话ID部分作为辅助标识
              const parts = session.session_id.split('-');
              const timestamp = parts[1]?.slice(0, 8) || '';
              const uuid = parts[2]?.slice(0, 4) || '';
              const sessionTag = `${timestamp}-${uuid}`;

              return (
              <tr key={session.session_id}>
                <td className="px-6 py-4 text-sm text-gray-900 font-mono">{session.session_id.substring(0, 8)}...</td>
                <td className="px-6 py-4 text-sm text-gray-900">
                  <div className="flex flex-col">
                    <span className="font-medium">{displayName}</span>
                    <span className="text-xs text-gray-500" title={session.user_id}>{sessionTag}</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm">
                  <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs ${
                    session.status === 'running' ? 'bg-yellow-100 text-yellow-800' :
                    session.status === 'completed' ? 'bg-green-100 text-green-800' :
                    session.status === 'waiting_for_input' ? 'bg-blue-100 text-blue-800' :
                    session.status === 'rejected' ? 'bg-red-100 text-red-800' :
                    session.status === 'error' ? 'bg-orange-100 text-orange-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {session.status === 'running' && '🔄'}
                    {session.status === 'completed' && '✅'}
                    {session.status === 'waiting_for_input' && '⏸️'}
                    {session.status === 'rejected' && '❌'}
                    {session.status === 'error' && '⚠️'}
                    {!['running', 'completed', 'waiting_for_input', 'rejected', 'error'].includes(session.status) && '📋'}
                    <span>{session.status}</span>
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">{new Date(session.created_at).toLocaleString('zh-CN')}</td>
                <td className="px-6 py-4 text-sm">
                  <button
                    onClick={() => handleViewSession(session.session_id)}
                    className="text-blue-600 hover:text-blue-800 hover:underline"
                  >
                    查看
                  </button>
                </td>
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">共 {total} 个会话</p>
        <div className="flex space-x-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300 disabled:opacity-50"
          >
            上一页
          </button>
          <span className="px-4 py-2">第 {page} 页</span>
          <button
            onClick={() => setPage(p => p + 1)}
            className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  );
}
