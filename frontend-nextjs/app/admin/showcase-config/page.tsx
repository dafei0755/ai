"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Loader2, Check, X, Save, AlertCircle } from "lucide-react";
import axios from "axios";

interface ShowcaseConfig {
  session_ids: string[];
  rotation_interval_seconds: number;
  autoplay: boolean;
  loop: boolean;
  show_navigation: boolean;
  show_pagination: boolean;
  max_slides: number;
  image_selection: string;
  fallback_behavior: string;
  cache_ttl_seconds: number;
}

interface ValidationResult {
  valid: boolean;
  exists: boolean;
  loading: boolean;
  title?: string;
  userInput?: string;
  createdAt?: string;
  analysisMode?: string;
}

export default function ShowcaseConfigPage() {
  const [config, setConfig] = useState<ShowcaseConfig>({
    session_ids: [],
    rotation_interval_seconds: 5,
    autoplay: true,
    loop: true,
    show_navigation: true,
    show_pagination: true,
    max_slides: 10,
    image_selection: "random",
    fallback_behavior: "skip",
    cache_ttl_seconds: 300,
  });

  const [validations, setValidations] = useState<Record<number, ValidationResult>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // 加载配置
  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setLoading(true);
    try {
      // 获取管理员token
      const token = localStorage.getItem('wp_jwt_token');
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

      const response = await axios.get("/api/admin/showcase/config", { headers });
      const loadedConfig = response.data;

      // 获取会话ID列表，如果为空则添加一个空项
      const sessionIds = loadedConfig.session_ids || [];
      if (sessionIds.length === 0) {
        sessionIds.push("");
      }

      setConfig({
        ...config,
        ...loadedConfig,
        session_ids: sessionIds,
      });

      console.log("配置加载成功:", loadedConfig);

      // 自动验证已存在的会话ID
      sessionIds.forEach((sessionId: string, index: number) => {
        if (sessionId && sessionId.trim()) {
          validateSessionId(index, sessionId);
        }
      });
    } catch (error) {
      console.error("加载配置失败:", error);
      toast.error("加载配置失败");
    } finally {
      setLoading(false);
    }
  };

  // 验证单个会话ID
  const validateSessionId = async (index: number, sessionId: string) => {
    if (!sessionId.trim()) {
      setValidations(prev => ({
        ...prev,
        [index]: { valid: false, exists: false, loading: false }
      }));
      return;
    }

    setValidations(prev => ({
      ...prev,
      [index]: { valid: false, exists: false, loading: true }
    }));

    try {
      // 尝试获取会话信息
      const response = await axios.get(`/api/sessions/archived/${sessionId}`);
      const session = response.data;

      // 安全解析 session_data
      let sessionData = session.session_data;
      if (typeof sessionData === 'string') {
        try {
          sessionData = JSON.parse(sessionData);
        } catch (e) {
          console.error(`解析会话数据失败: ${sessionId}`, e);
          sessionData = {};
        }
      }

      // 如果 sessionData 不存在或为空，使用 session 本身
      if (!sessionData || typeof sessionData !== 'object') {
        sessionData = session;
      }

      setValidations(prev => ({
        ...prev,
        [index]: {
          valid: true,
          exists: true,
          loading: false,
          title: sessionData.display_name || sessionData.user_input?.substring(0, 50) || "未命名",
          userInput: sessionData.user_input || "",
          createdAt: sessionData.created_at || session.created_at || "",
          analysisMode: sessionData.analysis_mode || "normal"
        }
      }));
    } catch (error) {
      // 如果归档中不存在，尝试从活跃会话获取
      try {
        const response = await axios.get(`/api/sessions`);
        const sessions = response.data.sessions || [];
        const found = sessions.find((s: any) => s.session_id === sessionId);

        if (found) {
          setValidations(prev => ({
            ...prev,
            [index]: {
              valid: true,
              exists: true,
              loading: false,
              title: found.user_input?.substring(0, 50) || "未命名",
              userInput: found.user_input || "",
              createdAt: found.created_at || "",
              analysisMode: found.analysis_mode || "normal"
            }
          }));
        } else {
          setValidations(prev => ({
            ...prev,
            [index]: { valid: false, exists: false, loading: false }
          }));
        }
      } catch (error2) {
        setValidations(prev => ({
          ...prev,
          [index]: { valid: false, exists: false, loading: false }
        }));
      }
    }
  };

  // 处理输入变化
  const handleSessionIdChange = (index: number, value: string) => {
    const newSessionIds = [...config.session_ids];
    newSessionIds[index] = value;
    setConfig({ ...config, session_ids: newSessionIds });

    // 延迟验证（避免频繁请求）
    const timer = setTimeout(() => {
      validateSessionId(index, value);
    }, 500);

    return () => clearTimeout(timer);
  };

  // 添加新的会话ID输入框
  const handleAddSession = () => {
    if (config.session_ids.length >= 10) {
      toast.error("最多只能添加10个精选会话");
      return;
    }
    setConfig({ ...config, session_ids: [...config.session_ids, ""] });
  };

  // 删除指定的会话ID
  const handleRemoveSession = (index: number) => {
    if (config.session_ids.length <= 1) {
      toast.error("至少需要保留一个会话");
      return;
    }
    const newSessionIds = config.session_ids.filter((_, i) => i !== index);
    setConfig({ ...config, session_ids: newSessionIds });

    // 清除验证状态
    const newValidations = { ...validations };
    delete newValidations[index];
    // 重新索引剩余的验证状态
    const reindexedValidations: Record<number, ValidationResult> = {};
    Object.keys(newValidations).forEach(key => {
      const oldIndex = parseInt(key);
      if (oldIndex > index) {
        reindexedValidations[oldIndex - 1] = newValidations[oldIndex];
      } else {
        reindexedValidations[oldIndex] = newValidations[oldIndex];
      }
    });
    setValidations(reindexedValidations);
  };

  // 保存配置
  const handleSave = async () => {
    setSaving(true);
    try {
      // 过滤空的会话ID
      const filteredSessionIds = config.session_ids.filter(id => id.trim() !== "");

      if (filteredSessionIds.length === 0) {
        toast.error("请至少添加一个会话ID");
        setSaving(false);
        return;
      }

      // 获取管理员token
      const token = localStorage.getItem('wp_jwt_token');
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

      console.log("保存配置:", {
        ...config,
        session_ids: filteredSessionIds,
      });

      const response = await axios.post("/api/admin/showcase/config", {
        ...config,
        session_ids: filteredSessionIds,
      }, { headers });

      console.log("保存响应:", response.data);

      toast.success(`配置保存成功！已配置 ${filteredSessionIds.length} 个精选会话`);

      // 重新加载配置以确认
      await loadConfig();
    } catch (error: any) {
      console.error("保存配置失败:", error);
      console.error("错误详情:", error.response?.data);
      toast.error(error.response?.data?.detail || "保存配置失败");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-5xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-3">精选展示配置</h1>
        <p className="text-base text-gray-600">
          设置首页幻灯片轮播展示的精选会话（最多10个）
        </p>
      </div>

      {/* 会话ID输入区 */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-1">精选会话列表</h2>
            <p className="text-sm text-gray-500">
              当前已添加 <span className="font-semibold text-blue-600">{config.session_ids.length}</span> / 10 个会话
            </p>
          </div>
          <button
            onClick={handleAddSession}
            disabled={config.session_ids.length >= 10}
            className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-sm font-semibold transition-all shadow-sm hover:shadow"
          >
            + 添加会话
          </button>
        </div>
        <div className="space-y-5">
          {config.session_ids.map((sessionId, index) => (
            <div key={index} className="border-2 border-gray-200 rounded-lg p-5 hover:border-blue-300 hover:shadow-sm transition-all bg-gray-50">
              <div className="flex items-start gap-4">
                <div className="flex items-center justify-center w-8 h-8 bg-blue-100 text-blue-700 font-bold rounded-full flex-shrink-0 mt-1">
                  {index + 1}
                </div>
                <div className="flex-1">
                  <div className="flex gap-3 mb-3">
                    <input
                      type="text"
                      value={sessionId}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => handleSessionIdChange(index, e.target.value)}
                      placeholder="输入会话ID（例如：8pdwoxj8-20260103181555-163e0ad3）"
                      className="flex-1 border-2 border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm bg-white placeholder:text-gray-500 placeholder:font-medium"
                    />
                    <button
                      onClick={() => handleRemoveSession(index)}
                      disabled={config.session_ids.length <= 1}
                      className="px-4 py-2.5 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-all border-2 border-red-200 hover:border-red-300 disabled:border-gray-200"
                      title="删除此会话"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  {/* 验证状态和内容摘要 */}
                  {validations[index]?.loading && (
                    <div className="flex items-center gap-2 text-sm text-gray-500 mt-2">
                      <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                      <span>验证中...</span>
                    </div>
                  )}

                  {validations[index]?.exists && !validations[index]?.loading && (
                    <div className="bg-green-50 border border-green-200 rounded-md p-4 mt-2">
                      <div className="flex items-start gap-3">
                        <Check className="w-5 h-5 text-green-600 flex-shrink-0 mt-1" />
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-base text-green-900 mb-2 leading-snug">
                            {validations[index]?.title}
                          </div>
                          {validations[index]?.userInput && (
                            <div className="text-sm text-gray-700 mb-3 leading-relaxed overflow-hidden" style={{
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical' as any,
                            }}>
                              {validations[index].userInput}
                            </div>
                          )}
                          <div className="flex flex-wrap gap-3 text-xs">
                            {validations[index]?.createdAt && (
                              <span className="text-gray-600 font-medium">
                                📅 {new Date(validations[index].createdAt!).toLocaleString('zh-CN', {
                                  year: 'numeric',
                                  month: '2-digit',
                                  day: '2-digit',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })}
                              </span>
                            )}
                            {validations[index]?.analysisMode && (
                              <span className="px-2.5 py-1 bg-blue-100 text-blue-800 rounded-md font-medium">
                                {validations[index].analysisMode === 'normal' ? '标准模式' :
                                 validations[index].analysisMode === 'chat' ? '对话模式' :
                                 validations[index].analysisMode}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {validations[index]?.valid === false &&
                   !validations[index]?.loading &&
                   sessionId.trim() !== "" && (
                    <div className="bg-red-50 border border-red-200 rounded-md p-3 mt-2">
                      <div className="flex items-center gap-2">
                        <X className="w-5 h-5 text-red-500" />
                        <span className="text-sm text-red-600">会话不存在或已被删除</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 轮播设置 */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6 mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-5">轮播设置</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-bold text-gray-800 mb-2">
              切换间隔（秒）
            </label>
            <input
              type="number"
              value={config.rotation_interval_seconds}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setConfig({
                  ...config,
                  rotation_interval_seconds: parseInt(e.target.value) || 5,
                })
              }
              min={1}
              max={30}
              className="w-full border-2 border-gray-300 rounded-lg px-4 py-2.5 text-base font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-bold text-gray-800 mb-2">
              图片选择策略
            </label>
            <select
              value={config.image_selection}
              onChange={(e) =>
                setConfig({ ...config, image_selection: e.target.value })
              }
              className="w-full border-2 border-gray-300 rounded-lg px-4 py-2.5 text-base font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              <option value="random">随机选择</option>
              <option value="first">第一张</option>
              <option value="latest">最新生成</option>
            </select>
          </div>
        </div>

        <div className="mt-6 space-y-3">
          <label className="flex items-center gap-3 cursor-pointer hover:bg-gray-50 p-2 rounded-lg transition-colors">
            <input
              type="checkbox"
              checked={config.autoplay}
              onChange={(e) =>
                setConfig({ ...config, autoplay: e.target.checked })
              }
              className="w-5 h-5 text-blue-600 cursor-pointer"
            />
            <span className="text-base font-semibold text-gray-800">自动播放</span>
          </label>
          <label className="flex items-center gap-3 cursor-pointer hover:bg-gray-50 p-2 rounded-lg transition-colors">
            <input
              type="checkbox"
              checked={config.loop}
              onChange={(e) => setConfig({ ...config, loop: e.target.checked })}
              className="w-5 h-5 text-blue-600 cursor-pointer"
            />
            <span className="text-base font-semibold text-gray-800">循环播放</span>
          </label>
          <label className="flex items-center gap-3 cursor-pointer hover:bg-gray-50 p-2 rounded-lg transition-colors">
            <input
              type="checkbox"
              checked={config.show_navigation}
              onChange={(e) =>
                setConfig({ ...config, show_navigation: e.target.checked })
              }
              className="w-5 h-5 text-blue-600 cursor-pointer"
            />
            <span className="text-base font-semibold text-gray-800">显示导航按钮</span>
          </label>
          <label className="flex items-center gap-3 cursor-pointer hover:bg-gray-50 p-2 rounded-lg transition-colors">
            <input
              type="checkbox"
              checked={config.show_pagination}
              onChange={(e) =>
                setConfig({ ...config, show_pagination: e.target.checked })
              }
              className="w-5 h-5 text-blue-600 cursor-pointer"
            />
            <span className="text-base font-semibold text-gray-800">显示分页指示器</span>
          </label>
        </div>
      </div>

      {/* 提示信息 */}
      <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-5 mb-6 flex gap-4">
        <AlertCircle className="w-6 h-6 text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-blue-900">
          <p className="font-bold mb-2 text-base">使用说明：</p>
          <ul className="list-disc list-inside space-y-1">
            <li>输入会话ID后会自动验证是否存在</li>
            <li>系统会自动从会话中提取概念图作为幻灯片背景</li>
            <li>配置保存后立即生效，无需重启服务</li>
            <li>只有包含概念图的会话才会显示在幻灯片中</li>
          </ul>
        </div>
      </div>

      {/* 保存按钮 */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="min-w-[140px] bg-blue-600 text-white px-8 py-3.5 rounded-lg font-bold text-base hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center shadow-md hover:shadow-lg transition-all"
        >
          {saving ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              保存中...
            </>
          ) : (
            <>
              <Save className="w-4 h-4 mr-2" />
              保存配置
            </>
          )}
        </button>
      </div>
    </div>
  );
}
