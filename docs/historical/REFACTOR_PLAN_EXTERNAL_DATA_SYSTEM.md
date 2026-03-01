# 爬虫系统独立化重构执行计划

## 📋 执行概览

**目标**：将分散的爬虫代码重组为独立子包 `external_data_system/`
**影响范围**：约27个文件需要迁移/修改
**预计时间**：2-3小时
**风险等级**：中等（需要更新多处导入）

---

## 📦 Phase 1: 文件迁移清单

### 1.1 Spider模块迁移

```bash
# 新系统（保留并迁移）
crawlers/base_spider.py          → external_data_system/spiders/base_spider.py
crawlers/archdaily_spider.py     → external_data_system/spiders/archdaily_spider.py
crawlers/spider_manager.py       → external_data_system/spiders/spider_manager.py

# 旧系统（标记为deprecated）
crawlers/base_crawler.py         → crawlers/deprecated/base_crawler.py
crawlers/archdaily_crawler.py    → crawlers/deprecated/archdaily_crawler.py
crawlers/gooood_crawler.py       → crawlers/deprecated/gooood_crawler.py
crawlers/category_crawler.py     → crawlers/deprecated/category_crawler.py
crawlers/playwright_crawler.py   → crawlers/deprecated/playwright_crawler.py
```

### 1.2 数据模型迁移

```bash
models/external_projects.py      → external_data_system/models/external_projects.py
# 保持一个兼容导入在原位置
```

### 1.3 任务模块迁移

```bash
tasks/external_data_tasks.py     → external_data_system/tasks/sync_tasks.py
# 拆分为sync_tasks.py + processing_tasks.py
```

### 1.4 API路由迁移

```bash
api/external_data_routes.py      → external_data_system/api/routes.py
```

### 1.5 配置与工具

```bash
# 新建文件
external_data_system/config/settings.py     # 爬虫配置集中管理
external_data_system/utils/rate_limiter.py  # 限流工具
external_data_system/utils/proxy_manager.py # 代理池管理
```

### 1.6 测试迁移

```bash
scripts/test_external_data_system.py  → external_data_system/tests/test_integration.py
scripts/init_external_database.py     → external_data_system/tests/setup_database.py
# 新增单元测试
external_data_system/tests/test_spiders.py
external_data_system/tests/test_models.py
```

---

## ⚙️ Phase 2: 创建目录结构

### 执行脚本（PowerShell）

```powershell
# 创建目录树
$dirs = @(
    "intelligent_project_analyzer\external_data_system\spiders",
    "intelligent_project_analyzer\external_data_system\models",
    "intelligent_project_analyzer\external_data_system\tasks",
    "intelligent_project_analyzer\external_data_system\api",
    "intelligent_project_analyzer\external_data_system\utils",
    "intelligent_project_analyzer\external_data_system\config",
    "intelligent_project_analyzer\external_data_system\tests",
    "intelligent_project_analyzer\crawlers\deprecated"
)

foreach ($dir in $dirs) {
    New-Item -Path $dir -ItemType Directory -Force
    New-Item -Path "$dir\__init__.py" -ItemType File -Force
}

Write-Host "✅ 目录结构创建完成" -ForegroundColor Green
```

---

## 🔄 Phase 3: 文件迁移与修改

### 3.1 迁移Spider文件

**操作**：移动文件 + 修改导入

```python
# external_data_system/spiders/__init__.py
from .base_spider import BaseSpider, ProjectData
from .archdaily_spider import ArchdailySpider
from .spider_manager import SpiderManager

def get_spider_manager():
    """工厂方法：获取配置好的SpiderManager实例"""
    manager = SpiderManager()
    manager.register_spider(ArchdailySpider())
    # 未来添加更多spider
    # manager.register_spider(GoooodSpider())
    return manager

__all__ = [
    "BaseSpider",
    "ProjectData",
    "ArchdailySpider",
    "SpiderManager",
    "get_spider_manager",
]
```

**修改导入**（3个文件内部）：
- `base_spider.py`：无需修改（无内部依赖）
- `archdaily_spider.py`：
  ```python
  # 旧：from intelligent_project_analyzer.crawlers.base_spider import BaseSpider
  # 新：from .base_spider import BaseSpider
  ```
- `spider_manager.py`：
  ```python
  # 旧：from intelligent_project_analyzer.crawlers.base_spider import BaseSpider
  #     from intelligent_project_analyzer.models.external_projects import ...
  # 新：from .base_spider import BaseSpider
  #     from ..models.external_projects import ...
  ```

### 3.2 迁移数据模型

```python
# external_data_system/models/__init__.py
from .external_projects import (
    ExternalProject,
    ExternalProjectImage,
    SyncHistory,
    QualityIssue,
    ExternalProjectDatabase,
    get_external_db,
)

__all__ = [
    "ExternalProject",
    "ExternalProjectImage",
    "SyncHistory",
    "QualityIssue",
    "ExternalProjectDatabase",
    "get_external_db",
]
```

