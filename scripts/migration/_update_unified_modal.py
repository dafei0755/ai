#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一次性更新 UnifiedProgressiveQuestionnaireModal.tsx
- 动态步骤指示器（圆形状态）
- 添加 Step 1 内容区（输出意图+需求分析+双动机）
"""
import re

file_path = "frontend-nextjs/components/UnifiedProgressiveQuestionnaireModal.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    data = f.read()

print(f"文件大小: {len(data)} 字符")

# ============================================================================
# 1. 更新 renderStep1Content - 改为输出意图确认
# ============================================================================
print("\n🔧 任务1: 更新 renderStep1Content...")

# 找到 renderStep1Content 函数定义
step1_pattern = r"  // 渲染 Step 1\n  const renderStep1Content = \(\) => \{[\s\S]*?^  \};"
step1_match = re.search(step1_pattern, data, re.MULTILINE)

if step1_match:
    new_step1_func = """  // 🆕 v8.3: Step 1 - 输出意图确认（含需求分析判断+双动机）
  const renderStep1Content = () => {
    const {
      delivery_types,
      identity_modes,
      requirements_judgement,
      motivation_routing_profile,
    } = stepData || {};

    const deliveryOptions = delivery_types?.options || [];
    const identityOptions = identity_modes?.options || [];

    // 交付类型选择状态
    const [selectedDeliveries, setSelectedDeliveries] = useState<string[]>(
      () => deliveryOptions.filter((o: any) => o.recommended).map((o: any) => o.id)
    );
    // 身份模式选择状态
    const [selectedModes, setSelectedModes] = useState<string[]>(
      () => identityOptions.filter((o: any) => o.recommended).map((o: any) => o.id)
    );

    return (
      <div className="space-y-6">
        {/* 需求分析师判断卡片 */}
        {requirements_judgement && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 space-y-3">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="text-sm font-semibold text-amber-800">需求分析师判断</div>
            </div>
            {requirements_judgement.summary && (
              <p className="text-sm text-amber-900 leading-relaxed">{requirements_judgement.summary}</p>
            )}
            {requirements_judgement.info_quality && (
              <div className="flex items-center gap-4 text-xs">
                <span className="text-amber-700">
                  信息完整度: <strong className="text-amber-900">{requirements_judgement.info_quality.score ?? 0}</strong>
                </span>
                <span className="px-2 py-0.5 bg-amber-200 text-amber-800 rounded">
                  {requirements_judgement.info_quality.confidence_level ?? 'medium'}
                </span>
              </div>
            )}
            {requirements_judgement.core_tensions && requirements_judgement.core_tensions.length > 0 && (
              <ul className="text-xs text-amber-800 space-y-1.5 pl-1">
                {requirements_judgement.core_tensions.slice(0, 3).map((t: any, idx: number) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-amber-600 mt-0.5">•</span>
                    <div>
                      <span className="font-medium">{t.name || '关键张力'}：</span>
                      <span className="text-amber-700">{t.implication || '待进一步补充'}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* 双动机展示 */}
        {motivation_routing_profile && (
          <div className="rounded-xl border border-blue-200 bg-blue-50 px-5 py-4 space-y-3">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <div className="text-sm font-semibold text-blue-800">双动机分析</div>
            </div>
            {motivation_routing_profile.primary_motivation && (
              <div className="space-y-1">
                <div className="text-xs text-blue-700">主要动机</div>
                <div className="text-sm text-blue-900">{motivation_routing_profile.primary_motivation}</div>
              </div>
            )}
            {motivation_routing_profile.secondary_motivation && (
              <div className="space-y-1">
                <div className="text-xs text-blue-700">次要动机</div>
                <div className="text-sm text-blue-900">{motivation_routing_profile.secondary_motivation}</div>
              </div>
            )}
          </div>
        )}

        {/* 交付类型选择 */}
        {delivery_types && (
          <div className="space-y-3">
            <div className="text-sm font-medium text-gray-700">{delivery_types.message || '交付类型：'}</div>
            <div className="space-y-2">
              {deliveryOptions.map((option: any) => {
                const isSelected = selectedDeliveries.includes(option.id);
                return (
                  <button
                    key={option.id}
                    onClick={() => {
                      setSelectedDeliveries(prev =>
                        prev.includes(option.id)
                          ? prev.filter(x => x !== option.id)
                          : [...prev, option.id]
                      );
                    }}
                    className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-all ${
                      isSelected
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-800">{option.label}</span>
                          {option.recommended && (
                            <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">推荐</span>
                          )}
                        </div>
                        {option.desc && <p className="text-sm text-gray-600 mt-1">{option.desc}</p>}
                      </div>
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                        isSelected ? 'bg-blue-500 border-blue-500' : 'border-gray-300'
                      }`}>
                        {isSelected && (
                          <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* 身份模式选择 */}
        {identity_modes && identityOptions.length > 0 && (
          <div className="space-y-3">
            <div className="text-sm font-medium text-gray-700">{identity_modes.message || '身份视角：'}</div>
            <div className="space-y-2">
              {identityOptions.map((option: any) => {
                const isSelected = selectedModes.includes(option.id);
                return (
                  <button
                    key={option.id}
                    onClick={() => {
                      setSelectedModes(prev =>
                        prev.includes(option.id)
                          ? prev.filter(x => x !== option.id)
                          : [...prev, option.id]
                      );
                    }}
                    className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-all ${
                      isSelected
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-800">{option.label}</span>
                          {option.recommended && (
                            <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">推荐</span>
                          )}
                        </div>
                        {option.spatial_need && (
                          <p className="text-sm text-gray-600 mt-1">{option.spatial_need}</p>
                        )}
                      </div>
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                        isSelected ? 'bg-blue-500 border-blue-500' : 'border-gray-300'
                      }`}>
                        {isSelected && (
                          <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  };"""

    data = data[: step1_match.start()] + new_step1_func + data[step1_match.end() :]
    print("✅ Step 1 内容区已更新")
else:
    print("❌ 未找到 renderStep1Content")

# ============================================================================
# 2. 更新 renderStepContent - 添加 Step 1 分支
# ============================================================================
print("\n🔧 任务2: 更新 renderStepContent...")

# 找到 renderStepContent 中的 switch 语句
switch_pattern = (
    r"(const renderStepContent = \(\) => \{[\s\S]*?switch \(currentStep\) \{)([\s\S]*?)(default:[\s\S]*?\}[\s\S]*?\};)"
)
switch_match = re.search(switch_pattern, data, re.MULTILINE)

if switch_match:
    switch_start = switch_match.group(1)
    switch_cases = switch_match.group(2)
    switch_end = switch_match.group(3)

    # 检查是否已有 case 1
    if "case 1:" not in switch_cases:
        new_case_1 = """
      case 1:
        return renderStep1Content();
"""
        # 在第一个 case 之前插入
        first_case_match = re.search(r"(\s+case \d+:)", switch_cases)
        if first_case_match:
            insert_pos = first_case_match.start()
            new_switch_cases = switch_cases[:insert_pos] + new_case_1 + switch_cases[insert_pos:]
            data = (
                data[: switch_match.start()] + switch_start + new_switch_cases + switch_end + data[switch_match.end() :]
            )
            print("✅ 添加了 Step 1 渲染分支")
        else:
            print("⚠️  未找到其他 case，手动添加")
    else:
        # 替换现有 case 1
        case1_pattern = r"case 1:[\s\S]*?(?=case \d+:|default:)"
        case1_new = """case 1:
        return renderStep1Content();
      """
        data = re.sub(case1_pattern, case1_new, data, count=1)
        print("✅ 更新了 Step 1 渲染分支")
else:
    print("❌ 未找到 renderStepContent switch")

# ============================================================================
# 3. 更新步骤指示器渲染逻辑
# ============================================================================
print("\n🔧 任务3: 更新步骤指示器...")

# 替换: step.number -> stepIndex (基于索引计算)
data = re.sub(r"key={step\.number}", "key={step.id}", data)
print("✅ 更新了 key 属性")

# ============================================================================
# 保存文件
# ============================================================================
with open(file_path, "w", encoding="utf-8") as f:
    f.write(data)

print(f"\n✅ 文件已保存: {file_path}")
print(f"总共修改: {len(data)} 字符")
