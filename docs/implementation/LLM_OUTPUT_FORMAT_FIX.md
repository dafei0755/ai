# 动态角色名称功能 - LLM输出格式修复

## 问题诊断

根据错误日志，LLM仍然输出旧格式：
```json
{
  "selected_roles": ["V2_设计总监_2-1", "V3_叙事与体验专家_3-1", ...],  // ❌ 字符串数组
  "reasoning": "...",
  "task_distribution": {...}
}
```

导致 Pydantic 验证失败：
```
Input should be a valid dictionary or instance of RoleObject
```

## 根本原因

1. ✅ **数据模型已更新**：`RoleSelection.selected_roles` 改为 `List[RoleObject]`
2. ❌ **提示词未更新**：LLM 不知道需要输出新格式（对象数组而非字符串数组）
3. ❌ **缺少输出示例**：没有明确告诉 LLM 输出结构

## 解决方案

### 修改文件：`dynamic_project_director.py`

#### 1. 更新 `_build_user_prompt` 方法

**修改前**：
```python
🚨🚨🚨 最后提醒（非常重要）：
你的响应必须包含以下三个字段，缺一不可：
1. selected_roles - 角色ID列表
2. reasoning - 选择理由（至少50个字符）
3. task_distribution - 任务分配字典（必须包含所有选中的角色，不能为空！）
```

**修改后**：
```python
⚠️ 重要格式要求：
你必须按照以下JSON格式返回结果：

{
  "selected_roles": [
    {
      "role_id": "2-1",
      "role_name": "居住空间设计总监",
      "dynamic_role_name": "针对本项目的具体称呼（如：三代同堂居住空间与生活模式总设计师）",
      "tasks": ["任务1描述（至少30字）", "任务2描述"],
      "focus_areas": ["关注点1", "关注点2"],
      "expected_output": "预期交付物描述",
      "dependencies": ["依赖的其他角色ID"]
    },
    ...
  ],
  "reasoning": "选择理由（至少50个字符）"
}

🚨🚨🚨 关键注意事项：
1. selected_roles 必须是对象数组，不能是字符串数组！
2. 每个角色对象必须包含 role_id, role_name, dynamic_role_name, tasks 等所有字段
3. dynamic_role_name 是必填项，要根据本项目需求创造一个精准反映该角色职责的名称
4. 不要输出 task_distribution 字段（系统会自动生成）
```

#### 2. 更新 `_build_user_prompt_with_weights` 方法

同样添加明确的 JSON 格式示例和关键注意事项。

## 关键改进

### 1. 明确输出格式
- ✅ 提供完整的 JSON 结构示例
- ✅ 强调 `selected_roles` 必须是**对象数组**
- ✅ 列出每个角色对象必须包含的所有字段

### 2. 突出 `dynamic_role_name`
- ✅ 标记为必填项
- ✅ 提供具体示例（"三代同堂居住空间与生活模式总设计师"）
- ✅ 说明其用途（根据项目需求创造精准称呼）

### 3. 简化输出要求
- ✅ 明确告知不要输出 `task_distribution`（系统自动生成）
- ✅ 减少 LLM 的认知负担

## 预期效果

修改后，LLM应该输出新格式：
```json
{
  "selected_roles": [
    {
      "role_id": "2-1",
      "role_name": "居住空间设计总监",
      "dynamic_role_name": "三代同堂居住空间与生活模式总设计师",
      "tasks": ["分析家庭代际关系，设计共享与私密空间平衡方案", ...],
      "focus_areas": ["居住空间", "生活方式"],
      "expected_output": "空间设计方案",
      "dependencies": ["4-1"]
    },
    ...
  ],
  "reasoning": "..."
}
```

## 验证步骤

1. **重新运行工作流**
   ```bash
   python intelligent_project_analyzer/frontend/run_frontend.py
   ```

2. **检查日志**
   - 查看 LLM 返回的 JSON 格式
   - 确认 `selected_roles` 是对象数组
   - 验证 Pydantic 验证通过

3. **测试显示**
   - 角色选择审核界面应显示动态名称
   - 任务分配界面应显示动态名称

## 后续优化（可选）

如果 LLM 仍然输出错误格式：

### 方案A：添加后处理逻辑
在 Pydantic 验证失败时，尝试自动转换旧格式到新格式：

```python
except ValidationError as e:
    # 检查是否是旧格式（字符串数组）
    if isinstance(raw_response.get("selected_roles", []), list):
        first_role = raw_response["selected_roles"][0]
        if isinstance(first_role, str):
            # 旧格式，尝试转换
            logger.warning("⚠️ 检测到旧格式输出，尝试自动转换...")
            converted = _convert_old_to_new_format(raw_response)
            response = RoleSelection.model_validate(converted)
```

### 方案B：使用系统提示词
在 `config/prompts/dynamic_project_director.yaml` 中添加输出格式说明。

### 方案C：Few-shot 示例
在系统提示词中提供1-2个完整的输入输出示例。

---

**修改日期**: 2024-01-19  
**状态**: ✅ 已完成提示词修改，等待测试验证
