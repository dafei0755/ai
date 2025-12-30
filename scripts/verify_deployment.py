"""
生产环境部署前验证脚本
一键检查所有必需和推荐的配置项
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class DeploymentVerifier:
    """部署验证器"""

    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.checks_warned = 0
        self.results = []

    def print_header(self, title: str):
        """打印标题"""
        print("\n" + "=" * 60)
        print(title)
        print("=" * 60)

    def print_section(self, title: str):
        """打印小节标题"""
        print(f"\n{title}")
        print("-" * 60)

    def check(self, description: str, check_func, required: bool = True) -> bool:
        """执行检查并记录结果"""
        try:
            result, message = check_func()
            if result:
                print(f"✅ {description}: {message}")
                self.checks_passed += 1
                self.results.append((description, "pass", message))
                return True
            else:
                if required:
                    print(f"❌ {description}: {message}")
                    self.checks_failed += 1
                    self.results.append((description, "fail", message))
                else:
                    print(f"⚠️ {description}: {message}")
                    self.checks_warned += 1
                    self.results.append((description, "warn", message))
                return False
        except Exception as e:
            if required:
                print(f"❌ {description}: 检查异常 - {e}")
                self.checks_failed += 1
                self.results.append((description, "fail", str(e)))
            else:
                print(f"⚠️ {description}: 检查异常 - {e}")
                self.checks_warned += 1
                self.results.append((description, "warn", str(e)))
            return False

    def print_summary(self):
        """打印总结"""
        self.print_header("验证总结")
        print(f"通过: {self.checks_passed}")
        print(f"失败: {self.checks_failed}")
        print(f"警告: {self.checks_warned}")
        print(f"总计: {self.checks_passed + self.checks_failed + self.checks_warned}")

        if self.checks_failed == 0:
            print("\n" + "=" * 60)
            print("✅ 验证通过！系统可以部署到生产环境")
            print("=" * 60)
            return True
        else:
            print("\n" + "=" * 60)
            print("❌ 验证失败！请修复以上错误后再部署")
            print("=" * 60)
            return False

    # ==================== 环境变量检查 ====================

    def check_env_file_exists(self) -> Tuple[bool, str]:
        """检查.env文件是否存在"""
        env_path = project_root / ".env"
        if env_path.exists():
            return True, ".env文件存在"
        return False, ".env文件不存在，请从.env.example复制并配置"

    def check_llm_api_keys(self) -> Tuple[bool, str]:
        """检查LLM API密钥"""
        from dotenv import load_dotenv
        load_dotenv()

        openai_key = os.getenv("OPENAI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        google_key = os.getenv("GOOGLE_API_KEY")

        if openai_key or anthropic_key or google_key:
            configured = []
            if openai_key:
                configured.append("OpenAI")
            if anthropic_key:
                configured.append("Anthropic")
            if google_key:
                configured.append("Google")
            return True, f"已配置: {', '.join(configured)}"
        return False, "未配置任何LLM API密钥"

    def check_redis_config(self) -> Tuple[bool, str]:
        """检查Redis配置"""
        from dotenv import load_dotenv
        load_dotenv()

        redis_host = os.getenv("REDIS_HOST")
        redis_port = os.getenv("REDIS_PORT")

        if redis_host and redis_port:
            return True, f"Redis配置: {redis_host}:{redis_port}"
        return False, "Redis配置不完整"

    def check_tencent_config(self) -> Tuple[bool, str]:
        """检查腾讯云配置"""
        from dotenv import load_dotenv
        load_dotenv()

        secret_id = os.getenv("TENCENT_CLOUD_SECRET_ID")
        secret_key = os.getenv("TENCENT_CLOUD_SECRET_KEY")
        enabled = os.getenv("ENABLE_TENCENT_CONTENT_SAFETY")

        if enabled != "true":
            return False, "腾讯云内容安全未启用（生产环境必需）"

        if not secret_id or not secret_key:
            return False, "腾讯云API密钥未配置"

        if not secret_id.startswith("AKID"):
            return False, f"SecretId格式错误（应以AKID开头）: {secret_id[:10]}..."

        return True, f"腾讯云配置正常: {secret_id[:10]}..."

    # ==================== 依赖检查 ====================

    def check_python_deps(self) -> Tuple[bool, str]:
        """检查Python依赖"""
        try:
            # 检查关键依赖
            import fastapi
            import langchain
            import langgraph
            import redis
            import yaml
            return True, "Python依赖已安装"
        except ImportError as e:
            return False, f"缺少依赖: {e}"

    def check_tencent_sdk(self) -> Tuple[bool, str]:
        """检查腾讯云SDK"""
        try:
            from tencentcloud.common import credential
            return True, "腾讯云SDK已安装"
        except ImportError:
            return False, "腾讯云SDK未安装，请运行: pip install tencentcloud-sdk-python"

    # ==================== 服务检查 ====================

    def check_redis_connection(self) -> Tuple[bool, str]:
        """检查Redis连接"""
        try:
            import redis
            from dotenv import load_dotenv
            load_dotenv()

            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                db=int(os.getenv("REDIS_DB", 0)),
                password=os.getenv("REDIS_PASSWORD") or None,
                decode_responses=True,
                socket_timeout=3
            )
            r.ping()
            return True, "Redis连接正常"
        except Exception as e:
            return False, f"Redis连接失败: {e}"

    # ==================== 文件检查 ====================

    def check_security_rules_yaml(self) -> Tuple[bool, str]:
        """检查安全规则配置文件"""
        rules_path = project_root / "intelligent_project_analyzer" / "security" / "security_rules.yaml"
        if not rules_path.exists():
            return False, "security_rules.yaml文件不存在"

        try:
            import yaml
            with open(rules_path, 'r', encoding='utf-8') as f:
                rules = yaml.safe_load(f)

            # 检查必需的键
            required_keys = ["version", "keywords", "privacy_patterns", "evasion_patterns"]
            missing = [k for k in required_keys if k not in rules]
            if missing:
                return False, f"配置文件缺少必需的键: {missing}"

            # 统计规则数量
            keywords_count = len(rules.get("keywords", {}))
            privacy_count = len(rules.get("privacy_patterns", {}))
            evasion_count = len(rules.get("evasion_patterns", {}))

            return True, f"配置正常 (关键词:{keywords_count}, 隐私:{privacy_count}, 规避:{evasion_count})"
        except yaml.YAMLError as e:
            return False, f"YAML语法错误: {e}"
        except Exception as e:
            return False, f"检查失败: {e}"

    def check_upload_directory(self) -> Tuple[bool, str]:
        """检查上传目录"""
        upload_dir = project_root / "data" / "uploads"
        if not upload_dir.exists():
            try:
                upload_dir.mkdir(parents=True, exist_ok=True)
                return True, "上传目录已创建"
            except Exception as e:
                return False, f"无法创建上传目录: {e}"

        if not os.access(upload_dir, os.W_OK):
            return False, "上传目录不可写"

        return True, "上传目录正常"

    # ==================== 功能测试 ====================

    def check_tencent_api_connection(self) -> Tuple[bool, str]:
        """检查腾讯云API连接"""
        try:
            from dotenv import load_dotenv
            load_dotenv()

            if os.getenv("ENABLE_TENCENT_CONTENT_SAFETY") != "true":
                return False, "腾讯云内容安全未启用"

            from intelligent_project_analyzer.security.tencent_content_safety import (
                TencentContentSafetyClient
            )

            client = TencentContentSafetyClient()
            result = client.check_text("测试文本")

            if "is_safe" in result:
                return True, "腾讯云API连接正常"
            return False, "腾讯云API响应格式错误"
        except Exception as e:
            return False, f"腾讯云API连接失败: {e}"

    def check_dynamic_rules_loader(self) -> Tuple[bool, str]:
        """检查动态规则加载器"""
        try:
            from intelligent_project_analyzer.security.dynamic_rule_loader import get_rule_loader

            loader = get_rule_loader()
            stats = loader.get_stats()

            return True, f"规则加载器正常 (版本:{stats['version']}, 类别:{stats['keywords']['total_categories']})"
        except Exception as e:
            return False, f"规则加载器失败: {e}"

    def check_content_safety_guard(self) -> Tuple[bool, str]:
        """检查内容安全守卫"""
        try:
            from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard

            guard = ContentSafetyGuard(use_dynamic_rules=True, use_external_api=False)
            result = guard.check("测试文本")

            if "is_safe" in result and "risk_level" in result:
                return True, "内容安全守卫正常"
            return False, "内容安全守卫响应格式错误"
        except Exception as e:
            return False, f"内容安全守卫失败: {e}"

    # ==================== 主验证流程 ====================

    def run_full_check(self):
        """运行完整验证"""
        self.print_header("生产环境部署前验证")

        # 第一阶段：环境配置检查
        self.print_section("第一阶段：环境配置检查")
        self.check(".env文件", self.check_env_file_exists, required=True)
        self.check("LLM API密钥", self.check_llm_api_keys, required=True)
        self.check("Redis配置", self.check_redis_config, required=True)
        self.check("腾讯云配置", self.check_tencent_config, required=True)

        # 第二阶段：依赖检查
        self.print_section("第二阶段：依赖安装检查")
        self.check("Python依赖", self.check_python_deps, required=True)
        self.check("腾讯云SDK", self.check_tencent_sdk, required=True)

        # 第三阶段：服务检查
        self.print_section("第三阶段：服务连接检查")
        self.check("Redis连接", self.check_redis_connection, required=True)

        # 第四阶段：文件检查
        self.print_section("第四阶段：配置文件检查")
        self.check("动态规则配置", self.check_security_rules_yaml, required=False)
        self.check("上传目录", self.check_upload_directory, required=False)

        # 第五阶段：功能测试
        self.print_section("第五阶段：功能验证")
        self.check("腾讯云API", self.check_tencent_api_connection, required=True)
        self.check("动态规则加载器", self.check_dynamic_rules_loader, required=False)
        self.check("内容安全守卫", self.check_content_safety_guard, required=True)

        # 打印总结
        return self.print_summary()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="生产环境部署前验证脚本")
    parser.add_argument("--full-check", action="store_true", help="运行完整检查")
    parser.add_argument("--check-env", action="store_true", help="仅检查环境变量")
    parser.add_argument("--check-deps", action="store_true", help="仅检查依赖")
    parser.add_argument("--check-redis", action="store_true", help="仅检查Redis")
    parser.add_argument("--check-rules", action="store_true", help="仅检查动态规则")

    args = parser.parse_args()

    verifier = DeploymentVerifier()

    if args.full_check or not any([args.check_env, args.check_deps, args.check_redis, args.check_rules]):
        # 默认运行完整检查
        success = verifier.run_full_check()
        sys.exit(0 if success else 1)

    # 运行部分检查
    if args.check_env:
        verifier.print_section("环境变量检查")
        verifier.check(".env文件", verifier.check_env_file_exists)
        verifier.check("LLM API密钥", verifier.check_llm_api_keys)
        verifier.check("Redis配置", verifier.check_redis_config)
        verifier.check("腾讯云配置", verifier.check_tencent_config)

    if args.check_deps:
        verifier.print_section("依赖检查")
        verifier.check("Python依赖", verifier.check_python_deps)
        verifier.check("腾讯云SDK", verifier.check_tencent_sdk)

    if args.check_redis:
        verifier.print_section("Redis检查")
        verifier.check("Redis连接", verifier.check_redis_connection)

    if args.check_rules:
        verifier.print_section("动态规则检查")
        verifier.check("动态规则配置", verifier.check_security_rules_yaml)

    verifier.print_summary()
    sys.exit(0 if verifier.checks_failed == 0 else 1)


if __name__ == "__main__":
    main()
