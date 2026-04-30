# 专家动态名称丢失问题修复

**修复日期**: 2025-12-10
**问题**: 专家的 `dynamic_role_name` 字段丢失或为空
**优先级**: P1 (重要)

---

## 问题描述

### 现象
- 前端显示专家名称时，显示的是通用的 `role_name`（如"商业零售设计总监"）
- 而不是项目定制化的 `dynamic_role_name`（如"30㎡精品咖啡空间总设计总监"）

### 根因分析
1. **LLM提示词不够明确**: 原提示词中只有1个 `dynamic_role_name` 示例，LLM容易忽略
2. **缺少生成规则**: 没有明确说明如何生成 `dynamic_role_name`
3. **缺少错误示例**: 没有告诉LLM哪些是错误的做法

---

## 修复方案

### 文件修改
**文件**: `intelligent_project_analyzer/config/prompts/dynamic_project_director_v2.yaml`

### 修复内容

#### 1. 添加 `dynamic_role_name` 生成规则（第133-154行）

```yaml
**🎭 dynamic_role_name 生成规则（重要！）**

每个角色必须生成一个**项目定制化的动态名称**，格式为：`{项目核心特征} + {角色专业领域} + {职责动词}`

**✅ 正确示例**：
- role_name: "个体叙事与心理洞察专家" → dynamic_role_name: "三代同堂家庭人物原型构建师"
- role_name: "居住空间设计总监" → dynamic_role_name: "30㎡精品咖啡空间总设计总监"
- role_name: "案例与对标策略师" → dynamic_role_name: "小型高效商业空间全球案例分析首席研究员"
- role_name: "商业零售运营专家" → dynamic_role_name: "高效坪效与顾客动线运营策略专家"
- role_name: "品牌叙事与顾客体验专家" → dynamic_role_name: "精品咖啡空间品牌故事与短留体验首席塑造师"
- role_name: "成本与价值工程师" → dynamic_role_name: "30㎡极致成本控制与价值工程首席分析师"

**❌ 错误示例**：
- ❌ dynamic_role_name: "个体叙事与心理洞察专家"（直接复制role_name）
- ❌ dynamic_role_name: "设计总监"（过于简单）
- ❌ dynamic_role_name: ""（空字符串）

**生成步骤**：
1. 提取项目核心特征（如"三代同堂"、"30㎡精品咖啡"、"四合院改造"）
2. 结合角色专业领域（如"人物原型"、"空间设计"、"成本控制"）
3. 添加职责动词（如"构建师"、"总设计师"、"首席分析师"）
4. 确保名称长度在10-25个汉字之间
```

#### 2. 在"避免的问题"中添加第7条（第164行）

```yaml
7. **dynamic_role_name缺失**: ❌ 每个角色必须有独特的dynamic_role_name，不能为空或直接复制role_name
```

#### 3. 更新输出格式示例（第178-279行）

将原来只有1个角色的示例，扩展为3个角色的完整示例，每个角色都有清晰的 `dynamic_role_name`：

```json
{
  "selected_roles": [
    {
      "role_id": "2-2",
      "role_name": "商业零售设计总监",
      "dynamic_role_name": "30㎡精品咖啡空间总设计总监",
      ...
    },
    {
      "role_id": "4-1",
      "role_name": "案例与对标策略师",
      "dynamic_role_name": "小型高效商业空间全球案例分析首席研究员",
      ...
    },
    {
      "role_id": "3-2",
      "role_name": "品牌叙事与顾客体验专家",
      "dynamic_role_name": "精品咖啡空间品牌故事与短留体验首席塑造师",
      ...
    }
  ],
  "reasoning": "..."
}
```

---

## 代码验证

### 已验证的代码路径

#### 1. LLM响应解析（✅ 无需修改）
**文件**: `intelligent_project_analyzer/agents/dynamic_project_director.py`

- **第815行**: `_convert_legacy_format_to_v2` 方法正确保留 `dynamic_role_name`
  ```python
  converted_role = {
      "role_id": role_data.get("role_id", ""),
      "role_name": role_data.get("role_name", ""),
      "dynamic_role_name": role_data.get("dynamic_role_name", ""),  # ✅ 正确保留
      "task_instruction": task_instruction,
      ...
  }
  ```

#### 2. 工作流传递（✅ 无需修改）
**文件**: `intelligent_project_analyzer/workflow/main_workflow.py`

- **第1108行**: 构建默认 role_object 时包含 `dynamic_role_name`
  ```python
  role_object = {
      "role_id": role_id,
      "role_name": role_config.get("name", role_id),
      "dynamic_role_name": role_config.get("name", role_id),  # ✅ 有默认值
      ...
  }
  ```

- **第1216行**: 从 role_object 提取 `dynamic_role_name`
  ```python
  dynamic_role_name = role_object.get("dynamic_role_name", role_name)  # ✅ 有降级
  ```

- **第1241-1246行**: WebSocket推送时包含 `dynamic_role_name`
  ```python
  asyncio.create_task(broadcast_to_websockets(session_id, {
      "type": "agent_result",
      "role_id": role_id,
      "role_name": role_name,
      "dynamic_role_name": dynamic_role_name,  # ✅ 正确推送
      ...
  }))
  ```

