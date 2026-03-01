'use client';

import React from 'react';
import { CheckCircle, Target, ListChecks, Sparkles } from 'lucide-react';

interface OutputBlock {
  name: string;
  sub_items: string[];
  estimated_length: string;
  priority: string;
}

interface OutputFramework {
  core_objective: string;
  deliverable_type: string;
  blocks: OutputBlock[];
  quality_standards: string[];
  search_hints: string;
}

interface Step1OutputFrameworkProps {
  framework: OutputFramework;
}

export default function Step1OutputFramework({ framework }: Step1OutputFrameworkProps) {
  if (!framework) return null;

  return (
    <div className="step1-output-framework border rounded-lg p-6 my-4 bg-gradient-to-br from-blue-50 to-indigo-50">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-5 h-5 text-indigo-600" />
        <h3 className="text-xl font-bold text-gray-900">
          步骤1：输出框架（动态生成）
        </h3>
      </div>

      {/* 核心目标 */}
      <div className="mb-6 p-4 bg-white rounded-lg border border-indigo-200">
        <div className="flex items-start gap-2">
          <Target className="w-5 h-5 text-indigo-600 mt-1 flex-shrink-0" />
          <div className="flex-1">
            <h4 className="font-semibold text-gray-900 mb-2">核心目标</h4>
            <p className="text-gray-700">{framework.core_objective}</p>
          </div>
        </div>
      </div>

      {/* 交付物类型 */}
      <div className="mb-6 p-4 bg-white rounded-lg border border-indigo-200">
        <div className="flex items-start gap-2">
          <CheckCircle className="w-5 h-5 text-indigo-600 mt-1 flex-shrink-0" />
          <div className="flex-1">
            <h4 className="font-semibold text-gray-900 mb-2">最终交付物类型</h4>
            <p className="text-gray-700">{framework.deliverable_type}</p>
          </div>
        </div>
      </div>

      {/* 输出板块 */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-3">
          <ListChecks className="w-5 h-5 text-indigo-600" />
          <h4 className="font-semibold text-gray-900">
            输出结构（{framework.blocks?.length || 0}个板块）
          </h4>
        </div>
        <div className="space-y-3">
          {framework.blocks?.map((block, index) => (
            <div
              key={index}
              className="p-4 bg-white rounded-lg border border-indigo-200 hover:border-indigo-300 transition-colors"
            >
              <div className="flex items-start justify-between mb-2">
                <h5 className="font-medium text-gray-900 flex-1">
                  板块{index + 1}：{block.name}
                </h5>
                <span className="text-xs px-2 py-1 rounded bg-indigo-100 text-indigo-700 ml-2">
                  {block.estimated_length}
                </span>
              </div>
              {block.sub_items && block.sub_items.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {block.sub_items.map((item, idx) => (
                    <li key={idx} className="text-sm text-gray-600 flex items-start gap-2">
                      <span className="text-indigo-400 mt-1">•</span>
                      <span className="flex-1">{item}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 质量标准 */}
      {framework.quality_standards && framework.quality_standards.length > 0 && (
        <div className="mb-6 p-4 bg-white rounded-lg border border-indigo-200">
          <h4 className="font-semibold text-gray-900 mb-3">输出质量标准</h4>
          <ul className="space-y-2">
            {framework.quality_standards.map((standard, index) => (
              <li key={index} className="text-sm text-gray-700 flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="flex-1">{standard}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 搜索方向提示 */}
      {framework.search_hints && (
        <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
          <h4 className="font-semibold text-gray-900 mb-2">搜索方向提示</h4>
          <p className="text-sm text-gray-700">{framework.search_hints}</p>
        </div>
      )}
    </div>
  );
}
