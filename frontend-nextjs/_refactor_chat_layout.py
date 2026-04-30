"""
重构项目态聊天布局：
1. flex-1 flex-col 外层容器（不滚动）
2. flex-1 overflow-y-auto 内层滚动区（聊天气泡）
3. 浮窗交互区（绝对定位于输入栏上方）
4. 常驻底部输入栏
"""

with open(r'app\analysis\[sessionId]\page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# ─── Step 1: 添加 SendHorizontal 到 lucide-react 导入 ───
content = content.replace(
    '\tArrowLeft\n} from \'lucide-react\';',
    '\tArrowLeft,\n\tSendHorizontal\n} from \'lucide-react\';',
    1
)

# ─── Step 2: 添加 projectInputValue state ───
content = content.replace(
    '\t// 项目态需求分析区折叠状态（任务完成后自动折叠）\n\tconst [requirementsCollapsed, setRequirementsCollapsed] = useState(false);',
    '\t// 项目态需求分析区折叠状态（任务完成后自动折叠）\n\tconst [requirementsCollapsed, setRequirementsCollapsed] = useState(false);\n\t// 项目态底部输入栏（UserQuestion 追问时启用）\n\tconst [projectInputValue, setProjectInputValue] = useState(\'\');',
    1
)

# ─── Step 3: 大块替换 - 项目态渲染区域 ───
# 从 flex-1 overflow-y-auto 开始到 ternary 结束

old_project_mode = '''\t\t\t\t\t\t\t<div className="flex-1 overflow-y-auto">
\t\t\t\t\t\t\t\t<div className="max-w-3xl mx-auto px-4 py-6 flex flex-col gap-4">'''

# 验证能找到这个标记
if old_project_mode not in content:
    print("ERROR: 找不到项目态外层div标记")
    exit(1)

# 找到 interaction block 的起始和结束（用于替换）
interaction_old_start = '\t\t\t\t\t\t\t\t\t{/* 活跃交互（问卷 / 确认 / 追问等） */}'
interaction_old_condition_line = "\t\t\t\t\t\t\t\t\t{(currentProgressiveStep > 0 || showRoleTaskReview || showQualityPreflight || showUserQuestion || showQuestionnaire || (showConfirmation && confirmationData?.interaction_type !== 'role_and_task_unified_review')) && ("

if interaction_old_start not in content:
    print("ERROR: 找不到交互块标记")
    exit(1)

# 找到交互块结尾（最后一个 )} 后面是 max-w-3xl 的关闭）
# 用更精确的标记
interaction_old_end_marker = "\t\t\t\t\t\t\t\t\t)}\n\n\t\t\t\t\t\t\t\t\t{/* 已完成 */}"
if interaction_old_end_marker not in content:
    print("ERROR: 找不到交互块结束标记")
    exit(1)

# ─── 构建 interaction block 旧文本（完整）───
# 从 {/* 活跃交互 */} 到 )} 之前的 {/* 已完成 */}
interaction_old_full = '''\t\t\t\t\t\t\t\t\t{/* 活跃交互（问卷 / 确认 / 追问等） */}
\t\t\t\t\t\t\t\t\t{(currentProgressiveStep > 0 || showRoleTaskReview || showQualityPreflight || showUserQuestion || showQuestionnaire || (showConfirmation && confirmationData?.interaction_type !== 'role_and_task_unified_review')) && (
\t\t\t\t\t\t\t\t\t\t<div className="w-full">
\t\t\t\t\t\t\t\t\t\t\t{currentProgressiveStep === 1 ? (
\t\t\t\t\t\t\t\t\t\t\t\t// 意图确认 → 简化为AI聊天气泡，AI推荐值一键确认，无需填表'''

if interaction_old_full not in content:
    print("ERROR: 找不到交互块开头精确内容")
    exit(1)

# 找到完整 interaction block
idx_start = content.index(interaction_old_full)
# 找对应的结束
idx_end_marker = content.index("\t\t\t\t\t\t\t\t\t{/* 已完成 */}", idx_start)
interaction_old_block = content[idx_start:idx_end_marker]

# ─── 构建 step1 bubble 内容（从旧 interaction block 中提取）───
# step1 bubble 在 {currentProgressiveStep === 1 ? ( 到 ) : currentProgressiveStep > 1 之间
step1_start_marker = '\t\t\t\t\t\t\t\t\t\t\t\t// 意图确认 → 简化为AI聊天气泡，AI推荐值一键确认，无需填表\n\t\t\t\t\t\t\t\t\t\t\t\t<div className="flex items-start gap-2">'
step1_end_marker = '\t\t\t\t\t\t\t\t\t\t\t) : currentProgressiveStep > 1 ? ('

if step1_start_marker not in content:
    print("ERROR: 找不到 step1 bubble 内容")
    exit(1)

idx_s1 = content.index(step1_start_marker)
idx_s1_end = content.index(step1_end_marker, idx_s1)
step1_bubble_inner = content[idx_s1:idx_s1_end].rstrip()

# step1 bubble 的最后 </div></div> 需要被提取
# 实际上 step1 bubble 从 <div className="flex items-start gap-2"> 到结束的 </div>
# 在 idx_s1 处开始，在 idx_s1_end 前结束
# content[idx_s1:idx_s1_end] 包含了 comment + the step1 div

# 新的 step1 只渲染，在 scroll 区 inline 显示
new_step1_in_scroll = '''\t\t\t\t\t\t\t\t\t\t{/* 意图确认气泡（step 1）*/}
\t\t\t\t\t\t\t\t\t\t{currentProgressiveStep === 1 && (
''' + step1_bubble_inner.replace('\t\t\t\t\t\t\t\t\t\t\t\t<div className="flex items-start gap-2">', '\t\t\t\t\t\t\t\t\t\t\t<div className="flex items-start gap-2">').replace(
    '\t\t\t\t\t\t\t\t\t\t\t\t\t', '\t\t\t\t\t\t\t\t\t\t\t\t'
) + '''
\t\t\t\t\t\t\t\t\t\t)}'''

# Actually - let me just take the step1_bubble_inner as-is and keep same indentation
# The comment line + <div className="flex items-start gap-2"> and its content until step1_end_marker
step1_content = content[idx_s1:idx_s1_end].rstrip()
# Remove the comment line prefix
step1_content_clean = step1_content.replace(
    '// 意图确认 → 简化为AI聊天气泡，AI推荐值一键确认，无需填表\n\t\t\t\t\t\t\t\t\t\t\t\t', 
    ''
)

print("step1 bubble 长度:", len(step1_content_clean))
print("step1前50:", repr(step1_content_clean[:80]))

# ─── 新的 interaction block 替换（仅保留 step1，其余移到 overlay）───
new_interaction_in_scroll = '''\t\t\t\t\t\t\t\t\t\t{/* 意图确认气泡（step 1）*/}
\t\t\t\t\t\t\t\t\t\t{currentProgressiveStep === 1 && (
\t\t\t\t\t\t\t\t\t\t\t''' + step1_content_clean.strip() + '''
\t\t\t\t\t\t\t\t\t\t)}

\t\t\t\t\t\t\t\t\t\t'''

content = content.replace(interaction_old_block, new_interaction_in_scroll, 1)
print("Step 3 (interaction block替换):", "OK" if new_interaction_in_scroll in content else "FAILED")

# ─── Step 4: 改造外层 div + 加 scroll wrapper + overlay + input bar ───

# 找到外层 div，在后面加 scroll wrapper
content = content.replace(
    '\t\t\t\t\t\t\t<div className="flex-1 overflow-y-auto">\n\t\t\t\t\t\t\t\t<div className="max-w-3xl mx-auto px-4 py-6 flex flex-col gap-4">',
    '\t\t\t\t\t\t\t<div className="flex-1 flex flex-col overflow-hidden">\n\t\t\t\t\t\t\t\t{/* 可滚动聊天区 */}\n\t\t\t\t\t\t\t\t<div className="flex-1 overflow-y-auto">\n\t\t\t\t\t\t\t\t\t<div className="max-w-3xl mx-auto px-4 py-6 flex flex-col gap-4">',
    1
)
print("Step 4a (外层div改造):", "OK" if 'flex-1 flex flex-col overflow-hidden' in content else "FAILED")

# 找到 scroll 关闭位置并加 inner scroll close + overlay + input bar
# 当前：endref + max-w-3xl close + outer div close + ternary close
# 在 endref 之前内容是 9-tab（现在变成10-tab）... 
# 等等，我们只改了外层div到flex-col，并在里面加了scroll div，但没有重新缩进 max-w-3xl 的内容，
# 所以 max-w-3xl 现在在 flex-1 overflow-y-auto 里...
# 实际上我们在step4a只改了两行，所以缩进仍然是8 tabs for max-w-3xl
# 新结构是:
# 7t: flex-1 flex-col   [outer]
# 8t:   {/* 可滚动 */}
# 8t:   flex-1 overflow-y-auto   [scroll wrapper, NEW]
# 8t:     max-w-3xl   [was 8t, now inside 8t scroll - actually the nesting is WRONG]

# PROBLEM: When I added `<div className="flex-1 overflow-y-auto">` at 8t level,
# and `max-w-3xl` is ALSO at 8t level, they're now SIBLINGS, not parent-child!

# I need max-w-3xl to be at 9t (inside the scroll wrapper at 8t)
# But I didn't change the indentation of max-w-3xl and its content

# Let me reconsider the approach. The inserted scroll wrapper needs to contain the max-w-3xl div.
# After step4a:
# 7t: <div className="flex-1 flex flex-col overflow-hidden">
# 8t:   {/* 可滚动聊天区 */}
# 8t:   <div className="flex-1 overflow-y-auto">   [NEW, but doesn't contain max-w-3xl!]
# 8t:   <div className="max-w-3xl ...">   [still at 8t, so it's a SIBLING of the scroll!]

# This is wrong. The correct structure requires max-w-3xl to be INSIDE the scroll div.
# I need to either:
# a) Put the scroll close AFTER max-w-3xl close
# b) Fix the indentation

# REVISED PLAN: Don't add the scroll wrapper inline - instead use the EXISTING
# overflow-y-auto on the outer div, just change the class later.

# For now, let me check what the current content looks like after step4a
print("\n=== Current structure around the change ===")
idx = content.index('flex-1 flex flex-col overflow-hidden')
print(repr(content[idx-20:idx+300]))

print("\nScript aborted - need to revise approach")
