'use client';

import { useEffect } from 'react';
import { AlertTriangle, RefreshCcw } from 'lucide-react';

export default function AnalysisError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[analysis/[sessionId]] render failed:', error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#111111] px-6 text-white">
      <div className="w-full max-w-lg rounded-3xl border border-white/10 bg-white/5 p-8 shadow-[0_24px_60px_rgba(0,0,0,0.35)] backdrop-blur-sm">
        <div className="flex items-center gap-3 text-white">
          <div className="rounded-2xl bg-amber-400/14 p-3 text-amber-300">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">分析页加载失败</h1>
            <p className="mt-1 text-sm text-white/68">已拦截页面异常，避免直接白屏。</p>
          </div>
        </div>

        <div className="mt-6 rounded-2xl border border-white/8 bg-black/20 p-4 text-sm text-white/72">
          <p className="leading-6">{error.message || '未知错误'}</p>
          {error.digest ? <p className="mt-2 text-xs text-white/40">digest: {error.digest}</p> : null}
        </div>

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={reset}
            className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-medium text-black transition hover:bg-white/90"
          >
            <RefreshCcw className="h-4 w-4" />
            重试
          </button>
          <a
            href="/"
            className="inline-flex items-center rounded-full border border-white/14 px-4 py-2 text-sm font-medium text-white/78 transition hover:bg-white/8"
          >
            返回首页
          </a>
        </div>
      </div>
    </div>
  );
}
