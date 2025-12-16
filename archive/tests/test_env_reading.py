"""快速测试 .env 配置读取"""
from decouple import config

print("=" * 60)
print("测试 .env 配置读取")
print("=" * 60)

# 读取配置
wp_url = config("WORDPRESS_URL", default="未配置")
wp_username = config("WORDPRESS_ADMIN_USERNAME", default="未配置")
wp_password = config("WORDPRESS_ADMIN_PASSWORD", default="未配置")

print(f"WordPress URL: {wp_url}")
print(f"用户名: {wp_username}")
print(f"密码长度: {len(wp_password)} 字符")
print(f"密码（首尾3字符）: {wp_password[:3]}...{wp_password[-3:]}")
print(f"密码包含特殊字符: {'%' in wp_password or '#' in wp_password or '@' in wp_password}")
print("=" * 60)
