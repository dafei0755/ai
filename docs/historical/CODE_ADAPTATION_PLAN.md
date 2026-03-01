# 代码适配计划：新配置文件集成

## 目标

将新创建的配置文件集成到现有代码中：
1. `role_gene_pool.yaml` - 角色元数据目录
2. `role_selection_rules.yaml` - 角色选择规则（替代 `role_selection_strategy.yaml`）
3. `MODE_TASK_LIBRARY.yaml` - 任务库（已更新为 `quality_target` 格式）

---

## 需要修改的文件

### 1. strategy_manager.py ✅ 优先
**当前问题：**
- 第 27 行：硬编码读取 `role_selection_strategy.yaml`
- 需要改为读取 `role_selection_rules.yaml`

**修改内容：**
```python
# 修改前
strategy_file = config_dir / "role_selection_strategy.yaml"

# 修改后
strategy_file = config_dir / "role_selection_rules.yaml"
```

**兼容性处理：**
- 如果 `role_selection_rules.yaml` 不存在，回退到 `role_selection_strategy.yaml`
- 添加日志提示使用了哪个配置文件

---

### 2. dynamic_project_director.py ✅ 优先
**当前问题：**
- 第 403 行：硬编码读取 `role_selection_strategy.yaml`
- 需要改为读取 `role_selection_rules.yaml`

**修改内容：**
```python
# 修改前
strategy_path = Path(__file__).parent.parent / "config" / "role_selection_strategy.yaml"

# 修改后
strategy_path = Path(__file__).parent.parent / "config" / "role_selection_rules.yaml"
```

---

### 3. role_weight_calculator.py ✅ 优先
**当前问题：**
- 第 45 行：硬编码读取 `role_selection_strategy.yaml`
- 需要改为读取 `role_selection_rules.yaml`

**修改内容：**
```python
# 修改前
default_path = Path(__file__).parent.parent / "config" / "role_selection_strategy.yaml"

# 修改后
default_path = Path(__file__).parent.parent / "config" / "role_selection_rules.yaml"
```

---

### 4. mode_task_library.py ⚠️ 中等优先级
**当前问题：**
- 第 140 行注释：提到返回 `validation_criteria`
- 实际代码需要处理 `quality_target` 格式

**修改内容：**
1. 更新注释：`validation_criteria` → `quality_target`
2. 确保任务提取逻辑支持新格式
3. 添加向后兼容性处理

**代码示例：**
```python
# 提取任务时同时支持新旧格式
def _extract_task_validation(task_config: Dict) -> Dict:
    """提取任务验证标准（兼容新旧格式）"""
    # 优先使用新格式
    if "quality_target" in task_config:
        return {
            "type": "quality_target",
            "dimension": task_config["quality_target"]["dimension"],
            "target_level": task_config["quality_target"]["target_level"],
            "reference": task_config["quality_target"]["reference"],
            "criteria_mapping": task_config["quality_target"]["criteria_mapping"]
        }
    # 回退到旧格式
    elif "validation_criteria" in task_config:
        return {
            "type": "validation_criteria",
            "criteria": task_config["validation_criteria"]
        }
    else:
        return {"type": "none"}
```

---

### 5. role_manager.py 📝 低优先级（未来优化）
**当前状态：**
- 已支持从 `config/roles/` 目录加载角色配置
- 可以读取 `role_gene_pool.yaml` 中的角色定义

**未来优化：**
- 添加专门的方法读取 `role_gene_pool.yaml`
- 实现 V6 子角色的显式选择逻辑
- 当前可以正常工作，不影响主流程

---

## 实施步骤

### 阶段 1：路径更新（P0）⏱️ 15 分钟
1. ✅ 修改 `strategy_manager.py` 第 27 行
2. ✅ 修改 `dynamic_project_director.py` 第 403 行
3. ✅ 修改 `role_weight_calculator.py` 第 45 行
4. ✅ 添加向后兼容性检查

### 阶段 2：任务验证格式更新（P1）⏱️ 30 分钟
1. ⏳ 修改 `mode_task_library.py` 注释
2. ⏳ 添加 `quality_target` 提取逻辑
3. ⏳ 保留 `validation_criteria` 兼容性
4. ⏳ 更新相关类型定义

### 阶段 3：测试验证（P0）⏱️ 20 分钟
1. ⏳ 测试配置文件加载
2. ⏳ 测试角色选择流程
3. ⏳ 测试任务分配流程
4. ⏳ 验证向后兼容性

### 阶段 4：V6 子角色显式选择（P2）⏱️ 1-2 小时
1. ⏳ 在 `role_manager.py` 中添加 V6 子角色查询方法
2. ⏳ 在 `dynamic_project_director.py` 中实现子角色选择逻辑
3. ⏳ 更新提示词以支持子角色选择
4. ⏳ 测试子角色选择功能

---

## 兼容性策略

### 配置文件回退机制
```python
def _load_config_with_fallback(primary_path: Path, fallback_path: Path) -> Dict:
    """加载配置文件，支持回退"""
    if primary_path.exists():
        logger.info(f"✅ 使用新配置: {primary_path.name}")
        return yaml.safe_load(primary_path.read_text(encoding='utf-8'))
    elif fallback_path.exists():
        logger.warning(f"⚠️ 新配置不存在，使用旧配置: {fallback_path.name}")
        return yaml.safe_load(fallback_path.read_text(encoding='utf-8'))
    else:
        logger.error(f"❌ 配置文件不存在: {primary_path.name} 和 {fallback_path.name}")
        return {}
```

### 任务验证格式兼容
```python
def _get_task_validation(task: Dict) -> Dict:
    """获取任务验证标准（兼容新旧格式）"""
    if "quality_target" in task:
        # 新格式：返回结构化的质量目标
        return {
            "format": "quality_target",
            "data": task["quality_target"]
        }
    elif "validation_criteria" in task:
        # 旧格式：返回验证标准列表
        return {
            "format": "validation_criteria",
            "data": task["validation_criteria"]
        }
    else:
        return {"format": "none", "data": None}
```

---

## 风险控制

### 已识别风险
1. **配置文件不存在**
   - 缓解：实现回退机制
   - 影响：低（有旧配置可用）

2. **配置格式不兼容**
   - 缓解：添加格式验证
   - 影响：中（可能导致加载失败）

3. **代码依赖旧格式**
   - 缓解：保留向后兼容性
   - 影响：低（逐步迁移）

### 回滚策略
- 保留旧配置文件（`role_selection_strategy.yaml`）
- 代码支持自动回退
- 每个阶段完成后创建 Git commit

---

## 测试清单

### 单元测试
- [ ] 配置文件加载测试
- [ ] 路径回退机制测试
- [ ] 任务验证格式解析测试

### 集成测试
- [ ] 角色选择流程测试
- [ ] 任务分配流程测试
- [ ] 混合模式任务注入测试

### 端到端测试
- [ ] 完整项目分析流程
- [ ] 验证新配置文件生效
- [ ] 验证旧配置文件兼容性

---

## 预期结果

### 成功标准
1. ✅ 所有代码成功读取新配置文件
2. ✅ 旧配置文件作为回退方案可用
3. ✅ 任务验证支持 `quality_target` 格式
4. ✅ 保留 `validation_criteria` 兼容性
5. ✅ 所有测试通过

### 性能指标
- 配置加载时间：< 100ms
- 角色选择时间：无明显变化
- 任务分配时间：无明显变化

---

## 下一步

开始实施**阶段 1：路径更新**，修改 3 个文件的配置路径。
