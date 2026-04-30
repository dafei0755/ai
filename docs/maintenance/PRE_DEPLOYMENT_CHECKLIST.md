# 生产环境部署前清单

**版本**: v1.0
**最后更新**: 2025-12-06
**适用场景**: 生产环境首次部署或重大版本更新

---

## 使用说明

在部署到生产环境前，请**逐项检查**以下清单。所有标注为**[必需]**的项目必须完成，**[推荐]**的项目强烈建议完成。

检查方式：
- ✅ 已完成
- ⚠️ 部分完成/有风险
- ❌ 未完成

---

## 第一阶段：环境配置检查

### 1.1 环境变量配置 [必需]

**验证命令**: `python scripts/verify_deployment.py --check-env`

- [ ] `.env`文件已创建（不在`.gitignore`中，但不提交到Git）
- [ ] 所有必需环境变量已配置：
  - [ ] `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY` 或 `GOOGLE_API_KEY`（至少一个）
  - [ ] `REDIS_HOST`、`REDIS_PORT`、`REDIS_DB`
  - [ ] `TENCENT_CLOUD_SECRET_ID`、`TENCENT_CLOUD_SECRET_KEY`（生产环境必需）
  - [ ] `TENCENT_CONTENT_SAFETY_APP_ID`
  - [ ] `ENABLE_TENCENT_CONTENT_SAFETY=true`（生产环境必需）
- [ ] 环境变量格式正确（SecretId以`AKID`开头）
- [ ] 无敏感信息泄露（密钥不在代码中）

### 1.2 依赖安装 [必需]

**验证命令**: `python scripts/verify_deployment.py --check-deps`

- [ ] Python依赖已安装：`pip install -r requirements.txt`
- [ ] 前端依赖已安装：`cd frontend-nextjs && npm install`
- [ ] 腾讯云SDK已安装：`pip install tencentcloud-sdk-python>=3.0.1100`
- [ ] 所有依赖版本兼容（无冲突）

### 1.3 Redis服务 [必需]

**验证命令**: `python scripts/verify_deployment.py --check-redis`

- [ ] Redis服务已启动
- [ ] Redis可访问（`redis-cli ping`返回`PONG`）
- [ ] Redis密码已配置（如有）
- [ ] Redis持久化已配置（RDB或AOF）
- [ ] Redis最大内存已设置（防止OOM）

---

## 第二阶段：功能配置检查

### 2.1 腾讯云内容安全 [必需]

**验证命令**: `python scripts/verify_tencent_config.py`

- [ ] 腾讯云账号已创建
- [ ] 内容安全服务已开通
- [ ] 应用已创建（Application ID: 1997127090860864256）
- [ ] 子账号已创建（推荐使用`sf2025`或类似）
- [ ] 子账号权限已分配（`QcloudTMSFullAccess`）
- [ ] API密钥已创建并配置到`.env`
- [ ] API调用测试成功（运行验证脚本）

### 2.2 动态安全规则 [推荐]

**验证命令**: `python scripts/verify_deployment.py --check-rules`

- [ ] `security_rules.yaml`文件存在
- [ ] YAML语法正确（无缩进错误）
- [ ] 关键词规则已配置（至少5个类别）
- [ ] 隐私信息规则已配置（14种类型）
- [ ] 变形规避规则已配置（5种模式）
- [ ] 白名单已配置（如有需要）
- [ ] 规则文件可读（权限正确）

### 2.3 文件上传配置 [推荐]

**验证命令**: `python scripts/verify_deployment.py --check-upload`

- [ ] 上传目录已创建（`./data/uploads`）
- [ ] 上传目录可写（权限正确）
- [ ] 文件大小限制已配置（默认10MB）
- [ ] 支持的文件类型已确认（.txt, .md, .pdf, .docx, .jpg, .png）

---

## 第三阶段：服务启动检查

### 3.1 后端服务 [必需]

**启动命令**: `python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000`

- [ ] 后端服务可启动（无报错）
- [ ] `/health`端点可访问（http://localhost:8000/health）
- [ ] `/readiness`端点返回`ready`状态
- [ ] `/docs` Swagger文档可访问
- [ ] 日志输出正常（无ERROR级别日志）

### 3.2 前端服务 [必需]

**启动命令**: `cd frontend-nextjs && npm run build && npm start`

- [ ] 前端构建成功（`npm run build`）
- [ ] 前端服务可启动（`npm start`）
- [ ] 首页可访问（http://localhost:3000）
- [ ] API连接正常（可与后端通信）

### 3.3 Celery Worker [推荐]

**启动命令**: `celery -A intelligent_project_analyzer.services.celery_app worker --loglevel=info`

- [ ] Celery worker可启动（如使用）
- [ ] Worker可连接到Redis
- [ ] 任务队列工作正常

---

## 第四阶段：功能验证

### 4.1 内容安全检测 [必需]

**验证命令**: `pytest tests/test_integration.py::TestIntegration::test_complete_detection_flow -v`

- [ ] 关键词检测正常
- [ ] 隐私信息检测正常（14种类型）
- [ ] 变形规避检测正常（5种模式）
- [ ] 腾讯云API调用成功
- [ ] 多层检测协同工作
- [ ] 正常内容不误拦截

### 4.2 动态规则热加载 [推荐]

