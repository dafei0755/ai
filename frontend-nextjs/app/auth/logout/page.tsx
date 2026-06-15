'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { LogOut } from 'lucide-react';

const APP_AUTH_TOKEN_KEY = 'app_auth_token';
const APP_AUTH_USER_KEY = 'app_auth_user';

export default function LogoutSuccessPage() {
  const router = useRouter();

  useEffect(() => {
    localStorage.removeItem(APP_AUTH_TOKEN_KEY);
    localStorage.removeItem(APP_AUTH_USER_KEY);
    window.dispatchEvent(new Event('app-auth-updated'));
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center p-4">
      <div className="w-full max-w-md rounded-xl border border-white/10 bg-white/5 p-8 text-center shadow-2xl">
        <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-orange-500/15">
          <LogOut className="h-8 w-8 text-orange-300" />
        </div>
        <h1 className="mb-2 text-2xl font-semibold">已退出</h1>
        <p className="mb-6 text-sm text-slate-300">当前本地登录状态已清除。</p>
        <button
          onClick={() => router.push('/auth/login')}
          className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
        >
          重新登录
        </button>
        <button
          onClick={() => router.push('/')}
          className="mt-3 w-full rounded-lg border border-white/10 px-4 py-3 text-sm text-slate-200 hover:bg-white/10 transition-colors"
        >
          返回首页
        </button>
      </div>
    </div>
  );
}
