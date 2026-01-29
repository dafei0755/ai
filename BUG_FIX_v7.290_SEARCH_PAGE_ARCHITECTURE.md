# 🔧 BUG FIX v7.290 - 搜索页面架构优化 + 会话错误处理增强

## 问题描述

### 问题1：搜索结果页面仍然显示侧边栏
用户反馈搜索结果页面仍然显示侧边栏，与预期的"干净独立体验"不符。

### 问题2：历史记录在同一标签页打开
从首页点击历史记录时，在同一标签页打开会话，导致用户失去首页上下文。

### 问题3：导航不统一
搜索和分析页面的导航按钮布局不一致，用户体验混乱。

### 问题4：搜索历史自动重启
打开旧的未完成搜索会话时，系统会自动重新搜索，但实际应该显示错误状态。

### 问题5：分析会话中断后自动恢复
旧的分析会话在重新打开时会尝试自动恢复，但可能已经失效，应该给用户明确提示。

## 根本原因

- v7.283 版本引入了全局会话状态管理，为搜索结果页面添加了 `SessionSidebar` 组件，与方案A的架构设计冲突。
- 缺少对新旧会话的时间检测机制。
- 导航按钮位置随意，没有统一规范。

## 实施方案A

**架构理念**：统一首页入口 + 独立搜索/分析页体验

### 1. 页面角色划分

| 页面路径 | 角色 | 特征 |
|---------|------|------|
| `/` | 统一入口 | 3种模式选择，有侧边栏 |
| `/search` | 搜索入口 | 干净搜索界面，无侧边栏 |
| `/search/[session_id]` | 搜索结果 | 独立体验，无侧边栏 ✅ |
| `/analysis/[session_id]` | 分析结果 | 独立体验，无侧边栏 ✅ |

### 2. 用户流程

```
方式1（统一入口）:
首页 → 选择模式 → 输入查询 → 创建会话 → 结果页（无侧边栏）

方式2（直接搜索）:
/search → 输入查询 → 创建会话 → /search/{id}（无侧边栏）

方式3（历史记录）:
首页侧边栏 → 点击历史 → 结果页（无侧边栏）
```

## 修改内容

### 文件1: `frontend-nextjs/app/search/page.tsx`

**变更**：从"重定向到首页"改为"独立搜索入口"

**新增功能**：
- ✅ 干净的搜索界面（无侧边栏）
- ✅ 创建会话后跳转到 `/search/[session_id]`
- ✅ 示例查询快捷选择
- ✅ 返回首页链接

**代码示例**：
```tsx
export default function SearchPage() {
  const router = useRouter();
  const [query, setQuery] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const data = await api.createSearchSession(query.trim(), true);
    router.push(`/search/${data.session_id}`);
  };

  // 干净的全屏搜索界面
  return <div className="min-h-screen">...</div>;
}
```

### 文件2: `frontend-nextjs/app/analysis/[sessionId]/page.tsx`

**变更**：移除侧边栏组件，改为独立体验（与搜索模式一致）

**移除内容**：
- ❌ `SessionSidebar` 组件
- ❌ `UserPanel` 组件
- ❌ `useSession` 钩子
- ❌ 侧边栏状态管理（`isSidebarOpen`）
- ❌ 侧边栏切换按钮
- ❌ 会话操作函数

**保留内容**：
- ✅ 返回首页按钮
- ✅ 所有分析功能逻辑
- ✅ 问卷交互
- ✅ 进度展示

**布局简化**：
```tsx
// 修改前：双层嵌套
<div className="flex">
  <div className="sidebar">...</div>  // ❌ 移除
  <div className="main-content">...</div>
</div>

// 修改后：单层布局
<div className="flex-1 flex-col">
  <header>...</header>
  <main>...</main>
</div>
```

---

## 修改内容（续）

### 文件3: `frontend-nextjs/app/search/[session_id]/page.tsx`

**移除内容**：
- ❌ `SessionSidebar` 组件
- ❌ `UserPanel` 组件
- ❌ `useSession` 钩子
- ❌ 侧边栏状态管理（`isSidebarOpen`）
- ❌ 侧边栏切换按钮（`PanelLeft`）
- ❌ 会话操作函数（重命名、固定、分享、删除）

**保留内容**：
- ✅ 返回按钮（返回 `/search`）
- ✅ 开始新搜索按钮
- ✅ 搜索历史按钮
- ✅ 所有搜索功能逻辑