**兼容性处理**（保留旧接口）：
```python
# intelligent_project_analyzer/models/external_projects.py
"""
⚠️ DEPRECATED: 请使用 external_data_system.models 代替

为了向后兼容，此文件重新导出 external_data_system 的模型。
将在 v2.0.0 版本中移除。
"""
import warnings
from intelligent_project_analyzer.external_data_system.models import *

warnings.warn(
    "导入 intelligent_project_analyzer.models.external_projects 已弃用，"
    "请使用 intelligent_project_analyzer.external_data_system.models",
    DeprecationWarning,
    stacklevel=2
)
```

### 3.3 迁移任务模块

**拆分为2个文件**：

```python
# external_data_system/tasks/__init__.py
from .sync_tasks import sync_external_source
from .processing_tasks import generate_embeddings_task, quality_check_task

__all__ = [
    "sync_external_source",
    "generate_embeddings_task",
    "quality_check_task",
]
```

```python
# external_data_system/tasks/sync_tasks.py
"""爬虫同步任务"""
from celery import Celery
from ..spiders import get_spider_manager

celery_app = Celery("external_data_tasks")

@celery_app.task(bind=True, max_retries=3)
def sync_external_source(self, source: str, category: str = None, ...):
    manager = get_spider_manager()
    # ... 原有逻辑
```

```python
# external_data_system/tasks/processing_tasks.py
"""数据处理任务"""
from celery import Celery
from ..models import get_external_db, ExternalProject

celery_app = Celery("external_data_tasks")

@celery_app.task
def generate_embeddings_task(project_id: int):
    # ... 向量生成逻辑

@celery_app.task
def quality_check_task(project_id: int):
    # ... 质量检查逻辑
```

### 3.4 迁移API路由

```python
# external_data_system/api/__init__.py
from .routes import router

__all__ = ["router"]
```

```python
# external_data_system/api/routes.py
from fastapi import APIRouter
from ..spiders import get_spider_manager
from ..models import get_external_db
from ..tasks import sync_external_source

router = APIRouter(prefix="/api/external", tags=["external-data"])

# ... 原有路由实现
```

**修改主服务器注册**：
```python
# intelligent_project_analyzer/api/server.py
# 旧：from intelligent_project_analyzer.api.external_data_routes import router
# 新：from intelligent_project_analyzer.external_data_system.api import router as external_data_router

app.include_router(external_data_router)
```

---

## 🔌 Phase 4: 更新所有导入引用

### 自动化替换脚本（PowerShell）

```powershell
# replace_imports.ps1
$replacements = @{
    "from intelligent_project_analyzer.crawlers import get_spider_manager" =
        "from intelligent_project_analyzer.external_data_system import get_spider_manager"

    "from intelligent_project_analyzer.crawlers.spider_manager import SpiderManager" =
        "from intelligent_project_analyzer.external_data_system.spiders import SpiderManager"

    "from intelligent_project_analyzer.models.external_projects import" =
        "from intelligent_project_analyzer.external_data_system.models import"

    "from intelligent_project_analyzer.tasks.external_data_tasks import" =
        "from intelligent_project_analyzer.external_data_system.tasks import"
}

Get-ChildItem -Recurse -Filter "*.py" | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    $modified = $false

    foreach ($old in $replacements.Keys) {
        $new = $replacements[$old]
        if ($content -match [regex]::Escape($old)) {
            $content = $content -replace [regex]::Escape($old), $new
            $modified = $true
        }
    }

    if ($modified) {
        Set-Content $_.FullName -Value $content -NoNewline
        Write-Host "✅ 更新: $($_.Name)" -ForegroundColor Green
    }
}
```

### 手动检查文件列表

根据之前的搜索结果，需要更新以下文件：

```
✏️ 需要更新导入的文件（约20个）：
- intelligent_project_analyzer/api/server.py
- intelligent_project_analyzer/api/external_data_routes.py (删除)
- intelligent_project_analyzer/tasks/external_data_tasks.py (删除)
- scripts/init_external_database.py
- scripts/test_external_data_system.py
- scripts/crawl_all_categories.py
- scripts/test_single_project.py
- intelligent_project_analyzer/scripts/*_crawler*.py (约6个文件)
- intelligent_project_analyzer/config/crawler_credentials.py
```

---

## 🧪 Phase 5: 测试验证

### 5.1 单元测试

```bash
# 测试Spider
python -m pytest external_data_system/tests/test_spiders.py -v

# 测试数据模型
python -m pytest external_data_system/tests/test_models.py -v

# 测试任务
python -m pytest external_data_system/tests/test_tasks.py -v
```

### 5.2 集成测试

```bash
# 运行完整测试套件
python -m pytest external_data_system/tests/test_integration.py -v

# 测试数据库初始化
python -c "from intelligent_project_analyzer.external_data_system.models import get_external_db; \
           db = get_external_db(); db.create_tables(); print('✅ 数据库测试通过')"

# 测试爬虫
python -c "from intelligent_project_analyzer.external_data_system import get_spider_manager; \
           manager = get_spider_manager(); print(f'✅ 已注册{len(manager.spiders)}个爬虫')"
```

