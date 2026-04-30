# 会话清理快速参考

## 🚀 快速开始（3步）

### Windows 用户（最简单）

```batch
REM 双击运行批处理文件
scripts\cleanup_sessions.bat

REM 或命令行执行
cd D:\11-20\langgraph-design
scripts\cleanup_sessions.bat
```

### Python 直接执行

```bash
# 1. 仅查看（推荐首次）
python scripts/cleanup_session_history.py --dry-run

# 2. 交互式清理
python scripts/cleanup_session_history.py

# 3. 自动清理
python scripts/cleanup_session_history.py -y
```

---

## 📋 清理什么？

✅ **会被清理的会话**:
- ❌ 状态异常：`failed`, `error`, `timeout`
- ⏰ 超时未完成：`processing` 超过 24 小时
- 🧪 测试会话：名称包含"测试"、"test"、"demo"等
- 📭 空会话：创建 1 小时后仍无数据
- 🔴 异常 user_id：`null`, `undefined`, `None`

✅ **不会被清理的会话**:
- ✓ 状态正常：`completed`, `in_progress`
- ✓ `web_user` 会话（除非明确异常）
- ✓ 有数据的活跃会话

---

## ⚡ 常用命令

| 命令 | 说明 |
|------|------|
| `scripts\cleanup_sessions.bat` | Windows图形菜单（推荐） |
| `python scripts/cleanup_session_history.py --dry-run` | 仅查看，不删除 |
| `python scripts/cleanup_session_history.py` | 交互式清理 |
| `python scripts/cleanup_session_history.py -y` | 自动清理（无确认） |

---

## 🔍 输出说明

### 扫描输出

```
→ 找到 15 个活跃会话
  ✗ abc12345... | alice | 测试项目 | completed
    原因: 测试会话: 测试项目

→ 发现 2 个异常活跃会话
```

- `✗` = 需要清理的会话
- `abc12345...` = 会话ID前8位
- `alice` = 用户ID
- `测试项目` = 项目名称
- `completed` = 会话状态

### 删除输出

```
  ✓ 已删除: abc12345...   # 删除成功
  ✗ 删除失败: def67890... # 删除失败
```

### 清理摘要

```
活跃会话: 15 个 → 删除 2 个
归档会话: 50 个 → 删除 1 个
失败: 0 个
```

---

## ⚠️ 重要提示

1. **首次使用**: 先用 `--dry-run` 查看要删除的内容
2. **数据备份**: 清理前建议先运行备份
3. **不可恢复**: 删除操作无法撤销
4. **停止服务**: 建议在服务停止时清理

---

## 🔧 故障处理

### Redis连接失败
```
✗ Redis连接失败: Connection refused
```
→ 检查 Redis 服务是否运行

### 归档数据库失败
```
⚠ 归档数据库连接失败
```
→ 检查 `data/archived_sessions.db` 是否存在

### 模块导入错误
```
ModuleNotFoundError
```
→ 确保在项目根目录执行

---

## 📖 详细文档

完整使用指南: [docs/SESSION_CLEANUP_GUIDE.md](docs/SESSION_CLEANUP_GUIDE.md)

---

## 🎯 推荐工作流

```bash
# 1. 备份（可选但推荐）
scripts\backup_project_fixed.bat

# 2. 仅扫描查看
python scripts/cleanup_session_history.py --dry-run

# 3. 确认后清理
python scripts/cleanup_session_history.py

# 4. 验证结果
redis-cli KEYS "session:*" | wc -l
```

---

**创建日期**: 2026-01-02
**版本**: v1.0
**相关修复**: v7.114 权限修复
