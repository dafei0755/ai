import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface MotivationScore {
  [key: string]: number;
}

interface MotivationSpectrumProps {
  scores: MotivationScore;
  primaryType: string;
  confidence: number;
  className?: string;
}

// 动机类型配置（对应12种类型）
const MOTIVATION_TYPES = {
  // P0: 高优先级
  cultural: { label: '文化认同', color: '#FF6B6B', priority: 'P0' },
  commercial: { label: '商业价值', color: '#4ECDC4', priority: 'P0' },
  wellness: { label: '健康疗愈', color: '#95E1D3', priority: 'P0' },

  // P1: 中优先级
  technical: { label: '技术创新', color: '#FFE66D', priority: 'P1' },
  sustainable: { label: '可持续性', color: '#7BC043', priority: 'P1' },

  // P2: 标准优先级
  professional: { label: '专业发展', color: '#A8DADC', priority: 'P2' },
  inclusive: { label: '包容性', color: '#F4A261', priority: 'P2' },

  // 基线类型
  functional: { label: '功能性', color: '#457B9D', priority: 'baseline' },
  emotional: { label: '情感性', color: '#E63946', priority: 'baseline' },
  aesthetic: { label: '审美性', color: '#F1FAEE', priority: 'baseline' },
  social: { label: '社交性', color: '#A8DADC', priority: 'baseline' },
  mixed: { label: '综合需求', color: '#B8B8B8', priority: 'baseline' }
};

export const MotivationSpectrumChart: React.FC<MotivationSpectrumProps> = ({
  scores,
  primaryType,
  confidence,
  className = ''
}) => {
  // 转换数据为雷达图格式
  const chartData = Object.entries(MOTIVATION_TYPES).map(([key, config]) => ({
    motivation: config.label,
    score: (scores[key] || 0) * 100, // 转换为百分比
    fullMark: 100,
    isPrimary: key === primaryType
  }));

  // 自定义Tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
          <p className="font-semibold text-gray-900 dark:text-white">
            {data.motivation}
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            得分: {data.score.toFixed(1)}%
          </p>
          {data.isPrimary && (
            <p className="text-xs text-blue-500 font-semibold mt-1">
              ★ 主要动机
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  // 自定义角度轴标签
  const CustomAngleAxisTick = (props: any) => {
    const { payload, x, y, cx, cy } = props;
    const data = chartData.find(d => d.motivation === payload.value);
    const isPrimary = data?.isPrimary;

    return (
      <text
        x={x}
        y={y}
        textAnchor={x > cx ? 'start' : 'end'}
        fill={isPrimary ? '#3B82F6' : '#6B7280'}
        className={`text-xs ${isPrimary ? 'font-bold' : 'font-normal'}`}
      >
        {payload.value}
        {isPrimary && ' ★'}
      </text>
    );
  };

  return (
    <div className={`motivation-spectrum ${className}`}>
      {/* 标题和置信度 */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          动机光谱分析
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">
            置信度:
          </span>
          <span className={`text-sm font-semibold ${
            confidence >= 0.7 ? 'text-green-600' :
            confidence >= 0.5 ? 'text-yellow-600' :
            'text-red-600'
          }`}>
            {(confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* 雷达图 */}
      <ResponsiveContainer width="100%" height={400}>
        <RadarChart data={chartData}>
          <PolarGrid stroke="#E5E7EB" />
          <PolarAngleAxis
            dataKey="motivation"
            tick={CustomAngleAxisTick}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
          />
          <Radar
            name="动机强度"
            dataKey="score"
            stroke="#3B82F6"
            fill="#3B82F6"
            fillOpacity={0.3}
          />
          <Tooltip content={<CustomTooltip />} />
        </RadarChart>
      </ResponsiveContainer>

      {/* 图例：显示优先级分组 */}
      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="p-2 bg-red-50 dark:bg-red-900/20 rounded">
          <div className="font-semibold text-red-700 dark:text-red-400 mb-1">P0 高优先级</div>
          <div className="space-y-1">
            {Object.entries(MOTIVATION_TYPES)
              .filter(([_, config]) => config.priority === 'P0')
              .map(([key, config]) => (
                <div key={key} className="flex items-center gap-1">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: config.color }}
                  />
                  <span className="text-gray-700 dark:text-gray-300">{config.label}</span>
                  {scores[key] && (
                    <span className="ml-auto text-gray-500">
                      {(scores[key] * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              ))}
          </div>
        </div>

        <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded">
          <div className="font-semibold text-blue-700 dark:text-blue-400 mb-1">基线类型</div>
          <div className="space-y-1">
            {Object.entries(MOTIVATION_TYPES)
              .filter(([_, config]) => config.priority === 'baseline')
              .map(([key, config]) => (
                <div key={key} className="flex items-center gap-1">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: config.color }}
                  />
                  <span className="text-gray-700 dark:text-gray-300">{config.label}</span>
                  {scores[key] && (
                    <span className="ml-auto text-gray-500">
                      {(scores[key] * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              ))}
          </div>
        </div>
      </div>

      {/* 主要动机高亮 */}
      <div className="mt-4 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <div className="flex items-center gap-2">
          <span className="text-2xl">★</span>
          <div>
            <div className="text-sm text-gray-600 dark:text-gray-400">主要动机</div>
            <div className="text-lg font-semibold text-blue-700 dark:text-blue-400">
              {MOTIVATION_TYPES[primaryType as keyof typeof MOTIVATION_TYPES]?.label || primaryType}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MotivationSpectrumChart;