**验证命令**: `pytest tests/test_p2_features.py::TestDynamicRuleLoader::test_hot_reload_detection -v`

- [ ] 规则加载器初始化成功
- [ ] 文件修改可自动检测
- [ ] 规则重载成功（60秒内）
- [ ] 重载后新规则生效

### 4.3 优雅降级 [推荐]

**验证命令**: `pytest tests/test_integration.py::TestIntegration::test_graceful_degradation* -v`

- [ ] 腾讯云API故障时回退到本地检测
- [ ] 动态规则加载失败时回退到静态规则
- [ ] 外部依赖故障不影响核心功能

---

## 第五阶段：性能测试

### 5.1 负载测试 [推荐]

**验证命令**: `pytest tests/test_integration.py::TestIntegration::test_performance_baseline -v`

- [ ] 单次检测响应时间<1秒（不含外部API）
- [ ] 并发10用户无错误
- [ ] 并发50用户无明显延迟
- [ ] 内存使用稳定（无泄漏）

### 5.2 规则加载性能 [推荐]

**验证命令**: `pytest tests/test_p2_features.py::TestPerformance -v`

- [ ] 规则初始加载<1秒
- [ ] 规则访问1000次<0.1秒
- [ ] 文件修改检测<10ms

---

## 第六阶段：安全审查

### 6.1 配置安全 [必需]

- [ ] `.env`文件不在Git中（`.gitignore`已配置）
- [ ] API密钥不在代码中硬编码
- [ ] 密钥不在日志中输出
- [ ] 数据库连接使用密码（Redis）

### 6.2 网络安全 [推荐]

- [ ] CORS配置限制允许的域名（生产环境）
- [ ] API速率限制已启用（防止滥用）
- [ ] HTTPS已配置（如对外服务）
- [ ] 防火墙规则已配置（限制端口访问）

### 6.3 内容安全 [必需]

- [ ] 所有用户输入经过内容安全检测
- [ ] 敏感信息自动脱敏（隐私信息）
- [ ] 误拦截率<1%（测试验证）
- [ ] 检测准确率>95%（结合腾讯云API）

---

## 第七阶段：监控和日志

### 7.1 健康检查 [必需]

**验证URL**:
- http://localhost:8000/health
- http://localhost:8000/readiness

- [ ] `/health`端点返回正常
- [ ] `/readiness`端点检查通过
- [ ] 负载均衡器配置健康检查（如使用）

### 7.2 日志配置 [推荐]

- [ ] 日志级别已设置（生产环境使用INFO或WARNING）
- [ ] 日志输出到文件（而非仅console）
- [ ] 日志轮转已配置（防止磁盘占满）
- [ ] 敏感信息已脱敏（不记录完整密钥）

### 7.3 错误监控 [推荐]

- [ ] 错误监控已集成（如Sentry）
- [ ] 关键错误告警已配置
- [ ] 告警渠道已测试（邮件/Slack/钉钉）

---

## 第八阶段：备份和恢复

### 8.1 数据备份 [推荐]

- [ ] Redis数据备份策略已制定
- [ ] 上传文件备份策略已制定
- [ ] 配置文件备份已完成
- [ ] 备份定期执行（cron或定时任务）

### 8.2 恢复测试 [推荐]

- [ ] 恢复流程已测试
- [ ] 恢复时间目标（RTO）已确认
- [ ] 恢复点目标（RPO）已确认

---

## 第九阶段：文档和培训

### 9.1 文档完整性 [推荐]

- [ ] README文档已更新
- [ ] DEPLOYMENT.md部署文档已阅读
- [ ] API文档已生成（Swagger）
- [ ] 故障排查文档已准备

### 9.2 团队培训 [推荐]

- [ ] 运维团队已培训（部署流程）
- [ ] 开发团队已培训（故障排查）
- [ ] 紧急联系方式已确认

---

## 快速自动验证

运行一键验证脚本，自动检查大部分项目：

```bash
python scripts/verify_deployment.py --full-check
```

预期输出：
```
============================================================
生产环境部署前验证
============================================================
✅ 环境变量配置: 通过
✅ 依赖安装: 通过
✅ Redis服务: 通过
✅ 腾讯云API: 通过
✅ 动态规则: 通过
✅ 健康检查: 通过
⚠️ Celery Worker: 未启用（可选）

============================================================
✅ 验证通过！系统可以部署到生产环境
============================================================
```

---

## 常见问题

### Q1: 某些检查项无法通过怎么办？

**A1**: 根据优先级处理：
- **[必需]项未通过**: 必须修复后才能部署
- **[推荐]项未通过**: 可以部署但建议尽快修复
- 参考DEPLOYMENT.md中的故障排查部分

### Q2: 如何快速定位问题？

**A2**:
1. 查看验证脚本输出的详细错误信息
2. 检查相关服务日志
3. 运行对应的单元测试
4. 参考DEPLOYMENT.md的常见问题章节

### Q3: 首次部署需要多长时间？

**A3**:
- 最小配置（仅必需项）：30-60分钟
- 标准配置（必需+推荐）：2-3小时
- 完整配置（所有项）：半天

---

## 部署完成后

- [ ] 运行冒烟测试（Smoke Test）
- [ ] 监控系统指标（CPU、内存、网络）
- [ ] 观察错误日志（前24小时）
- [ ] 准备回滚方案（如有问题）

**祝部署顺利！**