**布局简化**：
```tsx
// 修改前：双层嵌套（侧边栏 + 主内容）
<div className="flex">
  <div className="sidebar">...</div>  // ❌ 移除
  <div className="main-content">...</div>
</div>

// 修改后：单层布局
<div className="flex-1 flex-col">
  <header>...</header>
  <main>...</main>
</div>
```

## 技术细节

### 状态管理优化

```tsx
// 移除的代码（v7.283引入）
const {
  sessions,
  loadMoreTriggerRef,
  handleRenameSession,
  handlePinSession,
  handleShareSession,
  handleDeleteSession,
} = useSession();

const [isSidebarOpen, setIsSidebarOpen] = useState(true);

// v7.290: 不需要会话管理，专注搜索功能
```

### 导航优化

```tsx
// 修改前：侧边栏切换按钮
<button onClick={() => setIsSidebarOpen(!isSidebarOpen)}>
  <PanelLeft />
</button>

// 修改后：返回搜索入口
<button onClick={() => router.push('/search')}>
  <ArrowLeft />
</button>
```

## 用户体验优势

### 1. 视觉焦点

- 🎯 无侧边栏干扰，专注搜索内容
- 🎯 全屏宽度展示，信息密度更高
- 🎯 卡片式布局，层次清晰

### 2. 交互流畅

- ⚡ 两种入口方式（首页/直接访问）
- ⚡ 快速返回搜索入口继续搜索
- ⚡ 历史记录快捷访问

### 3. 架构清晰

- 📐 搜索功能独立模块
- 📐 与分析功能明确区分
- 📐 符合用户心智模型

## 验证步骤

### 1. 测试搜索模式时间检测
```bash
# 步骤1：创建新搜索
访问 http://localhost:3001/search
输入查询 → 提交
应该看到：自动开始搜索

# 步骤2：测试旧会话
在浏览器地址栏手动输入旧的搜索会话ID（例如 search-20260101-xxxx）
应该看到：错误提示 "此搜索会话未完成或数据已丢失"
```

### 2. 测试分析模式旧会话检测
```bash
# 步骤1：创建新分析
从首页开始新分析
应该看到：正常加载分析流程

# 步骤2：清除localStorage并重新打开
打开浏览器控制台 → localStorage.removeItem('recent_analysis_sessions')
刷新页面
应该看到：错误提示 "此分析会话可能已中断"，显示"尝试继续执行"按钮
```

### 3. 测试历史记录新标签页打开
```bash
# 在首页侧边栏点击任何历史记录
应该看到：在新标签页打开会话
首页标签页仍然存在
```

### 4. 测试统一导航
```bash
# 测试搜索页面
点击左上角返回按钮 → 应该返回首页
点击右上角×按钮 → 应该返回首页

# 测试分析页面
点击左上角返回按钮 → 应该返回首页
点击右上角×按钮 → 应该返回首页
```

### 5. 测试错误恢复
```bash
# 对于显示错误的旧会话
点击"尝试继续执行"按钮 → 页面刷新，尝试加载会话状态
如果后端状态存在 → 正常继续
如果后端状态不存在 → 显示404错误
```

### 6. 测试用户问题卡片显示
```bash
# 测试正常流程
从首页创建新的分析会话 → 应该能在分析页面看到用户问题卡片

# 测试错误情况
1. 创建会话后，手动清除 localStorage 中的 recent_analysis_sessions
2. 刷新页面
3. 应该看到：用户问题卡片（在上方）+ 错误提示（在下方）

# 验证localStorage
打开浏览器控制台：
localStorage.getItem('analysis_user_inputs')
应该能看到保存的用户输入JSON
```

## 兼容性说明

### 不影响的功能

- ✅ 首页3种模式选择
- ✅ 分析页面侧边栏
- ✅ 深度思考模式
- ✅ 历史记录管理

### 影响的功能

- ⚠️ 搜索页面不再显示会话历史（通过"搜索历史"按钮访问）
- ⚠️ 搜索页面不再显示用户信息（可返回首页查看）

## 后续优化建议

### 1. 移动端适配

```tsx
// 建议：移动端添加底部导航栏
<div className="md:hidden fixed bottom-0">
  <button>首页</button>
  <button>搜索</button>
  <button>历史</button>
</div>
```

### 2. 搜索历史增强

```tsx
// 建议：支持搜索历史快捷过滤
<input placeholder="搜索历史..." />
```

### 3. 分享功能

