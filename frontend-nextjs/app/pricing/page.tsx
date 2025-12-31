'use client';

/**
 * 会员套餐页面
 * 显示所有会员等级对比和升级选项
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Crown, Check, Zap, Star, ArrowRight } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface MembershipInfo {
  level: number;
  level_name: string;
  expire_date: string;
  is_expired: boolean;
  wallet_balance: number;
}

interface PricingTier {
  id: number;
  name: string;
  level_name: string;
  description: string;
  monthlyPrice: number;
  yearlyPrice: number;
  features: string[];
  icon: typeof Crown;
  color: string;
  gradient: string;
  popular?: boolean;
}

const pricingTiers: PricingTier[] = [
  {
    id: 1,
    name: '普通会员',
    level_name: '普通会员',
    description: '适合个人设计师和小型项目',
    monthlyPrice: 450,
    yearlyPrice: 3800,
    features: [
      '每月10次AI分析',
      '基础项目报告',
      '标准响应速度',
      '邮件支持',
      '7天历史记录',
    ],
    icon: Crown,
    color: 'text-blue-400',
    gradient: 'from-blue-500 to-cyan-600',
  },
  {
    id: 2,
    name: '超级会员',
    level_name: '超级会员',
    description: '适合设计团队和中型项目',
    monthlyPrice: 1180,
    yearlyPrice: 9800,
    features: [
      '每月50次AI分析',
      '深度项目洞察',
      '优先响应速度',
      '专属客服支持',
      '30天历史记录',
      '团队协作功能',
      'PDF报告导出',
    ],
    icon: Zap,
    color: 'text-purple-400',
    gradient: 'from-purple-500 to-pink-600',
    popular: true,
  },  
];

export default function PricingPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [currentMembership, setCurrentMembership] = useState<MembershipInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('yearly');

  useEffect(() => {
    if (!user) {
      // 未登录，跳转到主页
      router.push('/');
      return;
    }

    // 获取当前会员信息
    fetchCurrentMembership();
  }, [user, router]);

  const fetchCurrentMembership = async () => {
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const token = localStorage.getItem('wp_jwt_token');

      if (!token) {
        setLoading(false);
        return;
      }

      const response = await fetch(`${API_URL}/api/member/my-membership`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setCurrentMembership(data);
      }
    } catch (error) {
      console.error('获取会员信息失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = (tierId: number) => {
    // 跳转到设计知外官网续费/升级页面
    const wpUrl = 'https://www.ucppt.com/account/orders-list';
    window.open(wpUrl, '_blank');
  };

  const getPrice = (tier: PricingTier) => {
    return billingCycle === 'monthly' ? tier.monthlyPrice : tier.yearlyPrice;
  };

  const getSavings = (tier: PricingTier) => {
    const monthlyCost = tier.monthlyPrice * 12;
    const yearlyCost = tier.yearlyPrice;
    const savings = monthlyCost - yearlyCost;
    const percentage = Math.round((savings / monthlyCost) * 100);
    return { amount: savings, percentage };
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--background)] flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--background)] py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          {/* Current Membership Badge - 置顶显示 */}
          {currentMembership && currentMembership.level > 0 && (
            <div className="inline-flex items-center space-x-2 px-6 py-3 bg-green-500/10 border border-green-500/20 rounded-full mb-8 shadow-lg">
              <Crown className="w-5 h-5 text-green-500" />
              <span className="text-base font-semibold text-green-500">
                当前套餐: {currentMembership.level_name}
              </span>
              {currentMembership.expire_date && (
                <span className="text-sm text-[var(--foreground-secondary)]">
                  • 有效期至 {new Date(currentMembership.expire_date).toLocaleDateString('zh-CN')}
                </span>
              )}
            </div>
          )}

          <h1 className="text-4xl font-bold text-[var(--foreground)] mb-4">
            选择适合您的会员套餐
          </h1>
          <p className="text-lg text-[var(--foreground-secondary)] mb-8">
            专业的AI设计分析工具，助力您的设计项目成功
          </p>

          {/* Billing Cycle Toggle */}
          <div className="mt-8 inline-flex items-center space-x-4 bg-[var(--card-bg)] rounded-full p-1.5 border border-[var(--border-color)]">
            <button
              onClick={() => setBillingCycle('monthly')}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${
                billingCycle === 'monthly'
                  ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg'
                  : 'text-[var(--foreground-secondary)] hover:text-[var(--foreground)]'
              }`}
            >
              月付
            </button>
            <button
              onClick={() => setBillingCycle('yearly')}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all relative ${
                billingCycle === 'yearly'
                  ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg'
                  : 'text-[var(--foreground-secondary)] hover:text-[var(--foreground)]'
              }`}
            >
              年付
              {billingCycle === 'yearly' && (
                <span className="absolute -top-2 -right-2 bg-gradient-to-r from-amber-500 to-orange-600 text-white text-xs px-2 py-0.5 rounded-full">
                  省30%+
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto mb-12">
          {pricingTiers.map((tier) => {
            const Icon = tier.icon;
            const price = getPrice(tier);
            const savings = getSavings(tier);
            const isCurrentPlan = currentMembership?.level === tier.id;
            const canUpgrade = !currentMembership || currentMembership.level < tier.id;

            return (
              <div
                key={tier.id}
                className={`relative bg-[var(--card-bg)] rounded-2xl p-8 border transition-all hover:shadow-2xl ${
                  tier.popular
                    ? 'border-purple-500 shadow-lg shadow-purple-500/20'
                    : 'border-[var(--border-color)]'
                }`}
              >
                {/* Popular Badge */}
                {tier.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <div className="bg-gradient-to-r from-purple-500 to-pink-600 text-white text-xs font-bold px-4 py-1.5 rounded-full shadow-lg">
                      最受欢迎
                    </div>
                  </div>
                )}

                {/* Current Plan Badge */}
                {isCurrentPlan && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <div className="bg-gradient-to-r from-green-500 to-emerald-600 text-white text-xs font-bold px-4 py-1.5 rounded-full shadow-lg">
                      当前套餐
                    </div>
                  </div>
                )}

                {/* Icon */}
                <div className={`inline-flex p-3 rounded-xl bg-gradient-to-r ${tier.gradient} bg-opacity-10 mb-6`}>
                  <Icon className={`w-8 h-8 ${tier.color}`} />
                </div>

                {/* Title */}
                <h3 className="text-2xl font-bold text-[var(--foreground)] mb-2">
                  {tier.level_name}
                </h3>
                <p className="text-sm text-[var(--foreground-secondary)] mb-6">
                  {tier.description}
                </p>

                {/* Price */}
                <div className="mb-6">
                  <div className="flex items-baseline">
                    <span className="text-4xl font-bold text-[var(--foreground)]">
                      ¥{price}
                    </span>
                    <span className="text-[var(--foreground-secondary)] ml-2">
                      / {billingCycle === 'monthly' ? '月' : '年'}
                    </span>
                  </div>
                  {billingCycle === 'yearly' && (
                    <p className="text-xs text-green-500 mt-2">
                      年付节省 ¥{savings.amount} ({savings.percentage}%)
                    </p>
                  )}
                </div>

                {/* Features */}
                <ul className="space-y-3 mb-8">
                  {tier.features.map((feature, index) => (
                    <li key={index} className="flex items-start">
                      <Check className="w-5 h-5 text-green-500 mr-3 flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-[var(--foreground-secondary)]">
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>

                {/* CTA Button */}
                <button
                  onClick={() => handleUpgrade(tier.id)}
                  disabled={isCurrentPlan}
                  className={`w-full py-3 px-6 rounded-lg font-semibold transition-all flex items-center justify-center space-x-2 ${
                    isCurrentPlan
                      ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                      : canUpgrade
                      ? `bg-gradient-to-r ${tier.gradient} text-white hover:shadow-lg hover:scale-105`
                      : 'bg-gray-700 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  {isCurrentPlan ? (
                    <span>当前套餐</span>
                  ) : canUpgrade ? (
                    <>
                      <span>{currentMembership && currentMembership.level > 0 ? '升级到' : '选择'}{tier.level_name}</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  ) : (
                    <span>已拥有更高等级</span>
                  )}
                </button>
              </div>
            );
          })}
        </div>

        {/* FAQ or Additional Info */}
        <div className="bg-[var(--card-bg)] rounded-2xl p-8 border border-[var(--border-color)]">
          <h2 className="text-2xl font-bold text-[var(--foreground)] mb-6">
            常见问题
          </h2>
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-[var(--foreground)] mb-2">
                如何升级会员？
              </h3>
              <p className="text-sm text-[var(--foreground-secondary)]">
                点击上方套餐卡片的"升级"按钮，系统会跳转到WordPress会员中心完成支付。升级后立即生效。
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-[var(--foreground)] mb-2">
                会员到期后会怎样？
              </h3>
              <p className="text-sm text-[var(--foreground-secondary)]">
                会员到期后，您的账户会自动降级为免费用户，但历史记录和数据会保留。您可以随时续费恢复会员权益。
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-[var(--foreground)] mb-2">
                支持哪些支付方式？
              </h3>
              <p className="text-sm text-[var(--foreground-secondary)]">
                我们支持支付宝、微信支付等主流支付方式。所有支付均通过WordPress安全支付网关处理。
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
