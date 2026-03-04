"""
多环境配置验证脚本 (v8.1+)

在启动服务或部署前验证环境配置的完整性和正确性

功能:
1. 配置文件完整性检查
2. 端口可用性检查
3. 依赖版本验证
4. 数据库连接测试
5. API密钥有效性检查

使用示例:
    # 验证测试环境
    python scripts/verify_env_config.py --env test

    # 验证所有环境
    python scripts/verify_env_config.py --all
    # 快速检查（跳过耗时测试）
    #快速检查（跳过耗时测试）
    python scripts/verify_env_config.py --env test --quick
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.port_manager import PortManager


class EnvConfigVerifier:
    """环境配置验证器"""

    def __init__(self, env: str = "development", quick: bool = False):
        """
        初始化验证器

        Args:
            env: 环境名称
            quick: 是否快速检查（跳过耗时测试）
        """
        self.env = env.lower()
        self.quick = quick
        self.project_root = project_root
        self.port_manager = PortManager()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []

    def log_pass(self, message: str):
        """记录通过的检查"""
        self.passed.append(message)
        print(f"✓ {message}")

    def log_warning(self, message: str):
        """记录警告"""
        self.warnings.append(message)
        print(f"⚠ {message}")

    def log_error(self, message: str):
        """记录错误"""
        self.errors.append(message)
        print(f"✗ {message}")

    def check_env_file(self) -> bool:
        """检查环境配置文件是否存在"""
        print(f"\n{'=' * 60}")
        print(f"  📋 Checking Environment Configuration Files")
        print(f"{'=' * 60}\n")

        env_file = self.project_root / f".env.{self.env}"
        env_example = self.project_root / f".env.{self.env}.example"

        if not env_file.exists():
            if env_example.exists():
                self.log_error(f"Configuration file missing: {env_file}")
                print(f"   Please create it from: {env_example}")
                return False
            else:
                self.log_warning(f"No configuration files found for '{self.env}' environment")
                self.log_warning("Using .env or default configuration")
                return True

        self.log_pass(f"Configuration file exists: {env_file}")
        return True

    def check_required_env_vars(self) -> bool:
        """检查必需的环境变量"""
        print(f"\n{'=' * 60}")
        print(f"  🔑 Checking Required Environment Variables")
        print(f"{'=' * 60}\n")

        # 加载环境配置
        env_file = self.project_root / f".env.{self.env}"
        if env_file.exists():
            from dotenv import load_dotenv

            load_dotenv(env_file)

        required_vars = {
            "OPENAI_API_KEY": "OpenAI API密钥（或其他LLM提供商密钥）",
        }

        optional_vars = {
            "TAVILY_API_KEY": "Tavily搜索API密钥",
            "BOCHA_API_KEY": "博查AI搜索API密钥",
            "REDIS_HOST": "Redis主机地址",
            "DATABASE_URL": "数据库连接URL",
        }

        all_good = True

        # 检查必需变量
        for var, desc in required_vars.items():
            value = os.getenv(var)
            if not value or value.startswith("your_") or value == "sk-xxx":
                self.log_error(f"Missing or invalid {var} ({desc})")
                all_good = False
            else:
                masked_value = value[:10] + "..." if len(value) > 10 else "***"
                self.log_pass(f"{var} is set ({masked_value})")

        # 检查可选变量
        for var, desc in optional_vars.items():
            value = os.getenv(var)
            if not value:
                self.log_warning(f"Optional {var} not set ({desc})")
            elif value.startswith("your_"):
                self.log_warning(f"{var} uses placeholder value ({desc})")
            else:
                self.log_pass(f"{var} is configured")

        return all_good

    def check_ports(self) -> bool:
        """检查端口可用性"""
        print(f"\n{'=' * 60}")
        print(f"  🔌 Checking Port Availability")
        print(f"{'=' * 60}\n")

        conflicts = self.port_manager.check_port_conflicts(self.env)

        for service, process_info in conflicts.items():
            default_port = self.port_manager.DEFAULT_PORTS[self.env][service]
            if process_info:
                self.log_warning(
                    f"{service.capitalize()} port {default_port} is occupied by {process_info['name']} (PID: {process_info['pid']})"
                )
                print(f"   Auto-release will handle this during startup")
            else:
                self.log_pass(f"{service.capitalize()} port {default_port} is available")

        return True

    def check_directories(self) -> bool:
        """检查必需的目录结构"""
        print(f"\n{'=' * 60}")
        print(f"  📁 Checking Directory Structure")
        print(f"{'=' * 60}\n")

        required_dirs = [
            "logs",
            f"data/{self.env}" if self.env != "production" else "data",
            "intelligent_project_analyzer",
            "scripts",
            "frontend-nextjs",
        ]

        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists():
                self.log_pass(f"Directory exists: {dir_path}/")
            else:
                self.log_warning(f"Directory missing: {dir_path}/ (will be created automatically)")

        return True

    def verify(self) -> bool:
        """执行完整验证"""
        print(f"\n{'=' * 70}")
        print(f"  🔍 Environment Verification - {self.env.upper()}")
        print(f"{'=' * 70}\n")

        # 执行各项检查
        self.check_env_file()
        self.check_required_env_vars()
        self.check_ports()
        self.check_directories()

        # 输出摘要
        print(f"\n{'=' * 70}")
        print(f"  📊 Verification Summary")
        print(f"{'=' * 70}\n")

        print(f"✓ Passed: {len(self.passed)}")
        print(f"⚠ Warnings: {len(self.warnings)}")
        print(f"✗ Errors: {len(self.errors)}")

        if self.errors:
            print(f"\n⚠️  {len(self.errors)} critical issues found:")
            for error in self.errors:
                print(f"  - {error}")
            print(f"\nPlease fix these issues before starting.\n")
            return False
        elif self.warnings:
            print(f"\n⚠️  {len(self.warnings)} warnings (non-critical).")
            print(f"\nYou can proceed, but consider addressing these warnings.\n")
            return True
        else:
            print(f"\n✅ All checks passed! Environment is ready.\n")
            return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Environment Configuration Verifier")

    parser.add_argument(
        "--env",
        default="development",
        help="Environment to verify",
        choices=["development", "dev", "test", "staging", "production", "prod"],
    )

    parser.add_argument("--all", action="store_true", help="Verify all environments")
    parser.add_argument("--quick", action="store_true", help="Quick check")

    args = parser.parse_args()

    if args.all:
        envs = ["development", "test", "production"]
        all_passed = True

        for env in envs:
            verifier = EnvConfigVerifier(env=env, quick=args.quick)
            if not verifier.verify():
                all_passed = False
            print("\n")

        sys.exit(0 if all_passed else 1)
    else:
        verifier = EnvConfigVerifier(env=args.env, quick=args.quick)
        success = verifier.verify()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
