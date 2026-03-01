'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/** 已合并到「外部数据管理」页面，此页面自动跳转 */
export default function ExternalDataRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/admin/crawler-monitor'); }, [router]);
  return null;
}
