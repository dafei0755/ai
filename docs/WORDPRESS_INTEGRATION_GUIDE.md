# WordPress 集成开发指南

**最后更新**: 2025-12-14
**项目版本**: v3.0.4
**集成状态**: ✅ 生产就绪

---

## 📚 目录

1. [项目概述](#项目概述)
2. [架构设计](#架构设计)
3. [WordPress SSO 单点登录](#wordpress-sso-单点登录)
4. [会员系统集成](#会员系统集成)
5. [前端实现](#前端实现)
6. [后端API](#后端api)
7. [部署指南](#部署指南)
8. [常见问题](#常见问题)

---

## 项目概述

本项目将 Next.js 应用与 WordPress WPCOM Member Pro 会员系统集成，实现：

- ✅ WordPress SSO 单点登录（iframe 嵌入模式）
- ✅ 会员等级获取和显示
- ✅ 套餐展示和升级流程
- ✅ 钱包余额查询
- ✅ 基于VIP等级的访问控制

### 技术栈

**前端**:
- Next.js 14 (App Router)
- React 18
- TypeScript
- Tailwind CSS

**后端**:
- Python 3.10+
- FastAPI
- PyJWT (JWT认证)

**WordPress插件**:
- Next.js SSO Integration v3.0.4
- WPCOM Member Custom API v1.0.0
- WPCOM Member Pro (第三方)
- Simple JWT Login v3.6.4

---

## 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────┐
│          WordPress (www.ucppt.com)                  │
│  ┌──────────────────────────────────────────────┐  │
│  │   WPCOM Member Pro (会员系统)                 │  │
│  │   - 会员等级管理 (VIP 1/2/3)                 │  │
│  │   - 到期时间管理                              │  │
│  │   - 钱包余额管理                              │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │   WordPress 插件生态                         │  │
│  │   - Next.js SSO Integration v3.0.4           │  │
│  │   - WPCOM Custom API v1.0.0                  │  │
│  │   - Simple JWT Login v3.6.4                  │  │
│  └──────────────────────────────────────────────┘  │
│                      ↓ JWT Token                   │
│  ┌──────────────────────────────────────────────┐  │
│  │   WordPress 页面 + [nextjs_app] 短代码       │  │
│  │   └─→ iframe 嵌入 Next.js 应用              │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                      ↓ iframe + Token
┌─────────────────────────────────────────────────────┐
│       Next.js App (localhost:3000 / ai.ucppt.com)  │
│  ┌──────────────────────────────────────────────┐  │
│  │   前端功能                                    │  │
│  │   - SSO 自动登录（URL Token）                │  │
│  │   - 用户面板（会员卡片）                      │  │
│  │   - 套餐页面（/pricing）                     │  │
│  │   - VIP 等级显示                             │  │
│  └──────────────────────────────────────────────┘  │
│                      ↓ API 调用
│  ┌──────────────────────────────────────────────┐  │
│  │   Python FastAPI (localhost:8000)            │  │
│  │   - JWT Token 验证                           │  │
│  │   - 会员数据代理                              │  │
│  │   - VIP 访问控制                             │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 数据流程

**登录流程**:
```
1. 用户访问 WordPress 页面 (www.ucppt.com/nextjs)
2. WordPress 检测登录状态
   - 未登录: 显示登录按钮
   - 已登录: 继续步骤 3
3. WordPress 插件生成 JWT Token
4. 插件在 iframe URL 中传递 Token:
   http://localhost:3000?sso_token=eyJ...
5. Next.js 前端读取 URL Token 并保存到 localStorage
6. 清除 URL 参数（安全优化）
7. 前端使用 Token 调用 FastAPI 验证
8. 显示用户信息和会员等级
```

**会员数据获取**:
```
1. Next.js 发送请求: GET /api/member/my-membership
   Headers: Authorization: Bearer {token}
2. FastAPI 验证 JWT Token
3. 调用 WPCOM Custom API 获取会员数据
4. 返回格式化数据:
   {
     "level": 1,
     "level_name": "普通会员",
     "expire_date": "2026-11-10",
     "is_expired": false,
     "wallet_balance": 1.01
   }
5. 前端展示会员信息
```

---

## WordPress SSO 单点登录

### 插件安装

#### 1. Next.js SSO Integration v3.0.4

**插件文件**: `nextjs-sso-integration-v3.php`

**核心功能**:
- 生成 JWT Token（HS256 算法）
- iframe 嵌入 Next.js 应用
- URL 参数传递 Token（绕过跨域Cookie限制）

**关键代码**:

```php
// JWT 生成（使用 wp-config.php 中的密钥）
$secret = defined('PYTHON_JWT_SECRET') ? PYTHON_JWT_SECRET : 'YOUR_JWT_SECRET_KEY';

$payload = array(
    'sub' => $user->user_login,
    'user_id' => $user->ID,
    'email' => $user->user_email,
    'iat' => time(),
    'exp' => time() + (24 * 60 * 60)  // 24小时有效期
);

$jwt = generate_jwt($payload, $secret);
```

**短代码使用**:

```php
// WordPress 页面中添加
[nextjs_app]

// 生成的 HTML:
<iframe src="http://localhost:3000?v=3.0.4&sso_token={jwt_token}"
        width="100%" height="800px" frameborder="0">
</iframe>
```

#### 2. WPCOM Custom API v1.0.0

**插件文件**: `wpcom-custom-api-v1.0.0.php`

**REST API 端点**:

```php
// 获取用户会员信息
GET /wp-json/custom/v1/user-membership/{user_id}
Headers: Authorization: Bearer {wordpress_admin_token}

// 获取用户钱包余额
GET /wp-json/custom/v1/user-wallet/{user_id}
Headers: Authorization: Bearer {wordpress_admin_token}
```

### wp-config.php 配置

**必须添加的常量**:

```php
// JWT 密钥（与 Python 后端保持一致）
define('PYTHON_JWT_SECRET', 'YOUR_JWT_SECRET_KEY');

// WordPress 管理员凭证（用于API调用）
define('WP_ADMIN_USERNAME', 'YOUR_WORDPRESS_USERNAME');
define('WP_ADMIN_PASSWORD', 'YOUR_WORDPRESS_PASSWORD');
```

**安全注意事项**:
- ✅ JWT密钥从 wp-config.php 读取（不硬编码）
- ✅ 生产环境关闭 WP_DEBUG（避免日志泄露）
- ✅ 使用强密码和复杂密钥

---

## 会员系统集成

### 会员等级映射

| level | level_name | WordPress显示 | 价格（年付） |
|-------|-----------|--------------|------------|
| 0     | 免费用户   | 免费         | ¥0         |
| 1     | 普通会员   | VIP 1        | ¥3,800     |
| 2     | 超级会员   | VIP 2        | ¥9,800     |
| 3     | 钻石会员   | VIP 3        | -          |

**注**: 当前前端仅显示普通会员和超级会员（简化用户选择）

### 会员功能对比

#### 普通会员 (¥3,800/年)
- 每月10次AI分析
- 基础项目报告
- 标准响应速度
- 邮件支持
- 7天历史记录

#### 超级会员 (¥9,800/年)
- 每月50次AI分析
- 深度项目洞察
- 优先响应速度
- 专属客服支持
- 30天历史记录
- 团队协作功能
- PDF报告导出

### 套餐页面实现

**页面路由**: `/pricing`
**文件**: `frontend-nextjs/app/pricing/page.tsx`

**核心功能**:
1. ✅ 获取当前用户会员信息
2. ✅ 显示套餐对比（2个套餐）
3. ✅ 月付/年付切换（年付节省30%+）
4. ✅ 当前套餐徽章标记（置顶显示）
5. ✅ 智能升级按钮状态
6. ✅ 响应式设计（支持手机/平板/桌面）

**页面布局**:

```
┌─────────────────────────────────────────┐
│   [👑 当前套餐: 普通会员 • 2026/11/10]  │ ← 置顶
│                                         │
│      选择适合您的会员套餐                │
│                                         │
│         [ 月付 ] [ 年付 省30%+ ]        │
│                                         │
│  ┌──────────────┐  ┌──────────────┐   │
│  │ [当前套餐]   │  │ [最受欢迎]   │   │ ← 徽章居中
│  │  普通会员    │  │  超级会员    │   │
│  │  ¥3800/年   │  │  ¥9800/年   │   │ ← 卡片上对齐
│  │  • 10次/月  │  │  • 50次/月  │   │
│  │  • 基础报告 │  │  • 深度洞察 │   │
│  │  [当前套餐] │  │  [立即升级] │   │
│  └──────────────┘  └──────────────┘   │
│                                         │
│            常见问题                      │
└─────────────────────────────────────────┘
```

**关键实现细节**:

```typescript
// 获取会员信息
const fetchCurrentMembership = async () => {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  const token = localStorage.getItem('wp_jwt_token');

  const response = await fetch(`${API_URL}/api/member/my-membership`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });

  const data = await response.json();
  setCurrentMembership(data);
};

// 升级按钮处理
const handleUpgrade = (tierId: number) => {
  const wpUrl = 'https://www.ucppt.com/account/orders-list';
  window.open(wpUrl, '_blank');
};

// 套餐配置
const pricingTiers: PricingTier[] = [
  {
    id: 1,
    level_name: '普通会员',
    monthlyPrice: 450,
    yearlyPrice: 3800,
    features: [
      '每月10次AI分析',
      '基础项目报告',
      '标准响应速度',
      '邮件支持',
      '7天历史记录',
    ],
    icon: Crown,
    gradient: 'from-blue-500 to-cyan-600',
  },
  {
    id: 2,
    level_name: '超级会员',
    monthlyPrice: 1180,
    yearlyPrice: 9800,
    features: [
      '每月50次AI分析',
      '深度项目洞察',
      '优先响应速度',
      '专属客服支持',
      '30天历史记录',
      '团队协作功能',
      'PDF报告导出',
    ],
    icon: Zap,
    gradient: 'from-purple-500 to-pink-600',
    popular: true,  // 最受欢迎标签
  },
];
```

**升级按钮逻辑**:

```typescript
const isCurrentPlan = currentMembership?.level === tier.id;
const canUpgrade = !currentMembership || currentMembership.level < tier.id;

// 按钮状态:
// - 当前套餐: 灰色禁用，显示"当前套餐"
// - 可升级: 渐变色，显示"升级到XX会员"
// - 已拥有更高等级: 灰色禁用，显示"已拥有更高等级"
```

---

## 前端实现

### 文件结构

```
frontend-nextjs/
├── app/
│   ├── auth/
│   │   ├── callback/page.tsx       # SSO回调页面（预留，当前使用URL Token）
│   │   └── login/page.tsx          # 登录页面
│   ├── pricing/page.tsx            # 套餐展示页面 ⭐
│   ├── page.tsx                    # 首页
│   └── layout.tsx                  # 全局布局
├── components/
│   └── layout/
│       ├── MembershipCard.tsx      # 会员信息卡片 ⭐
│       └── UserPanel.tsx           # 用户面板
├── contexts/
│   └── AuthContext.tsx             # 认证上下文 ⭐
├── lib/
│   ├── wp-auth.ts                  # WordPress认证工具
│   └── formatters.ts               # 格式化工具
└── middleware.ts                   # Next.js中间件
```

### 关键组件

#### 1. AuthContext.tsx

**功能**: 全局认证状态管理

```typescript
// 从 URL 读取 Token（优先级最高）
const urlToken = new URLSearchParams(window.location.search).get('sso_token');
if (urlToken) {
  localStorage.setItem('wp_jwt_token', urlToken);
  // 清除 URL 参数（安全优化）
  window.history.replaceState({}, '', window.location.pathname);
}

// 从 localStorage 读取 Token
const token = localStorage.getItem('wp_jwt_token');

// 验证 Token
const response = await fetch(`${API_URL}/api/auth/verify`, {
  headers: { 'Authorization': `Bearer ${token}` },
});

if (response.ok) {
  const userData = await response.json();
  setUser(userData);
}
```

#### 2. MembershipCard.tsx

**功能**: 用户面板会员信息卡片

```typescript
// 获取会员信息
const fetchMembershipInfo = async () => {
  const response = await fetch(`${API_URL}/api/member/my-membership`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  const data = await response.json();
  setMembership(data);
};

// 显示内容:
// - 会员等级（使用后端返回的 level_name）
// - 到期时间
// - 钱包余额
// - 升级按钮（level < 2 显示）

// ✅ 直接使用后端返回的 level_name（不再硬编码）
const levelBadge = membership.level_name || `VIP ${membership.level}`;

// 升级按钮条件
{membership.level < 2 && (
  <button onClick={() => window.location.href = '/pricing'}>
    升级会员
  </button>
)}
```

**会员等级颜色**:

```typescript
const getLevelColor = (level: number) => {
  switch (level) {
    case 0: return 'text-gray-400';    // 免费用户
    case 1: return 'text-blue-400';    // 普通会员
    case 2: return 'text-purple-400';  // 超级会员
    case 3: return 'text-amber-400';   // 钻石会员
    default: return 'text-gray-400';
  }
};
```

#### 3. pricing/page.tsx

**功能**: 套餐展示和升级页面

**核心特性**:
- 当前会员信息置顶显示（绿色徽章）
- 月付/年付切换（年付显示节省金额）
- 套餐卡片徽章居中对齐
- 两个卡片完美上对齐（移除 scale-105）
- 智能按钮状态（当前/可升级/已拥有更高等级）

**样式优化**:

```typescript
// 当前套餐徽章（置顶显示）
{currentMembership && currentMembership.level > 0 && (
  <div className="inline-flex items-center space-x-2 px-6 py-3 bg-green-500/10 border border-green-500/20 rounded-full mb-8 shadow-lg">
    <Crown className="w-5 h-5 text-green-500" />
    <span className="text-base font-semibold text-green-500">
      当前套餐: {currentMembership.level_name}
    </span>
    <span className="text-sm text-[var(--foreground-secondary)]">
      • 有效期至 {new Date(currentMembership.expire_date).toLocaleDateString('zh-CN')}
    </span>
  </div>
)}

// 套餐卡片布局（2列，居中）
<div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto mb-12">

// 卡片样式（移除 scale-105，保持对齐）
<div className={`relative bg-[var(--card-bg)] rounded-2xl p-8 border transition-all hover:shadow-2xl ${
  tier.popular
    ? 'border-purple-500 shadow-lg shadow-purple-500/20'
    : 'border-[var(--border-color)]'
}`}>

// 徽章居中对齐
{tier.popular && (
  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
    <div className="bg-gradient-to-r from-purple-500 to-pink-600 text-white text-xs font-bold px-4 py-1.5 rounded-full shadow-lg">
      最受欢迎
    </div>
  </div>
)}

{isCurrentPlan && (
  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
    <div className="bg-gradient-to-r from-green-500 to-emerald-600 text-white text-xs font-bold px-4 py-1.5 rounded-full shadow-lg">
      当前套餐
    </div>
  </div>
)}
```

---

## 后端API

### 文件结构

```
intelligent_project_analyzer/
├── api/
│   ├── server.py              # FastAPI 主服务器
│   ├── auth_routes.py         # 认证路由 ⭐
│   ├── auth_middleware.py     # JWT 中间件 ⭐
│   └── member_routes.py       # 会员路由 ⭐
└── services/
    └── wordpress_jwt_service.py  # WordPress JWT 服务 ⭐
```

### 核心模块

#### 1. auth_middleware.py

**功能**: JWT Token 验证中间件

```python
from fastapi import HTTPException, Header
import jwt

async def get_current_user(authorization: str = Header(None)):
    """验证 JWT Token 并返回用户信息"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="未授权")

    token = authorization[7:]  # 移除 "Bearer " 前缀

    try:
        # 使用与 WordPress 相同的密钥验证
        secret = settings.jwt_secret_key  # 从 .env 读取
        payload = jwt.decode(token, secret, algorithms=['HS256'])

        return {
            'user_id': payload.get('user_id'),
            'username': payload.get('sub'),
            'email': payload.get('email')
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的Token")
```

#### 2. member_routes.py

**功能**: 会员数据API

**核心端点**:

```python
from fastapi import APIRouter, Depends
from wpcom_member_api import WPCOMMemberAPI

router = APIRouter(prefix="/api/member", tags=["会员"])

@router.get("/my-membership")
async def get_my_membership(current_user: dict = Depends(get_current_user)):
    """获取当前用户的会员信息"""
    user_id = current_user.get('user_id')

    # 调用 WPCOM API
    api = WPCOMMemberAPI()
    result = api.get_user_membership(user_id)
    membership = result.get("membership", {})

    # 🔥 如果 membership 为空，从 meta 字段读取 VIP 数据
    if not membership or membership.get("level") is None:
        vip_type = result.get("meta", {}).get("wp_vip_type")  # "1", "2", "3"
        vip_end_date = result.get("meta", {}).get("wp_vip_end_date")  # "2026-11-10"

        if vip_type:
            membership = {
                "level": vip_type,
                "expire_date": vip_end_date or "",
                "is_active": datetime.strptime(vip_end_date, "%Y-%m-%d") > datetime.now()
            }

    # 获取钱包信息
    wallet_result = api.get_user_wallet(user_id)
    wallet_balance = float(wallet_result.get("balance", 0))

    # 格式化返回数据
    level = int(membership.get("level", "0"))
    expire_date = membership.get("expire_date", "")
    is_expired = not membership.get("is_active", False)

    # 🎨 会员等级名称映射
    level_names = {
        0: "免费用户",
        1: "普通会员",
        2: "超级会员",
        3: "钻石会员"
    }
    level_name = level_names.get(level, f"VIP {level}")

    return {
        "level": level,
        "level_name": level_name,
        "expire_date": expire_date,
        "is_expired": is_expired,
        "wallet_balance": wallet_balance
    }
```

**其他端点**:

```python
@router.get("/my-wallet")
async def get_my_wallet(current_user: dict = Depends(get_current_user)):
    """获取当前用户的钱包余额"""
    # 实现略

@router.get("/check-access/{level}")
async def check_access_level(
    level: int,
    current_user: dict = Depends(get_current_user)
):
    """检查用户是否有访问指定VIP等级的权限"""
    # 实现略
```

#### 3. wpcom_member_api.py

**功能**: WordPress WPCOM Member API 客户端

```python
import httpx
from decouple import config

class WPCOMMemberAPI:
    """WordPress WPCOM Member Pro API 客户端"""

    def __init__(self):
        self.base_url = config('WORDPRESS_URL', 'https://www.ucppt.com')
        self.username = config('WORDPRESS_ADMIN_USERNAME')
        self.password = config('WORDPRESS_ADMIN_PASSWORD')
        self.token = None

    def get_token(self):
        """获取 WordPress JWT Token"""
        if self.token:
            return self.token

        url = f"{self.base_url}/wp-json/simple-jwt-login/v1/auth"
        response = httpx.post(
            url,
            json={'username': self.username, 'password': self.password},
            verify=False,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get('data', {}).get('jwt')
            return self.token
        else:
            raise Exception(f"获取Token失败: {response.text}")

    def get_user_membership(self, user_id: int):
        """获取用户会员信息"""
        token = self.get_token()
        url = f"{self.base_url}/wp-json/custom/v1/user-membership/{user_id}"

        response = httpx.get(
            url,
            headers={'Authorization': f'Bearer {token}'},
            verify=False,
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"获取会员信息失败: {response.text}")

    def get_user_wallet(self, user_id: int):
        """获取用户钱包余额"""
        token = self.get_token()
        url = f"{self.base_url}/wp-json/custom/v1/user-wallet/{user_id}"

        response = httpx.get(
            url,
            headers={'Authorization': f'Bearer {token}'},
            verify=False,
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"获取钱包信息失败: {response.text}")
```

### 环境变量配置

**文件**: `.env`

```bash
# WordPress 配置
WORDPRESS_URL=https://www.ucppt.com
WORDPRESS_ADMIN_USERNAME=YOUR_WORDPRESS_USERNAME
WORDPRESS_ADMIN_PASSWORD=YOUR_WORDPRESS_PASSWORD

# JWT 配置（与 WordPress wp-config.php 保持一致）
JWT_SECRET_KEY=YOUR_JWT_SECRET_KEY

# Next.js 配置
NEXTJS_APP_URL=http://localhost:3000

# CORS 配置
CORS_ORIGINS=http://localhost:3000,https://www.ucppt.com,https://ai.ucppt.com

# API 配置
API_HOST=0.0.0.0
API_PORT=8000
```

**生产环境** (`.env.production`):

```bash
WORDPRESS_URL=https://www.ucppt.com
JWT_SECRET_KEY=REPLACE_WITH_PRODUCTION_SECRET
NEXTJS_APP_URL=https://ai.ucppt.com
CORS_ORIGINS=https://www.ucppt.com,https://ai.ucppt.com
```

---

## 部署指南

### 开发环境

#### 1. 启动 Python 后端

```bash
cd d:\11-20\langgraph-design
python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. 启动 Next.js 前端

```bash
cd frontend-nextjs
npm install
npm run dev
```

**访问地址**: http://localhost:3000

#### 3. WordPress 配置

1. 安装插件:
   - Next.js SSO Integration v3.0.4
   - WPCOM Member Custom API v1.0.0

2. 配置 wp-config.php:
   ```php
   define('PYTHON_JWT_SECRET', 'YOUR_JWT_SECRET_KEY');
   define('WP_ADMIN_USERNAME', 'YOUR_WORDPRESS_USERNAME');
   define('WP_ADMIN_PASSWORD', 'YOUR_WORDPRESS_PASSWORD');
   ```

3. 创建 WordPress 页面，添加短代码:
   ```
   [nextjs_app]
   ```

4. 访问嵌入页面: https://www.ucppt.com/nextjs

### 生产环境

#### 1. Python 后端部署

```bash
# 使用 Gunicorn + Uvicorn
pip install gunicorn uvicorn[standard]

gunicorn intelligent_project_analyzer.api.server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

#### 2. Next.js 前端部署

```bash
cd frontend-nextjs
npm run build
npm run start
```

或使用 PM2:

```bash
npm install -g pm2
pm2 start npm --name "nextjs-app" -- start
pm2 save
pm2 startup
```

#### 3. Nginx 反向代理

```nginx
# Next.js 前端
server {
    listen 80;
    server_name ai.ucppt.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Python API
server {
    listen 80;
    server_name api.ucppt.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 部署检查清单

- [ ] WordPress 插件已激活
- [ ] wp-config.php 已配置 JWT 密钥
- [ ] Python 后端正常运行（端口 8000）
- [ ] Next.js 前端正常运行（端口 3000）
- [ ] CORS 配置正确
- [ ] API 端点可访问 (`/api/member/my-membership` 返回 200)
- [ ] WordPress 嵌入页面显示正常
- [ ] 会员等级显示正确（"普通会员" 而不是 "VIP 1"）
- [ ] 钱包余额显示正确
- [ ] 套餐页面可访问 (`/pricing`)
- [ ] 升级按钮跳转正确

---

## 常见问题

### Q1: 会员等级显示 "VIP 1" 而不是 "普通会员"

**原因**: 前端硬编码了会员等级名称，没有使用后端返回的 `level_name` 字段

**解决方案**: 修改 `MembershipCard.tsx`:

```typescript
// ❌ 错误: 硬编码
const levelBadge = getLevelBadge(membership.level);

// ✅ 正确: 使用后端数据
const levelBadge = membership.level_name || `VIP ${membership.level}`;
```

### Q2: 钱包余额显示 ¥0.00 而不是实际余额

**原因**: 后端钱包余额解析逻辑不兼容多种返回格式

**解决方案**: 修改 `member_routes.py`:

```python
# 处理多种可能的返回格式
if isinstance(wallet_result, dict):
    if "balance" in wallet_result:
        wallet_balance = float(wallet_result.get("balance", 0))
    elif "wallet" in wallet_result:
        wallet_balance = float(wallet_result.get("wallet", {}).get("balance", 0))
    else:
        wallet_balance = 0.0
```

### Q3: 套餐页面点击升级按钮出现 404 错误

**原因**: 升级按钮指向不存在的 WordPress 页面

**解决方案**: 修改 `MembershipCard.tsx`:

```typescript
// ❌ 错误: 跳转到不存在的页面
window.open('https://www.ucppt.com/member', '_blank');

// ✅ 正确: 跳转到内部套餐页面
window.location.href = '/pricing';
```

### Q4: 套餐卡片"当前套餐"和"最受欢迎"徽章不对齐

**原因**:
1. 超级会员卡片有 `scale-105`，导致垂直错位
2. "当前套餐"徽章使用 `right-4` 右对齐

**解决方案**: 修改 `pricing/page.tsx`:

```typescript
// 移除 scale-105
className={`relative bg-[var(--card-bg)] rounded-2xl p-8 border transition-all hover:shadow-2xl ${
  tier.popular
    ? 'border-purple-500 shadow-lg shadow-purple-500/20'  // 移除 scale-105
    : 'border-[var(--border-color)]'
}`}

// "当前套餐" 徽章居中对齐
{isCurrentPlan && (
  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">  // 改为居中
    <div className="bg-gradient-to-r from-green-500 to-emerald-600 text-white text-xs font-bold px-4 py-1.5 rounded-full shadow-lg">
      当前套餐
    </div>
  </div>
)}
```

### Q5: JWT Token 验证失败 (401 Unauthorized)

**原因**: WordPress 和 Python 使用的 JWT 密钥不一致

**解决方案**:

1. 检查 `wp-config.php`:
   ```php
   define('PYTHON_JWT_SECRET', 'YOUR_JWT_SECRET_KEY');
   ```

2. 检查 `.env`:
   ```bash
   JWT_SECRET_KEY=YOUR_JWT_SECRET_KEY
   ```

3. 确保两者完全一致（包括特殊字符）

### Q6: 浏览器 localStorage 缓存了旧 Token

**症状**: 清除缓存后仍然验证失败

**解决方案**:

```javascript
// 1. 按 F12 打开开发者工具
// 2. Application → Local Storage → http://localhost:3000
// 3. 删除 wp_jwt_token 项
// 4. 刷新页面 (Ctrl+F5)

// 或者通过 WordPress 嵌入页面重新登录
// https://www.ucppt.com/nextjs
```

### Q7: 生产环境不再输出敏感日志

**配置**: 在生产环境关闭 WordPress 调试模式

```php
// wp-config.php
define('WP_DEBUG', false);  // 生产环境设置为 false
define('WP_DEBUG_LOG', false);
define('WP_DEBUG_DISPLAY', false);
```

**WordPress 插件日志**:

```php
// 仅在调试模式下输出日志
if (defined('WP_DEBUG') && WP_DEBUG) {
    error_log('[Next.js SSO v3.0] JWT 生成中...');
}
```

---

## 版本历史

### v3.0.4 (2025-12-14)
- ✅ 修复 JWT 密钥安全问题（从 wp-config.php 读取）
- ✅ 生产环境不输出敏感日志
- ✅ 套餐页面简化为 2 个套餐
- ✅ 修复套餐卡片对齐问题
- ✅ 当前套餐信息置顶显示

### v3.0.3 (2025-12-14)
- ✅ 修复 JWT 密钥配置
- ✅ 与 WPCOM Custom API 插件配合工作
- ✅ 支持从 WordPress meta 字段读取会员等级

### v3.0.1 (2025-12-13)
- ✅ 解决跨域 iframe Cookie 限制问题
- ✅ WordPress 插件直接在 iframe URL 中传递 JWT Token
- ✅ Next.js 前端优先从 URL 参数读取 Token

### v3.0.0 (2025-12-13)
- ✅ 完整的 SSO 单点登录流程
- ✅ iframe 嵌入模式
- ✅ WordPress 短代码支持

---

## 技术支持

**项目仓库**: GitHub (private)
**WordPress 网站**: https://www.ucppt.com
**Next.js 应用**: http://localhost:3000 (开发) / https://ai.ucppt.com (生产)
**API 文档**: http://localhost:8000/docs (FastAPI Swagger UI)

**关键文件清单**:

**WordPress 插件**:
- `nextjs-sso-integration-v3.php` - SSO 插件
- `wpcom-custom-api-v1.0.0.php` - 会员 API 插件

**前端**:
- `frontend-nextjs/app/pricing/page.tsx` - 套餐页面
- `frontend-nextjs/components/layout/MembershipCard.tsx` - 会员卡片
- `frontend-nextjs/contexts/AuthContext.tsx` - 认证上下文

**后端**:
- `intelligent_project_analyzer/api/member_routes.py` - 会员 API
- `intelligent_project_analyzer/api/auth_middleware.py` - JWT 中间件
- `wpcom_member_api.py` - WordPress API 客户端

---

**最后更新**: 2025-12-14
**文档版本**: 1.0
**维护者**: UCPPT Team
