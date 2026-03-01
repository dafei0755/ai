'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
import { CheckCircle, XCircle, AlertCircle, Eye, RefreshCw } from 'lucide-react';

interface Candidate {
  id: number;
  dimension_data: string;
  confidence_score: number;
  source_session_id: string;
  created_at: string;
  review_status: string;
}

interface Statistics {
  pending: number;
  approved: number;
  rejected: number;
  total: number;
  high_confidence: number;
}

export default function ReviewCandidatesPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [rejectReason, setRejectReason] = useState('');

  const token = typeof window !== 'undefined' ? localStorage.getItem('wp_jwt_token') : null;
  const headers = { 'Authorization': `Bearer ${token}` };

  useEffect(() => {
    fetchCandidates();
  }, []);

  const fetchCandidates = async () => {
    try {
      setLoading(true);
      const res = await axios.get('/api/admin/dimension-learning/candidates?limit=100', { headers });
      setCandidates(res.data.items || []);
      setStatistics(res.data.statistics || null);
    } catch (error) {
      console.error('加载候选列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (candidateId: number) => {
    try {
      await axios.post(`/api/admin/dimension-learning/candidates/${candidateId}/approve`, {}, { headers });
      alert('候选维度已批准并写入本体论');
      await fetchCandidates();
      setShowModal(false);
    } catch (error: any) {
      console.error('批准失败:', error);
      alert('批准失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleReject = async (candidateId: number, reason: string) => {
    try {
      await axios.post(
        `/api/admin/dimension-learning/candidates/${candidateId}/reject`,
        { reason },
        { headers }
      );
      alert('候选维度已拒绝');
      await fetchCandidates();
      setShowModal(false);
      setRejectReason('');
    } catch (error: any) {
      console.error('拒绝失败:', error);
      alert('拒绝失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleBatchApprove = async () => {
    if (selectedIds.size === 0) {
      alert('请先选择要批准的候选');
      return;
    }

    if (!confirm(`确定批量批准 ${selectedIds.size} 个候选维度吗？`)) {
      return;
    }

    try {
      const res = await axios.post(
        '/api/admin/dimension-learning/candidates/batch',
        {
          action: 'approve',
          candidate_ids: Array.from(selectedIds),
          reason: ''
        },
        { headers }
      );

      alert(`批量批准完成: 成功 ${res.data.result.success.length}, 失败 ${res.data.result.failed.length}`);
      setSelectedIds(new Set());
      await fetchCandidates();
    } catch (error: any) {
      console.error('批量批准失败:', error);
      alert('批量批准失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const toggleSelection = (id: number) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const openReviewModal = (candidate: Candidate) => {
    setSelectedCandidate(candidate);
    setShowModal(true);
    setRejectReason('');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载候选列表...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* 顶部工具栏 */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">候选维度审核</h1>
            <p className="text-sm text-gray-500 mt-1">
              审核AI提取的候选维度并决定是否写入本体论
            </p>
          </div>
          <button
            onClick={fetchCandidates}
            className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
          >
            <RefreshCw className="w-4 h-4" />
            刷新
          </button>
        </div>

        {/* 统计卡片 */}
        {statistics && (
          <div className="grid grid-cols-5 gap-4">
            <div className="bg-white p-4 rounded-lg shadow-sm">
              <div className="text-sm text-gray-500">待审核</div>
              <div className="text-2xl font-bold text-orange-600">{statistics.pending || 0}</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-sm">
              <div className="text-sm text-gray-500">已批准</div>
              <div className="text-2xl font-bold text-green-600">{statistics.approved || 0}</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-sm">
              <div className="text-sm text-gray-500">已拒绝</div>
              <div className="text-2xl font-bold text-red-600">{statistics.rejected || 0}</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-sm">
              <div className="text-sm text-gray-500">总计</div>
              <div className="text-2xl font-bold text-gray-900">{statistics.total || 0}</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-sm">
              <div className="text-sm text-gray-500">高置信度</div>
              <div className="text-2xl font-bold text-purple-600">{statistics.high_confidence || 0}</div>
            </div>
          </div>
        )}
      </div>

      {/* 批量操作工具栏 */}
      {selectedIds.size > 0 && (
        <div className="mb-4 bg-purple-50 border border-purple-200 rounded-lg p-4 flex items-center justify-between">
          <span className="text-purple-700 font-medium">
            已选择 {selectedIds.size} 个候选
          </span>
          <div className="flex gap-3">
            <button
              onClick={handleBatchApprove}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              批量批准
            </button>
            <button
              onClick={() => setSelectedIds(new Set())}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
            >
              取消选择
            </button>
          </div>
        </div>
      )}

      {/* 候选列表表格 */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="w-12 px-4 py-3 text-left">
                <input
                  type="checkbox"
                  checked={selectedIds.size === candidates.length && candidates.length > 0}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedIds(new Set(candidates.map(c => c.id)));
                    } else {
                      setSelectedIds(new Set());
                    }
                  }}
                  className="rounded"
                />
              </th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">维度名称</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">置信度</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">来源会话</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">创建时间</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {candidates.map(candidate => {
              const dimData = JSON.parse(candidate.dimension_data);
              const confidenceColor =
                candidate.confidence_score > 0.8 ? 'text-green-600 bg-green-100' :
                candidate.confidence_score > 0.6 ? 'text-yellow-600 bg-yellow-100' :
                'text-red-600 bg-red-100';

              return (
                <tr key={candidate.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(candidate.id)}
                      onChange={() => toggleSelection(candidate.id)}
                      className="rounded"
                    />
                  </td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {dimData.name || 'Unknown'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${confidenceColor}`}>
                      {(candidate.confidence_score * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {candidate.source_session_id?.slice(0, 16) || 'N/A'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {new Date(candidate.created_at).toLocaleDateString('zh-CN')}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => openReviewModal(candidate)}
                      className="flex items-center gap-1 px-3 py-1 text-sm bg-purple-600 text-white rounded hover:bg-purple-700"
                    >
                      <Eye className="w-4 h-4" />
                      审核
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {candidates.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <AlertCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>暂无待审核的候选维度</p>
          </div>
        )}
      </div>

      {/* 审核弹窗 */}
      {showModal && selectedCandidate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-2xl font-bold mb-4">审核候选维度</h2>

              {(() => {
                const dimData = JSON.parse(selectedCandidate.dimension_data);
                return (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">名称</label>
                      <p className="text-gray-900">{dimData.name}</p>
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">描述</label>
                      <p className="text-gray-700">{dimData.description}</p>
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">引导性问题</label>
                      <p className="text-gray-700 italic">{dimData.ask_yourself}</p>
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">示例</label>
                      <p className="text-gray-700">{dimData.examples}</p>
                    </div>

                    <div className="flex items-center gap-2 pt-2 border-t">
                      <label className="text-sm font-semibold text-gray-700">置信度:</label>
                      <span className={`px-3 py-1 rounded text-sm font-semibold ${
                        selectedCandidate.confidence_score > 0.8 ? 'bg-green-100 text-green-800' :
                        selectedCandidate.confidence_score > 0.6 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {(selectedCandidate.confidence_score * 100).toFixed(0)}%
                      </span>
                    </div>

                    {/* 拒绝原因输入框 */}
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-1">
                        拒绝原因（可选）
                      </label>
                      <textarea
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder="如选择拒绝，可在此填写原因..."
                        className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                        rows={3}
                      />
                    </div>
                  </div>
                );
              })()}

              <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
                <button
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                >
                  取消
                </button>
                <button
                  onClick={() => handleReject(selectedCandidate.id, rejectReason)}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                >
                  <XCircle className="w-4 h-4" />
                  拒绝
                </button>
                <button
                  onClick={() => handleApprove(selectedCandidate.id)}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  <CheckCircle className="w-4 h-4" />
                  批准并写入本体论
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
