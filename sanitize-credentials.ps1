# 批量脱敏文档中的真实凭证
$username = '8pdwoxj8'
$password = 'M2euRVQMdpzJp%\*KLtD0#kK1'
$jwtSecret = '\$d4@5fg54ll_t_45gH'

$files = Get-ChildItem -Path . -Include *.md -Recurse |
    Where-Object { (Get-Content $_.FullName -Raw) -match "($username|$password|$jwtSecret)" }

foreach ($file in $files) {
    Write-Host "正在处理: $($file.Name)"

    $content = Get-Content $file.FullName -Raw -Encoding UTF8

    # 替换真实凭证为占位符
    $content = $content -replace '8pdwoxj8', 'YOUR_WORDPRESS_USERNAME'
    $content = $content -replace 'M2euRVQMdpzJp%\*KLtD0#kK1', 'YOUR_WORDPRESS_PASSWORD'
    $content = $content -replace '\$d4@5fg54ll_t_45gH', 'YOUR_JWT_SECRET_KEY'

    # 保存文件（UTF-8 无BOM）
    $utf8NoBom = New-Object System.Text.UTF8Encoding $False
    [System.IO.File]::WriteAllText($file.FullName, $content, $utf8NoBom)

    Write-Host "✅ 已脱敏: $($file.Name)"
}

Write-Host "`n✅ 完成！共处理 $($files.Count) 个文件"
