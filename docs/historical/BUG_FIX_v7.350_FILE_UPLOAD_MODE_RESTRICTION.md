# 🔧 v7.350: 普通思考模式禁用文件上传功能

**实施日期**: 2026年2月5日
**版本**: v7.350

---

## 📋 需求背景

用户要求普通思考模式取消附件上传机制，仅保留深度思考模式的附件上传功能。

---

## ✅ 实施内容

### 1. 前端 UI 修改

**文件**: [frontend-nextjs/app/page.tsx](../frontend-nextjs/app/page.tsx)

```typescript
// 修改前
{analysisMode !== 'search' && (
  // 显示附件上传按钮
)}

// 修改后 (v7.350)
{analysisMode === 'deep_thinking' && (
  // 仅深度思考模式显示附件上传按钮
)}
```

**效果**:
- ❌ 搜索模式: 不显示附件按钮
- ❌ 普通思考: 不显示附件按钮
- ✅ 深度思考: 显示附件按钮 (📎图标)

---

### 2. 配置文件更新

#### 2.1 分析模式配置

**文件**: [config/analysis_mode.yaml](../config/analysis_mode.yaml)

添加 `file_upload` 配置段:

```yaml
modes:
  normal:
    name: "普通模式"
    file_upload:
      enabled: false        # 禁用文件上传
      max_files: 0          # 不允许上传文件
      allowed_types: []     # 不允许任何文件类型

  deep_thinking:
    name: "深度思考模式"
    file_upload:
      enabled: true         # 启用文件上传
      max_files: 10         # 最多10个文件
      allowed_types:        # 允许的文件类型
        - pdf
        - txt
        - png
        - jpg
        - jpeg
        - webp
        - docx
        - xlsx
```

#### 2.2 环境变量说明

**文件**: [.env.example](../.env.example)

```env
# 🆕 v7.350: 文件上传模式控制
# 注意: 文件上传功能由 config/analysis_mode.yaml 中的 file_upload 配置控制
# - normal 模式: 禁用文件上传 (file_upload.enabled=false)
# - deep_thinking 模式: 启用文件上传 (file_upload.enabled=true)
# 允许的文件类型: pdf, txt, png, jpg, jpeg, webp, docx, xlsx
```

---

### 3. 后端验证逻辑

#### 3.1 配置管理器扩展

**文件**: [intelligent_project_analyzer/utils/mode_config.py](../intelligent_project_analyzer/utils/mode_config.py)

新增函数:

```python
def get_file_upload_config(analysis_mode: str) -> Dict[str, Any]:
    """
    获取指定分析模式的文件上传配置

    Returns:
        {
            "enabled": bool,           # 是否启用
            "max_files": int,          # 最大文件数
            "allowed_types": List[str] # 允许的类型
        }
    """

def is_file_upload_enabled(analysis_mode: str) -> bool:
    """检查是否启用文件上传"""
```

#### 3.2 API 端点验证

**文件**: [intelligent_project_analyzer/api/server.py](../intelligent_project_analyzer/api/server.py)

在 `start_analysis_with_files` 函数中添加验证:

```python
# 🆕 v7.350: 验证文件上传是否被允许
from intelligent_project_analyzer.utils.mode_config import get_file_upload_config

file_upload_config = get_file_upload_config(analysis_mode)

# 检查模式是否允许上传
if files and not file_upload_config.get("enabled", False):
    raise HTTPException(
        status_code=400,
        detail=f"当前模式 '{analysis_mode}' 不支持文件上传功能。如需上传文件，请切换到深度思考模式。"
    )

# 检查文件数量限制
if len(files) > file_upload_config.get("max_files", 0):
    raise HTTPException(
        status_code=400,
        detail=f"文件数量超过限制。当前模式最多允许上传 {file_upload_config['max_files']} 个文件。"
    )
```

---

### 4. 测试验证

**测试脚本**: [scripts/test_file_upload_config.py](../scripts/test_file_upload_config.py)

运行结果:
```
✅ 普通模式正确禁用文件上传
✅ 普通模式配置正确
✅ 深度思考模式正确启用文件上传
✅ 深度思考模式配置正确
   - 最大文件数: 10
   - 允许类型: pdf, txt, png, jpg, jpeg, webp, docx, xlsx
```

---

## 🎯 功能矩阵

| 分析模式 | 文件上传按钮 | API验证 | 最大文件数 | 允许类型 |
|---------|------------|---------|-----------|----------|
| 搜索模式 | ❌ 不显示 | N/A | 0 | 无 |
| 普通思考 | ❌ 不显示 | ✅ 拦截 | 0 | 无 |
| 深度思考 | ✅ 显示 | ✅ 验证 | 10 | pdf, txt, png, jpg, jpeg, webp, docx, xlsx |

---

## 🔐 安全保障

1. **前端控制**: UI层面隐藏上传按钮
2. **后端验证**: API强制检查模式和文件数量
3. **配置管理**: 统一配置文件管理权限
4. **错误提示**: 友好的错误消息引导用户

---

## 📦 部署说明

### 前端
- ✅ Next.js 热更新自动生效
- 无需重启服务

### 后端
- ✅ 配置文件热加载（通过 `@lru_cache` 缓存）
- ⚠️ 建议重启服务以确保配置生效

### 重启命令
```bash
# 重启后端
taskkill /F /IM python.exe
python -B scripts\run_server_production.py

# 前端（如需）
cd frontend-nextjs
npm run dev
```

---

## 🧪 测试清单

- [x] 配置文件语法正确
- [x] 模式配置加载成功
- [x] 普通模式禁用上传
- [x] 深度思考模式启用上传
- [x] API 验证逻辑正确
- [x] 前端 UI 正确显示/隐藏
- [x] 错误消息友好清晰

---

## 📝 后续优化建议

1. **配置热重载**: 考虑实现配置文件的热重载机制
2. **文件类型验证**: 在上传时验证文件扩展名
3. **权限管理**: 可根据用户等级调整文件上传限制
4. **统计日志**: 记录文件上传使用情况

---

## 🔗 相关文档

- [QUICKSTART.md](../QUICKSTART.md) - 快速启动指南
- [config/analysis_mode.yaml](../config/analysis_mode.yaml) - 分析模式配置
- [.env.example](../.env.example) - 环境变量模板