### 5.3 API测试

```bash
# 启动服务器
uvicorn intelligent_project_analyzer.api.server:app --reload

# 测试路由
curl http://localhost:8000/api/external/source-stats
curl http://localhost:8000/api/external/sync-history?limit=5
```

---

## 📊 Phase 6: 文档更新

### 需要更新的文档

```
1. ✏️ EXTERNAL_DATA_QUICKSTART.md
   - 更新所有导入示例
   - 更新文件路径引用

2. ✏️ EXTERNAL_DATA_MONITORING_GUIDE.md
   - 更新架构图
   - 更新安装说明

3. ✏️ README.md (主项目)
   - 添加子系统说明

4. ✅ external_data_system/README.md
   - 已创建完整文档
```

---

## ⚠️ 风险控制

### 回滚计划

```bash
# 创建Git分支
git checkout -b refactor/external-data-system-isolation
git commit -m "WIP: 爬虫系统独立化重构"

# 如果出现问题，可以快速回滚
git checkout main
```

### 兼容性策略

**策略1：渐进式迁移**（推荐）

1. ✅ 先创建新结构 `external_data_system/`
2. ✅ 保留旧接口，添加DeprecationWarning
3. ⏳ 更新所有内部引用
4. ⏳ 发布v1.1.0（新旧并存）
5. ⏳ 6个月后发布v2.0.0（移除旧接口）

**策略2：一次性迁移**

- 直接删除旧文件
- 适合项目无外部依赖的情况

---

## 📈 性能影响

### 预期改进

| 指标 | 迁移前 | 迁移后 | 改进 |
|------|--------|--------|------|
| 导入时间 | ~1.2s | ~0.8s | ⬇️33% |
| 模块独立性 | 低（多处耦合） | 高（清晰接口） | ⬆️ |
| 测试覆盖率 | 30% | 80% | ⬆️50% |
| 新增数据源成本 | 修改5+文件 | 修改1-2文件 | ⬇️60% |

---

## ✅ 验收标准

### 功能验收

- [ ] 所有原有功能正常工作
- [ ] API路由返回正确数据
- [ ] Celery任务可以正常调度
- [ ] 前端监控页面无报错

### 代码质量验收

- [ ] 所有文件符合新结构
- [ ] 无循环导入（运行 `pytest --collect-only`）
- [ ] 所有测试通过（覆盖率>70%）
- [ ] 无DeprecationWarning（除兼容层）

### 文档验收

- [ ] README.md更新
- [ ] 所有代码示例可运行
- [ ] API文档与实际一致

---

## 🚀 执行时间表

| 阶段 | 任务 | 预计时间 | 验证标准 |
|------|------|----------|----------|
| Phase 1 | 创建目录结构 | 15分钟 | 目录树完整 |
| Phase 2 | 迁移Spider文件 | 30分钟 | 导入无错误 |
| Phase 3 | 迁移模型+任务 | 30分钟 | 数据库可连接 |
| Phase 4 | 更新所有引用 | 45分钟 | 无导入错误 |
| Phase 5 | 编写测试 | 30分钟 | 覆盖率>70% |
| Phase 6 | 文档更新 | 20分钟 | 示例可运行 |
| **总计** | | **2.5小时** | 所有验收通过 |

---

## 📞 问题排查

### 常见问题

**Q1: 导入错误 `ModuleNotFoundError: No module named 'external_data_system'`**

```bash
# 确保在项目根目录运行
cd d:\11-20\langgraph-design

# 确保包已安装
pip install -e .
```

**Q2: Celery无法找到任务**

```python
# 更新celery配置
celery_app.conf.imports = (
    'intelligent_project_analyzer.external_data_system.tasks.sync_tasks',
    'intelligent_project_analyzer.external_data_system.tasks.processing_tasks',
)
```

**Q3: 数据库连接失败**

```bash
# 检查环境变量
echo $env:EXTERNAL_DB_URL
# 或
python -c "import os; print(os.getenv('EXTERNAL_DB_URL'))"
```

---

## 🎯 下一步行动

### 立即执行（推荐）

```bash
# 1. 创建分支
git checkout -b refactor/external-data-system

# 2. 执行Phase 1-2（安全操作）
python scripts/create_external_data_system_structure.py

# 3. 运行测试验证
python -m pytest external_data_system/tests/ -v

# 4. 提交第一阶段
git add external_data_system/
git commit -m "feat: 创建external_data_system独立子包结构"
```

### 后续步骤

1. ⏳ Phase 3-4: 迁移文件并更新引用
2. ⏳ Phase 5: 完善测试覆盖
3. ⏳ Phase 6: 更新文档
4. ⏳ Phase 7: 代码审查与合并

---

## 📝 记录变更

| 日期 | 版本 | 变更说明 |
|------|------|----------|
| 2026-02-17 | v1.0 | 初始重构计划 |
| | | |

**负责人**：AI Architecture Team
**审批人**：待定
**预计完成日期**：2026-02-18
