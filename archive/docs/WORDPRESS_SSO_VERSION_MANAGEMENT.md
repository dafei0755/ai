# WordPress SSO 插件版本管理规范

**文档版本**: 1.0
**创建时间**: 2025-12-16
**适用于**: Next.js SSO Integration v3

---

## 📋 版本号管理规范

### 版本号格式

采用语义化版本号（Semantic Versioning）：**v主版本.次版本.修订版本**

```
v3.0.17
 │ │ │
 │ │ └─ 修订版本（Patch）：Bug修复、小改进
 │ └─── 次版本（Minor）：新功能、向后兼容
 └───── 主版本（Major）：重大变更、可能不兼容
```

### 版本号更新规则

#### 必须更新版本号的情况 ✅

1. **任何代码修改** - 即使只改一行
2. **Bug修复** - 修复版本 +1
3. **新功能添加** - 次版本 +1
4. **配置修改** - 修订版本 +1
5. **安全修复** - 修订版本 +1（优先发布）
6. **性能优化** - 修订版本 +1
7. **日志增强** - 修订版本 +1

#### 不需要更新版本号的情况 ❌

1. **纯文档修改** - README、注释等（但保留选项）
2. **开发环境配置** - .gitignore、IDE配置
3. **测试文件修改** - 不影响生产代码

---

## 🔄 版本更新流程

### 标准更新流程（修订版本）

以 v3.0.16 → v3.0.17 为例：

#### 步骤1: 修改源代码

编辑 `nextjs-sso-integration-v3.php`:

**位置1: 插件头部（第6行）**
```php
* Version: 3.0.17  // 从 3.0.16 改为 3.0.17
```

**位置2: 插件描述（第5行）**
```php
* Description: WordPress 单点登录集成 Next.js（v3.0.17 - 修复说明）
```

**位置3: 更新日志（第11-17行）**
```php
* 🔥 v3.0.17 关键修复 (2025-12-16):
* ✅ 修复内容描述
* ✅ 修复内容描述
* ...
```

#### 步骤2: 验证版本号一致性

检查以下位置的版本号是否全部更新：

```bash
# 搜索所有版本号引用
grep -n "3.0.16" nextjs-sso-integration-v3.php
grep -n "v3.0.16" nextjs-sso-integration-v3.php
grep -n "Version: 3.0" nextjs-sso-integration-v3.php
```

确保所有关键位置已更新为新版本号。

#### 步骤3: 创建压缩包

```bash
# Windows PowerShell
Compress-Archive -Path 'nextjs-sso-integration-v3.php' -DestinationPath 'nextjs-sso-integration-v3.0.17.zip' -Force

# Linux/Mac
zip nextjs-sso-integration-v3.0.17.zip nextjs-sso-integration-v3.php
```

#### 步骤4: 验证压缩包

```bash
# 检查文件大小和哈希值
Get-FileHash nextjs-sso-integration-v3.0.17.zip -Algorithm MD5

# 验证压缩包内容
unzip -l nextjs-sso-integration-v3.0.17.zip
```

#### 步骤5: 创建版本发布文档

创建 `WORDPRESS_SSO_V3.0.17_RELEASE.md`，包含：
- 版本号和发布日期
- 修复内容
- 部署步骤
- 验证方法

---

## 📦 当前版本信息

### v3.0.17 (最新版本)

**发布日期**: 2025-12-16
**文件名**: `nextjs-sso-integration-v3.0.17.zip`
**文件大小**: 18,199 字节 (18 KB)
**MD5哈希**: `C3084BBCE925FCC89D1BEC20083F6D05`
**状态**: ✅ 生产就绪

#### 核心修复

```php
// 关键修复：第683行
'permission_callback' => '__return_true'  // 从 'nextjs_sso_v3_check_permission' 改为 '__return_true'
```

#### 修复内容

- ✅ 修复permission_callback导致插件代码未执行的问题
- ✅ 将get-token端点的permission_callback改为__return_true
- ✅ 允许未登录用户访问端点，在回调函数内部检测登录状态
- ✅ 解决debug.log中没有v3.0.16日志的根本原因
- ✅ 修复WordPress在插件代码运行前就返回401的问题
- ✅ 增强调试日志（v3.0.17标识）

