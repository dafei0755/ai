# 网页内容深度提取方案 v7.195

## 实施摘要

实现了 **Trafilatura + Playwright** 混合网页内容提取方案，解决 Bocha 搜索只返回 snippet（150-300字符）导致 LLM 无法充分利用来源内容的问题。

## 更新内容

### 1. 新增模块

**[web_content_extractor.py](intelligent_project_analyzer/services/web_content_extractor.py)**

混合网页内容提取器，提供：
- **Trafilatura**：静态网页内容提取（高效轻量，0.5-3秒）
- **Playwright**：动态网页渲染提取（JavaScript/SPA支持，3-10秒）

### 2. 智能策略

```
用户请求 → Bocha 搜索（snippet）
                ↓
          深度内容提取（Top-5 来源）
                ↓
        ┌───────────────────────────┐
        │ 1. 低质量站点？→ 跳过      │
        │ 2. 已知动态站点？→ Playwright │
        │ 3. 其他 → Trafilatura     │
        │    └── 失败/不足？→ Playwright │
        └───────────────────────────┘
                ↓
         返回增强后的来源（最多 2000 字内容）
```

### 3. 已知动态站点

自动使用 Playwright：
- 社交媒体：weibo.com, zhihu.com, xiaohongshu.com
- 设计网站：archdaily.cn, gooood.cn, pinterest.com
- 电商平台：taobao.com, jd.com

### 4. 低质量站点过滤

自动跳过：
- baijiahao.baidu.com
- zhidao.baidu.com
- tieba.baidu.com
- wenku.baidu.com

## 配置选项

在 `.env` 文件中添加：

```env
# 网页内容深度提取配置（v7.195）
DEEP_CONTENT_EXTRACTION_ENABLED=true    # 是否启用深度提取
DEEP_CONTENT_TOP_N=5                    # 每轮最多深度提取的来源数
CONTENT_EXTRACTION_MAX_LENGTH=2000      # 每页最大提取字符数
CONTENT_EXTRACTION_MIN_LENGTH=300       # 低于此长度触发 Playwright
CONTENT_EXTRACTION_TIMEOUT=10           # 超时秒数
```

## 依赖更新

**requirements.txt**
```
trafilatura>=1.6.0  # 静态网页内容提取
# playwright 已在系统中安装
```

安装：
```bash
pip install trafilatura
```

## 测试脚本

```bash
python -B scripts/test_web_content_extractor.py
```

测试输出示例：
```
📊 批量提取测试
📌 https://www.archdaily.cn/cn...
   方法=playwright | 长度=2000字 | 耗时=4.21秒

📌 https://gooood.cn/...
   方法=playwright | 长度=1113字 | 耗时=3.01秒

📌 https://www.designboom.com/...
   方法=trafilatura | 长度=1595字 | 耗时=2.34秒
```

## 代码变更

### ucppt_search_engine.py

1. **新增导入**
```python
from intelligent_project_analyzer.services.web_content_extractor import (
    get_web_content_extractor,
    ExtractionResult,
    ExtractionMethod,
)
```

2. **新增配置常量**
```python
DEEP_CONTENT_EXTRACTION_ENABLED = os.getenv("DEEP_CONTENT_EXTRACTION_ENABLED", "true").lower() == "true"
DEEP_CONTENT_TOP_N = int(os.getenv("DEEP_CONTENT_TOP_N", "5"))
```
- 搜索完成后调用 `_enhance_sources_with_deep_content()`
- 对 Top-5 来源进行深度内容提取
- 内容更长则替换原 snippet
    sources: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """对搜索结果进行深度内容提取"""
| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 来源内容长度 | 150-300字 | 最多2000字 |
| LLM 可利用信息量 | 极少 | 充分 |
| 答案引用质量 | 仅标题参考 | 内容详实 |
| 每轮延迟增加 | 0 | 约10-20秒（Top-5） |

## 注意事项

1. **性能影响**：深度提取会增加每轮搜索约 10-20 秒延迟
2. **资源消耗**：Playwright 需要启动浏览器，占用内存
3. **网络依赖**：部分网站可能有反爬措施
4. **禁用方法**：设置 `DEEP_CONTENT_EXTRACTION_ENABLED=false`
...up
## 后续优化方向

1. **内容缓存**：对相同 URL 进行缓存，避免重复提取
2. **优先级调整**：根据域名可信度调整提取优先级
3. **异步预取**：在 LLM 思考阶段预取下一轮可能的来源
4. **质量评估**：对提取内容进行质量评分，过滤噪音

---

**版本**: v7.195
**日期**: 2026-01-10
**作者**: AI Assistant
