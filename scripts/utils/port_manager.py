"""
端口管理工具 (v8.1+)

功能:
1. 检测端口占用情况
2. 自动分配可用端口
3. 释放指定端口（仅释放Python/Uvicorn进程）
4. 端口冲突检测和解决

使用示例:
    from scripts.utils.port_manager import PortManager
    
    # 检测端口是否可用
    pm = PortManager()
    if pm.is_port_available(8000):
        print("Port 8000 is available")
    
    # 为测试环境分配端口
    ports = pm.allocate_ports(env="test")
    print(f"Backend: {ports['backend']}, Frontend: {ports['frontend']}")
    
    # 释放端口
    pm.release_port(8000, process_names=["python.exe", "uvicorn.exe"])
"""

import os
import socket
import subprocess
import sys
from typing import Dict, List, Optional, Tuple


class PortManager:
    """端口管理器"""

    # 端口范围规划
    PORT_RANGES = {
        "development": {"backend": (8000, 8009), "frontend": (3001, 3009)},
        "dev": {"backend": (8000, 8009), "frontend": (3001, 3009)},
        "test": {"backend": (8100, 8109), "frontend": (3101, 3109)},
        "staging": {"backend": (8200, 8209), "frontend": (3201, 3209)},
        "production": {"backend": (8000, 8000), "frontend": (3001, 3001)},  # 生产环境固定端口
        "prod": {"backend": (8000, 8000), "frontend": (3001, 3001)},
    }

    # 默认端口映射
    DEFAULT_PORTS = {
        "development": {"backend": 8000, "frontend": 3001},
        "dev": {"backend": 8000, "frontend": 3001},
        "test": {"backend": 8100, "frontend": 3101},
        "staging": {"backend": 8200, "frontend": 3201},
        "production": {"backend": 8000, "frontend": 3001},
        "prod": {"backend": 8000, "frontend": 3001},
    }

    def __init__(self):
        """初始化端口管理器"""
        self.is_windows = sys.platform.startswith("win")

    def is_port_available(self, port: int, host: str = "0.0.0.0") -> bool:
        """
        检查端口是否可用

        Args:
            port: 端口号
            host: 主机地址

        Returns:
            True 如果端口可用, False 如果已被占用
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
                return True
            except OSError:
                return False

    def find_available_port(self, start_port: int, end_port: int, host: str = "0.0.0.0") -> Optional[int]:
        """
        在指定范围内查找可用端口

        Args:
            start_port: 起始端口
            end_port: 结束端口
            host: 主机地址

        Returns:
            可用端口号, 如果没有可用端口则返回 None
        """
        for port in range(start_port, end_port + 1):
            if self.is_port_available(port, host):
                return port
        return None

    def get_port_process(self, port: int) -> Optional[Dict[str, str]]:
        """
        获取占用端口的进程信息 (仅Windows)

        Args:
            port: 端口号

        Returns:
            进程信息字典 {"pid": "...", "name": "...", "command": "..."}
            如果端口未被占用或获取失败则返回 None
        """
        if not self.is_windows:
            # Linux/Mac 实现（待添加）
            return None

        try:
            # 使用 netstat 查找占用端口的 PID
            cmd = f"netstat -aon | findstr :{port} | findstr LISTENING"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8")

            if result.returncode != 0 or not result.stdout.strip():
                return None

            # 解析 netstat 输出获取 PID
            lines = result.stdout.strip().split("\n")
            for line in lines:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]

                    # 使用 tasklist 获取进程名称
                    cmd_tasklist = f'tasklist /FI "PID eq {pid}" /FO CSV /NH'
                    task_result = subprocess.run(
                        cmd_tasklist, shell=True, capture_output=True, text=True, encoding="utf-8"
                    )

                    if task_result.returncode == 0 and task_result.stdout.strip():
                        # CSV 格式: "进程名","PID","会话名","会话#","内存使用"
                        task_info = task_result.stdout.strip().replace('"', "").split(",")
                        if len(task_info) >= 2:
                            process_name = task_info[0]
                            return {"pid": pid, "name": process_name, "command": line.strip()}

            return None

        except Exception as e:
            print(f"Error getting port process: {e}")
            return None

    def release_port(
        self, port: int, process_names: Optional[List[str]] = None, force: bool = False
    ) -> Tuple[bool, str]:
        """
        释放指定端口 (仅Windows，且只释放指定进程类型)

        Args:
            port: 端口号
            process_names: 允许终止的进程名列表（如 ["python.exe", "uvicorn.exe"]）
                          如果为 None 且 force=False，则不会终止任何进程
            force: 是否强制终止所有占用端口的进程（危险操作）

        Returns:
            (成功/失败, 消息)
        """
        if not self.is_windows:
            return False, "Port release only supported on Windows currently"

        if not force and not process_names:
            return False, "Must specify process_names or set force=True"

        try:
            process_info = self.get_port_process(port)
            if not process_info:
                return True, f"Port {port} is not in use"

            pid = process_info["pid"]
            process_name = process_info["name"]

            # 检查进程名是否在允许列表中
            if not force:
                if not any(allowed_name.lower() in process_name.lower() for allowed_name in process_names):
                    return (
                        False,
                        f"Port {port} is used by '{process_name}' (PID: {pid}), which is not in the allowed list: {process_names}",
                    )

            # 终止进程
            cmd = f"taskkill /F /PID {pid}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8")

            if result.returncode == 0:
                return True, f"Successfully released port {port} (terminated {process_name}, PID: {pid})"
            else:
                return False, f"Failed to terminate process {process_name} (PID: {pid}): {result.stderr}"

        except Exception as e:
            return False, f"Error releasing port {port}: {e}"

    def allocate_ports(self, env: str = "development", prefer_default: bool = True) -> Dict[str, int]:
        """
        为指定环境分配端口

        Args:
            env: 环境名称 (development/test/staging/production)
            prefer_default: 是否优先使用默认端口

        Returns:
            端口分配字典 {"backend": xxxx, "frontend": yyyy}
        """
        env = env.lower()
        if env not in self.PORT_RANGES:
            raise ValueError(f"Unknown environment: {env}. Valid options: {list(self.PORT_RANGES.keys())}")

        allocated = {}

        # 后端端口
        backend_range = self.PORT_RANGES[env]["backend"]
        default_backend = self.DEFAULT_PORTS[env]["backend"]

        if prefer_default and self.is_port_available(default_backend):
            allocated["backend"] = default_backend
        else:
            backend_port = self.find_available_port(backend_range[0], backend_range[1])
            if backend_port is None:
                raise RuntimeError(f"No available backend port in range {backend_range} for environment '{env}'")
            allocated["backend"] = backend_port

        # 前端端口
        frontend_range = self.PORT_RANGES[env]["frontend"]
        default_frontend = self.DEFAULT_PORTS[env]["frontend"]

        if prefer_default and self.is_port_available(default_frontend):
            allocated["frontend"] = default_frontend
        else:
            frontend_port = self.find_available_port(frontend_range[0], frontend_range[1])
            if frontend_port is None:
                raise RuntimeError(f"No available frontend port in range {frontend_range} for environment '{env}'")
            allocated["frontend"] = frontend_port

        return allocated

    def check_port_conflicts(self, env: str = "development") -> Dict[str, Optional[Dict[str, str]]]:
        """
        检查环境默认端口是否被占用

        Args:
            env: 环境名称

        Returns:
            冲突信息字典 {"backend": process_info, "frontend": process_info}
            如果端口可用则对应值为 None
        """
        env = env.lower()
        if env not in self.DEFAULT_PORTS:
            raise ValueError(f"Unknown environment: {env}")

        conflicts = {}
        default_ports = self.DEFAULT_PORTS[env]

        for service, port in default_ports.items():
            if not self.is_port_available(port):
                conflicts[service] = self.get_port_process(port)
            else:
                conflicts[service] = None

        return conflicts

    def auto_release_and_allocate(self, env: str = "development") -> Dict[str, int]:
        """
        自动释放端口并分配（仅释放Python/Uvicorn进程）

        Args:
            env: 环境名称

        Returns:
            端口分配字典
        """
        env = env.lower()
        default_ports = self.DEFAULT_PORTS[env]

        # 尝试释放后端端口
        backend_port = default_ports["backend"]
        if not self.is_port_available(backend_port):
            success, msg = self.release_port(backend_port, process_names=["python.exe", "uvicorn.exe"])
            if success:
                print(f"✓ {msg}")
            else:
                print(f"⚠ {msg}")

        # 尝试释放前端端口
        frontend_port = default_ports["frontend"]
        if not self.is_port_available(frontend_port):
            success, msg = self.release_port(frontend_port, process_names=["node.exe", "next.exe"])
            if success:
                print(f"✓ {msg}")
            else:
                print(f"⚠ {msg}")

        # 分配端口
        return self.allocate_ports(env, prefer_default=True)


# CLI 功能
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Port Manager CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # check 命令
    check_parser = subparsers.add_parser("check", help="Check port availability")
    check_parser.add_argument("port", type=int, help="Port number to check")

    # allocate 命令
    allocate_parser = subparsers.add_parser("allocate", help="Allocate ports for environment")
    allocate_parser.add_argument("--env", default="development", help="Environment name")

    # release 命令
    release_parser = subparsers.add_parser("release", help="Release a port")
    release_parser.add_argument("port", type=int, help="Port number to release")
    release_parser.add_argument("--force", action="store_true", help="Force release (dangerous)")

    # conflicts 命令
    conflicts_parser = subparsers.add_parser("conflicts", help="Check port conflicts")
    conflicts_parser.add_argument("--env", default="development", help="Environment name")

    args = parser.parse_args()
    pm = PortManager()

    if args.command == "check":
        if pm.is_port_available(args.port):
            print(f"✓ Port {args.port} is available")
        else:
            process_info = pm.get_port_process(args.port)
            if process_info:
                print(f"✗ Port {args.port} is occupied by {process_info['name']} (PID: {process_info['pid']})")
            else:
                print(f"✗ Port {args.port} is occupied")

    elif args.command == "allocate":
        try:
            ports = pm.allocate_ports(args.env)
            print(f"✓ Allocated ports for '{args.env}':")
            print(f"  Backend:  {ports['backend']}")
            print(f"  Frontend: {ports['frontend']}")
        except Exception as e:
            print(f"✗ Error: {e}")
            sys.exit(1)

    elif args.command == "release":
        process_names = ["python.exe", "uvicorn.exe", "node.exe", "next.exe"] if not args.force else None
        success, msg = pm.release_port(args.port, process_names=process_names, force=args.force)
        if success:
            print(f"✓ {msg}")
        else:
            print(f"✗ {msg}")
            sys.exit(1)

    elif args.command == "conflicts":
        conflicts = pm.check_port_conflicts(args.env)
        print(f"Port conflicts for '{args.env}':")
        for service, info in conflicts.items():
            default_port = pm.DEFAULT_PORTS[args.env][service]
            if info:
                print(f"  ✗ {service.capitalize()} ({default_port}): occupied by {info['name']} (PID: {info['pid']})")
            else:
                print(f"  ✓ {service.capitalize()} ({default_port}): available")

    else:
        parser.print_help()
