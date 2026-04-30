# 动态角色名称功能 - 修改清单

## 📋 问题
任务分配和后续输出只显示基础名称（如"设计总监"），丢失了能体现具体职责的动态名称（如"居住空间设计总监"）。

## ✅ 解决方案
引入 `RoleObject` 模型和 `dynamic_role_name` 字段，打通 LLM → 模型 → 状态 → 显示 的完整数据流。

---

## 📝 修改文件清单

### 1. `intelligent_project_analyzer/agents/dynamic_project_director.py`
**修改内容**:
- ✅ 新增 `RoleObject` 模型（包含 `dynamic_role_name` 字段）
- ✅ 修改 `RoleSelection.selected_roles` 从 `List[str]` 改为 `List[RoleObject]`
- ✅ 添加 `task_distribution` 作为 `@property` 保证向后兼容
- ✅ 更新验证器适配新模型

### 2. `intelligent_project_analyzer/agents/project_director.py`
**修改内容**:
- ✅ 序列化 `RoleObject` 列表保存到状态
- ✅ 区分 `strategic_analysis.selected_roles`（完整信息）和 `active_agents`（仅ID）

### 3. `intelligent_project_analyzer/interaction/role_selection_review.py`
**修改内容**:
- ✅ `_format_roles_for_display` 方法支持读取 `RoleObject` 格式
- ✅ 优先使用 `dynamic_role_name` 显示
- ✅ 添加 `_construct_full_role_id` 辅助方法
- ✅ 保证向后兼容旧格式（`List[str]`）

### 4. `intelligent_project_analyzer/interaction/task_assignment_review.py`
**修改内容**:
- ✅ `_generate_detailed_task_list` 方法支持读取 `RoleObject` 格式
- ✅ 优先使用 `dynamic_role_name` 显示
- ✅ 添加 `_construct_full_role_id` 辅助方法
- ✅ 保证向后兼容旧格式

---

## 🔍 关键代码片段

### 1. RoleObject 模型（新增）
```python
class RoleObject(BaseModel):
    role_id: str
    role_name: str
    dynamic_role_name: str  # ✅ 核心字段
    tasks: List[str]
    focus_areas: List[str]
    expected_output: str
    dependencies: List[str]
```

### 2. RoleSelection 模型（修改）
```python
class RoleSelection(BaseModel):
    selected_roles: List[RoleObject]  # ✅ 改为对象列表
    reasoning: str
    
    @property
    def task_distribution(self) -> Dict[str, TaskDetail]:
        """向后兼容"""
        return {
            self._construct_full_role_id(role.role_id): TaskDetail(...)
            for role in self.selected_roles
        }
```

### 3. 状态保存（修改）
```python
# ✅ 序列化 RoleObject 列表
serialized_roles = [
    role.model_dump() if hasattr(role, 'model_dump') else role
    for role in selection.selected_roles
]

state_update = {
    "strategic_analysis": {
        "selected_roles": serialized_roles,  # ✅ 完整信息
        ...
    },
    "active_agents": [role.role_id for role in selection.selected_roles],  # ✅ 仅ID
}
```

### 4. 显示层读取（修改）
```python
def _format_roles_for_display(self, selected_roles, task_distribution):
    for role in selected_roles:
        if isinstance(role, dict) or hasattr(role, 'role_id'):
            # ✅ 新格式：读取 dynamic_role_name
            dynamic_name = role.get('dynamic_role_name', '') if isinstance(role, dict) else role.dynamic_role_name
            formatted_roles.append({
                "role_name": dynamic_name,  # ✅ 使用动态名称
                ...
            })
        else:
            # 旧格式：回退到硬编码映射
            formatted_roles.append({
                "role_name": self._get_role_display_name(role),
                ...
            })
```

---

## 🧪 测试验证

运行 `test_dynamic_role_name.py`:
```bash
python test_dynamic_role_name.py
```

**测试结果**: ✅ 所有测试通过

---

## 📊 数据流

```
LLM 输出
  ↓ (包含 dynamic_role_name)
Pydantic 解析 (RoleObject)
  ↓ (保留 dynamic_role_name)
状态保存 (serialized_roles)
  ↓ (序列化为字典列表)
显示层读取 (role["dynamic_role_name"])
  ↓
前端显示 ✅
```

---

## 🎯 效果对比

**旧版本**: V2_设计总监_2-1 → "设计总监" ❌  
**新版本**: V2_设计总监_2-1 → "三代同堂居住空间与生活模式总设计师" ✅

---

## ✅ 验证清单

- [x] RoleObject 模型定义正确
- [x] RoleSelection 模型支持 List[RoleObject]
- [x] 状态保存包含 dynamic_role_name
- [x] 显示层读取 dynamic_role_name
- [x] 向后兼容旧格式
- [x] 无语法错误
- [x] 测试全部通过

---

完成日期: 2024-01-19  
状态: ✅ 已完成并测试
