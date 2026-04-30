'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function AdminIndexPage() {
  const router = useRouter();

  useEffect(() => {
    // 重定向到仪表板
    router.push('/admin/dashboard');
  }, [router]);

  return (
    <div className="flex items-center justify-center h-64">
      <p className="text-gray-500">正在跳转到管理后台...</p>
    </div>
  );
}
