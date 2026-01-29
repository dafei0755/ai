# Docker 镜像加速器自动配置和测试脚本
# 功能: 测试镜像加速器可用性，推荐最佳配置

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "🔍 Docker 镜像加速器诊断和配置工具" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# 检查 Docker 是否运行
Write-Host "📋 步骤 1: 检查 Docker 服务状态..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Docker 已安装: $dockerVersion" -ForegroundColor Green
    } else {
        Write-Host "❌ Docker 未安装或未运行" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Docker 未安装或未运行" -ForegroundColor Red
    exit 1
}

try {
    docker ps > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Docker 服务正在运行" -ForegroundColor Green
    } else {
        Write-Host "❌ Docker 服务未运行，请先启动 Docker Desktop" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Docker 服务未运行，请先启动 Docker Desktop" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 测试镜像加速器可用性
Write-Host "📋 步骤 2: 测试镜像加速器可用性..." -ForegroundColor Yellow
Write-Host ""

$mirrors = @(
    @{Name="DaoCloud"; URL="https://docker.m.daocloud.io"},
    @{Name="1Panel"; URL="https://docker.1panel.live"},
    @{Name="RatDev"; URL="https://hub.rat.dev"},
    @{Name="腾讯云"; URL="https://mirror.ccs.tencentyun.com"}
)

$availableMirrors = @()

foreach ($mirror in $mirrors) {
    Write-Host "   测试 $($mirror.Name) ($($mirror.URL))..." -NoNewline
    try {
        $response = Invoke-WebRequest -Uri "$($mirror.URL)/v2/" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 401) {
            Write-Host " ✅ 可用" -ForegroundColor Green
            $availableMirrors += $mirror.URL
        } else {
            Write-Host " ⚠️ 状态码: $($response.StatusCode)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host " ❌ 不可用" -ForegroundColor Red
    }
}

Write-Host ""

if ($availableMirrors.Count -eq 0) {
    Write-Host "❌ 没有找到可用的镜像加速器" -ForegroundColor Red
    Write-Host "建议: 使用 VPN 或代理访问 Docker Hub" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ 找到 $($availableMirrors.Count) 个可用的镜像加速器" -ForegroundColor Green
Write-Host ""

# 显示推荐配置
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📝 推荐的 Docker Engine 配置" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

$registryMirrors = $availableMirrors | ForEach-Object { "    `"$_`"" }
$registryMirrorsJson = $registryMirrors -join ",`n"

$configTemplate = @"
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "registry-mirrors": [
$registryMirrorsJson
  ],
  "dns": [
    "8.8.8.8",
    "114.114.114.114"
  ]
}
"@

Write-Host $configTemplate -ForegroundColor White
Write-Host ""

# 保存配置到文件
$configFile = "docker-daemon-config.json"
$configTemplate | Out-File -FilePath $configFile -Encoding UTF8
Write-Host "✅ 配置已保存到: $configFile" -ForegroundColor Green
Write-Host ""

# 显示配置步骤
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "🔧 配置步骤" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. 打开 Docker Desktop" -ForegroundColor Yellow
Write-Host "2. 点击右上角 ⚙️ 齿轮图标（Settings）" -ForegroundColor Yellow
Write-Host "3. 选择左侧 'Docker Engine' 标签" -ForegroundColor Yellow
Write-Host "4. 将上面的 JSON 配置复制到编辑器中" -ForegroundColor Yellow
Write-Host "5. 点击 'Apply & Restart' 按钮" -ForegroundColor Yellow
Write-Host "6. 等待 Docker Desktop 重启完成" -ForegroundColor Yellow
Write-Host ""

Write-Host "💡 提示: 配置内容已保存在 $configFile 文件中，可以直接复制" -ForegroundColor Cyan
Write-Host ""

# 测试 Milvus 镜像拉取
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "🧪 测试镜像拉取" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

$testImage = Read-Host "是否现在测试拉取 Milvus 镜像? (y/n)"

if ($testImage -eq "y" -or $testImage -eq "Y") {
    Write-Host ""
    Write-Host "🚀 正在拉取 milvusdb/milvus:v2.4.0..." -ForegroundColor Yellow
    Write-Host ""

    docker pull milvusdb/milvus:v2.4.0

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Milvus 镜像拉取成功！" -ForegroundColor Green
        Write-Host ""

        # 检查镜像
        Write-Host "📋 已安装的 Milvus 镜像:" -ForegroundColor Cyan
        docker images | Select-String "milvus"

        Write-Host ""
        Write-Host "🎯 下一步: 运行启动脚本" -ForegroundColor Yellow
        Write-Host "   python -B scripts\run_server_production.py" -ForegroundColor Gray
    } else {
        Write-Host ""
        Write-Host "❌ 镜像拉取失败" -ForegroundColor Red
        Write-Host "可能原因:" -ForegroundColor Yellow
        Write-Host "  1. 镜像加速器未配置或未生效" -ForegroundColor Gray
        Write-Host "  2. 网络连接问题" -ForegroundColor Gray
        Write-Host "  3. 需要重启 Docker Desktop" -ForegroundColor Gray
    }
} else {
    Write-Host ""
    Write-Host "⏭️ 跳过镜像拉取测试" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "配置完成后，请运行以下命令测试:" -ForegroundColor Cyan
    Write-Host "  docker pull milvusdb/milvus:v2.4.0" -ForegroundColor Gray
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "✅ 诊断完成" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "📚 相关文档:" -ForegroundColor Cyan
Write-Host "  - 详细解决方案: DOCKER_REGISTRY_MIRROR_SOLUTION.md" -ForegroundColor Gray
Write-Host "  - Milvus 诊断: MILVUS_STARTUP_FAILURE_DIAGNOSIS.md" -ForegroundColor Gray
Write-Host ""

pause
