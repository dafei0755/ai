# 项目清理总结

## 清理结果

### 已清理内容
- Python 缓存文件已清理
- 测试缓存已清理
- 项目当前大小: 589.60 MB

### 大文件分析
1. frontend-nextjs/node_modules (约200 MB) - 必需
2. data/archived_sessions.db (45.90 MB) - 可清理旧数据
3. frontend-nextjs/.next/cache (约30 MB) - 可删除重建

## 清理建议

### 可安全删除
1. Next.js 构建缓存: `cd frontend-nextjs && rm -rf .next`
2. 旧日志文件: `find logs -name "*.log" -mtime +7 -delete`
3. 归档会话数据（需备份）

### 定期维护
- 每周运行 `python cleanup.py`
- 每月清理 Next.js 缓存
- 每季度审查大文件

## 清理脚本
运行 `python cleanup.py` 自动清理缓存和临时文件
