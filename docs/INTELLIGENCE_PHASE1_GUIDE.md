# Phase 1 智能化演进系统 - 使用指南

> **版本**: 1.0.0
> **发布日期**: 2026-02-11
> **适用范围**: 智能Few-Shot选择、使用数据跟踪、示例质量分析

---

## 快速开始 🚀

### 1. 安装依赖

```bash
# 安装Phase 1所需依赖
pip install sentence-transformers==2.3.1 faiss-cpu==1.7.4 scikit-learn==1.3.2

# 或使用requirements.txt安装全部依赖
pip install -r requirements.txt
```

### 2. 首次使用

```python
from intelligent_project_analyzer.intelligence import (
    IntelligentFewShotSelector,
    UsageTracker,
    ExampleQualityAnalyzer
)

# 1. 创建智能选择器
selector = IntelligentFewShotSelector()

# 2. 为角色构建索引（首次会下载模型，需要几分钟）
selector.build_index_for_role("V2_0")

# 3. 选择相关示例
examples = selector.select_relevant_examples(
    role_id="V2_0",
    user_query="我需要分析住宅项目的功能需求",
    top_k=2
)

print(f"选中 {len(examples)} 个示例:")
for ex in examples:
    print(f"  - {ex.example_id}: {ex.description}")
```

---

## 核心功能 📦

### 功能 1: 智能Few-Shot选择

#### 基本使用

```python
from intelligent_project_analyzer.intelligence import IntelligentFewShotSelector

# 创建选择器
selector = IntelligentFewShotSelector()

# 为所有需要的角色构建索引
roles = ["V2_0", "V3_1", "V4_1", "V5_1", "V6_1", "V7_0"]
for role_id in roles:
    selector.build_index_for_role(role_id)

# 使用选择器
examples = selector.select_relevant_examples(
    role_id="V2_0",
    user_query="分析商业综合体的功能需求和技术要求",
    top_k=2,
    category="targeted_mode",  # 可选: "targeted_mode" 或 "comprehensive_mode"
    diversity_threshold=0.7     # 可选: 多样性阈值 (0.0-1.0)
)
```

#### 高级配置

```python
from intelligent_project_analyzer.intelligence import (
    IntelligentFewShotSelector,
    SelectorConfig
)

# 自定义配置
config = SelectorConfig(
    model_name="paraphrase-multilingual-mpnet-base-v2",  # 更大更准确的模型
    cache_dir=Path("./custom_cache"),
    diversity_threshold=0.75,
    use_faiss=True
)

selector = IntelligentFewShotSelector(config)
```

#### 性能对比

```python
# 与传统关键词匹配对比
test_queries = [
    "住宅项目需求分析",
    "商业综合体技术需求",
    "办公楼用户调研"
]

results = selector.compare_with_baseline(
    role_id="V2_0",
    test_queries=test_queries
)

print(f"与基线方法一致率: {results['agreement_rate']:.1%}")
```

---

### 功能 2: 使用数据跟踪

#### 基本记录

```python
from intelligent_project_analyzer.intelligence import UsageTracker

# 创建跟踪器 (SQLite版本，适合生产环境)
tracker = UsageTracker(use_sqlite=True)

# 记录专家使用情况
tracker.log_expert_usage(
    role_id="V2_0",
    user_request="分析住宅项目的功能需求",
    selected_examples=["v2_0_targeted_001", "v2_0_comprehensive_002"],
    output_tokens=1500,
    response_time=2.5,
    user_feedback={"liked": True, "rating": 5},  # 可选
    session_id="session_abc123",                  # 可选
    metadata={"version": "1.0", "model": "gpt-4"} # 可选
)
```

#### 查询日志

```python
from datetime import datetime, timedelta

# 查询最近7天的所有日志
recent_logs = tracker.get_logs(
    start_date=datetime.now() - timedelta(days=7)
)

# 查询特定角色的日志
v2_logs = tracker.get_logs(
    role_id="V2_0",
    limit=100
)

# 查询特定会话的日志
session_logs = tracker.get_logs(
    session_id="session_abc123"
)
```

#### 分析示例有效性

```python
# 分析V2_0角色最近30天的示例使用情况
stats = tracker.analyze_example_effectiveness("V2_0", days=30)

for example_id, metrics in stats.items():
    print(f"{example_id}:")
    print(f"  使用次数: {metrics['usage_count']}")
    print(f"  质量分数: {metrics['quality_score']:.2f}")
    print(f"  平均tokens: {metrics['avg_tokens']:.1f}")
    print(f"  正面反馈: {metrics['positive_feedback']}")
    print(f"  负面反馈: {metrics['negative_feedback']}")
```

#### 获取统计信息

