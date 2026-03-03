'use client';

/**
 * 会员信息卡片组件
 * v7.10.2: 移除余额显示，保持简洁
 * 显示用户的 WPCOM Member Pro 会员等级、到期时间
 */

import React, { useState, useEffect } from 'react';
import { Crown, Calendar, TrendingUp } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

interface MembershipInfo {
  level: number;
  level_name: string;
  expire_date: string;
  is_expired: boolean;
  wallet_balance: number;
}

// 🔧 v3.0.23优化：全局缓存会员信息，避免重复请求
let membershipCache: {
  data: MembershipInfo | null;
  timestamp: number;
  userId: number | null;
} = {
  data: null,
  timestamp: 0,
  userId: null
};

const CACHE_TTL = 60000; // 缓存60秒

export function MembershipCard() {
  const { user } = useAuth();
  const [membership, setMembership] = useState<MembershipInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }

    // 🔧 v3.0.23优化：检查缓存，避免重复请求
    const now = Date.now();
    const isCacheValid =
      membershipCache.data !== null &&
      membershipCache.userId === user.user_id &&
      (now - membershipCache.timestamp) < CACHE_TTL;

    if (isCacheValid) {
      console.log('[MembershipCard] 使用缓存的会员数据');
      setMembership(membershipCache.data);
      setLoading(false);
      return;
    }

    // 缓存失效，重新获取
    console.log('[MembershipCard] 缓存失效，重新获取会员数据');
    fetchMembershipInfo();
  }, [user]);

  const fetchMembershipInfo = async () => {
    try {
      setLoading(true);
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const token = localStorage.getItem('wp_jwt_token');

      if (!token || !user) {
        setLoading(false);
        return;  // 未登录时静默返回，不当作错误
      }

      const response = await fetch(`${API_URL}/api/member/my-membership`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('获取会员信息失败');
      }

      const data = await response.json();
      setMembership(data);
      setError(null);

      // 🔧 v3.0.23优化：更新缓存
      membershipCache = {
        data: data,
        timestamp: Date.now(),
        userId: user.user_id
      };
      console.log('[MembershipCard] 会员数据已缓存');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '获取会员信息失败';
      console.warn('获取会员信息失败:', message);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  if (!user) return null;

  if (loading) {
    return (
      <div className="px-3 py-4 border-t border-[var(--border-color)]">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-700 rounded w-1/2 mb-2"></div>
          <div className="h-3 bg-gray-700 rounded w-3/4"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-3 py-4 border-t border-[var(--border-color)]">
        <p className="text-xs text-red-500">{error}</p>
      </div>
    );
  }

  if (!membership) return null;

  // 会员等级颜色
  const getLevelColor = (level: number) => {
    switch (level) {
      case 0: return 'text-gray-400';
      case 1: return 'text-blue-400';
      case 2: return 'text-purple-400';
      case 3: return 'text-amber-400';
      default: return 'text-gray-400';
    };
  };

  // ✅ 直接使用后端返回的 level_name（不再硬编码）
  const levelColor = getLevelColor(membership.level);
  const levelBadge = membership.level_name || `VIP ${membership.level}`;

  return (
    <div className="px-3 py-4 border-t border-[var(--border-color)]">
      {/* 会员等级 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Crown className={`w-4 h-4 ${levelColor}`} />
          <span className={`text-sm font-semibold ${levelColor}`}>
            {levelBadge}
          </span>
        </div>
        {membership.level > 0 && !membership.is_expired && (
          <span className="px-2 py-0.5 text-xs bg-blue-500/10 text-blue-500 rounded">
            有效
          </span>
        )}
        {membership.is_expired && (
          <span className="px-2 py-0.5 text-xs bg-red-500/10 text-red-500 rounded">
            已过期
          </span>
        )}
      </div>

      {/* 会员信息 */}
      <div className="space-y-2">
        {/* 到期时间 */}
        {membership.level > 0 && membership.expire_date && (
          <div className="flex items-center space-x-2 text-xs text-[var(--foreground-secondary)]">
            <Calendar className="w-3.5 h-3.5" />
            <span>
              到期: {new Date(membership.expire_date).toLocaleDateString('zh-CN')}
            </span>
          </div>
        )}
      </div>

      {/* 升级按钮 */}
      {membership.level < 2 && (
        <button
          onClick={() => {
            // 跳转到套餐页面
            window.location.href = '/pricing';
          }}
          className="w-full mt-3 px-3 py-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white text-xs font-medium rounded-lg transition-all flex items-center justify-center space-x-1.5"
        >
          <TrendingUp className="w-3.5 h-3.5" />
          <span>升级会员</span>
        </button>
      )}
    </div>
  );
}
