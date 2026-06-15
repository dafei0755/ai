import React from 'react';
import { useGeoStore } from '@/store/useGeoStore';
import { GeoScorePanel } from './GeoScorePanel';
import { GeoThesisCard } from './GeoThesisCard';
import { GeoAnchorCard } from './GeoAnchorCard';
import { Map, Play } from 'lucide-react';
import type { GeoThesis } from '@/types/geo';

export function GeoIntelligencePanel() {
  const { geoThesis, thesisLoading, openPicker, geoAnchor, setGeoThesis, setThesisLoading } = useGeoStore();

  const handleSimulateAI = () => {
    if (!geoAnchor) {
      alert("请先锁定地理位置(GeoAnchor)");
      return;
    }
    setThesisLoading(true);
    
    // 模拟网络请求与 AI 生成延时
    setTimeout(() => {
      const mockThesis: GeoThesis = {
        project_id: "mock_project_001",
        site_type: "目的地位的标杆型野奢酒店 / 疗愈中心",
        core_assets: ["稀缺绝版山景", "静谧原生林地", "高差落差"],
        demand_catchment: {
          primary_persona: "一二线城市高净值人群、高压疲劳的治愈系度假客",
          travel_motivation: "逃离城市喧嚣，寻找自然庇护所与极致的松弛感官体验",
          willingness_to_pay: "极高（2000-5000元/晚）",
          catchment_radius_desc: "3小时内高铁/自驾度假圈，辐射全国高净值隐客"
        },
        substitution_summary: {
          direct_competitors: ["周边同纬度的老牌精品民宿", "高端连锁康养村"],
          cross_category_alternatives: ["大理全包式高端营地", "三亚奢华度假酒店"],
          no_spend_alternatives: ["城市周边短暂露营", "由于没有合意选择而搁置出行"]
        },
        review_signals_summary: {
          top_praise: ["风景绝美震撼", "出片率极高", "私密性绝佳"],
          top_complaints: ["交通不便，最后一公里难走", "周边文旅配套匮乏", "餐饮体验单一"],
          experience_gap_opportunities: [
            "周边竞品餐饮乏味？引入定制化在地融合高级餐饮",
            "体验平淡？打造强落差的悬崖打卡装置",
            "到达感差？改善抵达前1公里的视觉铺垫与专属接驳体验"
          ]
        },
        design_leverage_nodes: ["到达落客庭院 (The Arrival)", "悬崖全景落日餐厅 (The Sunset Hub)", "客房独享景观露台 (The Private Halo)"],
        commercial_risks: ["淡旺季明显致使平季空置率陡增", "山地复杂施工导致成本及周期超预期风险", "后期设备与景观维护运营成本高昂"],
        design_commands: {
          must_do: [
            "必须在落客点处提供最震撼的无死角观景视线",
            "优先保证所有核心客房拥有270度的大横屏取景视野",
            "材料选择必须强化当地自然属性（如：原木、夯土、微水泥）"
          ],
          must_not: [
            "切忌使用阻断视线的高大混凝土实体围墙",
            "切忌存在明显的人工硬化铺装破坏原始地貌形态",
            "客房之间视线不可存在相互交叉与干扰"
          ],
          defer: ["先不深入探讨具体的庭院小品细分绿植，需优先确立整体建筑与地形的关系"]
        },
        validation_metrics: ["社交媒体首月核心打卡点分享量", "前两个季度日均入住率 > 65%", "非房费（餐饮/康养/体验）收入占比 > 40%"],
        scores: {
          place_viability: 82,
          geo_friction_index: 35,
          experience_gap_index: 88,
          design_leverage_score: 92,
          geo_premium_score: 85
        },
        generated_at: new Date().toISOString(),
        confidence: 0.92
      };
      setGeoThesis(mockThesis);
    }, 2500);
  };

  return (
    <div className="w-full h-full flex flex-col bg-[#f6f7fa] overflow-hidden">
      {/* Header */}
      <div className="border-b border-slate-200 bg-white/90 backdrop-blur py-4 px-5 shrink-0 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <Map className="w-5 h-5 text-indigo-600" />
            <h3 className="text-lg font-bold text-slate-800 tracking-tight">商业地理智能引擎</h3>
            <span className="px-2 py-0.5 bg-indigo-50 text-indigo-600 text-xs font-bold rounded uppercase">G1 - G5</span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            基于高德地图底盘，实时计算地理商业摩擦、套利空间，并转化为空间设计指令。
          </p>
        </div>
        
        {/* Mock Trigger Button */}
        {geoAnchor && !thesisLoading && (
          <button 
            onClick={handleSimulateAI}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg shadow-sm hover:shadow-md hover:from-indigo-600 hover:to-purple-700 transition"
          >
            <Play className="w-4 h-4 fill-white" />
            <span className="text-sm font-semibold">{geoThesis ? '重新运行 AI 引擎' : '测试: 运行地理智能计算'}</span>
          </button>
        )}
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <GeoAnchorCard onOpenGeoWorkspace={openPicker} />

        {geoThesis && (
          <div className="flex flex-col gap-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <GeoScorePanel scores={geoThesis.scores} loading={thesisLoading} />
            <GeoThesisCard thesis={geoThesis} loading={thesisLoading} />
          </div>
        )}
        
        {!geoThesis && thesisLoading && (
          <div className="flex flex-col gap-4">
            <GeoScorePanel scores={null as any} loading={true} />
            <GeoThesisCard thesis={null as any} loading={true} />
          </div>
        )}
        
        {!geoThesis && !thesisLoading && (
          <div className="p-8 text-center text-slate-400 bg-white/50 rounded-2xl border border-slate-100 border-dashed mt-4">
            请先在上方设定地理锚点(GeoAnchor)，引擎将自动计算生成地点商业命题(GeoThesis)与智能评分。
          </div>
        )}
      </div>
    </div>
  );
}
