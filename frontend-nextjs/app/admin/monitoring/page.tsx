'use client';

import { useState, useEffect } from 'react';

export default function MonitoringPage() {
  const grafanaUrl = process.env.NEXT_PUBLIC_GRAFANA_URL || 'http://localhost:3200';
  const [isGrafanaAvailable, setIsGrafanaAvailable] = useState<boolean | null>(null);
  const [isChecking, setIsChecking] = useState(true);

  // 检测 Grafana 服务是否可用
  useEffect(() => {
    const checkGrafana = async () => {
      try {
        const response = await fetch(`${grafanaUrl}/api/health`, {
          method: 'GET',
          mode: 'no-cors', // 避免 CORS 错误
        });
        // no-cors 模式下无法读取响应，但能检测连接
        setIsGrafanaAvailable(true);
      } catch (error) {
        setIsGrafanaAvailable(false);
      } finally {
        setIsChecking(false);
      }
    };

    checkGrafana();
    // 每 30 秒检测一次
    const interval = setInterval(checkGrafana, 30000);
    return () => clearInterval(interval);
  }, [grafanaUrl]);

  // Dashboard 配置
  const dashboards = [
    {
      name: 'API 性能监控',
      url: `${grafanaUrl}/d-solo/api-perf/api-performance?orgId=1&panelId=1&refresh=10s&from=now-1h&to=now&theme=light`,
      description: '实时监控 API 响应时间、请求量、错误率'
    },
    {
      name: 'LLM 调用统计',
      url: `${grafanaUrl}/d-solo/llm-stats/llm-statistics?orgId=1&panelId=1&refresh=30s&from=now-6h&to=now&theme=light`,
      description: '跟踪 LLM 调用次数、Token 消耗、成本统计'
    }
  ];

  return (
    <div className="space-y-6 p-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">📊 系统监控</h1>
          <p className="text-sm text-gray-500 mt-1">基于 Grafana + Loki 的日志聚合与可视化</p>
        </div>
        {!isChecking && (
          <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
            isGrafanaAvailable
              ? 'bg-green-100 text-green-800'
              : 'bg-red-100 text-red-800'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              isGrafanaAvailable ? 'bg-green-600 animate-pulse' : 'bg-red-600'
            }`} />
            <span className="font-semibold text-sm">
              {isGrafanaAvailable ? 'Grafana 在线' : 'Grafana 离线'}
            </span>
          </div>
        )}
      </div>

      {/* Grafana 服务状态提示 */}
      {isChecking ? (
        <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-8 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">正在检测 Grafana 服务...</p>
        </div>
      ) : !isGrafanaAvailable ? (
        <div className="bg-gradient-to-br from-red-50 to-orange-50 rounded-xl shadow-lg border-2 border-red-300 p-8">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0">
              <div className="w-16 h-16 bg-red-500 rounded-full flex items-center justify-center">
                <span className="text-3xl text-white">⚠️</span>
              </div>
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-red-900 mb-3">Grafana 服务未启动</h2>
              <p className="text-red-800 mb-4 leading-relaxed">
                监控面板需要 Grafana 服务支持。请按以下步骤启动服务：
              </p>

              <div className="bg-white rounded-lg p-5 mb-4 border-2 border-red-200">
                <h3 className="font-bold text-gray-900 mb-3 flex items-center gap-2">
                  <span className="bg-red-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-sm">1</span>
                  启动 Docker 服务
                </h3>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-sm font-mono">
{`cd docker
docker-compose -f docker-compose.logging.yml up -d`}
                </pre>
              </div>

              <div className="bg-white rounded-lg p-5 mb-4 border-2 border-red-200">
                <h3 className="font-bold text-gray-900 mb-3 flex items-center gap-2">
                  <span className="bg-red-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-sm">2</span>
                  验证服务状态
                </h3>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-sm font-mono">
{`docker ps | findstr grafana
# 应该看到 grafana 容器正在运行，端口 0.0.0.0:3200->3000/tcp`}
                </pre>
              </div>

              <div className="bg-white rounded-lg p-5 border-2 border-red-200">
                <h3 className="font-bold text-gray-900 mb-3 flex items-center gap-2">
                  <span className="bg-red-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-sm">3</span>
                  刷新此页面
                </h3>
                <p className="text-gray-700 mb-3">服务启动后，刷新页面即可看到监控面板。</p>
                <button
                  onClick={() => window.location.reload()}
                  className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-all font-semibold shadow-md"
                >
                  🔄 刷新页面
                </button>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-6 border-t-2 border-red-200">
            <details className="text-left">
              <summary className="cursor-pointer font-semibold text-red-900 hover:text-red-700 transition-colors">
                💡 查看完整配置说明
              </summary>
              <div className="mt-4 bg-white rounded-lg p-4 border border-red-200">
                <p className="text-sm text-gray-700 mb-2">
                  <strong>docker-compose.logging.yml 已包含以下配置：</strong>
                </p>
                <pre className="bg-gray-100 p-3 rounded text-xs overflow-x-auto">
{`environment:
  - GF_AUTH_ANONYMOUS_ENABLED=true
  - GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer
  - GF_SECURITY_ALLOW_EMBEDDING=true
  - GF_SECURITY_X_FRAME_OPTIONS=SAMEORIGIN`}
                </pre>
                <p className="text-xs text-gray-600 mt-2">
                  ✅ 匿名访问已启用，无需修改配置文件
                </p>
              </div>
            </details>
          </div>
        </div>
      ) : (
        <>
          {/* 配置说明卡片（成功状态） */}
          <div className="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-300 rounded-xl p-5 shadow-md">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center">
                <span className="text-white font-bold">✓</span>
              </div>
              <h3 className="font-bold text-green-900 text-lg">服务运行正常</h3>
            </div>
            <p className="text-sm text-green-800 ml-11">
              Grafana 服务已启动，匿名访问和 iframe 嵌入已启用
            </p>
          </div>

          {/* Dashboard 卡片 */}
          <div className="space-y-6">
            {dashboards.map((dashboard, index) => (
              <div key={index} className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200">
                  <h2 className="text-xl font-bold text-gray-900">{dashboard.name}</h2>
                  <p className="text-sm text-gray-600 mt-1">{dashboard.description}</p>
                </div>
                <div className="p-2 bg-gray-50">
                  <iframe
                    src={dashboard.url}
                    width="100%"
                    height="600"
                    frameBorder="0"
                    className="w-full rounded-lg bg-white"
                    title={dashboard.name}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* 访问完整 Grafana */}
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-300 rounded-xl p-6 shadow-md">
            <h3 className="font-bold text-blue-900 mb-3 text-lg">🔗 访问完整 Grafana UI</h3>
            <p className="text-sm text-blue-800 mb-4">
              在 Grafana 中可以自定义 Dashboard、查询日志、配置告警规则等高级功能
            </p>
            <a
              href={grafanaUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all font-semibold shadow-md hover:shadow-lg"
            >
              <span>打开 Grafana</span>
              <span className="text-xs opacity-80">(admin / admin123)</span>
              <span className="text-lg">→</span>
            </a>
          </div>
        </>
      )}
    </div>
  );
}
