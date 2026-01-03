# 问卷第一步快速验证脚本
# 用于验证动机识别功能是否正常工作

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "问卷第一步快速验证" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查后端是否运行
Write-Host "[1/4] 检查后端服务..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✅ 后端服务运行正常" -ForegroundColor Green
} catch {
    Write-Host "   ❌ 后端服务未运行" -ForegroundColor Red
    Write-Host "   请先运行: python -B run_server_production.py" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# 2. 清除缓存
Write-Host "[2/4] 清除Python缓存..." -ForegroundColor Yellow
Get-ChildItem -Path "intelligent_project_analyzer" -Recurse -Include "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path "intelligent_project_analyzer" -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "   ✅ 缓存已清除" -ForegroundColor Green
Write-Host ""

# 3. 运行测试
Write-Host "[3/4] 运行动机识别测试..." -ForegroundColor Yellow
$testOutput = python test_questionnaire_step1.py 2>&1
$testResult = $LASTEXITCODE

# 检查测试结果
if ($testOutput -match "✅ 所有测试通过") {
    Write-Host "   ✅ 测试通过！" -ForegroundColor Green

    # 提取关键信息
    $culturalCount = ([regex]::Matches($testOutput, "cultural")).Count
    $commercialCount = ([regex]::Matches($testOutput, "commercial")).Count
    $inclusiveCount = ([regex]::Matches($testOutput, "inclusive")).Count

    Write-Host ""
    Write-Host "   识别结果统计：" -ForegroundColor Cyan
    Write-Host "   - cultural (文化认同): $culturalCount 次" -ForegroundColor White
    Write-Host "   - commercial (商业价值): $commercialCount 次" -ForegroundColor White
    Write-Host "   - inclusive (包容性): $inclusiveCount 次" -ForegroundColor White
} else {
    Write-Host "   ⚠️ 测试未通过" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "详细输出：" -ForegroundColor Yellow
    Write-Host $testOutput
}
Write-Host ""

# 4. 前端检查
Write-Host "[4/4] 检查前端状态..." -ForegroundColor Yellow
try {
    $frontendResponse = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✅ 前端运行正常" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️ 前端未运行" -ForegroundColor Yellow
    Write-Host "   运行命令: cd frontend-nextjs && npm run dev" -ForegroundColor Cyan
}
Write-Host ""

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "验证完成！" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

if ($testOutput -match "✅ 所有测试通过") {
    Write-Host "下一步：在浏览器中测试" -ForegroundColor Green
    Write-Host "1. 访问 http://localhost:3000" -ForegroundColor White
    Write-Host "2. 输入测试用例：'深圳蛇口渔村改造，保留渔民文化记忆'" -ForegroundColor White
    Write-Host "3. 查看任务卡片上的动机类型标签" -ForegroundColor White
    Write-Host "4. 应该显示 '文化认同需求' 标签" -ForegroundColor White
} else {
    Write-Host "请查看详细日志排查问题：" -ForegroundColor Yellow
    Write-Host "   Get-Content logs\server.log -Wait -Tail 50 -Encoding UTF8" -ForegroundColor Cyan
}
Write-Host ""