#### 包含功能（继承自v3.0.16）

- ✅ WPCOM Member Pro API集成（7层用户检测）
- ✅ 5种WPCOM Cookie模式支持
- ✅ PHP Session认证支持
- ✅ 详细调试日志输出
- ✅ 自动降级策略

---

## 📂 版本历史

### v3.0.17 (2025-12-16) - 当前版本

**类型**: 🔥 关键修复
**修复**: permission_callback配置错误
**影响**: 修复所有用户无法登录的问题
**文件哈希**: C3084BBCE925FCC89D1BEC20083F6D05

---

### v3.0.16 (2025-12-16)

**类型**: 🔥 功能增强
**新增**: WPCOM Member Pro深度兼容
**问题**: permission_callback配置错误（已在v3.0.17修复）
**状态**: ⚠️ 已废弃（请升级到v3.0.17）

---

### v3.0.15 (2025-12-16)

**类型**: 🎯 架构重构
**变更**: 极简重构，职责分离
**问题**: 未集成WPCOM Member Pro支持
**状态**: ⚠️ 已过时（建议升级到v3.0.17）

---

## 🔍 版本校验方法

### 方法1: WordPress后台检查

```
WordPress后台 → 插件 → 已安装的插件
查找: Next.js SSO Integration v3
确认版本号显示: 3.0.17
```

### 方法2: 代码文件检查

```bash
# 查看插件文件头部
head -20 /wp-content/plugins/nextjs-sso-integration-v3/nextjs-sso-integration-v3.php

# 搜索版本号
grep "Version:" /wp-content/plugins/nextjs-sso-integration-v3/nextjs-sso-integration-v3.php
```

### 方法3: REST API检查

访问WordPress REST API，检查响应头或错误日志：

```
GET https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token

查看debug.log中的版本标识:
[Next.js SSO v3.0.17] ...
```

### 方法4: 文件哈希校验

```bash
# 计算本地文件哈希
md5sum nextjs-sso-integration-v3.0.17.zip

# 对比官方哈希
Expected: C3084BBCE925FCC89D1BEC20083F6D05
```

---

## 🚀 版本发布清单

每次发布新版本时，必须完成以下所有步骤：

### 开发阶段

- [ ] 修改源代码
- [ ] 更新版本号（第6行）
- [ ] 更新插件描述（第5行）
- [ ] 添加更新日志（第11-20行）
- [ ] 更新debug.log日志标识（如果有）
- [ ] 本地测试验证

### 打包阶段

- [ ] 删除旧版本压缩包
- [ ] 创建新版本压缩包
- [ ] 计算文件MD5哈希值
- [ ] 记录文件大小
- [ ] 验证压缩包内容

### 文档阶段

- [ ] 创建版本发布说明（RELEASE.md）
- [ ] 创建部署清单（DEPLOYMENT_CHECKLIST.md）
- [ ] 更新版本变更日志（CHANGELOG.md）
- [ ] 更新README文档
- [ ] 创建快速参考卡（QUICK_REF.md）

### 测试阶段

- [ ] 在测试环境部署
- [ ] 验证REST API响应
- [ ] 检查debug.log日志
- [ ] 测试完整登录流程
- [ ] 运行Playwright自动化测试

### 发布阶段

- [ ] 在生产环境部署
- [ ] 执行验证测试
- [ ] 监控错误日志
- [ ] 更新版本管理文档
- [ ] 标记旧版本状态

---

## 📝 版本命名规范

### 文件命名

```
格式: nextjs-sso-integration-v{major}.{minor}.{patch}.zip

示例:
✅ nextjs-sso-integration-v3.0.17.zip  （正确）
❌ nextjs-sso-v3.0.17.zip              （缺少完整名称）
❌ nextjs-sso-integration-3.0.17.zip   （缺少v前缀）
❌ nextjs-sso-integration-v3-0-17.zip  （使用连字符）
```

### 文档命名

```
格式: WORDPRESS_SSO_V{major}.{minor}.{patch}_{TYPE}.md

示例:
✅ WORDPRESS_SSO_V3.0.17_RELEASE.md
✅ WORDPRESS_SSO_V3.0.17_DEPLOYMENT.md
✅ WORDPRESS_SSO_V3.0.17_QUICK_REF.md
```

