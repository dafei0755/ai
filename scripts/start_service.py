"""
统一服务启动脚本 (v8.1+)

支持多环境配置的服务启动工具，可以启动后端或前端服务

功能:
- 自动加载环境配置 (.env.{env})
- 端口冲突检测和自动分配
- 服务健康检查
- 友好的启动日志输出

使用示例:
    # 启动开发环境后端
    python scripts/start_service.py --env development --service backend

    # 启动测试环境前端
    python scripts/start_service.py --env test --service frontend

    # 启动测试环境全套服务
    python scripts/start_service.py --env test --service all

    # 启动生产环境（固定端口）
    python scripts/start_service.py --env production --service all
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.port_manager import PortManager


class ServiceStarter:
    """服务启动器"""

    def __init__(self, env: str = "development", service: str = "all", auto_release: bool = True):
        """
        初始化服务启动器

        Args:
            env: 环境名称 (development/test/production)
            service: 服务类型 (backend/frontend/all)
            auto_release: 是否自动释放端口
        """
        self.env = env.lower()
        self.service = service.lower()
        self.auto_release = auto_release
        self.project_root = project_root
        self.port_manager = PortManager()

        # 验证环境名称
        valid_envs = ["development", "dev", "test", "staging", "production", "prod"]
        if self.env not in valid_envs:
            raise ValueError(f"Invalid environment: {env}. Valid options: {valid_envs}")

        # 验证服务类型
        valid_services = ["backend", "frontend", "all"]
        if self.service not in valid_services:
            raise ValueError(f"Invalid service: {service}. Valid options: {valid_services}")

    def set_env_variable(self, key: str, value: str):
        """设置环境变量"""
        os.environ[key] = value

    def load_env_config(self) -> dict:
        """
        加载环境配置

        Returns:
            配置字典
        """
        print(f"\n{'=' * 60}")
        print(f"  🚀 Starting Service - Environment: {self.env.upper()}")
        print(f"{'=' * 60}\n")

        # 设置 APP_ENV 环境变量（优先级最高）
        self.set_env_variable("APP_ENV", self.env)

        # 加载 .env.{env} 文件
        env_file = self.project_root / f".env.{self.env}"
        if not env_file.exists():
            print(f"⚠ Warning: Environment config file not found: {env_file}")
            print(f"  Please create it from .env.{self.env}.example")
            response = input("\nContinue with default configuration? (y/n): ")
            if response.lower() != "y":
                sys.exit(1)

        # 分配端口
        print(f"\n📍 Port Allocation:")
        if self.auto_release:
            ports = self.port_manager.auto_release_and_allocate(self.env)
        else:
            ports = self.port_manager.allocate_ports(self.env, prefer_default=True)

        print(f"  Backend:  http://localhost:{ports['backend']}")
        print(f"  Frontend: http://localhost:{ports['frontend']}")

        # 设置端口环境变量
        self.set_env_variable("API_PORT", str(ports["backend"]))
        self.set_env_variable("FRONTEND_PORT", str(ports["frontend"]))

        return ports

    def start_backend(self, port: int, background: bool = False) -> Optional[subprocess.Popen]:
        """
        启动后端服务

        Args:
            port: 后端端口
            background: 是否后台运行

        Returns:
            进程对象（如果是后台运行）
        """
        print(f"\n🔧 Starting Backend Service on port {port}...")

        # 确保日志目录存在
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)

        # 构建启动命令
        python_exec = sys.executable  # 使用当前Python解释器
        script_path = self.project_root / "scripts" / "run_server_production.py"

        if not script_path.exists():
            print(f"✗ Backend startup script not found: {script_path}")
            sys.exit(1)

        cmd = [python_exec, "-B", str(script_path)]

        # 设置环境变量
        env = os.environ.copy()
        env["APP_ENV"] = self.env
        env["API_PORT"] = str(port)

        print(f"  Command: {' '.join(cmd)}")
        print(f"  Working Directory: {self.project_root}")
        print(f"  Environment: APP_ENV={self.env}, API_PORT={port}")

        if background:
            # 后台运行
            process = subprocess.Popen(
                cmd,
                cwd=str(self.project_root),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform.startswith("win") else 0,
            )
            print(f"✓ Backend started in background (PID: {process.pid})")
            return process
        else:
            # 前台运行
            print(f"\n{'=' * 60}")
            print(f"  🎉 Backend is starting...")
            print(f"  Access API docs at: http://localhost:{port}/docs")
            print(f"{'=' * 60}\n")

            try:
                subprocess.run(cmd, cwd=str(self.project_root), env=env)
            except KeyboardInterrupt:
                print("\n\n⚠ Backend stopped by user")
                sys.exit(0)

        return None

    def start_frontend(self, port: int, backend_port: int, background: bool = False) -> Optional[subprocess.Popen]:
        """
        启动前端服务

        Args:
            port: 前端端口
            backend_port: 后端端口（用于API连接）
            background: 是否后台运行

        Returns:
            进程对象（如果是后台运行）
        """
        print(f"\n🎨 Starting Frontend Service on port {port}...")

        frontend_dir = self.project_root / "frontend-nextjs"
        if not frontend_dir.exists():
            print(f"✗ Frontend directory not found: {frontend_dir}")
            sys.exit(1)

        # 检查 node_modules
        if not (frontend_dir / "node_modules").exists():
            print("⚠ node_modules not found. Please run:")
            print(f"  cd {frontend_dir} && npm install")
            sys.exit(1)

        # 构建启动命令
        cmd = ["npm", "run", "dev", "--", "-p", str(port)]

        # 设置环境变量
        env = os.environ.copy()
        env["NEXT_PUBLIC_API_BASE_URL"] = f"http://localhost:{backend_port}"
        env["PORT"] = str(port)

        print(f"  Command: {' '.join(cmd)}")
        print(f"  Working Directory: {frontend_dir}")
        print(f"  API Backend: http://localhost:{backend_port}")

        if background:
            # 后台运行
            process = subprocess.Popen(
                cmd,
                cwd=str(frontend_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform.startswith("win") else 0,
            )
            print(f"✓ Frontend started in background (PID: {process.pid})")
            return process
        else:
            # 前台运行
            print(f"\n{'=' * 60}")
            print(f"  🎉 Frontend is starting...")
            print(f"  Access app at: http://localhost:{port}")
            print(f"{'=' * 60}\n")

            try:
                subprocess.run(cmd, cwd=str(frontend_dir), env=env)
            except KeyboardInterrupt:
                print("\n\n⚠ Frontend stopped by user")
                sys.exit(0)

        return None

    def health_check(self, port: int, service_name: str = "Backend", timeout: int = 30) -> bool:
        """
        服务健康检查

        Args:
            port: 服务端口
            service_name: 服务名称
            timeout: 超时时间(秒)

        Returns:
            True 如果服务健康, False 否则
        """
        import requests

        url = f"http://localhost:{port}/health" if service_name == "Backend" else f"http://localhost:{port}"

        print(f"\n🔍 Health Check: {service_name} on port {port}...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200 or response.status_code == 404:  # 404也算正常（前端可能没有/health）
                    print(f"✓ {service_name} is healthy!")
                    return True
            except requests.exceptions.RequestException:
                pass

            time.sleep(2)

        print(f"✗ {service_name} health check failed (timeout after {timeout}s)")
        return False

    def start(self):
        """启动服务"""
        try:
            # 加载配置和分配端口
            ports = self.load_env_config()

            if self.service == "backend":
                self.start_backend(ports["backend"], background=False)

            elif self.service == "frontend":
                self.start_frontend(ports["frontend"], ports["backend"], background=False)

            elif self.service == "all":
                # 启动后端（后台）
                backend_process = self.start_backend(ports["backend"], background=True)

                # 等待后端启动
                time.sleep(3)

                # 健康检查
                if not self.health_check(ports["backend"], "Backend", timeout=30):
                    print("✗ Backend failed to start properly")
                    if backend_process:
                        backend_process.terminate()
                    sys.exit(1)

                # 启动前端（前台）
                try:
                    self.start_frontend(ports["frontend"], ports["backend"], background=False)
                except KeyboardInterrupt:
                    print("\n\n⚠ Stopping all services...")
                    if backend_process:
                        backend_process.terminate()
                        print("✓ Backend stopped")
                    sys.exit(0)

        except Exception as e:
            print(f"\n✗ Error: {e}")
            sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Multi-Environment Service Starter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 启动开发环境后端
  python scripts/start_service.py --env development --service backend

  # 启动测试环境全套服务
  python scripts/start_service.py --env test --service all

  # 启动生产环境（手动端口管理）
  python scripts/start_service.py --env production --service all --no-auto-release
        """,
    )

    parser.add_argument(
        "--env",
        default="development",
        help="Environment (development/test/production)",
        choices=["development", "dev", "test", "staging", "production", "prod"],
    )

    parser.add_argument(
        "--service",
        default="all",
        help="Service to start (backend/frontend/all)",
        choices=["backend", "frontend", "all"],
    )

    parser.add_argument("--no-auto-release", action="store_true", help="Do not automatically release ports")

    args = parser.parse_args()

    starter = ServiceStarter(env=args.env, service=args.service, auto_release=not args.no_auto_release)

    starter.start()


if __name__ == "__main__":
    main()
