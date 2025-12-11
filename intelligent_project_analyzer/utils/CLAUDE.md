# 实用工具模块 - AI 协作文档

> 📍 **路径导航**: [根目录](../../CLAUDE.md) > [intelligent_project_analyzer](../) > **utils**

---

## 📋 模块职责

**实用工具函数 (Utilities)**

本模块提供通用的工具函数，包括配置管理、意图解析等。

### 核心功能
- ⚙️ **配置管理**: 加载和验证环境配置
- 💬 **意图解析器**: 理解用户自然语言输入

---

## 📁 文件结构

```
utils/
├── config.py          # 配置管理工具
└── intent_parser.py   # 用户意图解析器
```

---

## 🔑 核心工具

### 1. 意图解析器 (Intent Parser)

**职责**: 将用户的自然语言输入解析为标准化的意图和内容。

**支持的意图**:
- `approve`: 批准/确认/同意
- `reject`: 拒绝/不同意
- `revise`: 修改/重新分析
- `modify`: 修改（带内容）
- `skip`: 跳过
- `add`: 补充信息

**使用示例**:
```python
from intelligent_project_analyzer.utils.intent_parser import parse_user_intent

# 解析用户输入
result = parse_user_intent(
    user_response="我同意这个方案",
    context="需求确认",
    stage="requirements_confirmation"
)

print(result)
# {
#     "intent": "approve",
#     "method": "keyword",
#     "content": "",
#     "confidence": 1.0
# }
```

**解析方法**:
1. **字典格式检测**: 优先识别 `{"action": "..."}`
2. **关键词匹配**: 匹配预定义关键词（同意、拒绝等）
3. **LLM 解析**: 使用 LLM 理解复杂自然语言（可选）

**关键词映射**:
```python
INTENT_KEYWORDS = {
    "approve": ["同意", "确认", "批准", "好的", "可以", "approve", "yes"],
    "reject": ["拒绝", "不同意", "不行", "reject", "no"],
    "skip": ["跳过", "不填", "skip"],
    "modify": ["修改", "改", "modify", "change"],
    "revise": ["重新分析", "重做", "revise"],
    "add": ["补充", "添加", "追加", "add"]
}
```

---

### 2. 配置管理 (Config)

**职责**: 加载和验证环境变量配置。

**使用示例**:
```python
from intelligent_project_analyzer.utils.config import load_config

config = load_config()
print(config["openai_api_key"])
print(config["tavily_api_key"])
```

**注**: 本项目已迁移到 Pydantic Settings，优先使用 `intelligent_project_analyzer/settings.py`。

---

## 🧪 测试

**测试意图解析器**:
```python
def test_intent_parser():
    test_cases = [
        ("同意", "approve"),
        ("拒绝", "reject"),
        ("我要修改这个地方", "modify"),
        ("跳过问卷", "skip"),
        ("补充一些信息", "add")
    ]

    for text, expected_intent in test_cases:
        result = parse_user_intent(text, context="测试", stage="test")
        assert result["intent"] == expected_intent
```

---

## 📚 相关资源

- [人机交互节点](../interaction/CLAUDE.md)
- [统一配置系统](../settings.py)

---

**最后更新**: 2025-11-16
**覆盖率**: 100%
**文档版本**: 1.0.0
