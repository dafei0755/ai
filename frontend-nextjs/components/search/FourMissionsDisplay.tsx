'use client';

import React, { useState } from 'react';
import {
  FourMissions,
  Mission1UserProblemAnalysis,
  Mission2ClearObjectives,
  Mission3TaskDimensions,
  Mission4ExecutionRequirements,
  DeliverableItem,
  KeyStep,
  BreakthroughPoint
} from '@/types';
import {
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  User,
  Target,
  Lightbulb,
  AlertTriangle,
  MapPin,
  Ruler,
  Tag,
  Lock,
  Heart,
  Zap,
  Package,
  CheckCircle,
  Users,
  Layers,
  TrendingUp,
  Shield,
  XCircle,
  AlertCircle,
  Wrench
} from 'lucide-react';
import {
  formatMission1ToNaturalLanguage,
  formatMission2ToNaturalLanguage,
  formatMission3ToNaturalLanguage,
  formatMission4ToNaturalLanguage,
  formatAllMissionsToNaturalLanguage
} from '@/utils/missionFormatter';

interface FourMissionsDisplayProps {
  missions: FourMissions;
  className?: string;
}

interface MissionCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  children: React.ReactNode;
  defaultExpanded?: boolean;
}

const MissionCard: React.FC<MissionCardProps> = ({
  title,
  description,
  icon,
  color,
  children,
  defaultExpanded = true
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className={`border rounded-lg overflow-hidden ${color} bg-white shadow-sm`}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${color.replace('border-l-4', 'bg-opacity-10')}`}>
            {icon}
          </div>
          <div className="text-left">
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            <p className="text-sm text-gray-600">{description}</p>
          </div>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        )}
      </button>

      {isExpanded && (
        <div className="px-6 py-4 border-t bg-gray-50">
          {children}
        </div>
      )}
    </div>
  );
};

const InfoItem: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string | string[];
  color?: string;
}> = ({ icon, label, value, color = 'text-blue-600' }) => {
  const displayValue = Array.isArray(value) ? value.join(', ') : value;

  return (
    <div className="flex items-start gap-3 mb-3">
      <div className={`mt-0.5 ${color}`}>{icon}</div>
      <div className="flex-1">
        <span className="text-sm font-medium text-gray-700">{label}:</span>
        <p className="text-sm text-gray-900 mt-1">{displayValue}</p>
      </div>
    </div>
  );
};

export const FourMissionsDisplay: React.FC<FourMissionsDisplayProps> = ({
  missions,
  className = ''
}) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formattedContent = formatAllMissionsToNaturalLanguage(missions);

  return (
    <div className={`${className}`}>
      {/* 单一统一卡片：需求理解与深度分析 */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        {/* 卡片头部 */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-200 px-6 py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-blue-900 mb-1">需求理解与深度分析</h2>
              <p className="text-sm text-blue-700">{missions.creation_command}</p>
            </div>
            <button
              onClick={() => copyToClipboard(formattedContent)}
              className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-blue-300 rounded-lg hover:bg-blue-50 transition-colors"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4 text-green-600" />
                  <span className="text-green-600">已复制</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4 text-blue-600" />
                  <span className="text-blue-600">复制全部</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* 卡片内容：连续的自然语言 */}
        <div className="px-6 py-5">
          <div className="prose prose-sm max-w-none">
            <div
              className="text-gray-700 whitespace-pre-line leading-relaxed"
              dangerouslySetInnerHTML={{
                __html: formattedContent
                  .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                  .replace(/^# (.+)$/gm, '<h1 class="text-xl font-bold text-gray-900 mb-4">$1</h1>')
                  .replace(/^## (.+)$/gm, '<h2 class="text-lg font-semibold text-gray-800 mt-6 mb-3">$1</h2>')
                  .replace(/^---$/gm, '<hr class="my-4 border-gray-200" />')
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default FourMissionsDisplay;
