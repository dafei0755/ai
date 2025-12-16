# 宣传页面跳转问题诊断指南

## 🐛 问题描述

**现象**：点击"立即使用"按钮后，跳转到账户页面（`/account`）而不是应用页面

**预期行为**：在新窗口打开应用页面

---

## 🔍 诊断步骤

### 步骤1: 检查页面源代码

1. 访问：`https://www.ucppt.com/js`
2. 右键 → "查看页面源代码"
3. 搜索：`entrance-button-logged-in`
4. 查看按钮的HTML代码

**应该看到**：
```html
<a href="#"
   class="entrance-button"
   id="entrance-button-logged-in"
   data-app-url="https://ai.ucppt.com?mode=standalone"
   data-token="eyJ0eXAiOiJKV1QiLC...">
    立即使用 →
</a>
```

**检查点**：
- [ ] `data-app-url` 的值是否正确？
- [ ] `data-app-url` 是否是 `https://ai.ucppt.com` 开头？
- [ ] 还是 `http://localhost:3000`？

---

### 步骤2: 检查浏览器控制台

1. 访问：`https://www.ucppt.com/js`
2. 按 `F12` 打开开发者工具
3. 切换到 "Console" 标签
4. 点击 "立即使用" 按钮
5. 查看控制台输出

**应该看到的日志**：
```javascript
[Next.js App Entrance] 已登录用户在新窗口打开应用: https://ai.ucppt.com?mode=standalone&sso_token=...
```

**如果没有看到日志，说明JavaScript没有执行！**

---

### 步骤3: 手动测试JavaScript

在控制台执行以下命令，诊断问题：

#### 3.1 检查按钮元素是否存在
```javascript
const btn = document.getElementById('entrance-button-logged-in');
console.log('按钮元素:', btn);
console.log('app_url:', btn ? btn.dataset.appUrl : 'button not found');
console.log('token:', btn ? btn.dataset.token : 'button not found');
```

**预期输出**：
```javascript
按钮元素: <a href="#" class="entrance-button" id="entrance-button-logged-in" ...>
app_url: https://ai.ucppt.com?mode=standalone
token: eyJ0eXAiOiJKV1QiLC...
```

**如果输出 `null`，说明按钮不存在或ID不匹配！**

---

#### 3.2 检查事件监听器是否绑定
```javascript
const btn = document.getElementById('entrance-button-logged-in');
console.log('事件监听器:', getEventListeners(btn));
```

**预期输出**：
```javascript
{
  click: [
    {
      listener: function(e) { ... },
      useCapture: false,
      ...
    }
  ]
}
```

**如果 `click` 数组为空，说明事件监听器没有绑定！**

---

#### 3.3 手动触发打开应用
```javascript
const btn = document.getElementById('entrance-button-logged-in');
const appUrl = btn.dataset.appUrl;
const token = btn.dataset.token;
const separator = appUrl.includes('?') ? '&' : '?';
const targetUrl = appUrl + separator + 'sso_token=' + encodeURIComponent(token);
console.log('目标URL:', targetUrl);
window.open(targetUrl, '_blank', 'noopener,noreferrer');
```

**预期行为**：新窗口打开应用页面

**如果仍然跳转到 `/account`，说明有其他JavaScript拦截了！**

---

### 步骤4: 检查短代码配置

1. WordPress后台 → 页面 → 找到标题为 "js" 的页面
2. 点击 "编辑"
3. 查看页面内容中的短代码

**当前短代码可能是**：
```
[nextjs-app-entrance]
```

**应该改为**：
```
[nextjs-app-entrance app_url="https://ai.ucppt.com?mode=standalone"]
```

---

### 步骤5: 检查WordPress插件冲突

可能有其他插件拦截了按钮点击事件。

#### 5.1 临时禁用其他插件
```bash
WordPress后台 → 插件 → 已安装的插件
除了 "Next.js SSO Integration v3" 外，暂时停用所有插件
刷新页面测试
```

#### 5.2 检查主题JavaScript冲突
```bash
# 在浏览器控制台执行
console.log('jQuery版本:', jQuery ? jQuery.fn.jquery : 'not loaded');
console.log('所有全局变量:', Object.keys(window));
```

---

### 步骤6: 查看网络请求

1. 开发者工具 → "Network" 标签
2. 点击 "立即使用" 按钮
3. 查看是否有跳转请求

**如果看到跳转到 `/account`**：
- 检查请求的 Initiator（发起者）
- 查看是哪个JavaScript文件触发的跳转

---

## 🔧 常见问题和解决方案

### 问题1: `data-app-url` 值错误

**检查**：页面源代码中 `data-app-url` 的值

**原因**：短代码没有配置 `app_url` 参数，使用了默认值

**解决**：
```bash
# 编辑WordPress页面，修改短代码为：
[nextjs-app-entrance app_url="https://ai.ucppt.com?mode=standalone"]

# 更新页面
# 清除缓存（WP Super Cache → 删除缓存）
# Ctrl + Shift + R 强制刷新
```

---

### 问题2: JavaScript没有执行

**检查**：控制台是否有报错

**可能原因**：
- WordPress主题冲突
- 其他插件冲突
- JavaScript语法错误

**解决**：
```bash
# 1. 检查控制台错误
F12 → Console → 查看红色错误信息

# 2. 清除所有缓存
WordPress后台 → 设置 → WP Super Cache → 删除缓存
浏览器：Ctrl + Shift + Delete → 清除缓存

# 3. 禁用其他插件测试
WordPress后台 → 插件 → 停用所有插件（除了Next.js SSO v3）
测试是否正常
```

---

### 问题3: 事件监听器被覆盖

**检查**：是否有多个 `click` 事件监听器

**可能原因**：WordPress主题或其他插件也绑定了相同按钮的点击事件

**解决**：修改按钮使用 `<button>` 而不是 `<a>` 标签

---

### 问题4: 浏览器弹窗拦截

**检查**：浏览器地址栏右侧是否有弹窗拦截图标

**解决**：允许 `www.ucppt.com` 的弹窗

---

## 📝 请提供以下信息

为了准确定位问题，请执行以上诊断步骤，并提供：

1. **步骤1的截图**：页面源代码中的 `data-app-url` 值
2. **步骤2的截图**：浏览器控制台的输出（点击按钮后）
3. **步骤3.1的输出**：按钮元素和数据属性
4. **步骤4的截图**：WordPress页面编辑器中的短代码
5. **步骤6的截图**：Network标签中的跳转请求

---

## 🚨 紧急修复方案

如果上述诊断无法解决问题，可以尝试以下紧急修复：

### 方案A: 修改按钮为 `<button>` 标签

这需要修改WordPress插件代码，将 `<a>` 改为 `<button>`。

### 方案B: 使用行内JavaScript

在短代码中直接使用行内 `onclick` 事件，跳过事件监听器。

### 方案C: 创建独立的登录跳转页面

不使用短代码，而是创建一个专门的PHP页面处理跳转逻辑。

---

请先执行诊断步骤，并将结果告诉我，我会根据具体情况提供针对性的解决方案！
