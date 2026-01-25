@echo off
chcp 65001 >nul
echo.
echo ==========================================
echo  🧪 Progressive Questionnaire 修复测试
echo ==========================================
echo.
echo [✅] 前端服务: http://localhost:3000
echo [✅] 后端服务: http://localhost:8000
echo.
echo ==========================================
echo  📋 测试步骤
echo ==========================================
echo.
echo 1️⃣  打开浏览器访问: http://localhost:3000
echo.
echo 2️⃣  强制刷新清除缓存:
echo    - Windows/Linux: Ctrl + Shift + R
echo    - Mac: Cmd + Shift + R
echo.
echo 3️⃣  输入测试需求（复制以下内容）:
echo    ────────────────────────────────────
echo    深圳蛇口，20000平米，菜市场更新，
echo    对标苏州黄桥菜市场，希望融入蛇口
echo    渔村传统文化。给出室内改造框架。
echo    兼顾蛇口老居民街坊，香港访客，
echo    蛇口特色外籍客群，和社区居民。
echo    希望能成为深圳城市更新的标杆。
echo    ────────────────────────────────────
echo.
echo 4️⃣  点击"开始分析"
echo.
echo 5️⃣  等待Step 1任务梳理显示（约10秒）
echo    ✅ 应显示7个任务
echo    ✅ 点击"确认任务列表"
echo.
echo 6️⃣  关键测试点 - Step 2信息补全:
echo    ✅ 应在3-5秒内显示问卷（不再卡住）
echo    ✅ 应显示5个问题
echo    ✅ 标题显示"信息补全"
echo    ✅ 进度显示"第2步 / 共3步"
echo.
echo ==========================================
echo  🔍 调试检查
echo ==========================================
echo.
echo 按 F12 打开浏览器开发者工具
echo.
echo 在 Console 标签查找日志:
echo   ✅ "📋 收到第2步 - 信息补全问卷（interaction_type=step3）"
echo.
echo 在 Network 标签:
echo   ✅ WebSocket 连接状态应为 Connected (绿色)
echo.
echo ==========================================
echo  ✅ 成功标准
echo ==========================================
echo.
echo [✓] Step 2问卷在5秒内显示
echo [✓] 问卷内容完整（5个问题）
echo [✓] 可以提交或跳过
echo [✓] 浏览器控制台无错误
echo.
echo ==========================================
echo.
echo 准备开始测试了吗？
echo.
pause
start http://localhost:3000
echo.
echo 🚀 浏览器已打开，开始测试吧！
echo.
echo 测试完成后，请在下方记录结果：
echo.
echo 测试时间: %date% %time%
echo 测试结果: [ ] 成功 / [ ] 失败
echo 问题描述: ___________________________
echo.
pause
