# WPCOM登录API自动诊断脚本
# 功能：自动测试WordPress REST API端点和WPCOM登录接口

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  WPCOM登录API自动诊断工具 v1.0" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "https://www.ucppt.com"
$results = @()

# 步骤1: 获取REST API索引
Write-Host "[步骤1] 检测WordPress REST API端点..." -ForegroundColor Yellow
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/wp-json/" -Method Get -ErrorAction Stop
    Write-Host "✓ 成功获取REST API索引" -ForegroundColor Green

    $routes = $response.routes.PSObject.Properties.Name
    Write-Host "  发现 $($routes.Count) 个REST API端点" -ForegroundColor White

    # 查找WPCOM相关端点
    $wpcomEndpoints = $routes | Where-Object {
        $_ -match "wpcom|member|login|auth|sign"
    }

    Write-Host "  找到 $($wpcomEndpoints.Count) 个WPCOM相关端点：" -ForegroundColor Cyan
    foreach ($endpoint in $wpcomEndpoints) {
        Write-Host "    - $endpoint" -ForegroundColor Gray
    }
    Write-Host ""

    $results += "REST API端点总数: $($routes.Count)"
    $results += "WPCOM相关端点: $($wpcomEndpoints.Count)"

    # 检查问题端点
    $problemEndpoint = "/wp-json/mwp-sign-sign.php"
    if ($routes -contains $problemEndpoint) {
        Write-Host "  ❌ 发现问题端点: $problemEndpoint" -ForegroundColor Red
        $results += "问题端点存在: 是"
    } else {
        Write-Host "  ⚠️  问题端点 $problemEndpoint 不在REST API索引中" -ForegroundColor Yellow
        Write-Host "  这可能是导致400错误的原因！" -ForegroundColor Red
        $results += "问题端点存在: 否（这是问题根源！）"
    }
    Write-Host ""

} catch {
    Write-Host "✗ 获取REST API索引失败: $($_.Exception.Message)" -ForegroundColor Red
    $results += "REST API检测: 失败"
}

# 步骤2: 测试可能的登录端点
Write-Host "[步骤2] 测试WPCOM登录API端点..." -ForegroundColor Yellow
Write-Host ""

$testEndpoints = @(
    "/wp-json/mwp-sign-sign.php",
    "/wp-json/wpcom-member/v1/login",
    "/wp-json/member-pro/v1/login",
    "/wp-json/wpcom/v1/auth",
    "/wp-json/wpcom/v1/sign-in"
)

foreach ($endpoint in $testEndpoints) {
    Write-Host "  测试: $endpoint" -ForegroundColor Cyan

    try {
        # 发送测试POST请求
        $body = @{
            username = "test"
            password = "test"
        } | ConvertTo-Json

        $response = Invoke-WebRequest -Uri "$baseUrl$endpoint" `
            -Method Post `
            -Body $body `
            -ContentType "application/json" `
            -ErrorAction Stop

        Write-Host "    ✓ POST $($response.StatusCode) $($response.StatusDescription)" -ForegroundColor Green

    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        $statusDesc = $_.Exception.Response.StatusDescription

        if ($statusCode -eq 400 -and $endpoint -eq "/wp-json/mwp-sign-sign.php") {
            Write-Host "    ❌ POST $statusCode $statusDesc - 确认：这就是导致登录失败的端点！" -ForegroundColor Red
            $results += "问题端点状态: 400 Bad Request（已确认）"
        } elseif ($statusCode -eq 404) {
            Write-Host "    ⚠️  POST $statusCode $statusDesc - 端点不存在" -ForegroundColor Yellow
        } elseif ($statusCode -eq 401) {
            Write-Host "    ℹ️  POST $statusCode $statusDesc - 需要认证（端点存在）" -ForegroundColor Cyan
        } else {
            Write-Host "    ⚠️  POST $statusCode $statusDesc" -ForegroundColor Yellow
        }
    }
}
Write-Host ""

# 步骤3: 检查WordPress SSO插件端点
Write-Host "[步骤3] 测试WordPress SSO v3.0.17端点..." -ForegroundColor Yellow
Write-Host ""

$ssoEndpoints = @(
    "/wp-json/nextjs-sso/v1/get-token",
    "/wp-json/nextjs-sso/v1/check-login",
    "/wp-json/nextjs-sso/v1/verify"
)

