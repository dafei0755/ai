import React from 'react';
import type { GeoScores } from '@/types/geo';
import { Target, MapPin, Activity, PenTool, Zap } from 'lucide-react';

interface GeoScorePanelProps {
  scores: GeoScores;
  loading?: boolean;
}

const scoreItems = [
  { key: 'place_viability', label: '地点商业成立度', icon: MapPin, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
  { key: 'geo_friction_index', label: '地理摩擦指数', icon: Activity, color: 'text-rose-500', bg: 'bg-rose-500/10', inverse: true },
  { key: 'experience_gap_index', label: '体验套利指数', icon: Target, color: 'text-indigo-500', bg: 'bg-indigo-500/10' },
  { key: 'design_leverage_score', label: '设计杠杆指数', icon: PenTool, color: 'text-amber-500', bg: 'bg-amber-500/10' },
  { key: 'geo_premium_score', label: '地理溢价能力', icon: Zap, color: 'text-violet-500', bg: 'bg-violet-500/10' },
];

export function GeoScorePanel({ scores, loading = false }: GeoScorePanelProps) {
  if (loading) {
    return (
      <div className="p-3 bg-white border border-slate-200 animate-pulse space-y-3">
        <div className="h-5 bg-slate-200/70 w-2/3 mb-3"></div>
        <div className="grid grid-cols-1 gap-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 bg-slate-200/50"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!scores) return null;

  return (
    <div className="p-3 bg-white border border-slate-200">
      <div className="flex items-start gap-2 mb-3">
        <div className="shrink-0 p-1.5 bg-indigo-600">
          <Zap className="w-4 h-4 text-white" />
        </div>
        <h3 className="min-w-0 text-sm font-semibold leading-5 text-slate-900">
          G3 地理商业智能评分 
          <span className="ml-1 inline-block border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-medium text-slate-500">Core Indices</span>
        </h3>
      </div>

      <div className="grid grid-cols-1 gap-2">
        {scoreItems.map((item) => {
          const val = scores[item.key as keyof GeoScores] || 0;
          const percentage = Math.min(100, Math.max(0, val));
          
          return (
            <div key={item.key} className="relative border border-slate-200 bg-slate-50 p-2">
              <div className="flex items-start gap-2">
                <div className={`shrink-0 p-1.5 ${item.bg}`}>
                  <item.icon className={`w-4 h-4 ${item.color}`} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-medium leading-4 text-slate-600">
                    {item.label}
                  </div>
                  <div className="mt-1 h-1 bg-slate-200 overflow-hidden">
                    <div 
                      className={`h-full ${item.inverse ? (val < 30 ? 'bg-emerald-400' : val > 70 ? 'bg-rose-400' : 'bg-amber-400') : item.color.replace('text-', 'bg-')}`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
                <div className="shrink-0 text-base font-semibold tabular-nums text-slate-900">
                  {val.toFixed(1)}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
