// components/report/ChallengeDetectionCard.tsx
// 挑战检测结果展示卡片

'use client';

import { FC, useState } from 'react';
import { AlertOctagon, AlertTriangle, ChevronDown, ChevronUp, ShieldCheck, Lightbulb, User } from 'lucide-react';
import { ChallengeDetection, ChallengeItem } from '@/types';

interface ChallengeDetectionCardProps {
  detection: ChallengeDetection;
}

// 挑战类型中文映射
const CHALLENGE_TYPE_MAP: Record<string, string> = {
  'reinterpret': '重新诠释',
  'flag_risk': '风险标记',
  'escalate': '升级处理',
  'question': '质疑',
  'alternative': '替代方案',
};

// 决策类型中文映射
const DECISION_MAP: Record<string, { label: string; color: string }> = {
  'accept': { label: '已采纳', color: 'text-green-400' },
  'synthesize': { label: '综合处理', color: 'text-blue-400' },
  'escalate': { label: '已升级', color: 'text-amber-400' },
  'pending': { label: '待处理', color: 'text-gray-400' },
};

// 🔥 v7.6: 使用统一的格式化函数
import { formatExpertName } from '@/lib/formatters';

const ChallengeItemCard: FC<{ challenge: ChallengeItem; index: number }> = ({ challenge, index }) => {
  const [expanded, setExpanded] = useState(false);
  const isMustFix = challenge.severity === 'must-fix';
  const decisionInfo = DECISION_MAP[challenge.decision] || DECISION_MAP['pending'];
  
  return (
    <div 
      className={`rounded-lg border ${
        isMustFix 
          ? 'border-red-500/30 bg-red-500/5' 
          : 'border-amber-500/30 bg-amber-500/5'
      }`}
    >
      {/* 头部 */}
      <div 
        className="p-4 cursor-pointer flex items-start justify-between gap-3"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start gap-3 flex-1">
          {/* 严重程度图标 */}
          <div className={`mt-0.5 ${isMustFix ? 'text-red-400' : 'text-amber-400'}`}>
            {isMustFix ? (
              <AlertOctagon className="w-5 h-5" />
            ) : (
              <AlertTriangle className="w-5 h-5" />
            )}
          </div>
          
          <div className="flex-1 min-w-0">
            {/* 标题行 */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                isMustFix 
                  ? 'bg-red-500/20 text-red-400' 
                  : 'bg-amber-500/20 text-amber-400'
              }`}>
                {isMustFix ? '必须修复' : '建议修复'}
              </span>
              <span className="text-xs text-gray-500">
                {CHALLENGE_TYPE_MAP[challenge.challenge_type] || challenge.challenge_type}
              </span>
              {challenge.decision && (
                <span className={`text-xs ${decisionInfo.color}`}>
                  • {decisionInfo.label}
                </span>
              )}
            </div>
            
            {/* 质疑事项 */}
            <p className="text-sm text-gray-200 mt-1 font-medium">
              {challenge.challenged_item}
            </p>
            
            {/* 专家信息 */}
            <div className="flex items-center gap-1.5 mt-1.5 text-xs text-gray-500">
              <User className="w-3 h-3" />
              <span>{formatExpertName(challenge.expert_name || challenge.expert_id)}</span>
            </div>
          </div>
        </div>
        
        {/* 展开/收起 */}
        <button className="text-gray-500 hover:text-gray-300 transition-colors">
          {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
      </div>
      
      {/* 详情展开 */}
      {expanded && (
        <div className="px-4 pb-4 pt-0 space-y-3 border-t border-gray-700/50 mt-0">
          {/* 质疑理由 */}
          {challenge.rationale && (
            <div className="pt-3">
              <h4 className="text-xs font-medium text-gray-400 mb-1.5 flex items-center gap-1.5">
                <AlertTriangle className="w-3 h-3" />
                质疑理由
              </h4>
              <p className="text-sm text-gray-300 leading-relaxed">
                {challenge.rationale}
              </p>
            </div>
          )}
          
          {/* 建议替代方案 */}
          {challenge.proposed_alternative && (
            <div>
              <h4 className="text-xs font-medium text-gray-400 mb-1.5 flex items-center gap-1.5">
                <Lightbulb className="w-3 h-3" />
                建议替代方案
              </h4>
              <p className="text-sm text-gray-300 leading-relaxed">
                {challenge.proposed_alternative}
              </p>
            </div>
          )}
          
          {/* 设计影响 */}
          {challenge.design_impact && (
            <div>
              <h4 className="text-xs font-medium text-gray-400 mb-1.5 flex items-center gap-1.5">
                <ShieldCheck className="w-3 h-3" />
                对设计的影响
              </h4>
              <p className="text-sm text-gray-300 leading-relaxed">
                {challenge.design_impact}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const ChallengeDetectionCard: FC<ChallengeDetectionCardProps> = ({ detection }) => {
  const [showAll, setShowAll] = useState(false);
  
  if (!detection.has_challenges || detection.challenges.length === 0) {
    return null;
  }
  
  // 分离 must-fix 和 should-fix
  const mustFixChallenges = detection.challenges.filter(c => c.severity === 'must-fix');
  const shouldFixChallenges = detection.challenges.filter(c => c.severity === 'should-fix');
  
  // 默认只显示前3个
  const displayChallenges = showAll 
    ? detection.challenges 
    : detection.challenges.slice(0, 3);
  
  return (
    <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl p-6 space-y-5">
      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-orange-500/20 rounded-lg flex items-center justify-center">
            <AlertOctagon className="w-5 h-5 text-orange-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">挑战检测</h2>
            <p className="text-xs text-gray-500 mt-0.5">专家对需求分析的质疑与建议</p>
          </div>
        </div>
        
        {/* 统计徽章 */}
        <div className="flex items-center gap-2">
          {mustFixChallenges.length > 0 && (
            <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400 flex items-center gap-1">
              <AlertOctagon className="w-3 h-3" />
              {mustFixChallenges.length} 必须修复
            </span>
          )}
          {shouldFixChallenges.length > 0 && (
            <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/20 text-amber-400 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              {shouldFixChallenges.length} 建议修复
            </span>
          )}
        </div>
      </div>
      
      {/* 处理摘要 */}
      {detection.handling_summary && (
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
          <p className="text-sm text-blue-300">
            <span className="font-medium">处理摘要：</span>
            {detection.handling_summary}
          </p>
        </div>
      )}
      
      {/* 挑战列表 */}
      <div className="space-y-3">
        {displayChallenges.map((challenge, index) => (
          <ChallengeItemCard 
            key={`${challenge.expert_id}-${index}`} 
            challenge={challenge} 
            index={index}
          />
        ))}
      </div>
      
      {/* 展开更多 */}
      {detection.challenges.length > 3 && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="w-full py-2 text-sm text-gray-400 hover:text-gray-300 transition-colors flex items-center justify-center gap-1"
        >
          {showAll ? (
            <>
              <ChevronUp className="w-4 h-4" />
              收起
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              查看全部 {detection.challenges.length} 个挑战
            </>
          )}
        </button>
      )}
    </div>
  );
};

export default ChallengeDetectionCard;