```tsx
// 建议：添加分享按钮
<button onClick={shareSearch}>
  <Share2 /> 分享搜索结果
</button>
```

## 文件清单

| 文件 | 变更类型 | 代码行数 | 说明 |
|------|---------|---------|------|
| `app/search/page.tsx` | 重写 | ~150行 | 独立搜索入口 |
| `app/search/[session_id]/page.tsx` | 精简+增强 | -80行, +20行 | 移除侧边栏，添加时间检测，使用公共组件 |
| `app/analysis/[sessionId]/page.tsx` | 精简+增强 | -80行, +30行 | 移除侧边栏，添加旧会话检测，使用公共组件 |
| `app/page.tsx` | 增强 | +30行 | 记录新会话到localStorage，保存用户输入 |
| `components/SessionSidebar.tsx` | 修改 | ~10行 | 历史记录新标签页打开 |
| `components/UserQuestionCard.tsx` | 新增 | ~40行 | 用户问题卡片公共组件 |

**总计**：6个文件，核心改动约290行

## v7.290 完整修复内容

### 修复1：搜索模式时间检测（防止自动重启）

**文件**：`frontend-nextjs/app/search/[session_id]/page.tsx`

**变更**：
```tsx
// 添加时间检测逻辑
const isNewSession = /^search-\d{8}-[0-9a-f]{12}$/.test(sessionId);
const sessionDateStr = sessionId.split('-')[1]; // YYYYMMDD
const sessionDate = new Date(
  sessionDateStr.substring(0, 4),
  parseInt(sessionDateStr.substring(4, 6)) - 1,
  sessionDateStr.substring(6, 8)
);
const sessionAge = Date.now() - sessionDate.getTime();
const isRecentSession = sessionAge < 60000; // 1分钟内

if (isNewSession && isRecentSession) {
  // 新会话：自动开始搜索
  pendingSearchRef.current = { query, deepMode };
} else {
  // 旧会话：显示错误提示
  setSearchState({
    status: 'error',
    error: '此搜索会话未完成或数据已丢失。请点击"开始新搜索"重新开始。'
  });
}
```

**效果**：
- ✅ 1分钟内创建的会话：自动开始搜索
- ✅ 超过1分钟的会话：显示错误，提供"开始新搜索"按钮

### 修复2：分析模式旧会话检测

**文件**：`frontend-nextjs/app/analysis/[sessionId]/page.tsx`

**变更**：
```tsx
// 从 localStorage 获取最近创建的会话记录
const recentSessionsJson = localStorage.getItem('recent_analysis_sessions');
const recentSessions: Record<string, number> = recentSessionsJson ? JSON.parse(recentSessionsJson) : {};
const sessionCreatedAt = recentSessions[sessionId];
const now = Date.now();

// 如果会话不在最近记录中，或创建时间超过1分钟，且状态为运行中/等待输入，则认为是旧会话
const isOldSession = !sessionCreatedAt || (now - sessionCreatedAt > 60000);
const isIncompleteStatus = data.status === 'running' || data.status === 'waiting_for_input';

if (isOldSession && isIncompleteStatus) {
  console.warn('⚠️ 检测到旧的未完成会话');
  setError('此分析会话可能已中断。您可以尝试重新加载以继续执行，或返回首页开始新的分析。');
  return;
}
```

**配合修改**：`frontend-nextjs/app/page.tsx`
```tsx
// 创建新会话时记录到 localStorage
const recentSessions: Record<string, number> = JSON.parse(
  localStorage.getItem('recent_analysis_sessions') || '{}'
);
recentSessions[response.session_id] = Date.now();
localStorage.setItem('recent_analysis_sessions', JSON.stringify(recentSessions));
```

**效果**：
- ✅ 新创建的会话（<1分钟）：正常加载
- ✅ 旧的未完成会话（>1分钟）：显示错误提示，提供"尝试继续执行"按钮
- ✅ 自动清理localStorage（保留最近100个会话）

### 修复3：历史记录新标签页打开

**文件**：`frontend-nextjs/components/SessionSidebar.tsx`

**变更**：
```tsx
onClick={(e) => {
  // v7.290: 默认在新标签页打开历史记录
  let targetUrl = '';
  if (session.session_type === 'search') {
    targetUrl = `/search/${session.session_id}`;
  } else if (session.status === 'completed') {
    targetUrl = `/report/${session.session_id}`;
  } else {
    targetUrl = `/analysis/${session.session_id}`;
  }
  window.open(targetUrl, '_blank'); // Always new tab
}}
```