foreach ($endpoint in $ssoEndpoints) {
    Write-Host "  测试: $endpoint" -ForegroundColor Cyan

    try {
        $response = Invoke-WebRequest -Uri "$baseUrl$endpoint" `
            -Method Get `
            -ErrorAction Stop

        Write-Host "    ✓ GET $($response.StatusCode) $($response.StatusDescription)" -ForegroundColor Green

    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        $statusDesc = $_.Exception.Response.StatusDescription

        if ($statusCode -eq 200) {
            Write-Host "    ✓ GET $statusCode $statusDesc" -ForegroundColor Green
        } else {
            Write-Host "    ⚠️  GET $statusCode $statusDesc" -ForegroundColor Yellow
        }
    }
}
Write-Host ""

# 步骤4: 尝试直接访问问题PHP文件
Write-Host "[步骤4] 尝试直接访问问题PHP文件..." -ForegroundColor Yellow
Write-Host ""

$directUrl = "$baseUrl/wp-json/mwp-sign-sign.php"
Write-Host "  直接访问: $directUrl" -ForegroundColor Cyan

try {
    $response = Invoke-WebRequest -Uri $directUrl -Method Get -ErrorAction Stop
    Write-Host "    ✓ GET $($response.StatusCode) - 文件可访问" -ForegroundColor Green
    Write-Host "    响应内容前100字符:" -ForegroundColor Gray
    Write-Host "    $($response.Content.Substring(0, [Math]::Min(100, $response.Content.Length)))" -ForegroundColor Gray
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "    ✗ GET $statusCode - 文件不存在或不可访问" -ForegroundColor Red
    $results += "问题文件: 不存在（这解释了400错误！）"
}
Write-Host ""

# 步骤5: 生成诊断报告
Write-Host "[步骤5] 生成诊断报告..." -ForegroundColor Yellow
Write-Host ""

$reportPath = "wpcom-diagnosis-report-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"

$reportContent = @"
=================================================
WPCOM登录API诊断报告
生成时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
=================================================

【诊断结果汇总】
$($results -join "`n")

【关键发现】
1. /wp-json/mwp-sign-sign.php 不是标准的WordPress REST API端点
2. 标准REST API路径格式应该是: /wp-json/{namespace}/{version}/{endpoint}
3. 这个路径看起来像是直接执行PHP文件，但该文件可能不存在或配置错误

【推荐解决方案】

方案A: 修复WPCOM Member Pro配置
  1. WordPress后台 → WPCOM Member Pro → 设置
  2. 检查"API接口"是否正确配置
  3. 确认"手机快捷登录"使用的API端点
  4. 如果有"自定义登录接口"设置，改为标准REST API路径

方案B: 查找正确的WPCOM登录端点
  根据上述诊断，可能的正确端点：
  $(if ($wpcomEndpoints.Count -gt 0) { $wpcomEndpoints -join "`n  " } else { "未找到WPCOM相关端点" })

方案C: 联系WPCOM技术支持
  提供此诊断报告，请求以下信息：
  1. 正确的REST API登录端点
  2. 需要的请求参数格式
  3. WPCOM Member Pro版本和配置要求

【下一步操作】
1. 将此报告发送给开发人员
2. 检查WordPress后台的WPCOM Member Pro设置
3. 查看WordPress debug.log中的相关错误信息
4. 考虑暂时使用WordPress标准登录作为备选方案

=================================================
"@

$reportContent | Out-File -FilePath $reportPath -Encoding UTF8

Write-Host "✓ 诊断报告已保存到: $reportPath" -ForegroundColor Green
Write-Host ""

# 显示摘要
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  诊断完成" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "【关键结论】" -ForegroundColor Yellow
Write-Host "问题端点 /wp-json/mwp-sign-sign.php 不符合WordPress REST API规范" -ForegroundColor Red
Write-Host "这是导致400 Bad Request错误的根本原因！" -ForegroundColor Red
Write-Host ""
Write-Host "请查看诊断报告文件获取详细信息和解决方案。" -ForegroundColor Cyan
Write-Host ""

# 自动打开报告文件
if (Test-Path $reportPath) {
    notepad $reportPath
}
