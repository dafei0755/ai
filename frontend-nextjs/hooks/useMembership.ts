/**
 * User Membership Hook
 *
 * Fetches and caches user membership information from WordPress API
 *
 * v7.141.3 - User Authentication Integration
 */

'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { mapVipLevelToTier, type QuotaTier } from '@/lib/tier-mapping';

interface MembershipData {
  level: number;  // WordPress VIP level (0-3)
  level_name: string;
  tier: QuotaTier;  // Quota tier
  expire_date: string;
  is_expired: boolean;
  wallet_balance: number;
}

export function useMembership() {
  const { user, isAuthenticated } = useAuth();
  const [membership, setMembership] = useState<MembershipData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated || !user) {
      // User not authenticated, default to free tier
      setMembership({
        level: 0,
        level_name: '免费用户',
        tier: 'free',
        expire_date: '',
        is_expired: false,
        wallet_balance: 0,
      });
      setLoading(false);
      return;
    }

    // Fetch membership data
    const fetchMembership = async () => {
      try {
        setLoading(true);
        const token = localStorage.getItem('wp_jwt_token');

        const response = await fetch('/api/member/my-membership', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error('Failed to fetch membership');
        }

        const data = await response.json();

        // Map to quota tier
        const tier = mapVipLevelToTier(data.level);

        setMembership({
          level: data.level,
          level_name: data.level_name,
          tier,
          expire_date: data.expire_date,
          is_expired: data.is_expired,
          wallet_balance: data.wallet_balance,
        });

        setError(null);
      } catch (err) {
        console.error('[useMembership] Error fetching membership:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');

        // Fallback to free tier
        setMembership({
          level: 0,
          level_name: '免费用户',
          tier: 'free',
          expire_date: '',
          is_expired: false,
          wallet_balance: 0,
        });
      } finally {
        setLoading(false);
      }
    };

    fetchMembership();
  }, [user, isAuthenticated]);

  return {
    membership,
    loading,
    error,
    // Convenience getters
    tier: membership?.tier || 'free',
    vipLevel: membership?.level || 0,
    displayName: membership?.level_name || '免费用户',
    isExpired: membership?.is_expired || false,
  };
}
