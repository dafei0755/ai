# 项目目录整理方案

## 📋 整理目标

将测试脚本、文档、历史文件分类整理，保持项目根目录清爽。

---

## 📁 目录结构规划

```
langgraph-design/
├── docs/                          # 📚 所有项目文档
│   ├── setup/                     # 配置指南
│   │   ├── OPENROUTER_SETUP_GUIDE.md
│   │   ├── OPENROUTER_VS_OFFICIAL_API.md
│   │   └── PRIORITY_CONFIG_SUMMARY.md
│   ├── fixes/                     # 修复记录
│   │   └── QUALITY_PREFLIGHT_JSON_FIX.md
│   ├── comparisons/               # 对比分析
│   │   └── LLM_PROVIDER_COMPARISON.md
│   └── PROJECT_STRUCTURE.md       # 项目结构
│
├── tests/                         # 🧪 所有测试脚本
│   ├── test_openrouter.py
│   ├── test_priority_config.py
│   ├── test_quality_preflight_fix.py
│   └── test_jtbd_transform.py
│
├── scripts/                       # 🔧 工具脚本
│   └── check_llm_config.py
│
├── .env                           # 环境配置
├── README.md                      # 项目说明
├── requirements.txt               # 依赖列表
└── start_services.bat             # 启动脚本
```

---

## 🎯 整理操作

### 1️⃣ 创建子目录
```bash
docs/setup/
docs/fixes/
docs/comparisons/
```

### 2️⃣ 移动文档
- `OPENROUTER_SETUP_GUIDE.md` → `docs/setup/`
- `OPENROUTER_VS_OFFICIAL_API.md` → `docs/setup/`
- `PRIORITY_CONFIG_SUMMARY.md` → `docs/setup/`
- `QUALITY_PREFLIGHT_JSON_FIX.md` → `docs/fixes/`
- `LLM_PROVIDER_COMPARISON.md` → `docs/comparisons/`
- `PROJECT_STRUCTURE.md` 保留在 `docs/`

### 3️⃣ 移动测试脚本
- `test_openrouter.py` → `tests/`
- `test_priority_config.py` → `tests/`
- `test_quality_preflight_fix.py` → `tests/`
- `test_jtbd_transform.py` → `tests/`

### 4️⃣ 移动工具脚本
- `check_llm_config.py` → `scripts/`

### 5️⃣ 清理缓存
- 删除 `__pycache__/`（根目录）

---

## ✅ 整理后的根目录

```
langgraph-design/
├── .env
├── .github/
├── .vscode/
├── docs/                 # 📚 文档目录
├── intelligent_project_analyzer/
├── logs/
├── README.md
├── reports/
├── requirements.txt
├── scripts/              # 🔧 工具脚本
├── start_services.bat
└── tests/                # 🧪 测试脚本
```

**保持根目录清爽，便于维护！**