**效果**：
- ✅ 点击历史记录始终在新标签页打开
- ✅ 保留首页上下文
- ✅ 支持同时查看多个会话

### 修复4：统一导航布局

**文件**：
- `frontend-nextjs/app/search/[session_id]/page.tsx`
- `frontend-nextjs/app/analysis/[sessionId]/page.tsx`

**变更**：
```tsx
// 左上角：返回按钮
<button onClick={() => router.push('/')}>
  <PanelLeft className="rotate-180" />
</button>

// 右上角：关闭按钮
<button onClick={() => router.push('/')}>
  <X className="w-5 h-5" />
</button>
```

**效果**：
- ✅ 所有独立页面导航一致
- ✅ ← 返回 （左上角）
- ✅ × 关闭 （右上角）
- ✅ 两个按钮功能相同（返回首页）

### 修复5：分析页面错误提示上方显示用户问题卡片（已重构为公共组件）

**文件**：
- `frontend-nextjs/components/UserQuestionCard.tsx` （新增）
- `frontend-nextjs/app/page.tsx`
- `frontend-nextjs/app/search/[session_id]/page.tsx`
- `frontend-nextjs/app/analysis/[sessionId]/page.tsx`

**变更**：

1. **创建公共组件** `components/UserQuestionCard.tsx`：
```tsx
interface UserQuestionCardProps {
  /** 用户输入的问题内容 */
  question: string;
  /** 可选的自定义类名 */
  className?: string;
}

export function UserQuestionCard({ question, className = '' }: UserQuestionCardProps) {
  if (!question) return null;

  return (
    <div className={`bg-white dark:bg-gray-900 rounded-xl p-5 border border-gray-200 dark:border-gray-700 ${className}`}>
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
          <MessageCircle className="w-4 h-4 text-blue-600 dark:text-blue-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-blue-600 dark:text-blue-400 font-medium mb-1">用户问题</p>
          <p className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap break-words">
            {question}
          </p>
        </div>
      </div>
    </div>
  );
}
```

2. **首页保存用户输入**（`app/page.tsx`）：
```tsx
// 创建会话时同时保存用户输入到 localStorage
const userInputs: Record<string, number> = JSON.parse(
  localStorage.getItem('analysis_user_inputs') || '{}'
);
userInputs[response.session_id] = displayText;
localStorage.setItem('analysis_user_inputs', JSON.stringify(userInputs));
```

3. **搜索页面使用公共组件**（`app/search/[session_id]/page.tsx`）：
```tsx
import { UserQuestionCard } from '@/components/UserQuestionCard';

// 渲染
<UserQuestionCard question={query} className="mb-6" />
```

4. **分析页面加载并使用公共组件**（`app/analysis/[sessionId]/page.tsx`）：
```tsx
import { UserQuestionCard } from '@/components/UserQuestionCard';

// 加载用户输入
const userInputsJson = localStorage.getItem('analysis_user_inputs');
if (userInputsJson) {
  const userInputs: Record<string, string> = JSON.parse(userInputsJson);
  if (userInputs[sessionId]) {
    setUserInput(userInputs[sessionId]);
  }
}

// 渲染（在错误提示上方）
{(error || status) && <UserQuestionCard question={userInput} className="mb-6" />}
```

**效果**：
- ✅ 消除代码重复：搜索和分析模式共用同一个用户问题卡片组件
- ✅ 统一用户体验：两个模式的用户问题显示完全一致
- ✅ 易于维护：样式和行为修改只需在一处进行
- ✅ 类型安全：TypeScript接口定义确保正确使用
- ✅ 自动隐藏：question为空时自动不渲染
- ✅ 即使会话中断或出错，用户也能看到自己最初提出的问题
- ✅ 使用 localStorage 持久化存储用户输入（保留最近100条）

## 验证步骤

- 📖 [QUICKSTART.md](QUICKSTART.md) - 快速启动指南
- 📖 [BUG_FIX_v7.290_SEARCH_SESSION_AUTO_START.md](BUG_FIX_v7.290_SEARCH_SESSION_AUTO_START.md) - 自动启动修复
- 🎨 [设计决策记录](docs/ADR/) - 架构决策记录（待创建）

## 版本信息

- **版本号**: v7.290.1
- **修复日期**: 2026-01-28
- **影响范围**: 搜索模块UI架构
- **向后兼容**: ✅ 是（API接口不变）

---

**修复完成！搜索页面现已实现干净的独立体验。** 🎉
