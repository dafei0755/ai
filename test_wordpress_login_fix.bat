@echo off
chcp 65001 >nul
echo.
echo ============================================
echo  🐛 WordPress 登录死循环修复 - 测试指南
echo ============================================
echo.
echo [v7.129.2] 修复内容：
echo  ✅ 增强跨域环境检测（防止误清除Token）
echo  ✅ 移除页面强制刷新（防止刷新死循环）
echo  ✅ 优化日志输出（便于调试）
echo.
echo ============================================
echo  📋 测试步骤
echo ============================================
echo.
echo 🔧 前置准备：
echo  1. 前端服务运行中: http://localhost:3000
echo  2. 后端服务运行中: http://localhost:8000
echo  3. 已登录WordPress账号
echo.
echo ============================================
echo  🧪 测试场景1: 跨域登录保护
echo ============================================
echo.
echo 1️⃣  在浏览器打开: https://www.ucppt.com
echo 2️⃣  确认已登录WordPress账号
echo 3️⃣  打开新标签: http://localhost:3000
echo 4️⃣  等待2分钟（观察是否被踢出）
echo.
echo ✅ 预期结果：
echo    - 保持登录状态（不被踢出）
echo    - 浏览器控制台显示：
echo      [AuthContext v7.129.2] ⏭️ 跨域环境，跳过 WordPress 退出检测
echo.
echo ============================================
echo  🧪 测试场景2: 用户切换不刷新
echo ============================================
echo.
echo 1️⃣  以用户A身份登录
echo 2️⃣  在WordPress后台切换为用户B
echo 3️⃣  返回前端页面（不刷新）
echo 4️⃣  观察是否自动更新Token
echo.
echo ✅ 预期结果：
echo    - 自动切换到用户B（无需刷新）
echo    - 浏览器控制台显示：
echo      [AuthContext v7.129.2] ✅ 成功获取新用户Token
echo      [AuthContext v7.129.2] 🔔 已发送 auth-token-updated 事件
echo    - 页面不会刷新（无白屏闪烁）
echo.
echo ============================================
echo  🧪 测试场景3: 正常退出检测
echo ============================================
echo.
echo 1️⃣  在 https://www.ucppt.com 登录
echo 2️⃣  在同一域名下退出登录
echo 3️⃣  观察前端是否清除Token
echo.
echo ✅ 预期结果：
echo    - Token被正确清除
echo    - 显示未登录状态
echo    - 控制台显示：
echo      [AuthContext v3.0.23] ✅ 检测到WordPress已退出
echo.
echo ============================================
echo  🔍 调试检查
echo ============================================
echo.
echo 按 F12 打开浏览器开发者工具
echo.
echo 在 Console 标签查找关键日志：
echo  ✅ [AuthContext v7.129.2] ⏭️ 跨域环境...
echo  ✅ [AuthContext v7.129.2] 🔔 已发送 auth-token-updated 事件
echo.
echo 在 Network 标签查找请求：
echo  ✅ /api/auth/check-device - 应返回 200
echo  ✅ /wp-json/nextjs-sso/v1/sync-status - 正常调用
echo.
echo ============================================
echo  ⚠️ 常见问题
echo ============================================
echo.
echo Q: 仍然出现死循环？
echo A: 1. 清除浏览器缓存（Ctrl+Shift+Delete）
echo    2. 清除localStorage（Application - Local Storage - Clear）
echo    3. 重启前端服务
echo    4. 检查浏览器控制台的完整日志
echo.
echo Q: 用户切换后页面仍然刷新？
echo A: 1. 检查是否有其他组件监听了旧的刷新逻辑
echo    2. 查找代码中是否还有 window.location.reload()
echo.
echo Q: 跨域检测没有生效？
echo A: 1. 确认当前域名不是 www.ucppt.com 或 ucppt.com
echo    2. 检查控制台是否有跨域相关日志
echo.
echo ============================================
echo.
echo 准备开始测试了吗？
echo.
pause
start http://localhost:3000
echo.
echo 🚀 浏览器已打开！
echo.
echo 📝 测试完成后，请记录：
echo  [ ] 场景1: 跨域登录保护 - 通过/失败
echo  [ ] 场景2: 用户切换不刷新 - 通过/失败
echo  [ ] 场景3: 正常退出检测 - 通过/失败
echo.
echo 如有问题，请提供完整的浏览器控制台日志截图。
echo.
pause
