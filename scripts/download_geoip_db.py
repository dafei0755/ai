#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
下载 MaxMind GeoLite2-City 数据库

GeoLite2 是 MaxMind 提供的免费 IP 地理位置数据库
需要注册免费账号获取 License Key

官网: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
"""

import os
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

# 数据库下载URL（需要替换YOUR_LICENSE_KEY）
# 注册地址: https://www.maxmind.com/en/geolite2/signup
GEOLITE2_DOWNLOAD_URL = (
    "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key={license_key}&suffix=tar.gz"
)

# 项目根目录的 data 文件夹
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TARGET_FILE = DATA_DIR / "GeoLite2-City.mmdb"


def print_banner():
    """打印欢迎横幅"""
    print("=" * 70)
    print(" 📥 GeoLite2-City 数据库下载脚本")
    print("=" * 70)
    print()


def check_existing_db():
    """检查数据库是否已存在"""
    if TARGET_FILE.exists():
        file_size_mb = TARGET_FILE.stat().st_size / (1024 * 1024)
        print(f"✅ 数据库已存在: {TARGET_FILE}")
        print(f"   文件大小: {file_size_mb:.2f} MB")

        response = input("\n是否重新下载？(y/N): ").strip().lower()
        if response != "y":
            print("✅ 使用现有数据库")
            return True

        print("🗑️ 删除旧数据库...")
        TARGET_FILE.unlink()

    return False


def get_license_key():
    """获取 License Key"""
    print("\n📝 获取 MaxMind License Key:")
    print("   1. 访问: https://www.maxmind.com/en/geolite2/signup")
    print("   2. 注册免费账号")
    print("   3. 登录后前往: https://www.maxmind.com/en/accounts/current/license-key")
    print("   4. 生成 License Key")
    print()

    # 尝试从环境变量读取
    license_key = os.getenv("MAXMIND_LICENSE_KEY")

    if license_key:
        print(f"✅ 从环境变量读取 License Key: {license_key[:8]}...")
        return license_key

    # 手动输入
    license_key = input("请输入 License Key: ").strip()

    if not license_key or len(license_key) < 10:
        print("❌ License Key 无效")
        sys.exit(1)

    return license_key


def download_database(license_key: str):
    """下载数据库文件"""
    download_url = GEOLITE2_DOWNLOAD_URL.format(license_key=license_key)
    temp_file = DATA_DIR / "GeoLite2-City.tar.gz"

    try:
        # 确保 data 目录存在
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        print(f"\n📥 开始下载...")
        print(f"   保存到: {temp_file}")

        # 下载文件（带进度条）
        def show_progress(block_count, block_size, total_size):
            """显示下载进度"""
            downloaded = block_count * block_size
            percent = min(100, (downloaded / total_size) * 100) if total_size > 0 else 0
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)

            bar_length = 40
            filled = int(bar_length * percent / 100)
            bar = "█" * filled + "░" * (bar_length - filled)

            print(f"\r   [{bar}] {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="")

        urllib.request.urlretrieve(download_url, temp_file, show_progress)
        print("\n✅ 下载完成")

        return temp_file

    except urllib.error.HTTPError as e:
        print(f"\n❌ 下载失败: HTTP {e.code}")
        if e.code == 401:
            print("   License Key 无效或已过期")
            print("   请检查: https://www.maxmind.com/en/accounts/current/license-key")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        sys.exit(1)


def extract_database(tar_file: Path):
    """解压数据库文件"""
    try:
        print(f"\n📦 解压文件...")

        with tarfile.open(tar_file, "r:gz") as tar:
            # 查找 .mmdb 文件
            mmdb_member = None
            for member in tar.getmembers():
                if member.name.endswith("GeoLite2-City.mmdb"):
                    mmdb_member = member
                    break

            if not mmdb_member:
                print("❌ 压缩包中未找到 .mmdb 文件")
                sys.exit(1)

            # 提取文件
            print(f"   提取: {mmdb_member.name}")
            extracted = tar.extractfile(mmdb_member)

            if extracted:
                with open(TARGET_FILE, "wb") as f:
                    shutil.copyfileobj(extracted, f)

                file_size_mb = TARGET_FILE.stat().st_size / (1024 * 1024)
                print(f"✅ 解压完成: {TARGET_FILE}")
                print(f"   文件大小: {file_size_mb:.2f} MB")
            else:
                print("❌ 解压失败")
                sys.exit(1)

        # 清理临时文件
        print("\n🗑️ 清理临时文件...")
        tar_file.unlink()

    except Exception as e:
        print(f"❌ 解压失败: {e}")
        sys.exit(1)


def verify_database():
    """验证数据库文件"""
    try:
        print("\n🔍 验证数据库...")

        import geoip2.database

        reader = geoip2.database.Reader(str(TARGET_FILE))

        # 测试查询（Google DNS）
        test_ip = "8.8.8.8"
        response = reader.city(test_ip)

        print(f"✅ 数据库验证成功")
        print(f"   测试IP: {test_ip}")
        print(f"   国家: {response.country.name}")
        print(f"   城市: {response.city.name or '未知'}")

        reader.close()

    except ImportError:
        print("⚠️ geoip2 未安装，跳过验证")
        print("   安装命令: pip install geoip2")

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        sys.exit(1)


def main():
    """主函数"""
    print_banner()

    # 检查是否已存在
    if check_existing_db():
        return

    # 获取 License Key
    license_key = get_license_key()

    # 下载数据库
    tar_file = download_database(license_key)

    # 解压数据库
    extract_database(tar_file)

    # 验证数据库
    verify_database()

    print("\n" + "=" * 70)
    print("✅ 安装完成！")
    print("=" * 70)
    print(f"\n数据库位置: {TARGET_FILE}")
    print("\n💡 提示:")
    print("   - 数据库建议每月更新一次以保持准确性")
    print("   - 可以设置环境变量 MAXMIND_LICENSE_KEY 避免重复输入")
    print("   - 数据库文件约 70 MB，请确保有足够磁盘空间")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 意外错误: {e}")
        sys.exit(1)
