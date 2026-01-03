@echo off
echo ========================================
echo 安装安全扫描工具
echo ========================================
echo.

echo [1/4] 安装 detect-secrets...
python -m pip install detect-secrets

echo.
echo [2/4] 安装 pre-commit...
python -m pip install pre-commit

echo.
echo [3/4] 设置 pre-commit hooks...
python -m pre_commit install

echo.
echo [4/4] 建立密钥检测基线...
python -m detect_secrets scan --exclude-files '.git/.*' --exclude-files 'node_modules/.*' --exclude-files 'venv/.*' > .secrets.baseline

echo.
echo ========================================
echo ✅ 安装完成！
echo ========================================
echo.
echo 使用方法:
echo   1. 每次提交前会自动扫描密钥
echo   2. 手动扫描: python -m detect_secrets scan
echo   3. 更新基线: python -m detect_secrets scan > .secrets.baseline
echo.
pause
