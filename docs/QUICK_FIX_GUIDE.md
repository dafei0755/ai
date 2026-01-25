# 常见问题快速修复指南

> 遇到问题？先在这里查找！本文档提供最常见问题的即时解决方案。

## 🖼️ 图片相关问题

### 问题 1: 概念图显示为黑色方块
**症状**: 报告中的概念图显示为黑色方块，需要点击后才能在弹窗中查看

**快速诊断**:
```bash
# 1. 检查图片文件是否存在
ls data/generated_images/[session_id]/*.png

# 2. 检查后端服务是否运行
curl -I http://localhost:8000/generated_images/[session_id]/[filename].png

# 3. 检查前端代理配置
cat frontend-nextjs/next.config.mjs | grep generated_images
```

**解决方案**:
→ **[BUGFIX_v7.126_IMAGE_DISPLAY.md](./BUGFIX_v7.126_IMAGE_DISPLAY.md)**

**关键修复**:
- 移除LazyImage组件的懒加载逻辑
- 改为16:9比例全宽直接展示
- 移除loading状态

**修复代码位置**:
- `frontend-nextjs/components/report/ExpertReportAccordion.tsx:1640-2070`

---

### 问题 2: 生成的图片与项目内容无关
**症状**: AI生成的概念图完全偏离项目主题，看起来很随机

**快速诊断**:
```bash
# 检查图片metadata中的prompt
cat data/generated_images/[session_id]/metadata.json | grep "prompt"

# 如果看到 "prompt": "A" 或单字符，说明遇到了v7.121的bug
```

**解决方案**:
→ **[BUGFIX_v7.122_IMAGE_PROMPT.md](./BUGFIX_v7.122_IMAGE_PROMPT.md)**

**关键修复**:
- 修复字符串索引错误：`visual_prompts[0]` → `visual_prompts`
- 添加prompt长度验证（>10字符）

**修复代码位置**:
- `intelligent_project_analyzer/services/image_generator.py:1011-1020`

**注意**:
- 修复前生成的旧会话数据会永久保留单字符prompt
- 需要重新生成分析才能获得正确的概念图

---

### 问题 3: 图片加载缓慢或一直转圈
**症状**: 图片加载时间超过5秒，或显示加载动画但从不消失

**快速检查**:
```bash
# 检查后端服务状态
netstat -ano | grep 8000

# 检查Next.js dev server
netstat -ano | grep 3000

# 检查图片文件大小
du -h data/generated_images/[session_id]/*.png
```

**可能原因**:
1. 后端服务未运行（端口8000）
2. 图片文件过大（> 2MB）
3. 懒加载逻辑问题（v7.126已修复）

**解决方案**:
```bash
# 重启后端服务
python scripts/run_server_production.py

# 重启前端服务
cd frontend-nextjs && npm run dev
```

---

## 🎨 前端UI问题

### 问题 4: 鼠标悬停时出现蓝色边框或文字提示
**症状**: 鼠标移到图片上时显示蓝色边框和"点击查看大图"文字

**快速修复**: 已在v7.126中移除

**验证**:
```typescript
// 检查 ExpertReportAccordion.tsx
// 应该看到 border-transparent (无边框)
// 不应该有悬停遮罩代码
```

---

## 🔧 后端API问题

### 问题 5: API返回空数据或null
**症状**: `/api/report/{session_id}` 返回 `structured_report: null`

**快速诊断**:
```bash
# 1. 检查Redis中的数据
redis-cli
> GET "session:[session_id]"

# 2. 检查归档数据库
sqlite3 data/archived_sessions.db
> SELECT session_id FROM archived_sessions WHERE session_id LIKE '%[部分ID]%';

# 3. 检查后端日志
tail -f logs/app.log | grep ERROR
```

**常见原因**:
1. 会话尚未完成 (`status != "completed"`)
2. 数据序列化失败（Pydantic验证错误）
3. Redis连接断开

**解决方案**:
```bash
# 重启Redis
sudo systemctl restart redis

# 检查会话状态
curl http://localhost:8000/api/status/[session_id]
```

---

## 📊 性能问题

### 问题 6: 报告加载超过10秒
**症状**: 打开报告页面后长时间白屏或loading

**性能检查清单**:
- [ ] 检查图片总大小（建议 < 5MB）
- [ ] 检查报告内容长度（建议 < 100KB）
- [ ] 检查网络请求数量（应 < 10个）
- [ ] 检查Redis响应时间（应 < 100ms）

**优化建议**:
```bash
# 压缩图片
mogrify -resize 1920x1080 -quality 85 data/generated_images/*/*.png

# 清理旧会话数据（保留最近100个）
python scripts/cleanup_old_sessions.py --keep 100
```

---

## 🐛 调试技巧

### 浏览器控制台检查
```javascript
// 打开浏览器控制台 (F12)

// 1. 检查API响应
fetch('/api/report/[session_id]')
  .then(r => r.json())
  .then(d => console.log('structured_report:', d.structured_report))

// 2. 检查图片URL
document.querySelectorAll('img').forEach(img =>
  console.log(img.src, img.complete ? '✅' : '❌')
)

// 3. 检查网络请求
// Network标签 → 过滤PNG → 查看状态码
```

### 后端日志分析
```bash
# 实时查看错误日志
tail -f logs/app.log | grep -E "ERROR|WARNING"

# 查找特定会话的日志
grep "[session_id]" logs/app.log

# 检查图片生成日志
grep "generate_deliverable_image" logs/app.log
```

### 数据库检查
```bash
# 检查Redis
redis-cli INFO | grep connected_clients
redis-cli --bigkeys

# 检查SQLite
sqlite3 data/archived_sessions.db
> .schema
> SELECT COUNT(*) FROM archived_sessions;
> SELECT session_id, status, created_at FROM archived_sessions
  ORDER BY created_at DESC LIMIT 10;
```

---

## 📚 完整文档索引

### 修复文档
- [Bug修复索引](./BUGFIX_INDEX.md) - 所有修复记录汇总
- [v7.126 概念图显示优化](./BUGFIX_v7.126_IMAGE_DISPLAY.md)
- [v7.122 图片Prompt修复](./BUGFIX_v7.122_IMAGE_PROMPT.md)

### 开发规范
- [核心开发规范](../.github/DEVELOPMENT_RULES_CORE.md)
- [变更检查清单](../.github/PRE_CHANGE_CHECKLIST.md)

### API文档
- [API参考](../api/README.md)
- [数据模型](../intelligent_project_analyzer/models/README.md)

---

## 🆘 仍然无法解决？

1. **查看完整文档**: [BUGFIX_INDEX.md](./BUGFIX_INDEX.md)
2. **搜索历史Issue**: `grep -r "your_problem" docs/`
3. **创建新Issue**: 详细描述问题、错误日志、复现步骤
4. **联系维护者**: 提供会话ID和错误截图

---

**最后更新**: 2026-01-03
**维护者**: Claude Code
**反馈渠道**: GitHub Issues
