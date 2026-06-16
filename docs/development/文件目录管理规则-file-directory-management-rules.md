# 文件目录管理规则

本文档定义本项目的文件目录归属、临时文件清理、资料归档和自动化整理规则。目标是让项目根目录清晰、资料不误删、代码可维护、文档可追溯。

## 一、根目录原则

根目录只保留项目入口级文件和一级功能目录。

允许长期存在于根目录的文件：

- `README.md`
- `QUICKSTART.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `Makefile`
- `requirements.txt`
- `.gitignore`
- `.pre-commit-config.yaml`
- 必要的根级配置文件，例如 `pyproject.toml`、`pytest.ini`、`mypy.ini`、`ruff.toml`

不应长期存在于根目录的文件：

- `_patch*.py`
- `_test*.py`
- `_verify*.py`
- `_scan*.py`
- `_*.txt`
- `patch.py`
- `patch*.js`
- `update.py`
- `check.py`
- `temp.txt`
- `old.txt`
- `new_str.txt`
- `*.log`
- 本地数据库：`*.db`、`*.sqlite`、`*.sqlite3`
- 临时安全扫描报告、临时 requirements 文件

这些文件如果仍需保留，只能进入 `_archive/local-cleanup/<date>/`，不能继续散落在根目录。

## 二、一级目录职责

| 目录 | 职责 | 规则 |
|---|---|---|
| `intelligent_project_analyzer/` | 后端业务代码、服务、API、工作流、知识治理运行逻辑 | 正式源码必须 Git 跟踪 |
| `frontend-nextjs/` | Next.js 前端、管理后台、页面组件、前端测试 | 正式源码必须 Git 跟踪 |
| `tests/` | 后端、服务、集成、回归测试 | 跟随对应功能提交 |
| `docs/` | 项目文档、架构文档、开发规则、计划、审计报告 | 核心文档必须 Git 跟踪 |
| `sf/` | 方案高参产品定义、空间分类、本体论、知识资产源材料 | 核心正文资料必须 Git 跟踪或单独登记 |
| `scripts/` | 可复用工程脚本、校验脚本、归档脚本 | 正式脚本必须 Git 跟踪 |
| `config/` | 根级配置、配额、外部化配置 | 示例和非密钥配置可跟踪 |
| `data/` | 根级本地运行数据、动态索引、上传产物、临时审批草稿 | 默认不直接入 Git；可复用小型数据应移入 `config/`、`docs/examples/` 或加明确例外 |
| `_archive/` | 本地归档、临时清理结果、历史整理快照 | 默认本地保留，不作为正式代码入口 |

## 三、`.gitignore` 规则

`.gitignore` 只能保护本地运行产物，不能隐藏正式源码、正式文档和测试资产。

必须遵守：

1. 通用目录名必须优先使用根锚定写法，例如 `/data/`、`/logs/`、`/dist/`、`/build/`、`/tmp/`。
2. 不允许写未锚定的源码高频目录名，例如 `lib/`、`types/`、`docs/`、`src/`、`app/`、`components/`、`services/`。
3. `frontend-nextjs/lib/`、`frontend-nextjs/types/`、`frontend-nextjs/app/` 属于正式前端源码，必须可被 Git 发现。
4. `intelligent_project_analyzer/`、`frontend-nextjs/`、`tests/`、`docs/`、`sf/`、`scripts/` 下新增正式文件时，不能靠忽略规则长期隐藏。
5. 如果某个目录同时可能放源码和运行数据，优先调整目录结构；临时保留时必须写具体路径和注释，不能用宽泛规则兜底。
6. 每次修改忽略规则后，必须用 `git check-ignore -v -- <path>` 验证至少一组源码路径和一组运行产物路径。
7. 被忽略不等于安全存在；重要文件必须进入 Git 跟踪，或在目录管理/备份清单中登记。

## 四、`docs/` 目录规则

`docs/` 是项目知识入口，不是临时目录。

推荐结构：

- `docs/architecture/`：系统架构、治理边界、模块关系、ADR。
- `docs/development/`：开发规范、启动规则、版本管理、目录管理、阶段计划。
- `docs/superpowers/plans/`：较大任务的实施计划。
- `docs/superpowers/specs/`：较大任务的设计说明。
- `docs/system-completeness-audit/`：系统完整性、动态治理、模块审计。
- `docs/development/方案高参需求重构运行时开发纲领.md`：需求重构运行时、字段、路由、测试基线的当前开发入口。
- `docs/examples/`：可复用样例、标准输入输出样例。

规则：

1. 面向团队成员的正式文档必须 Git 跟踪。
2. 阶段计划、开发规范、架构说明不能长期停留在 `??` 未跟踪状态。
3. 草稿如果不准备入库，应移动到 `_archive/local-cleanup/<date>/docs-drafts/`。
4. 不允许用 `git stash -u` 或 `git clean -fd` 粗暴处理 `docs/`。

## 五、`sf/` 资料目录规则

`sf/` 是方案高参产品定义和知识源材料，不按普通临时文件处理。

应 Git 跟踪：

- `sf/2026.5.23/` 下的方案高参核心正文。
- 空间分类、本体论、知识资产、需求重构、入口机制、任务书、产品定义类 Markdown。
- 作为系统定义依据的清单、黄金问题、映射表。

可本地保留但不一定入 Git：

- `.rar`、`.zip` 压缩包。
- 原始备份包。
- 大型未整理资料。
- 私有、版权不明确或客户相关资料。

规则：

1. `sf/` 下文件移动前必须先列清单。
2. `sf/2026.5.23/` 不参与自动清理。
3. `sf/` 压缩包如果不入 Git，必须在清单中记录来源、用途、备份位置。
4. 不允许用全局 clean 或全局 stash 移走 `sf/`。

## 六、需求重构相关文件规则

需求重构是当前方案高参入口基线，不再使用旧入口概念命名。

应 Git 跟踪：

- `intelligent_project_analyzer/services/demand_reconstruction_*.py`
- `tests/services/test_demand_reconstruction_service.py`
- `tests/api/test_scheme_advisor_entry_route.py`
- `frontend-nextjs/components/ConversationMode/GuidanceCard.tsx`
- `frontend-nextjs/components/ConversationMode/ConversationChat.tsx`
- `frontend-nextjs/lib/api.ts`
- `docs/development/方案高参需求重构运行时开发纲领.md`
- `sf/2026.5.23/10 方案高参需求重构到设计任务书升级机制_专题H_v1.0_20260616.md`

规则：

1. 不新增以旧入口概念命名的文件。
2. 字段统一使用 `demand_reconstruction_context`、`demand_reconstruction_blueprint`、`blueprint`。
3. 前台统一使用“需求重构”和“行动蓝图”。
4. 需求重构相关文档修改必须同步检查 `docs/development/` 与 `sf/2026.5.23/`。

## 七、临时文件处理规则

临时文件分三种处理方式。

### 1. 可再生成

例如缓存、构建产物、测试输出、截图输出。

处理方式：

- 写入 `.gitignore`
- 必要时直接重新生成
- 不进入 Git

### 2. 有排查价值但不是正式资产

例如旧调试脚本、历史测试输出、一次性扫描结果。

处理方式：

- 移动到 `_archive/local-cleanup/<date>/root-temp/`
- 生成归档清单
- 不进入正式源码目录

### 3. 可能是资料或正式脚本

例如研究正文、长期可复用脚本、产品定义文档。

处理方式：

- 先人工确认
- 如果正式保留，移动到 `docs/`、`sf/`、`scripts/` 或对应业务目录
- 不直接归档或删除

## 八、自动化归档机制

本项目使用 `scripts/archive_workspace_files.py` 做本地归档。

默认只 dry-run，不移动文件：

```bash
python scripts/archive_workspace_files.py
```

实际归档根目录临时文件：

```bash
python scripts/archive_workspace_files.py --apply
```

归档位置：

```text
_archive/local-cleanup/<YYYY-MM-DD>/root-temp/
```

归档脚本必须遵守：

1. 只处理根目录明确临时命名的文件。
2. 不处理目录。
3. 不处理已被 Git 跟踪的文件。
4. 不处理 `docs/`、`sf/`、`intelligent_project_analyzer/`、`frontend-nextjs/`、`tests/`。
5. 不删除文件，只移动归档。
6. 每次归档生成 manifest，记录原路径、目标路径、大小、时间。

## 九、禁止动作

文件整理时禁止执行：

```bash
git clean -fd
git clean -fdx
git reset --hard
git checkout -- .
git stash -u
git stash --all
```

如需清理，必须按以下顺序：

1. 先列清单。
2. 区分 Git 跟踪、忽略、本地保留。
3. `docs/`、`sf/` 单独确认。
4. 临时文件只移动到 `_archive/`。
5. 确认工作区状态。
6. 再决定是否提交规则、脚本或正式文档。

## 十、整理前检查清单

每次目录整理前必须确认：

1. 当前分支是什么？
2. `git status --short` 有哪些未跟踪文件？
3. 是否包含 `docs/` 或 `sf/`？
4. 候选文件是否已被 Git 跟踪？
5. 是否存在本地资料、客户资料、压缩包或大文件？
6. 归档后是否有 manifest？
7. 是否可以单独恢复？

答不清楚，不执行整理。

## 十一、当前项目执行口径

当前只自动归档根目录明确临时文件。

暂不自动处理：

- `docs/`
- `sf/`
- `frontend-nextjs/`
- `intelligent_project_analyzer/`
- `tests/`
- 压缩包
- 客户资料
- 大型素材

这些目录和文件必须按功能批次单独确认。
