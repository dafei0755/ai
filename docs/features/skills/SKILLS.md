# Skills 使用与维护手册

## 1. 目的

本文件记录本项目中与 Codex Skills 相关的关键信息，包括：
- 可用系统 Skills
- 已安装第三方 Skills
- 安装来源与地址
- 标准调用方式
- 网站扫描与信息整理流程
- 常见问题与排障

## 2. Skills 概念

Skill 是一组可复用的本地指令与资源，核心文件是 `SKILL.md`。
Codex 会根据 `name/description` 与用户请求匹配并触发对应 Skill。

典型目录结构：

```text
<skill-name>/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
├── references/
└── assets/
```

## 3. 当前会话可用的系统 Skills

以下为当前环境预装系统 Skills（`.system`）：

1. `skill-creator`
   - 路径：`C:/Users/SF/.codex/skills/.system/skill-creator/SKILL.md`
   - 用途：创建或更新 Skill
2. `skill-installer`
   - 路径：`C:/Users/SF/.codex/skills/.system/skill-installer/SKILL.md`
   - 用途：列出/安装 Skills（curated 或 GitHub 路径）

## 4. 已安装的研究与扫描相关 Skills

安装位置（本机）：

- `C:\Users\SF\.codex\skills\playwright`
- `C:\Users\SF\.codex\skills\screenshot`
- `C:\Users\SF\.codex\skills\notion-research-documentation`

## 5. 安装来源地址

官方仓库与目录：

- 仓库主页：<https://github.com/openai/skills>
- curated 目录：<https://github.com/openai/skills/tree/main/skills/.curated>

本项目已安装 Skill 对应地址：

- `playwright`：<https://github.com/openai/skills/tree/main/skills/.curated/playwright>
- `screenshot`：<https://github.com/openai/skills/tree/main/skills/.curated/screenshot>
- `notion-research-documentation`：<https://github.com/openai/skills/tree/main/skills/.curated/notion-research-documentation>

## 6. skill-installer 脚本位置

- `C:\Users\SF\.codex\skills\.system\skill-installer\scripts\list-skills.py`
- `C:\Users\SF\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py`

## 7. 标准调用方式

### 7.1 列出可安装 Skills（curated）

```bash
python C:/Users/SF/.codex/skills/.system/skill-installer/scripts/list-skills.py
```

### 7.2 安装 curated Skills

```bash
python C:/Users/SF/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo openai/skills \
  --path skills/.curated/playwright skills/.curated/screenshot skills/.curated/notion-research-documentation
```

### 7.3 从指定 GitHub 路径安装

```bash
python C:/Users/SF/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo <owner>/<repo> \
  --path <path/to/skill>
```

安装完成后：**重启 Codex** 使新 Skill 生效。

## 8. 网站扫描与信息整理推荐流程

默认策略：
- 两阶段扫描：全网发现 + 重点站点深挖
- 输出：结构化 Markdown 报告
- 质量：官方/一手来源优先

输入结构建议（`ScanTask`）：
- `topic`
- `time_window`
- `seed_sites`
- `languages`
- `max_depth_per_site`
- `exclusions`

输出结构建议（`ResearchReport`）：
- `summary`
- `findings`
- `comparison_table`
- `sources`
- `verification`
- `open_questions`

参考文档：
- `docs/research_scan/EXECUTION_SOP.md`
- `docs/research_scan/SCAN_TASK_TEMPLATE.md`
- `docs/research_scan/REPORT_TEMPLATE.md`
- `docs/research_scan/QUALITY_GATE_CHECKLIST.md`

## 9. 质量门禁建议

交付前至少满足：

- 关键结论由 2 个独立来源交叉验证
- 时间敏感信息使用绝对日期（如 `2026-02-25`）
- 每条结论可追溯到具体 URL
- 标注 `T1/T2/T3` 与 `primary/secondary`
- 明确区分事实与推断

## 10. 常见问题

1. 新安装 Skill 不触发
   - 处理：重启 Codex；确认技能目录在 `~/.codex/skills/<skill-name>`

2. experimental 列表查询失败
   - 处理：先用 curated；或检查上游目录是否可访问

3. 安装脚本鉴权失败
   - 处理：配置 `GITHUB_TOKEN`/`GH_TOKEN`，或改用 git 凭据
