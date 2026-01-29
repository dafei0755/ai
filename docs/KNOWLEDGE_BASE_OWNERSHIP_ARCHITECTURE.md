# 知识库所有权和角色架构说明

## 版本: v7.141.4+
## 日期: 2026-01-06

---

## 一、知识库类型

### 1. 公共知识库（System Knowledge Base）

**定义**:
- `owner_type = "system"`
- `owner_id = "public"`
- `visibility = "public"` (固定)

**特性**:
- ✅ 所有用户可见、可搜索
- ✅ 仅管理员可创建/编辑/删除
- ✅ 不受配额限制
- ✅ 永不过期（`expires_at = 0`）
- ✅ 不计入任何用户的配额

**用途**:
- 官方设计规范
- 通用技术知识
- 公共案例库
- 系统文档

**管理界面**:
- 在 `/admin/knowledge-base` 中管理
- 选择"公共知识库"类型

---

### 2. 用户知识库（User Knowledge Base）

**定义**:
- `owner_type = "user"`
- `owner_id = {user_id}` (实际用户ID)
- `visibility = "public" | "private"`

**特性**:
- ✅ 可以是任何用户创建（包括管理员作为用户）
- ✅ 受用户配额限制
- ✅ 按会员等级过期
- ✅ 计入用户配额

**子类型**:

#### 2.1 私有知识库
- `visibility = "private"`
- 仅所有者可见

#### 2.2 共享知识库
- `visibility = "public"`
- 所有用户可见（但仍属于某个用户）

**用途**:
- 个人收藏的资料
- 私有项目文档
- 分享给他人的内容

**管理界面**:
- 在 `/user/dashboard` → 知识库管理
- 或 `/admin/knowledge-base` 中管理（选择"私有知识库"）

---

### 3. 团队知识库（Team Knowledge Base）

**定义**:
- `owner_type = "team"`
- `owner_id = {team_id}`
- `team_id = {team_id}` (冗余字段，便于查询)

**特性**:
- ✅ 仅团队成员可见
- ✅ 团队级别配额
- ✅ 按团队会员等级过期

**用途**:
- 团队共享资料
- 部门知识库
- 项目文档

---

## 二、用户角色

### 1. 普通用户（Regular User）

**身份**:
- `role = "user"`
- 有会员等级（free, basic, professional, enterprise）

**权限**:
- ✅ 访问 `/user/*` 页面
- ✅ 创建私有/共享知识库
- ✅ 搜索公共知识库 + 共享知识库 + 自己的私有库
- ❌ 无法创建公共知识库
- ❌ 无法访问 `/admin/*` 页面

**配额**:
- 受会员等级限制
- 可升级会员提升配额

---

### 2. 管理员（Administrator）

**双重身份**:

#### 2.1 作为管理员
- `role = "admin"`
- 访问 `/admin/*` 页面

**权限**:
- ✅ 创建/编辑/删除公共知识库
- ✅ 查看所有用户的知识库
- ✅ 系统配置和管理
- ✅ 用户管理
- ✅ 配额管理

**特殊说明**:
- 管理公共知识库时，不计入个人配额
- 可以代表"系统"创建内容

#### 2.2 作为用户
- `role = "admin"` 但以用户身份操作
- 访问 `/user/*` 页面

**权限**:
- ✅ 与普通用户相同
- ✅ 创建个人私有/共享知识库
- ✅ 受配额限制（除非豁免）

**配额**:
- **默认**: 受会员等级限制
- **可选豁免**: 在 `config/knowledge_base_quota.yaml` 中添加到 `exempt_users` 列表

---

## 三、知识库搜索范围

### 搜索范围对比表

| 用户类型 | search_scope="all" | search_scope="system" | search_scope="user" | search_scope="team" |
|---------|-------------------|----------------------|---------------------|---------------------|
| **普通用户** | 公共 + 共享 + 自己的私有 + 团队 | 仅公共 | 仅自己的私有+共享 | 仅所属团队 |
| **管理员（管理员身份）** | 所有知识库 | 仅公共 | 所有用户的私有 | 所有团队 |
| **管理员（用户身份）** | 公共 + 共享 + 自己的私有 + 团队 | 仅公共 | 仅自己的私有+共享 | 仅所属团队 |

---

## 四、典型使用场景

### 场景 1: 管理员创建官方规范

**操作**:
1. 管理员登录 `/admin/knowledge-base`
2. 选择"数据导入" → 知识库类型: "公共知识库"
3. 上传文档（如: 《国家建筑设计规范》）

**结果**:
- `owner_type = "system"`
- `owner_id = "public"`
- 所有用户可搜索到这个文档
- 不计入管理员的个人配额

---

### 场景 2: 管理员创建个人收藏

**操作**:
1. 管理员登录 `/user/dashboard` 或 `/admin/knowledge-base`
2. 选择"数据导入" → 知识库类型: "私有知识库"
3. 设置可见性: "私有"
4. 上传文档（如: 个人笔记）

**结果**:
- `owner_type = "user"`
- `owner_id = "admin_user_123"`
- `visibility = "private"`
- 仅管理员自己可见
- **计入管理员的个人配额**（除非豁免）

