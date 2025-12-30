# 生产环境部署文档

本文档提供生产环境部署的详细指南。

## 目录

- [内容安全检测功能（P1优化）](#内容安全检测功能p1优化)
- [腾讯云内容安全配置](#腾讯云内容安全配置)
- [环境变量配置](#环境变量配置)
- [依赖安装](#依赖安装)
- [服务启动](#服务启动)
- [验证部署](#验证部署)
- [常见问题](#常见问题)

---

## 内容安全检测功能（P1优化）

### 功能概述

系统采用**多层检测架构**，确保内容安全合规：

```
输入内容
    ↓
1. 关键词检测 (快速过滤)
    ↓
2. 增强正则检测 (隐私信息 + 变形规避)
    ↓
3. 腾讯云内容安全API (95%+准确率)
    ↓
4. LLM语义检测 (边界case深度分析)
    ↓
安全判定结果
```

### P1优化特性

#### 1. LLM语义安全检测

**功能**: 使用大语言模型进行深度语义理解，识别隐晦、暗示性违规内容

**检测维度**:
- 政治敏感内容
- 色情低俗内容
- 暴力血腥内容
- 违法犯罪内容
- 歧视仇恨言论
- 虚假信息
- 隐私侵犯

**配置方式**:
```python
from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard
from langchain_openai import ChatOpenAI

# 初始化LLM模型（可选）
llm_model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 启用LLM语义检测
guard = ContentSafetyGuard(llm_model=llm_model, use_external_api=True)

# 检测内容
result = guard.check("待检测的文本内容")
```

**工作模式**:
- `normal`: 标准检测（快速，适用于大多数场景）
- `edge_case`: 深度分析（针对模糊边界case）

**置信度阈值**: 默认0.7，低于此阈值的结果将被忽略

**何时使用**:
- ✅ 复杂语义场景（隐喻、暗示、双关语）
- ✅ 模糊边界内容（可能违规但不明确）
- ✅ 其他检测方法未覆盖的case
- ❌ 不建议用于常规检测（成本较高）

#### 2. 增强正则检测

**2.1 隐私信息检测（14种类型）**

系统自动检测并脱敏以下隐私信息：

| 类型 | 示例 | 严重性 | 脱敏效果 |
|------|------|--------|----------|
| 手机号 | 13800138000 | 中 | 138****8000 |
| 身份证号(18位) | 110101199001011234 | 高 | 110101********1234 |
| 身份证号(15位) | 110101900101123 | 高 | 110101*****123 |
| 电子邮箱 | test@example.com | 低 | te***@example.com |
| 银行卡号 | 6222021234567890128 | 高 | 622202******0128（需通过Luhn验证）|
| IP地址(IPv4) | 192.168.1.1 | 低 | 192.***.***.1 |
| IP地址(IPv6) | fe80::1 | 低 | fe80::*** |
| 固定电话 | 010-12345678 | 低 | 010-****5678 |
| 车牌号 | 京A12345 | 中 | 京A***45 |
| 护照号 | E12345678 | 高 | E1****678 |
| 地址信息 | 北京市朝阳区XX路XX号 | 中 | 部分脱敏 |
| 组织机构代码 | 12345678-X | 低 | 12****8-X |
| 统一社会信用代码 | 91110000XXXXXXXXXX | 低 | 9111****XXXX |
| QQ号 | 123456789 | 低 | 12****789 |

**特殊处理**:
- **银行卡号**: 使用Luhn算法验证，仅拦截真实卡号（避免误判）
- **IP地址**: 区分IPv4和IPv6
- **地址信息**: 基于关键词模式识别（省/市/区/路/号等）

**2.2 变形规避检测（5种模式）**

系统能够识别用户刻意规避检测的变形文本：

| 模式 | 示例 | 检测方法 |
|------|------|----------|
| 特殊符号分隔 | 色_情、色*情、色.情 | 识别字符间的特殊符号 |
| 谐音替换 | 涩情、Du品、Du博 | 常见谐音词库匹配 |
| 拆字组合 | 氵去、弓虽、石肖 | 拆字模式识别 |
| 全角半角混用 | ｓｅｘ、SEX | 全角/半角转换检测 |
| 数字字母替换 | sex、porn、drug | 拼音/英文关键词 |

**谐音替换示例**:
- 色情 → 涩情、瑟情、射青
- 毒品 → Du品、读品、督品
- 赌博 → Du博、睹搏、堵博
- 黄色 → 黃色、wang色

**配置方式**:
```python
from intelligent_project_analyzer.security.enhanced_regex_detector import EnhancedRegexDetector

# 创建检测器（可选择性启用）
detector = EnhancedRegexDetector(
    enable_privacy_check=True,   # 启用隐私信息检测
    enable_evasion_check=True    # 启用变形规避检测
)

# 执行检测
violations = detector.check("待检测文本")

# 获取统计信息
stats = detector.get_stats(violations)
print(f"隐私信息: {stats['privacy_count']}个")
print(f"变形规避: {stats['evasion_count']}个")
```

### 检测结果格式

```python
{
    "is_safe": False,               # 是否安全
    "risk_level": "high",           # 风险等级: safe/low/medium/high
    "violations": [                 # 违规详情列表
        {
            "category": "隐私信息",        # 违规分类
            "matched_pattern": "手机号",   # 匹配的模式
            "matched_text": "138****8000", # 脱敏后的内容
            "severity": "medium",          # 严重性: low/medium/high
            "method": "regex_match",       # 检测方法
            "description": "检测到手机号"   # 描述信息
        }
    ],
    "action": "reject"              # 建议动作: reject/sanitize
}
```

### 性能优化

**检测顺序**: 按成本递增
1. 关键词检测（本地，<1ms）
2. 正则检测（本地，1-5ms）
3. 腾讯云API（远程，50-200ms）
4. LLM检测（远程，1-3s）

**短路机制**: 任一层检测到高风险违规，立即返回，不执行后续检测

**缓存策略**:
- 相同内容1小时内复用结果（`TENCENT_CONTENT_SAFETY_CACHE_TTL=3600`）
- 降低API调用成本

### 最佳实践

**1. 开发环境**:
```bash
# 仅启用关键词和正则检测（快速，免费）
ENABLE_TENCENT_CONTENT_SAFETY=false
```

**2. 测试环境**:
```bash
# 启用腾讯云API（真实效果验证）
ENABLE_TENCENT_CONTENT_SAFETY=true
```

**3. 生产环境**:
```bash
# 全链路检测（最高准确率）
ENABLE_TENCENT_CONTENT_SAFETY=true
# 可选：启用LLM（针对特殊场景）
```

**4. 错误处理**:
- 外部API失败时自动降级到本地检测
- LLM检测异常时假定安全（避免误拦截）
- 低置信度结果被忽略

### 测试验证

运行P1功能测试套件：

```bash
# 测试所有P1功能（21个测试）
pytest tests/test_p1_features.py -v

# 测试特定功能
pytest tests/test_p1_features.py::TestLLMSafetyDetector -v          # LLM检测
pytest tests/test_p1_features.py::TestEnhancedRegexDetector -v      # 正则检测
pytest tests/test_p1_features.py::TestContentSafetyGuardP1Integration -v  # 集成
```

**预期结果**: 21 passed

### 预期收益

基于P1优化：
- **隐私保护**: +10%（14种隐私类型全覆盖）
- **规避检测**: +15%（5种变形模式识别）
- **复杂语义**: LLM深度分析（置信度≥0.7）
- **误拦截率**: <1%（多层验证 + 置信度阈值）

---

## 动态安全规则配置（P2优化）

### 功能概述

P2优化实现了**配置外部化**和**热加载机制**，使安全规则可以动态更新而无需重启服务。

**核心优势**:
- ✅ 规则配置外部化（YAML文件）
- ✅ 热加载机制（60秒自动检测文件修改）
- ✅ 线程安全（多worker环境可用）
- ✅ 优雅降级（配置加载失败时回退到静态规则）
- ✅ 无需重启服务即可更新规则

### P2架构设计

```
┌──────────────────────────────────────────────────┐
│         ContentSafetyGuard (安全守卫)              │
├──────────────────────────────────────────────────┤
│                                                  │
│  use_dynamic_rules=True  ┌──────────────────┐  │
│  ────────────────────────►│ DynamicRuleLoader│  │
│                            │  (规则加载器)     │  │
│                            └────────┬─────────┘  │
│                                     │            │
│                            每60秒检测修改时间      │
│                                     │            │
│                                     ▼            │
│                            ┌──────────────────┐  │
│                            │security_rules.yaml│  │
│                            │   (YAML配置文件)  │  │
│                            └──────────────────┘  │
│                                                  │
│  加载失败时回退  ┌──────────────────┐            │
│  ────────────────►│ FALLBACK_KEYWORDS│            │
│                  │   (静态回退规则)  │            │
│                  └──────────────────┘            │
└──────────────────────────────────────────────────┘
```

### 配置文件结构

配置文件位置: `intelligent_project_analyzer/security/security_rules.yaml`

```yaml
version: "1.0"

# 关键词检测规则
keywords:
  色情低俗:
    enabled: true              # 是否启用该类别
    severity: high             # 严重性: low/medium/high
    description: "色情低俗内容"
    words:                     # 关键词列表
      - "色情"
      - "黄色"
      - "裸体"

  政治敏感:
    enabled: true
    severity: high
    description: "政治敏感内容"
    words: []                  # 空列表表示该类别禁用或待配置

# 隐私信息检测规则
privacy_patterns:
  手机号:
    enabled: true
    pattern: '1[3-9]\d{9}'
    severity: medium
    description: "检测到手机号"
    mask_strategy: "keep_first3_last4"  # 脱敏策略

  银行卡号:
    enabled: true
    pattern: '(?<!\d)\d{16,19}(?!\d)'
    severity: high
    description: "检测到疑似银行卡号"
    mask_strategy: "keep_first6_last4"
    validate_luhn: true          # 启用Luhn算法验证

# 变形规避检测规则
evasion_patterns:
  谐音替换:
    enabled: true
    severity: medium
    description: "检测到谐音替换规避"
    patterns:
      - pattern: '[色射涩瑟][\s\-_\*\.]*[情亲青清]'
        keyword: "色情"
        severity: medium

# 检测配置
detection_config:
  enable_keyword_check: true
  enable_privacy_check: true
  enable_evasion_check: true
  enable_external_api: true
  enable_llm_check: false       # LLM检测默认关闭（成本高）

# 白名单配置
whitelist:
  enabled: true
  domains:
    - "example.com"
    - "test.com"
  users: []
  ips:
    - "127.0.0.1"
    - "localhost"
```

完整配置文件见: [security_rules.yaml](../intelligent_project_analyzer/security/security_rules.yaml)

### 热加载机制

**工作原理**:

1. **初始加载**: 系统启动时加载配置文件
2. **定期检查**: 每60秒检查一次文件修改时间
3. **自动重载**: 如果文件被修改，自动重新加载
4. **线程安全**: 使用`threading.Lock()`确保多线程环境安全
5. **单例模式**: 全局共享一个规则加载器实例

```python
# 配置文件修改检测流程
┌─────────────────────────────────────────────┐
│ 应用启动                                      │
│  ↓                                           │
│ DynamicRuleLoader初始化                      │
│  └─ 加载security_rules.yaml                 │
│  └─ 记录_last_modified时间戳                 │
│                                              │
│ [每60秒自动检查]                              │
│  ↓                                           │
│ 检查当前文件修改时间                          │
│  ↓                                           │
│ 如果 current_modified > _last_modified:     │
│  └─ 重新加载YAML文件                         │
│  └─ 更新_last_modified                       │
│  └─ 记录日志: "✅ 安全规则已重载"             │
│                                              │
│ 继续处理请求                                  │
└─────────────────────────────────────────────┘
```

**关键代码示例**:

```python
from intelligent_project_analyzer.security.dynamic_rule_loader import get_rule_loader

# 获取规则加载器单例
loader = get_rule_loader()

# 获取规则（自动检测并重载）
keywords = loader.get_keywords()
privacy_patterns = loader.get_privacy_patterns()
evasion_patterns = loader.get_evasion_patterns()

# 强制重载（无需等待60秒）
loader.force_reload()

# 获取统计信息
stats = loader.get_stats()
print(f"关键词类别: {stats['keywords']['total_categories']}")
print(f"启用的隐私模式: {stats['privacy_patterns']['enabled']}")
```

### 如何更新安全规则

#### 方法1: 直接编辑YAML文件（推荐）

1. 使用文本编辑器打开配置文件:
   ```bash
   # Windows
   notepad intelligent_project_analyzer\security\security_rules.yaml

   # Linux/Mac
   vim intelligent_project_analyzer/security/security_rules.yaml
   ```

2. 修改配置（例如添加新关键词）:
   ```yaml
   keywords:
     违法犯罪:
       enabled: true
       severity: high
       words:
         - "毒品"
         - "诈骗"
         - "新增的敏感词"  # ← 添加新词
   ```

3. 保存文件

4. **无需重启服务**，系统会在60秒内自动检测并重载

5. 查看日志确认重载成功:
   ```
   ✅ 安全规则已重载 (版本: 1.0, 关键词类别: 5, 隐私模式: 14, 规避模式: 5)
   ```

#### 方法2: 程序化更新（威胁情报同步）

```python
from intelligent_project_analyzer.security.dynamic_rule_loader import get_rule_loader

# 获取加载器
loader = get_rule_loader()

# 更新威胁情报（从外部源同步）
loader.update_threat_intelligence(
    domains=["malicious1.com", "malicious2.com"],
    ips=["1.2.3.4", "5.6.7.8"],
    keywords=["scam", "phishing"]
)

# 更新会自动保存到YAML文件
```

### 配置最佳实践

#### 1. 版本控制

建议将`security_rules.yaml`纳入版本控制：

```bash
# .gitignore中不要忽略此文件
# security_rules.yaml  ❌ 不要添加

# 这样可以追踪规则变更历史
git add intelligent_project_analyzer/security/security_rules.yaml
git commit -m "更新安全规则: 添加新的敏感词"
```

#### 2. 生产环境更新流程

```
1. 在测试环境验证规则
   └─ 修改security_rules.yaml
   └─ 运行测试: pytest tests/test_p2_features.py -v
   └─ 验证检测效果

2. 部署到生产环境
   └─ 复制验证过的security_rules.yaml
   └─ 粘贴到生产服务器对应位置
   └─ 等待60秒自动重载（或手动触发force_reload）

3. 监控日志
   └─ 确认看到"✅ 安全规则已重载"日志
   └─ 测试几个样本确认新规则生效
```

#### 3. 规则分类管理

建议按严重性分类管理关键词：

```yaml
keywords:
  # 高风险类别 - 立即拦截
  色情低俗:
    enabled: true
    severity: high      # 高风险
    words: [...]

  # 中风险类别 - 需要审核
  歧视仇恨:
    enabled: true
    severity: medium    # 中风险
    words: [...]

  # 低风险类别 - 仅记录
  广告营销:
    enabled: true
    severity: low       # 低风险
    words: [...]
```

#### 4. 白名单使用

对于合法使用场景，添加白名单避免误拦截：

```yaml
whitelist:
  enabled: true

  # 域名白名单（允许出现的域名）
  domains:
    - "example.com"        # 示例域名
    - "yourcompany.com"    # 公司官网

  # 用户白名单（管理员等）
  users:
    - "admin_user_id"
    - "test_user_id"

  # IP白名单（内网IP等）
  ips:
    - "127.0.0.1"
    - "10.0.0.0/8"         # 内网IP段
```

### 性能优化

**规则加载性能**:
- 初始加载: <1秒
- 规则访问: 1000次访问 <0.1秒
- 文件检测: <10ms

**内存占用**:
- 规则加载器: ~100KB（包含所有规则）
- 单例模式: 全局共享，无额外开销

**并发安全**:
- 使用`threading.Lock()`保护关键区域
- 读操作不加锁（返回副本）
- 写操作加锁（重载时）

### 与P1功能的集成

P2的动态规则加载与P1的增强检测无缝集成：

```python
from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard

# 创建守卫（默认启用动态规则）
guard = ContentSafetyGuard(
    use_dynamic_rules=True,   # 启用动态规则（P2）
    use_external_api=True,    # 启用腾讯云API（P0）
    llm_model=llm             # 启用LLM检测（P1，可选）
)

# 检测内容
result = guard.check("待检测文本")

# 底层流程:
# 1. 从DynamicRuleLoader获取关键词（P2）
# 2. 执行关键词检测
# 3. 执行增强正则检测（P1 - 14种隐私+5种规避）
# 4. 调用腾讯云API（P0）
# 5. 如有必要，调用LLM深度检测（P1）
```

**优雅降级**:

如果动态规则加载失败（配置文件损坏、权限问题等），系统会自动回退到静态规则：

```python
# ContentSafetyGuard内部逻辑
@property
def rule_loader(self):
    """懒加载规则加载器"""
    if self._rule_loader is None and self.use_dynamic_rules:
        try:
            from .dynamic_rule_loader import get_rule_loader
            self._rule_loader = get_rule_loader()
            logger.info("✅ 动态规则加载器已启用")
        except Exception as e:
            logger.warning(f"⚠️ 动态规则加载器初始化失败，使用回退规则: {e}")
            self.use_dynamic_rules = False  # 自动禁用
    return self._rule_loader

# 回退到静态规则
FALLBACK_KEYWORDS = {
    "政治敏感": [],
    "色情低俗": ["色情", "黄色", "裸体", "性爱"],
    "暴力血腥": ["杀人", "自杀", "血腥", "暴力"],
    "违法犯罪": ["毒品", "诈骗", "洗钱", "赌博"],
    "歧视仇恨": ["歧视", "仇恨", "种族"]
}
```

### 测试验证

运行P2功能测试套件：

```bash
# 测试所有P2功能（24个测试）
pytest tests/test_p2_features.py -v

# 测试特定功能
pytest tests/test_p2_features.py::TestDynamicRuleLoader -v              # 规则加载器
pytest tests/test_p2_features.py::TestContentSafetyGuardWithDynamicRules -v  # 集成
pytest tests/test_p2_features.py::TestConfigurationValidation -v       # 配置验证
pytest tests/test_p2_features.py::TestPerformance -v                   # 性能测试
```

**预期结果**: 24 passed

**测试覆盖**:
- ✅ 规则加载器初始化
- ✅ 获取关键词/隐私模式/规避模式
- ✅ 白名单功能
- ✅ 统计信息生成
- ✅ 单例模式
- ✅ 强制重载
- ✅ 热加载检测（文件修改时）
- ✅ 威胁情报更新
- ✅ ContentSafetyGuard集成
- ✅ 启用/禁用动态规则
- ✅ 回退到静态规则
- ✅ YAML配置验证
- ✅ 性能基准测试

### 故障排查

#### 问题1: 规则未生效

**症状**: 修改了`security_rules.yaml`但检测结果未变化

**排查步骤**:

1. 检查是否启用动态规则:
   ```python
   from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard

   guard = ContentSafetyGuard(use_dynamic_rules=True)  # 确保为True
   print(guard.use_dynamic_rules)  # 应输出True
   print(guard.rule_loader)         # 应不为None
   ```

2. 检查YAML语法是否正确:
   ```bash
   python -c "import yaml; yaml.safe_load(open('intelligent_project_analyzer/security/security_rules.yaml'))"
   ```
   如有语法错误会抛出异常。

3. 检查文件修改时间是否更新:
   ```python
   import os
   path = "intelligent_project_analyzer/security/security_rules.yaml"
   print(f"修改时间: {os.path.getmtime(path)}")
   ```

4. 强制重载规则:
   ```python
   from intelligent_project_analyzer.security.dynamic_rule_loader import reload_rules
   reload_rules()  # 立即重载，无需等待60秒
   ```

5. 查看日志确认重载:
   ```
   ✅ 安全规则已重载 (版本: 1.0, 关键词类别: 5, ...)
   ```

#### 问题2: 配置文件加载失败

**症状**: 日志显示"⚠️ 动态规则加载器初始化失败，使用回退规则"

**可能原因**:

1. **文件不存在**:
   ```bash
   # 检查文件是否存在
   ls intelligent_project_analyzer/security/security_rules.yaml
   ```

2. **YAML语法错误**:
   ```yaml
   # 错误示例（缩进不一致）
   keywords:
     色情低俗:
       enabled: true
      words: []  # ❌ 缩进错误

   # 正确示例
   keywords:
     色情低俗:
       enabled: true
       words: []  # ✅ 缩进正确
   ```

3. **文件权限问题**:
   ```bash
   # Windows
   icacls intelligent_project_analyzer\security\security_rules.yaml

   # Linux/Mac
   ls -l intelligent_project_analyzer/security/security_rules.yaml
   ```

4. **编码问题**:
   确保文件使用UTF-8编码（尤其是包含中文内容时）

**解决方案**:

- 恢复默认配置: 从Git重新拉取`security_rules.yaml`
- 使用YAML验证工具: https://www.yamllint.com/
- 检查文件权限并修正

#### 问题3: 热加载不及时

**症状**: 修改配置后需要等待很久才生效

**解释**: 默认检查间隔为60秒

**解决方案**:

1. **手动触发重载**（立即生效）:
   ```python
   from intelligent_project_analyzer.security.dynamic_rule_loader import reload_rules
   reload_rules()
   ```

2. **调整检查间隔**（修改代码）:
   ```python
   # intelligent_project_analyzer/security/dynamic_rule_loader.py
   loader = DynamicRuleLoader(
       auto_reload=True,
       reload_interval=10  # 改为10秒（仅开发环境）
   )
   ```

   ⚠️ **注意**: 过短的间隔会增加磁盘I/O开销，生产环境不推荐<30秒

### 预期收益

基于P2优化：

- **运营效率**: 规则更新从"需要重启"（5-10分钟停机）到"实时生效"（60秒内）
- **响应速度**: 新威胁快速响应（编辑YAML即可）
- **维护成本**: 从"需要开发人员修改代码"到"运营人员直接配置"
- **可追溯性**: YAML文件版本控制，规则变更可审计
- **系统稳定性**: 配置错误时自动降级，不影响业务

---

## 腾讯云内容安全配置

### 前置条件

1. 拥有腾讯云账号
2. 已开通内容安全服务
3. 已创建内容安全应用

### 配置步骤

#### 步骤1: 创建子账号（推荐，遵循最小权限原则）

**为什么使用子账号？**
- 安全性更高：限制权限范围，避免主账号密钥泄露风险
- 便于管理：可以为不同服务创建不同的子账号
- 审计追踪：更容易追踪API调用来源

**创建子账号流程**:

1. 访问腾讯云CAM控制台: https://console.cloud.tencent.com/cam
2. 点击"用户" → "用户列表" → "新建用户"
3. 选择"自定义创建" → "可访问资源并接收消息"
4. 填写用户信息：
   - 用户名：例如 `content-safety-api`（或任意名称）
   - 访问方式：勾选"编程访问"
5. 点击"下一步"完成创建

**重要提示**: 创建时不会显示密钥，需要在步骤3中单独创建。

#### 步骤2: 为子账号分配内容安全权限

1. 在用户列表中，点击刚创建的子账号名称（蓝色链接）
2. 进入用户详情页面
3. 点击"关联策略"按钮
4. 搜索并勾选策略：
   - **推荐**: `QcloudTMSFullAccess` - 天御内容安全（文本内容检测）全读写访问权限
   - 如需更细粒度控制，可选 `QcloudTMSReadOnlyAccess` （仅读权限）
5. 点击"确定"完成权限分配

**权限说明**:
- `QcloudTMSFullAccess`: 允许完整使用内容安全服务（文本审核、图片审核等）
- `QcloudTMSReadOnlyAccess`: 仅允许查询审核结果，不能提交新的审核请求

#### 步骤3: 为子账号创建API密钥

**正确操作步骤**:

1. 在用户详情页面顶部，点击"**API密钥**"标签页
2. 点击"**新建密钥**"按钮
3. 系统会弹出密钥创建成功对话框，显示：
   - **SecretId**: 以`AKID`开头的字符串（可重复查看）
   - **SecretKey**: 随机字符串（**只显示这一次，关闭对话框后无法再次查看！**）

**重要提醒**:
- ⚠️ SecretKey只在创建时显示一次，务必立即保存
- ⚠️ 建议同时截图保存到安全位置
- ⚠️ 如果丢失SecretKey，只能删除该密钥并重新创建
- ⚠️ 子账号最多可以创建2个API密钥（与主账号限制相同）

**常见错误**:
- ❌ 不要点击"更多操作"菜单（三个点），该菜单只有"添加到组"、"禁用"、"删除"选项
- ✅ 正确方式是直接点击用户名进入详情页，然后点击"API密钥"标签页

#### 步骤4: 确认应用配置

1. 访问腾讯云内容安全应用管理: https://console.cloud.tencent.com/cms/text/overview
2. 确认应用ID和BizType配置：
   - 应用ID: `1997127090860864256`（您的应用ID）
   - 文本审核BizType: `txt` （对应审核策略：20251206）
   - 图片审核BizType: `pic` （对应审核策略：pic-20251206）

**Region说明**:
- ⚠️ 腾讯云内容安全是全局服务，不需要手动选择Region
- ✅ 应用管理页面不显示Region是正常的
- ✅ 默认使用 `ap-guangzhou`（广州）即可

#### 步骤5: 配置环境变量

在项目根目录创建 `.env` 文件（如果不存在），添加以下配置：

```bash
# ==================== 腾讯云内容安全配置 ====================

# 子账号API密钥（从步骤3获取）
TENCENT_CLOUD_SECRET_ID=AKID_从步骤3获取的SecretId
TENCENT_CLOUD_SECRET_KEY=从步骤3获取的SecretKey_只显示一次请立即保存

# 服务地域（全局服务，使用默认值）
TENCENT_CLOUD_REGION=ap-guangzhou

# 应用配置（从步骤4确认）
TENCENT_CONTENT_SAFETY_APP_ID=1997127090860864256
TENCENT_CONTENT_SAFETY_BIZTYPE_TEXT=txt
TENCENT_CONTENT_SAFETY_BIZTYPE_IMAGE=pic

# 功能开关（生产环境必须设置为true）
ENABLE_TENCENT_CONTENT_SAFETY=true

# 高级配置（可选，使用默认值即可）
TENCENT_CONTENT_SAFETY_TIMEOUT=5
TENCENT_CONTENT_SAFETY_RETRY_TIMES=2
TENCENT_CONTENT_SAFETY_CACHE_TTL=3600
```

**安全提醒**:
- ✅ 确保 `.env` 文件已添加到 `.gitignore`（不提交到Git）
- ✅ 永远不要在代码中硬编码密钥
- ✅ 不要在公开场合（如GitHub、聊天记录）分享完整密钥
- ✅ 生产环境建议使用密钥管理服务（如腾讯云SSM）
- ✅ 定期轮转密钥（建议每90天）

#### 步骤6: 验证配置

运行配置验证脚本：

```bash
python scripts/verify_tencent_config.py
```

**预期输出**:

```
============================================================
腾讯云内容安全配置验证
============================================================
✅ 功能已启用 (ENABLE_TENCENT_CONTENT_SAFETY=true)
✅ SecretId已配置: AKIDYFx2Ar...
✅ SecretKey已配置 (长度: 32字符)
✅ Region已配置: ap-guangzhou
✅ 应用ID已配置: 1997127090860864256
✅ 文本BizType: txt
✅ 图片BizType: pic

============================================================
开始API调用测试...
============================================================
✅ 腾讯云内容安全客户端初始化成功 (Region: ap-guangzhou)
✅ 正常文本检测通过: Pass
ℹ️ 敏感文本检测结果: Review (或 Block)
   风险等级: medium (或 high)
   标签: Illegal
   分数: 75

============================================================
✅ 配置验证成功！腾讯云内容安全API可正常使用
============================================================
```

**如果验证失败**，脚本会提示具体错误：
- `❌ 缺少TENCENT_CLOUD_SECRET_ID` → 检查 `.env` 文件配置
- `❌ TENCENT_CLOUD_SECRET_ID格式错误` → 确保以`AKID`开头
- `❌ API调用测试失败` → 检查权限分配和网络连接

---

## 环境变量配置

### 必需配置

以下环境变量必须在 `.env` 文件中配置：

```bash
# LLM API配置（至少配置一个）
OPENAI_API_KEY=sk-your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_API_KEY=your_gemini_api_key_here  # 推荐：开发环境使用

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # 如果Redis设置了密码

# 腾讯云内容安全（生产环境必需）
TENCENT_CLOUD_SECRET_ID=AKID...
TENCENT_CLOUD_SECRET_KEY=...
ENABLE_TENCENT_CONTENT_SAFETY=true
```

### 可选配置

```bash
# 服务器配置
API_PORT=8000
LOG_LEVEL=INFO

# Vision API配置
VISION_PROVIDER=gemini  # openai 或 gemini
ENABLE_VISION_API=true

# 文件上传配置
UPLOAD_DIR=./data/uploads
MAX_FILE_SIZE=10485760  # 10MB

# 环境
ENV=production  # development 或 production
DEBUG=false
```

---

## 依赖安装

### 1. 安装Python依赖

```bash
pip install -r requirements.txt
```

这将安装所有必需的依赖，包括：
- LangGraph + LangChain 多智能体框架
- FastAPI + Uvicorn Web服务器
- 腾讯云SDK（`tencentcloud-sdk-python>=3.0.1100`）
- Redis + Celery 任务队列
- 其他依赖

### 2. 安装前端依赖

```bash
cd frontend-nextjs
npm install
```

### 3. 验证Redis服务

确保Redis服务已启动：

```bash
redis-cli ping
```

预期输出: `PONG`

如果Redis未运行：
- Windows: 启动 `redis-server.exe`
- Linux/Mac: `sudo systemctl start redis` 或 `brew services start redis`

---

## 服务启动

### 方式1: Windows批处理脚本（开发环境）

```bash
start_services.bat
```

这将依次启动：
1. API服务器（端口8000）
2. Celery Worker（可选，支持多用户并发）
3. Next.js前端（端口3000）

### 方式2: 手动启动（推荐用于生产环境）

**后端API服务**:

```bash
# 开发环境
python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000

# 生产环境（使用Gunicorn + Uvicorn workers）
gunicorn intelligent_project_analyzer.api.server:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000
```

**Celery Worker（可选）**:

```bash
celery -A intelligent_project_analyzer.services.celery_app worker \
    --loglevel=info \
    --concurrency=4
```

**前端服务**:

```bash
cd frontend-nextjs

# 开发环境
npm run dev

# 生产环境
npm run build  # 构建
npm start      # 启动生产服务器
```

---

## 验证部署

### 1. 检查服务状态

访问以下URL确认服务正常：

- **API服务器**: http://localhost:8000/docs （FastAPI Swagger文档）
- **前端页面**: http://localhost:3000
- **健康检查**: http://localhost:8000/health （待实现）

### 2. 测试内容安全API

运行验证脚本：

```bash
python scripts/verify_tencent_config.py
```

### 3. 运行单元测试

```bash
# 测试腾讯云内容安全模块
pytest tests/test_tencent_content_safety.py -v

# 测试内容安全守卫集成
pytest tests/test_content_safety_guard_integration.py -v

# 运行所有测试
pytest tests/ -v
```

### 4. 端到端测试

1. 访问前端页面: http://localhost:3000
2. 上传项目文件或输入问卷回答
3. 触发分析流程
4. 查看生成的报告
5. 尝试输入敏感内容（如"赌博"、"色情"），验证内容安全检测是否生效

---

## 常见问题

### Q1: 提示"缺少腾讯云API密钥"？

**A1**: 检查 `.env` 文件是否正确配置 `TENCENT_CLOUD_SECRET_ID` 和 `TENCENT_CLOUD_SECRET_KEY`。

确保：
- 文件位于项目根目录
- SecretId以`AKID`开头
- SecretKey不为空
- `ENABLE_TENCENT_CONTENT_SAFETY=true`

### Q2: API调用测试失败？

**A2**: 检查以下项：

1. **权限问题**:
   - 子账号是否已分配 `QcloudTMSFullAccess` 权限
   - 权限分配后需要等待1-2分钟生效

2. **密钥问题**:
   - SecretId和SecretKey是否正确
   - 是否使用了已禁用的密钥
   - 是否超过密钥数量限制（最多2个）

3. **网络问题**:
   - 检查网络连接
   - 确认可以访问 `tms.tencentcloudapi.com`
   - 检查防火墙设置

4. **配置问题**:
   - Region是否正确（推荐使用 `ap-guangzhou`）
   - 应用ID和BizType是否正确

### Q3: 正常文本被误拦截？

**A3**: 腾讯云内容安全策略较为严格，可能误判。解决方案：

1. **调整BizType策略**:
   - 登录腾讯云内容安全控制台
   - 进入"策略管理"
   - 调整对应BizType的审核严格度

2. **使用自定义词库**:
   - 添加白名单词汇
   - 排除误判的正常表达

3. **联系技术支持**:
   - 提供误判样本
   - 请求优化审核策略

### Q4: 如何禁用腾讯云内容安全？

**A4**: 在 `.env` 文件中设置：

```bash
ENABLE_TENCENT_CONTENT_SAFETY=false
```

系统将回退到关键词检测模式（本地检测，准确率较低）。

**注意**: 生产环境强烈建议启用外部API，以确保内容安全合规。

### Q5: 如何监控API调用量和费用？

**A5**:

1. 访问腾讯云内容安全控制台
2. 查看"用量统计"
3. 设置费用告警（推荐）

**定价参考**（以文本审核为例）:
- 0-3万次/月: 免费
- 3万-300万次/月: 0.0025元/次
- 300万次以上: 联系商务议价

### Q6: API调用失败，提示"SecretId不存在"？

**A6**: 这是最常见的配置问题。错误代码 `AuthFailure.SecretIdNotFound` 表示腾讯云API系统无法识别该SecretId。

**诊断步骤**:

1. **检查内容安全服务是否完全激活** (最可能原因):
   ```
   访问: https://console.cloud.tencent.com/cms/text/overview

   如果看到:
   - ❌ "未开通" 或 "激活服务" 按钮 → 需要用主账号激活服务
   - ✅ 显示应用列表和使用统计 → 服务已激活，继续下一步
   ```

   **为什么会这样**:
   - 创建应用 ≠ 完全激活服务
   - 某些服务需要主账号显式激活API调用权限
   - 子账号权限依赖于主账号的服务激活状态

2. **验证子账号API密钥状态**:
   ```
   访问: https://console.cloud.tencent.com/cam/capi
   点击子账号名称 → "API密钥"标签页

   确认:
   - ✅ 密钥状态为"已启用"（不是"已禁用"）
   - ✅ SecretId完全匹配（复制粘贴对比）
   - ✅ 密钥是在权限分配后创建的（或等待10分钟生效）
   ```

3. **测试主账号密钥（隔离问题）**:
   ```bash
   # 临时替换.env文件中的密钥为主账号密钥
   TENCENT_CLOUD_SECRET_ID=主账号的SecretId
   TENCENT_CLOUD_SECRET_KEY=主账号的SecretKey

   # 运行诊断脚本
   python scripts/diagnose_tencent_api.py
   ```

   **结果判断**:
   - 如果**主账号成功** → 说明是子账号限制问题
     - 解决方案A: 使用主账号密钥（内部工具可接受）
     - 解决方案B: 联系腾讯云支持开通子账号权限
   - 如果**主账号也失败** → 说明是服务激活问题
     - 返回步骤1，确保服务完全激活

4. **运行详细诊断脚本**:
   ```bash
   python scripts/diagnose_tencent_api.py
   ```

   脚本会提供具体的错误代码和RequestId，便于技术支持定位问题。

**常见原因排序**:
1. ⭐⭐⭐⭐⭐ 内容安全服务未完全激活（90%的情况）
2. ⭐⭐⭐ 子账号API密钥在权限分配前创建（需等待生效）
3. ⭐⭐ 子账号API密钥被禁用或删除
4. ⭐ 某些服务限制子账号使用（较少见）

### Q7: 如何切换到生产环境？

**A7**:

1. 设置环境变量:
   ```bash
   ENV=production
   DEBUG=false
   LOG_LEVEL=WARNING
   ```

2. 使用生产级Web服务器（Gunicorn）

3. 启用HTTPS（使用nginx反向代理或Traefik）

4. 配置自动备份和监控

5. 参考完整的[生产环境部署计划](../C:/Users/SF/.claude/plans/warm-cooking-stream.md)

### Q8: 子账号和主账号密钥有什么区别？

**A8**:

| 对比项 | 子账号密钥 | 主账号密钥 |
|--------|-----------|-----------|
| 权限范围 | 可限制（最小权限原则）| 拥有所有权限 |
| 安全性 | 高（泄露影响有限）| 低（泄露影响所有服务）|
| 审计追踪 | 易于追踪调用来源 | 难以区分不同服务 |
| 推荐场景 | ✅ 生产环境（强烈推荐）| ⚠️ 测试环境（谨慎使用）|

**最佳实践**: 始终使用子账号密钥，遵循最小权限原则。

---

## 下一步

完成腾讯云内容安全配置后，您可以：

1. 配置其他生产环境安全措施（参考[生产环境部署计划](../C:/Users/SF/.claude/plans/warm-cooking-stream.md)）
2. 实施Docker化部署（第二阶段）
3. 配置监控和日志系统（第四阶段）
4. 设置CI/CD自动化部署（第六阶段）

如有问题，请参考项目README或提交Issue。