```python
# 全局统计
stats = tracker.get_statistics(days=7)
print(f"总调用: {stats['total_calls']}")
print(f"角色分布: {stats['role_distribution']}")
print(f"平均响应时间: {stats['avg_response_time']:.2f}秒")

# 单个角色统计
v2_stats = tracker.get_statistics(role_id="V2_0", days=7)
```

---

### 功能 3: 示例质量分析

#### 分析单个角色

```python
from intelligent_project_analyzer.intelligence import ExampleQualityAnalyzer

# 创建分析器
analyzer = ExampleQualityAnalyzer()

# 分析V2_0角色
report = analyzer.analyze_role(
    role_id="V2_0",
    days=30,                    # 分析最近30天
    quality_threshold=0.5,      # 质量分数阈值
    usage_threshold=5           # 使用次数阈值
)

# 查看报告
print(f"总示例: {report.total_examples}")
print(f"使用率: {report.summary['usage_rate']:.1%}")
print(f"高质量示例: {len(report.high_quality_examples)}")
print(f"低质量示例: {len(report.low_quality_examples)}")
print(f"未使用示例: {len(report.unused_examples)}")
```

#### 保存报告

```python
# 保存为JSON
json_path = analyzer.save_report(report, format='json')

# 保存为Markdown
md_path = analyzer.save_report(report, format='markdown')
```

#### 分析所有角色

```python
# 批量分析所有角色
reports = analyzer.analyze_all_roles(days=30)

print(f"分析了 {len(reports)} 个角色")
```

#### 查看优化建议

```python
for recommendation in report.recommendations:
    print(f"[{recommendation['priority'].upper()}] {recommendation['type']}")
    print(f"  {recommendation['description']}")
    print(f"  行动: {recommendation['action']}")
```

---

## 完整工作流示例 🔄

### 集成到现有系统

```python
from intelligent_project_analyzer.intelligence import (
    IntelligentFewShotSelector,
    UsageTracker
)
from intelligent_project_analyzer.core.expert_prompt_template import ExpertPromptTemplate
import time

class IntelligentExpertSystem:
    """集成智能化功能的专家系统"""

    def __init__(self):
        self.selector = IntelligentFewShotSelector()
        self.tracker = UsageTracker()

        # 预构建所有角色的索引
        self.roles = ["V2_0", "V3_1", "V4_1", "V5_1", "V6_1", "V7_0"]
        for role_id in self.roles:
            self.selector.build_index_for_role(role_id)

    def process_request(
        self,
        role_id: str,
        user_request: str,
        session_id: str
    ) -> str:
        """处理用户请求"""
        start_time = time.time()

        # 1. 智能选择Few-Shot示例
        examples = self.selector.select_relevant_examples(
            role_id=role_id,
            user_query=user_request,
            top_k=2
        )

        # 2. 生成专家输出 (这里简化，实际应调用LLM)
        prompt_template = ExpertPromptTemplate(role_id)
        output = self._generate_output(prompt_template, user_request, examples)

        # 3. 记录使用数据
        response_time = time.time() - start_time
        self.tracker.log_expert_usage(
            role_id=role_id,
            user_request=user_request,
            selected_examples=[ex.example_id for ex in examples],
            output_tokens=len(output.split()),
            response_time=response_time,
            session_id=session_id
        )

        return output

    def collect_feedback(
        self,
        session_id: str,
        feedback: dict
    ):
        """收集用户反馈（异步更新）"""
        # 实际应该查询最近的log并更新feedback字段
        # 这里简化处理
        pass

    def _generate_output(self, template, request, examples):
        """生成输出（占位符）"""
        return f"基于 {len(examples)} 个示例生成的专业输出"


# 使用示例
system = IntelligentExpertSystem()
output = system.process_request(
    role_id="V2_0",
    user_request="分析住宅项目需求",
    session_id="session_001"
)
```

---

## 定时分析任务 ⏰

### 每日质量分析脚本

创建 `scripts/daily_quality_analysis.py`:

```python
"""每日示例质量分析任务"""

from intelligent_project_analyzer.intelligence import ExampleQualityAnalyzer
from datetime import datetime

def run_daily_analysis():
    """运行每日分析"""
    print(f"开始每日质量分析: {datetime.now()}")

    analyzer = ExampleQualityAnalyzer()

    # 分析所有角色
    reports = analyzer.analyze_all_roles(days=7)

    # 统计关键指标
    total_issues = sum(len(r.issues) for r in reports.values())
    critical_issues = sum(
        len([i for i in r.issues if i.severity == 'high'])
        for r in reports.values()
    )

    print(f"分析完成:")
    print(f"  角色数: {len(reports)}")
    print(f"  总问题: {total_issues}")
    print(f"  严重问题: {critical_issues}")

    # 如果有严重问题，发送告警
    if critical_issues > 0:
        print(f"⚠️ 发现 {critical_issues} 个严重质量问题，建议立即处理")

if __name__ == "__main__":
    run_daily_analysis()
```