---

## 测试验证

### 测试步骤

1. **清除旧会话缓存**:
   ```bash
   redis-cli FLUSHDB
   ```

2. **重启后端服务**:
   ```bash
   python -m uvicorn intelligent_project_analyzer.api.server:app --reload
   ```

3. **提交测试用例**:
   ```bash
   # 使用"上海静安区一家30平米的精品咖啡店"测试用例
   ```

4. **检查日志**:
   ```bash
   # 搜索日志中的 dynamic_role_name
   grep "dynamic_role_name" logs/api.log
   ```

### 预期结果

#### 日志应显示：
```
📤 [Progressive] 已推送专家结果: V2_设计总监_2-2 (30㎡精品咖啡空间总设计总监)
📤 [Progressive] 已推送专家结果: V4_设计研究员_4-1 (小型高效商业空间全球案例分析首席研究员)
📤 [Progressive] 已推送专家结果: V5_场景与行业专家_5-2 (高效坪效与顾客动线运营策略专家)
📤 [Progressive] 已推送专家结果: V3_叙事与体验专家_3-2 (精品咖啡空间品牌故事与短留体验首席塑造师)
📤 [Progressive] 已推送专家结果: V6_专业总工程师_6-4 (30㎡极致成本控制与价值工程首席分析师)
📤 [Progressive] 已推送专家结果: V6_专业总工程师_6-3 (精品咖啡空间室内工艺细节与材料实现专家)
```

#### 前端应显示：
- 专家卡片标题：**30㎡精品咖啡空间总设计总监**（而不是"商业零售设计总监"）
- 专家报告标题：**小型高效商业空间全球案例分析首席研究员**（而不是"案例与对标策略师"）

---

## 降级保护

### 如果LLM仍未生成 dynamic_role_name

代码中已有多层降级保护：

1. **第1216行**: 如果 `dynamic_role_name` 为空，使用 `role_name`
   ```python
   dynamic_role_name = role_object.get("dynamic_role_name", role_name)
   ```

2. **第1108行**: 构建默认 role_object 时，`dynamic_role_name` 默认等于 `role_name`
   ```python
   "dynamic_role_name": role_config.get("name", role_id)
   ```

3. **第815行**: 格式转换时保留原值
   ```python
   "dynamic_role_name": role_data.get("dynamic_role_name", "")
   ```

### 最坏情况
即使LLM完全不生成 `dynamic_role_name`，系统也会降级使用 `role_name`，不会导致前端显示空白。

---

## 长期优化建议

### 1. 添加 dynamic_role_name 验证
在 `RoleObject` 的 Pydantic 模型中添加验证器：

```python
from pydantic import field_validator

class RoleObject(BaseModel):
    role_id: str
    role_name: str
    dynamic_role_name: str

    @field_validator('dynamic_role_name')
    def validate_dynamic_name(cls, v, values):
        # 检查是否为空
        if not v or v.strip() == "":
            raise ValueError("dynamic_role_name 不能为空")

        # 检查是否直接复制 role_name
        if 'role_name' in values and v == values['role_name']:
            raise ValueError(f"dynamic_role_name 不能与 role_name 相同: {v}")

        # 检查长度
        if len(v) < 10 or len(v) > 30:
            raise ValueError(f"dynamic_role_name 长度应在10-30字之间，当前: {len(v)}")

        return v
```

### 2. 添加监控指标
在日志中记录 `dynamic_role_name` 的质量：

```python
# 在 select_roles_for_task 方法中
for role in response.selected_roles:
    if role.dynamic_role_name == role.role_name:
        logger.warning(f"⚠️ 角色 {role.role_id} 的 dynamic_role_name 与 role_name 相同")
    elif len(role.dynamic_role_name) < 10:
        logger.warning(f"⚠️ 角色 {role.role_id} 的 dynamic_role_name 过短: {role.dynamic_role_name}")
```

### 3. 前端显示优化
在前端添加 tooltip，同时显示 `role_name` 和 `dynamic_role_name`：

```tsx
<Tooltip content={`基础角色: ${role.role_name}`}>
  <h3>{role.dynamic_role_name}</h3>
</Tooltip>
```

---

## 修复总结

| 修改项 | 文件 | 行数 | 状态 |
|--------|------|------|------|
| 添加 dynamic_role_name 生成规则 | dynamic_project_director_v2.yaml | 133-154 | ✅ 已完成 |
| 添加错误示例说明 | dynamic_project_director_v2.yaml | 145-148 | ✅ 已完成 |
| 更新输出格式示例（3个角色） | dynamic_project_director_v2.yaml | 178-279 | ✅ 已完成 |
| 添加"避免的问题"第7条 | dynamic_project_director_v2.yaml | 164 | ✅ 已完成 |

**总计**: 4处修改，全部完成

---

**修复负责人**: Claude Code
**测试状态**: 待验证
**预计生效**: 下次LLM调用时立即生效
