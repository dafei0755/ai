import React from 'react';
import type { GeoThesis } from '@/types/geo';
import { Compass, Users, GitMerge, MessageSquare, Hexagon, AlertTriangle, PlayCircle } from 'lucide-react';

interface GeoThesisCardProps {
  thesis: GeoThesis;
  loading?: boolean;
}

export function GeoThesisCard({ thesis, loading = false }: GeoThesisCardProps) {
  if (loading) {
    return (
      <div className="p-4 bg-white border border-slate-200 animate-pulse space-y-4">
        <div className="h-6 bg-slate-200/50 w-1/2 mb-6"></div>
        <div className="space-y-3">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-24 bg-slate-200/50"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!thesis) return null;

  return (
    <div className="bg-white border border-slate-200 overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 bg-slate-50">
        <div className="flex flex-col gap-3">
          <div className="flex items-start gap-3">
            <div className="shrink-0 p-2 bg-blue-600">
              <Compass className="w-5 h-5 text-white" />
            </div>
            <div className="min-w-0">
              <h3 className="text-base font-bold text-slate-900 leading-tight">
                G4 地点商业命题
              </h3>
              <p className="text-xs font-medium text-slate-500 mt-1 leading-5">
                {thesis.site_type} · {thesis.core_assets.join(' · ')}
              </p>
            </div>
          </div>
          <div className="w-fit border border-indigo-100 bg-indigo-50 px-2 py-1 text-[10px] font-bold uppercase tracking-widest text-indigo-600">
            CONFIRMED
          </div>
        </div>
      </div>

      {/* Body Content */}
      <div className="p-4 flex-1 overflow-y-auto custom-scrollbar space-y-4">
        
        {/* Section 1: Demand Catchment */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-slate-700 font-semibold text-sm">
            <Users className="w-4 h-4 text-blue-500" />
            <h4>需求捕获</h4>
          </div>
          <div className="p-3 bg-blue-50/50 border border-blue-100/50 text-xs leading-5 space-y-2">
            <p><span className="text-slate-500 mr-2">核心客群:</span> <span className="font-medium text-slate-800">{thesis.demand_catchment?.primary_persona}</span></p>
            <p><span className="text-slate-500 mr-2">出行心智:</span> <span className="text-slate-700">{thesis.demand_catchment?.travel_motivation}</span></p>
            <p><span className="text-slate-500 mr-2">付费意愿:</span> <span className="text-slate-700">{thesis.demand_catchment?.willingness_to_pay}</span></p>
          </div>
        </div>

        {/* Section 2: Substitution Summary */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-slate-700 font-semibold text-sm">
            <GitMerge className="w-4 h-4 text-purple-500" />
            <h4>竞争与替代方案</h4>
          </div>
          <div className="grid grid-cols-1 gap-3">
             <div className="p-3 bg-white border border-slate-200 text-xs leading-5">
               <span className="text-xs text-slate-400 block mb-1 uppercase font-bold tracking-wider">直接竞品</span>
               <div className="flex flex-wrap gap-1">
                 {thesis.substitution_summary?.direct_competitors?.map((c, i) => (
                   <span key={i} className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs">{c}</span>
                 )) || <span className="text-slate-400 italic">暂无信息</span>}
               </div>
             </div>
             <div className="p-3 bg-white border border-slate-200 text-xs leading-5">
               <span className="text-xs text-slate-400 block mb-1 uppercase font-bold tracking-wider">跨品类替代</span>
               <div className="flex flex-wrap gap-1">
                 {thesis.substitution_summary?.cross_category_alternatives?.map((c, i) => (
                   <span key={i} className="px-2 py-0.5 bg-purple-50 text-purple-600 text-xs">{c}</span>
                 )) || <span className="text-slate-400 italic">暂无信息</span>}
               </div>
             </div>
          </div>
        </div>

        {/* Section 3: Value Opportunities (Review Signals) */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-slate-700 font-semibold text-sm">
            <MessageSquare className="w-4 h-4 text-emerald-500" />
            <h4>用户体验套利空间</h4>
          </div>
          <ul className="space-y-1.5 p-3 bg-emerald-50/40 border border-emerald-100/50">
            {thesis.review_signals_summary?.experience_gap_opportunities?.map((opp, idx) => (
              <li key={idx} className="text-sm flex items-start gap-2 text-slate-700">
                <span className="text-emerald-500 font-bold mt-0.5">•</span>
                <span>{opp}</span>
              </li>
            ))}
          </ul>
        </div>
        
        {/* Section 4: Design Leverage & Commands */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-slate-700 font-semibold text-sm">
            <Hexagon className="w-4 h-4 text-amber-500" />
            <h4>G5 设计指令 (Design Commands)</h4>
          </div>
          <div className="p-3 bg-amber-50/40 border border-amber-200/50 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-2 opacity-10">
              <PlayCircle className="w-12 h-12" />
            </div>
            
            <div className="mb-3">
               <span className="text-xs text-amber-600/80 block mb-1 uppercase font-bold tracking-wider">高优发力节点</span>
               <div className="flex flex-wrap gap-1.5">
                 {thesis.design_leverage_nodes?.map((node, i) => (
                   <span key={i} className="px-2 py-1 bg-white border border-amber-200 text-amber-700 font-medium text-xs">{node}</span>
                 ))}
               </div>
            </div>
            
            {thesis.design_commands && Object.entries(thesis.design_commands).length > 0 && (
              <div className="space-y-2 mt-3">
                <span className="text-xs text-amber-600/80 block uppercase font-bold tracking-wider">具体指令</span>
                {Object.entries(thesis.design_commands).map(([key, commands], i) => (
                  <div key={key} className="text-sm">
                    <span className="font-semibold text-slate-800 bg-amber-100/50 px-1.5 py-0.5 capitalize">{key}</span>
                    <ul className="mt-1 space-y-1 pl-1">
                      {(commands as string[]).map((cmd, j) => (
                        <li key={j} className="flex items-start gap-2 text-slate-700 text-xs">
                          <span className="text-amber-500 mt-0.5">›</span>
                          <span>{cmd}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Risks */}
        {thesis.commercial_risks && thesis.commercial_risks.length > 0 && (
          <div className="pt-2">
            <div className="flex gap-2 p-3 bg-rose-50/50 border border-rose-100/50 items-start">
              <AlertTriangle className="w-4 h-4 text-rose-500 mt-0.5 shrink-0" />
              <div className="text-sm">
                <span className="text-rose-800 font-semibold block mb-1">关键商业风险</span>
                <ul className="space-y-1">
                  {thesis.commercial_risks.map((risk, idx) => (
                    <li key={idx} className="text-rose-600/90 text-xs list-disc ml-3">{risk}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
