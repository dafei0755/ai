# TikHub 社交媒体搜索集成实施报告 v7.162

## 📋 实施概要

**版本**: v7.162
**日期**: 2026-01-07
**需求**: 将 TikHub.io 社交媒体 API 集成到博查搜索工具，作为子数据源扩展搜索覆盖范围

## ✅ 实施完成

### 1. 配置系统更新

**文件**: `intelligent_project_analyzer/settings.py`

在 `BochaConfig` 类中新增 TikHub 子配置:

```python
# TikHub 子数据源配置 (v7.162)
tikhub_enabled: bool = Field(default=False, alias="BOCHA_TIKHUB_ENABLED")
tikhub_api_key: str = Field(default="", alias="BOCHA_TIKHUB_API_KEY")
tikhub_base_url: str = Field(default="https://api.tikhub.io", alias="BOCHA_TIKHUB_BASE_URL")
tikhub_platforms: str = Field(default="xiaohongshu,douyin", alias="BOCHA_TIKHUB_PLATFORMS")
tikhub_count: int = Field(default=5, alias="BOCHA_TIKHUB_COUNT")
```

### 2. 环境变量配置

**文件**: `.env.example`

```bash
# TikHub 社交媒体搜索配置 (博查子数据源)
BOCHA_TIKHUB_ENABLED=false
BOCHA_TIKHUB_API_KEY=your_tikhub_api_key_here
BOCHA_TIKHUB_BASE_URL=https://api.tikhub.io
BOCHA_TIKHUB_PLATFORMS=xiaohongshu,douyin
BOCHA_TIKHUB_COUNT=5
```

### 3. 依赖添加

**文件**: `requirements.txt`

```
tikhub>=1.13.0
```

### 4. 搜索工具增强

**文件**: `intelligent_project_analyzer/agents/bocha_search_tool.py`

#### 新增初始化参数

```python
def __init__(
    self,
    # ... 原有参数 ...
    # 🆕 v7.162: TikHub子数据源
    tikhub_enabled: bool = False,
    tikhub_api_key: str = "",
    tikhub_base_url: str = "https://api.tikhub.io",
    tikhub_platforms: str = "xiaohongshu,douyin",
    tikhub_count: int = 5,
):
```

#### 新增方法

| 方法 | 功能 |
|------|------|
| `_search_tikhub(query)` | 聚合搜索所有配置的社交媒体平台 |
| `_search_tikhub_platform(platform, query)` | 搜索单个平台 |
| `_normalize_xiaohongshu_result(item)` | 标准化小红书结果 |
| `_normalize_douyin_result(item)` | 标准化抖音结果 |
| `_normalize_wechat_channels_result(item)` | 标准化视频号结果 |

## 🔧 使用方式

### 1. 配置 `.env` 文件

```bash
# 启用 TikHub 子数据源
BOCHA_TIKHUB_ENABLED=true
BOCHA_TIKHUB_API_KEY=你的TikHub密钥

# 可选：指定搜索平台（逗号分隔）
BOCHA_TIKHUB_PLATFORMS=xiaohongshu,douyin,wechat_channels

# 可选：每个平台返回的结果数
BOCHA_TIKHUB_COUNT=5

# 国内用户推荐使用国内节点
BOCHA_TIKHUB_BASE_URL=https://api.tikhub.dev
```

### 2. 支持的平台

| 平台ID | 名称 | 搜索内容 |
|--------|------|----------|
| `xiaohongshu` | 小红书 | 图文笔记、视频笔记 |
| `douyin` | 抖音 | 短视频 |
| `wechat_channels` | 微信视频号 | 视频内容 |

### 3. 获取 TikHub API 密钥

1. 访问 [tikhub.io](https://tikhub.io)
2. 注册账号并登录
3. 进入控制台创建 API Key
4. 将密钥填入 `.env` 的 `BOCHA_TIKHUB_API_KEY`

## 📊 搜索结果格式

TikHub 返回的结果会标准化为以下格式:

```json
{
  "title": "[小红书] 咖啡店设计灵感分享",
  "url": "https://www.xiaohongshu.com/explore/xxxxx",
  "snippet": "今天分享一家超美的咖啡店...",
  "summary": "完整描述内容",
  "siteName": "小红书",
  "author": "设计师小美",
  "source_type": "social",
  "platform": "xiaohongshu",
  "liked_count": 1234
}
```

## 🔍 调试日志

启用 TikHub 后，日志会显示:

```
✅ TikHub社交媒体搜索已启用: platforms=['xiaohongshu', 'douyin']
✅ [TikHub/xiaohongshu] Found 5 results
✅ [TikHub/douyin] Found 5 results
✅ [Bocha] Added 10 TikHub social media results
```

## ⚠️ 注意事项

1. **API 费用**: TikHub 是付费 API，请关注用量
2. **网络**: 国内用户建议使用 `api.tikhub.dev` 节点
3. **限流**: 默认每平台返回 5 条结果，可通过 `BOCHA_TIKHUB_COUNT` 调整
4. **降级**: 如果 TikHub 搜索失败，不影响博查网页搜索正常运行

## 📁 修改文件清单

| 文件 | 修改类型 |
|------|----------|
| `intelligent_project_analyzer/settings.py` | 新增配置字段 |
| `intelligent_project_analyzer/agents/bocha_search_tool.py` | 新增搜索逻辑 |
| `.env.example` | 新增配置项 |
| `requirements.txt` | 新增依赖 |
