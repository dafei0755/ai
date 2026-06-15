'use client';

import { useRouter } from 'next/navigation';

const APP_AUTH_TOKEN_KEY = 'app_auth_token';
const APP_AUTH_USER_KEY = 'app_auth_user';

const DEV_USER = {
  user_id: 9999,
  username: 'dev_user',
  name: '开发测试用户',
  display_name: '开发测试用户',
  email: 'dev@localhost',
  roles: ['administrator'],
  tier: 'enterprise',
};

export default function LoginPage() {
  const router = useRouter();

  const handleDevelopmentLogin = () => {
    localStorage.setItem(APP_AUTH_TOKEN_KEY, 'dev-token-mock');
    localStorage.setItem(APP_AUTH_USER_KEY, JSON.stringify(DEV_USER));
    window.dispatchEvent(new Event('app-auth-updated'));
    router.push('/');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center p-4">
      <div className="w-full max-w-md rounded-xl border border-white/10 bg-white/5 p-8 shadow-2xl">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold mb-2">方案高参登录</h1>
          <p className="text-sm text-slate-300">
            独立账号、会员、付费和权限系统正在建设中。当前本地环境可使用开发账号进入系统。
          </p>
        </div>
        <button
          onClick={handleDevelopmentLogin}
          className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
        >
          使用开发账号进入
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
