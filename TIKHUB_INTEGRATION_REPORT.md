# TikHub 社交媒体搜索集成报告

**版本**: v7.162
**日期**: 2026-01-09
**状态**: ✅ 已完成

## 概述

成功将 TikHub.io 社交媒体搜索 API 集成到博查搜索工具 (BochaSearchTool) 中，作为子数据源实现社交媒体内容搜索能力。

## 平台支持状态

| 平台 | 状态 | API类型 | 说明 |
|------|------|---------|------|
| 小红书 (Xiaohongshu) | ✅ 已支持 | SDK | `XiaohongshuWeb.search_notes` |
| 抖音 (Douyin) | ✅ 已支持 | HTTP | `Douyin-Search-API` |
| 微信视频号 (WeChat Channels) | ❌ 暂不支持 | - | API需要特殊权限 |

## 配置方式

### 1. 环境变量 (.env)

```bash
# TikHub 社交媒体搜索配置
BOCHA_TIKHUB_ENABLED=true
BOCHA_TIKHUB_API_KEY=your_api_key_here
BOCHA_TIKHUB_BASE_URL=https://api.tikhub.dev  # 中国大陆用户
BOCHA_TIKHUB_PLATFORMS=xiaohongshu,douyin
BOCHA_TIKHUB_COUNT=5
```

### 2. API域名选择

- **中国大陆**: `https://api.tikhub.dev` (无需代理)
- **海外用户**: `https://api.tikhub.io`

## 技术实现

### 文件修改

1. **settings.py**: 添加 TikHub 配置字段到 `BochaConfig`
2. **bocha_search_tool.py**: 实现 TikHub 搜索集成
   - `_search_tikhub()`: 聚合多平台搜索
   - `_search_tikhub_platform()`: 单平台搜索
   - `_normalize_xiaohongshu_result()`: 小红书结果标准化
   - `_normalize_douyin_result()`: 抖音结果标准化
3. **requirements.txt**: 添加 `tikhub>=1.13.0`
4. **.env / .env.example**: 添加 TikHub 配置项

### API调用方式

**小红书** (SDK):
```python
await client.XiaohongshuWeb.search_notes(
    keyword=query,
    page=1,
    sort="general"
)
```

**抖音** (HTTP POST):
```python
POST /api/v1/douyin/search/fetch_video_search_v1
{
    "keyword": "搜索词",
    "offset": 0,
    "count": 5,
    "sort_type": "0",       # 字符串类型!
    "publish_time": "0",
    "filter_duration": "0"
}
```

## 测试验证

运行测试脚本:
```bash
python scripts/test_bocha_tikhub.py
```

预期输出:
```
✅ [TikHub/xiaohongshu] Found 5 results
✅ [TikHub/douyin] Found 5 results

📊 Platform Summary:
  - xiaohongshu: 5 results
  - douyin: 5 results
```

## 数据结构

### 标准化输出格式

```python
{
    "title": "[小红书] 笔记标题",
    "url": "https://www.xiaohongshu.com/explore/...",
    "snippet": "内容摘要...",
    "summary": "完整描述...",
    "siteName": "小红书",
    "author": "作者昵称",
    "source_type": "social",
    "platform": "xiaohongshu",
    "liked_count": 1234
}
```

## 后续优化建议

1. **微信视频号**: 联系 TikHub 支持获取 API 权限
2. **缓存机制**: 添加结果缓存减少 API 调用
3. **更多平台**: TikHub 支持微博、B站等，可按需扩展

## 参考资料

- TikHub 文档: https://docs.tikhub.io/
- TikHub API: https://api.tikhub.io/
- TikHub SDK: https://github.com/TikHub/TikHub-API-Python-SDK