---

## 🔄 版本升级路径

### 从 v3.0.16 → v3.0.17

**必须升级**: ✅ 强烈推荐（修复关键Bug）

**升级原因**:
- v3.0.16存在permission_callback配置错误
- 导致所有用户无法登录
- v3.0.17完全修复此问题

**升级步骤**:
1. 停用并删除v3.0.16
2. 上传并启用v3.0.17
3. 验证REST API返回200
4. 测试完整登录流程

**数据兼容性**: ✅ 完全兼容（无需数据迁移）

---

### 从 v3.0.15 → v3.0.17

**必须升级**: ✅ 推荐（增强WPCOM支持）

**升级收益**:
- 完整的WPCOM Member Pro支持
- 7层用户检测机制
- 修复permission_callback问题
- 详细调试日志

**升级步骤**: 与v3.0.16→v3.0.17相同

**数据兼容性**: ✅ 完全兼容

---

### 从 v3.0.14及更早版本 → v3.0.17

**必须升级**: ✅ 强烈推荐（架构变更）

**注意事项**:
- v3.0.15进行了架构重构
- 宣传页面行为改变
- 应用内部认证流程变更

**升级步骤**:
1. 阅读v3.0.15、v3.0.16、v3.0.17的完整变更日志
2. 备份现有配置
3. 部署v3.0.17
4. 完整测试所有功能

---

## 💾 版本备份策略

### 备份内容

每次发布新版本时，保留以下文件：

```
版本备份目录结构:
/backups/
  /v3.0.17/
    nextjs-sso-integration-v3.php         （源文件）
    nextjs-sso-integration-v3.0.17.zip    （压缩包）
    WORDPRESS_SSO_V3.0.17_RELEASE.md      （发布说明）
    WORDPRESS_SSO_V3.0.17_DEPLOYMENT.md   （部署指南）
    file_hash.txt                          （文件哈希）
    changelog.txt                          （变更记录）
```

### 保留策略

- **当前版本**: 永久保留
- **前1个版本**: 保留3个月（v3.0.16 → 2026-03-16前）
- **前2-3个版本**: 保留1个月
- **更早版本**: 仅保留发布说明和变更日志

---

## 📊 版本统计信息

### 文件大小变化

```
v3.0.15: 未知
v3.0.16: 17,951 字节
v3.0.17: 18,199 字节 (+248字节，+1.4%)
```

**大小增加原因**: 增强调试日志代码

---

## 🎯 下次更新指南

### 如果需要发布 v3.0.18

#### 情况1: Bug修复（修订版本+1）

```
1. 修改代码
2. 更新版本号: 3.0.17 → 3.0.18
3. 添加更新日志
4. 重新打包
5. 部署测试
```

#### 情况2: 新功能（次版本+1）

```
1. 开发新功能
2. 更新版本号: 3.0.17 → 3.1.0
3. 完整的功能说明
4. 全面测试
5. 用户文档更新
```

#### 情况3: 重大变更（主版本+1）

```
1. 完成重大变更
2. 更新版本号: 3.0.17 → 4.0.0
3. 迁移指南
4. 兼容性说明
5. 完整回归测试
```

---

## ✅ 总结

### 版本管理要点

1. **每次代码修改都更新版本号** - 确保可追溯
2. **遵循语义化版本号规范** - 便于用户理解
3. **完整的文档和测试** - 保证质量
4. **保留版本备份** - 方便回滚
5. **清晰的升级路径** - 用户友好

### v3.0.17 快速参考

```
✅ 文件名: nextjs-sso-integration-v3.0.17.zip
✅ 大小: 18,199 字节
✅ MD5: C3084BBCE925FCC89D1BEC20083F6D05
✅ 状态: 生产就绪
✅ 修复: permission_callback配置错误
✅ 兼容: 完全向后兼容v3.0.16
```

---

**文档版本**: 1.0
**创建时间**: 2025-12-16
**维护人**: Claude Sonnet 4.5
**状态**: ✅ 最新
