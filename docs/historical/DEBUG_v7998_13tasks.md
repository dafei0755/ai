# v7.998终极诊断清单

## 问题：重启后端仍然13个任务

### ✅ 已验证项目

1. **代码修复正确** ✅
   - 阈值: 0.12/0.25/0.45 (从0.15/0.30/0.50)
   - 最小任务数: 8/18/28/40 (从8/13/23/36)
   - 文件: core_task_decomposer.py

2. **本地验证通过** ✅
   - 狮岭村0.290 → 推荐28-36个
   - verify_v7998.py 验证通过

3. **后端已重启** ✅
   - 旧进程已停止 (PID: 34456)
   - 新窗口启动新进程
   - __pycache__缓存已清理

### ⚠️  可能原因（按概率排序）

#### 原因1: **使用了旧session** (90%概率) ⚠️

**症状**:
- 前端显示13个任务
- 后端日志显示28-36个

**原因**:
旧session的任务列表已存入数据库，后端不会重新生成

**解决**:
```
前端 → 点击"新建会话" → 重新输入狮岭村案例 → 检查任务数
```

#### 原因2: **Prompt未传递推荐范围** (5%概率)

**检查**:
查看后端日志是否包含:
```
推荐任务数量范围: 28-36个
```

**如果没有**:
检查代码是否正确拼接Prompt

#### 原因3: **LLM仍选择下限** (3%概率)

**检查**:
- 后端日志: 推荐28-36个 ✅
- LLM生成: 18个 ❌

**原因**: Prompt措辞问题

**解决**: 优化Prompt措辞（v7.999）

#### 原因4: **配置文件未加载** (2%概率)

**检查**:
后端日志是否有:
```
配置加载成功: core_task_decomposer.yaml
```

**如果失败**: YAML格式错误

---

## 🔬 立即诊断命令

### 命令1: 检查后端实际加载的阈值
```python
python -c "from intelligent_project_analyzer.services.core_task_decomposer import TaskComplexityAnalyzer; import inspect; print(inspect.getsource(TaskComplexityAnalyzer.analyze).split('complexity_score <')[1:4])"
```

### 命令2: 检查数据库中旧session
```python
python -c "
import sqlite3
conn = sqlite3.connect('session_storage.db')
cursor = conn.execute('SELECT session_id, created_at, COUNT(*) as task_count FROM analysis_sessions JOIN tasks ON analysis_sessions.session_id = tasks.session_id GROUP BY analysis_sessions.session_id ORDER BY created_at DESC LIMIT 5')
for row in cursor: print(row)
"
```

### 命令3: 实时监控后端日志
```bash
tail -f backend.log | grep "建议任务数"
```

---

## 🎯 终极解决方案

### 方案A: 如果是旧session问题 ✅ 推荐

**步骤**:
1. 前端清空所有session历史
2. 创建全新session
3. 输入狮岭村案例
4. 等待后端生成
5. 检查任务数

**预期结果**: 30-34个任务

### 方案B: 如果仍是13个 ⚠️

**可能性1**: Prompt未传递范围

**检查代码**: `core_task_decomposer.py` 第800-850行
```python
system_prompt = system_prompt.replace(
    "推荐任务数量范围",
    f"推荐任务数量范围: {recommended_min}-{recommended_max}个"
)
```

**可能性2**: LLM仍选择下限18

**优化Prompt** (v7.999):
```yaml
- 当前项目复杂度: {complexity_score}
- 推荐任务数: **至少{recommended_min + 5}个**
- 最大任务数: {recommended_max}个
- 要求: 充分拆解，确保调研深度
```

---

## 📊 验证检查表

- [ ] 后端进程已重启（检查PID变化）
- [ ] __pycache__已清理
- [ ] verify_v7998.py 验证通过（28-36个）
- [ ] **前端创建新session** ← 最关键
- [ ] 后端日志显示"建议任务数=28-36"
- [ ] Prompt包含"推荐任务数量范围: 28-36个"
- [ ] LLM生成任务数 > 13

---

## 🆘 如果以上都不行

**最后手段**: 直接修改Prompt强制最小值

```yaml
### 任务数量硬性要求
- 本案例复杂度高（5位建筑师对标+文化深挖）
- **必须生成至少30个任务**
- 不得少于28个
```

或直接在代码中强制:
```python
if complexity_score >= 0.25 and len(tasks) < 25:
    logger.warning(f"⚠️ 复杂项目仅生成{len(tasks)}个任务，强制补齐")
    # 补齐逻辑...
```

---

**创建时间**: 2026-02-14 18:20
**状态**: 等待前端新session验证