### 配置定时任务 (Windows)

```powershell
# 使用Task Scheduler或手动定时运行
python scripts/daily_quality_analysis.py
```

### 配置定时任务 (Linux/macOS)

```bash
# 编辑crontab
crontab -e

# 添加每天凌晨2点执行
0 2 * * * cd /path/to/project && python scripts/daily_quality_analysis.py
```

---

## 性能优化建议 ⚡

### 1. 索引缓存

```python
# 预构建所有索引，避免实时构建
selector = IntelligentFewShotSelector()

for role_id in all_role_ids:
    selector.build_index_for_role(role_id, force_rebuild=False)
```

### 2. 使用GPU加速 (可选)

```python
# 如果有GPU，embedding速度可提升10倍+
# 自动检测并使用GPU
import torch
if torch.cuda.is_available():
    print("GPU可用，Sentence-BERT将自动使用GPU")
```

### 3. 数据库优化

```python
# SQLite优化: 使用WAL模式
tracker = UsageTracker(use_sqlite=True)

# 手动优化数据库
import sqlite3
conn = sqlite3.connect(tracker.db_path)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("VACUUM")
conn.close()
```

---

## 故障排查 🔧

### 问题1: 缺少依赖

**症状**: `RuntimeError: 请先安装必需的依赖`

**解决**:
```bash
pip install sentence-transformers faiss-cpu
```

### 问题2: 模型下载慢

**症状**: 首次使用时卡在"加载Embedding模型"

**解决**:
```python
# 方案1: 使用国内镜像
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 方案2: 手动下载模型到本地
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2',
                            cache_folder='./models')
```

### 问题3: 内存不足

**症状**: `MemoryError` 或进程被杀

**解决**:
```python
# 使用更小的模型
config = SelectorConfig(
    model_name="sentence-transformers/paraphrase-MiniLM-L3-v2",  # 只有16MB
    use_faiss=True
)
```

### 问题4: 查询速度慢

**症状**: 每次查询超过100ms

**解决**:
```python
# 确保已构建索引
selector.build_index_for_role(role_id)

# 检查是否使用了FAISS
assert config.use_faiss is True
```

---

## API参考 📚

### IntelligentFewShotSelector

```python
class IntelligentFewShotSelector:
    def __init__(self, config: Optional[SelectorConfig] = None)

    def build_index_for_role(self, role_id: str, force_rebuild: bool = False)

    def select_relevant_examples(
        self,
        role_id: str,
        user_query: str,
        top_k: int = 2,
        category: Optional[str] = None,
        diversity_threshold: Optional[float] = None
    ) -> List[FewShotExample]

    def compare_with_baseline(
        self,
        role_id: str,
        test_queries: List[str],
        ground_truth: Optional[List[List[str]]] = None
    ) -> dict
```

### UsageTracker

```python
class UsageTracker:
    def __init__(self, data_dir: Optional[Path] = None, use_sqlite: bool = True)

    def log_expert_usage(
        self,
        role_id: str,
        user_request: str,
        selected_examples: List[str],
        output_tokens: int,
        response_time: float,
        user_feedback: Optional[Dict] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    )

    def get_logs(
        self,
        role_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]

    def analyze_example_effectiveness(
        self,
        role_id: str,
        days: int = 30
    ) -> Dict[str, Dict]

    def get_statistics(
        self,
        role_id: Optional[str] = None,
        days: int = 7
    ) -> Dict
```

### ExampleQualityAnalyzer

```python
class ExampleQualityAnalyzer:
    def __init__(
        self,
        usage_tracker: Optional[UsageTracker] = None,
        example_loader: Optional[FewShotExampleLoader] = None,
        output_dir: Optional[Path] = None
    )

    def analyze_role(
        self,
        role_id: str,
        days: int = 30,
        quality_threshold: float = 0.5,
        usage_threshold: int = 5
    ) -> QualityReport

    def save_report(self, report: QualityReport, format: str = 'json') -> Path

    def analyze_all_roles(self, days: int = 30) -> Dict[str, QualityReport]
```

---

## 下一步 🎯

完成Phase 1后，可以：

1. **收集数据**: 运行系统30天，积累使用数据
2. **评估效果**: 对比智能选择vs传统方法的准确率和用户满意度
3. **启动Phase 2**: 开发示例自动优化和A/B测试框架

详见: [EXPERT_SYSTEM_INTELLIGENCE_ROADMAP.md](../EXPERT_SYSTEM_INTELLIGENCE_ROADMAP.md)

---

## 支持与反馈 💬

- **文档**: [完整技术路线图](../EXPERT_SYSTEM_INTELLIGENCE_ROADMAP.md)
- **测试**: `pytest tests/intelligence/ -v`
- **问题**: 提交Issue到项目仓库
