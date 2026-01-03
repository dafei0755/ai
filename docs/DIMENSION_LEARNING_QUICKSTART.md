# 🚀 维度学习系统快速启用指南

> **5分钟启用智能维度推荐系统**
> 版本：v7.105 | 更新：2025-12-31

---

## ⚡ 快速启动

### 1. 启用学习系统

编辑 `.env` 文件：

```env
# 启用维度学习系统
ENABLE_DIMENSION_LEARNING=true

# 可选：自定义配置
DIMENSION_FEEDBACK_SAMPLE_RATE=0.20  # 20%用户反馈抽样率
DIMENSION_LOW_SCORE_THRESHOLD=40.0   # 低效维度阈值
```

### 2. 重启后端服务

```bash
# Windows
taskkill /F /IM python.exe
python -B run_server_production.py

# Linux/Mac
pkill python
python -B run_server_production.py
```

### 3. 验证启用

查看启动日志：

```log
✅ Redis 会话管理器已启动
✅ 会话归档管理器已启动
✅ 维度反馈路由已注册  # 🆕 看到此行说明成功
✅ 服务器启动成功
```

---

## 📊 工作原理

### 混合策略

```
┌─────────────────────────────────┐
│  第一次使用（无历史数据）       │
│  100% 规则引擎 → 保证稳定性     │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│  50次会话后（有数据积累）       │
│  80% 规则引擎 + 20% 学习优化    │
│  开始替换低效维度               │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│  500次会话后（充分学习）        │
│  30% 规则引擎 + 70% 学习优化    │
│  智能推荐主导策略               │
└─────────────────────────────────┘
```

### 学习循环

```
用户填写雷达图 → 生成报告 →
20%用户弹出评分弹窗（可跳过）→
提交评分（1-5星）→
系统记录反馈 →
下次会话自动优化维度选择
```

---

## 🎯 用户体验

### 前端变化

**Step 2 提交后（20%用户可见）**：

```
┌──────────────────────────────────────┐
│ ⭐ 维度有用性反馈（可选）            │
│                                      │
│ 哪些维度对您的需求最有帮助？         │
│                                      │
│ 📊 文化归属轴                        │
│    东方禅意 ← → 西方现代              │
│    ⭐⭐⭐⭐⭐ 非常有用                │
│                                      │
│ 🔒 隐私等级轴                        │
│    开放通透 ← → 私密内敛              │
│    ⭐⭐ 用处不大                      │
│                                      │
│ [跳过]  [提交反馈 (8/10)]           │
└──────────────────────────────────────┘
```

### 后端优化

系统自动：
- ✅ 记录每个维度的选择来源（规则/学习）
- ✅ 计算维度效果得分（0-100分）
- ✅ 替换低分维度（<40分）为高价值维度（>75分）
- ✅ 日志记录优化过程

---

## 📈 监控指标

### 查看学习效果

```bash
# 查看学习日志
tail -f logs/server.log | grep AdaptiveDimGen

# 示例输出
[AdaptiveDimGen] 学习优化开始 - 历史数据:125条, 学习权重:20%, 阶段:low
[AdaptiveDimGen] 发现3个低效维度, 计划替换1个
[AdaptiveDimGen] 替换维度 - 移除:privacy_level(得分:28.3) → 添加:spiritual_atmosphere(得分:78.5)
[AdaptiveDimGen] 学习优化完成 - 替换数量:1, 最终维度数:10
```

### 查看用户反馈

```bash
# 查看反馈日志
tail -f logs/server.log | grep DimensionFeedback

# 示例输出
[DimensionFeedback] 反馈已保存 - 会话:abc-123, 平均评分:4.20
[DimensionTracker] 记录用户反馈 - 有用维度:8, 低效维度:1
```

---

## 🔧 配置调优

### 调整学习权重

```env
# 更激进的学习策略（不推荐新手）
DIMENSION_LEARNING_WEIGHT_MINIMAL=0.20  # 0-50会话: 20%
DIMENSION_LEARNING_WEIGHT_LOW=0.40      # 50-200会话: 40%
DIMENSION_LEARNING_WEIGHT_MEDIUM=0.60   # 200-500会话: 60%
DIMENSION_LEARNING_WEIGHT_HIGH=0.80     # 500+会话: 80%

# 更保守的学习策略（推荐）
DIMENSION_LEARNING_WEIGHT_MINIMAL=0.05  # 0-50会话: 5%
DIMENSION_LEARNING_WEIGHT_LOW=0.10      # 50-200会话: 10%
DIMENSION_LEARNING_WEIGHT_MEDIUM=0.20   # 200-500会话: 20%
DIMENSION_LEARNING_WEIGHT_HIGH=0.40     # 500+会话: 40%
```

### 调整反馈抽样率

```env
# 增加反馈收集（更多数据）
DIMENSION_FEEDBACK_SAMPLE_RATE=0.50  # 50%用户

# 减少反馈收集（降低打扰）
DIMENSION_FEEDBACK_SAMPLE_RATE=0.10  # 10%用户
```

---

## 🐛 故障排查

### 问题1：学习系统未生效

**症状**：日志中没有 `AdaptiveDimGen` 记录

**检查**：
```bash
# 确认环境变量
echo $ENABLE_DIMENSION_LEARNING
# 输出应为: true

# 重启服务器
python -B run_server_production.py
```

### 问题2：反馈弹窗不出现

**可能原因**：
1. 抽样率设置过低（<20%）
2. 前端组件未集成
3. 浏览器缓存

**解决**：
```env
# 临时提高抽样率测试
DIMENSION_FEEDBACK_SAMPLE_RATE=1.0  # 100%弹出
```

### 问题3：历史数据不足

**症状**：日志显示 "历史数据不足10条，跳过学习优化"

**正常！** 系统设计为至少需要10条历史数据才启用学习。

**加速测试**：
```bash
# 创建测试会话（开发环境）
python scripts/generate_test_sessions.py --count 50
```

---

## 📊 A/B测试（可选）

### 启用对照实验

```python
# 在 adaptive_dimension_generator.py 中添加
def get_strategy(session_id: str) -> str:
    if hash(session_id) % 100 < 50:  # 50%对照组
        return "baseline"
    else:
        return "learning_optimized"
```

### 对比指标

在 Grafana/Kibana 中监控：
- 平均用户评分（baseline vs optimized）
- Gap触发后跟进率
- 报告完成率

---

## 🎓 深入学习

完整技术文档：[docs/DIMENSION_LEARNING_SYSTEM.md](../../docs/DIMENSION_LEARNING_SYSTEM.md)

包含：
- 详细算法设计
- 数据流图
- API接口文档
- 性能指标KPI
- 未来规划

---

## 💬 反馈与支持

遇到问题？请提交 [GitHub Issue](https://github.com/dafei0755/ai/issues/new)

---

<div align="center">

**快速启用完成！** 🎉
系统将在后台自动学习并优化维度推荐

[← 返回主文档](../../README.md)

</div>
