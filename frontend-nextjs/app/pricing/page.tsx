'use client';

import { ArrowLeft, ShieldCheck } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function PricingPage() {
  const router = useRouter();

  return (
    <main className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      <div className="mx-auto flex min-h-screen max-w-4xl flex-col justify-center px-6 py-16">
        <button
          type="button"
          onClick={() => router.push('/')}
          className="mb-8 inline-flex w-fit items-center gap-2 rounded-full border border-[var(--border-color)] px-4 py-2 text-sm text-[var(--foreground-secondary)] hover:text-[var(--foreground)]"
        >
          <ArrowLeft className="h-4 w-4" />
          返回首页
        </button>

        <section className="rounded-2xl border border-[var(--border-color)] bg-[var(--card-bg)] p-8 shadow-sm">
          <div className="mb-6 flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-white">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm text-[var(--foreground-secondary)]">独立会员系统</p>
              <h1 className="text-2xl font-bold">登录、付费、会员和权限管理正在独立建设</h1>
            </div>
          </div>

          <div className="space-y-4 text-sm leading-7 text-[var(--foreground-secondary)]">
            <p>
              方案高参已停止调用原 ucppt.com 会员信息。后续会使用独立的用户、订单、会员和权限系统。
            </p>
            <p>
              当前页面只作为过渡说明，不再展示旧会员套餐，也不会跳转到原站支付或会员中心。
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