---

### 场景 3: 普通用户分享文档

**操作**:
1. 用户登录 `/user/dashboard`
2. 选择"数据导入" → 知识库类型: "私有知识库"
3. 设置可见性: "公开"
4. 上传文档

**结果**:
- `owner_type = "user"`
- `owner_id = "user_456"`
- `visibility = "public"`
- 所有用户可搜索到
- 计入用户配额

---

## 五、管理员豁免机制

### 配置位置

**文件**: `config/knowledge_base_quota.yaml`

```yaml
# 特殊用户豁免列表 (用户ID列表)
exempt_users:
  - "admin"
  - "system"
  - "admin_user_123"  # 具体管理员的用户ID
```

### 豁免效果

**如果管理员在豁免列表中**:
- ✅ 个人知识库不受配额限制
- ✅ 文档永不过期
- ✅ 可上传任意大小文件
- ⚠️ 仍需选择会员等级（用于功能权限，如团队库）

**如果管理员不在豁免列表中**:
- ❌ 与普通用户相同，受配额限制
- ❌ 需要升级会员提升配额

---

## 六、UI 改进建议

### 6.1 管理员后台 - 知识库类型选择

**当前**:
```
<select value={ownerType}>
  <option value="system">📚 公共知识库（所有用户可见）</option>
  <option value="user">🔒 私有知识库（仅自己可见）</option>
  <option value="team">👥 团队知识库（团队成员可见）</option>
</select>
```

**改进**:
```tsx
<select value={ownerType}>
  <option value="system">
    📚 公共知识库（系统级，所有用户可见，不计入个人配额）
  </option>
  <option value="user">
    🔒 私有知识库（个人的，可选择公开/私有，计入个人配额）
  </option>
  <option value="team">
    👥 团队知识库（团队成员可见，计入团队配额）
  </option>
</select>

{/* 提示文本 */}
{ownerType === 'system' && (
  <p className="text-xs text-blue-600 mt-1">
    💡 提示: 公共知识库由系统管理，不受配额限制，永不过期
  </p>
)}
{ownerType === 'user' && (
  <p className="text-xs text-gray-600 mt-1">
    💡 提示: 这是您个人的知识库，受配额限制，可选择是否公开分享
  </p>
)}
```

### 6.2 用户中心 - 角色切换

**在用户中心顶部添加**:
```tsx
{userIsAdmin && (
  <button
    onClick={() => router.push('/admin/dashboard')}
    className="px-4 py-2 bg-purple-600 text-white rounded"
  >
    🔧 切换到管理员视图
  </button>
)}
```

**在管理员后台顶部添加**:
```tsx
<button
  onClick={() => router.push('/user/dashboard')}
  className="px-4 py-2 bg-blue-600 text-white rounded"
>
  👤 切换到用户视图
</button>
```

---

## 七、数据库查询示例

### 7.1 查询公共知识库

```python
# 所有用户都能看到
expr = 'owner_type == "system"'
```

### 7.2 查询用户的所有知识库（包括私有和共享）

```python
# 用户 user_123 的所有知识库
expr = 'owner_type == "user" AND owner_id == "user_123"'
```

### 7.3 查询用户可见的所有知识库

```python
# 公共 + 共享 + 自己的私有
expr = '''
  owner_type == "system"
  OR (owner_type == "user" AND visibility == "public")
  OR (owner_type == "user" AND owner_id == "user_123")
'''
```

### 7.4 管理员查看所有知识库

```python
# 不需要过滤条件，查询所有
# 或者在代码层面跳过权限检查
```

---

## 八、常见问题 (FAQ)

### Q1: 管理员创建的知识库默认是什么类型？
**A**: 取决于管理员在哪里操作：
- 在 `/admin/knowledge-base` 手动选择类型
- 建议默认选择"公共知识库"（系统级）

### Q2: 管理员的个人知识库会计入配额吗？
**A**:
- 如果管理员在豁免列表中 → 不计入
- 如果不在豁免列表中 → 计入（与普通用户相同）

### Q3: 公共知识库可以删除吗？
**A**:
- 仅管理员可删除
- 建议添加二次确认

### Q4: 管理员可以编辑其他用户的私有知识库吗？
**A**:
- 技术上可以（管理员有全部权限）
- 建议在 UI 中显示警告："您正在编辑用户 XXX 的私有文档"

### Q5: 团队知识库由谁管理？
**A**:
- 团队管理员（team_admin）
- 或者系统管理员

---

## 九、总结

**核心原则**:
1. **公共知识库** = 系统级，不属于任何用户
2. **用户知识库** = 个人的，可以是任何用户（包括管理员）
3. **管理员** = 双重角色，既是管理员也是用户
4. **配额** = 仅针对用户知识库，公共知识库不受限

**最佳实践**:
- 管理员创建官方内容 → 使用"公共知识库"
- 管理员创建个人笔记 → 使用"私有知识库"
- 普通用户分享内容 → 使用"私有知识库" + `visibility="public"`

---

**创建日期**: 2026-01-06
**最后更新**: 2026-01-06
