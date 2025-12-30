"""
腾讯云内容安全详细诊断脚本
用于诊断"SecretId不存在"错误的根本原因
"""

import os
import sys
import base64
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

print("=" * 80)
print("腾讯云内容安全详细诊断")
print("=" * 80)

# 1. 检查环境变量
print("\n[步骤 1] 检查环境变量配置")
print("-" * 80)

secret_id = os.getenv("TENCENT_CLOUD_SECRET_ID")
secret_key = os.getenv("TENCENT_CLOUD_SECRET_KEY")
region = os.getenv("TENCENT_CLOUD_REGION", "ap-guangzhou")
app_id = os.getenv("TENCENT_CONTENT_SAFETY_APP_ID")
enabled = os.getenv("ENABLE_TENCENT_CONTENT_SAFETY", "false").lower() == "true"

print(f"ENABLE_TENCENT_CONTENT_SAFETY: {enabled}")
print(f"TENCENT_CLOUD_SECRET_ID: {secret_id[:15] if secret_id else 'None'}...")
print(f"TENCENT_CLOUD_SECRET_KEY: {'*' * 20 if secret_key else 'None'} (length: {len(secret_key) if secret_key else 0})")
print(f"TENCENT_CLOUD_REGION: {region}")
print(f"TENCENT_CONTENT_SAFETY_APP_ID: {app_id}")

if not secret_id or not secret_key:
    print("\n[ERROR] Missing API key configuration")
    sys.exit(1)

# 2. 测试SDK导入
print("\n[步骤 2] 测试SDK导入")
print("-" * 80)

try:
    from tencentcloud.common import credential
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    from tencentcloud.tms.v20201229 import tms_client, models
    print("[OK] Tencent Cloud SDK imported successfully")
except ImportError as e:
    print(f"[ERROR] SDK import failed: {e}")
    sys.exit(1)

# 3. 创建客户端
print("\n[步骤 3] 创建腾讯云客户端")
print("-" * 80)

try:
    # 创建认证对象
    cred = credential.Credential(secret_id, secret_key)
    print("[OK] Credential object created successfully")

    # 创建HTTP配置
    httpProfile = HttpProfile()
    httpProfile.endpoint = "tms.tencentcloudapi.com"
    print(f"[OK] HTTP profile created (endpoint: {httpProfile.endpoint})")

    # 创建客户端配置
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    print("[OK] Client profile created successfully")

    # 创建TMS客户端
    client = tms_client.TmsClient(cred, region, clientProfile)
    print(f"[OK] TMS client created successfully (region: {region})")

except Exception as e:
    print(f"[ERROR] Client creation failed: {e}")
    sys.exit(1)

# 4. 测试API调用 - 使用最简单的请求
print("\n[步骤 4] 测试API调用")
print("-" * 80)

try:
    # 创建请求对象
    req = models.TextModerationRequest()

    # 文本内容需要Base64编码
    test_text = "test text for content safety verification"
    text_bytes = test_text.encode('utf-8')
    text_base64 = base64.b64encode(text_bytes).decode('utf-8')

    req.Content = text_base64
    req.BizType = "txt"

    print("Request parameters:")
    print(f"  - Content (original): {test_text}")
    print(f"  - Content (base64): {text_base64[:50]}...")
    print(f"  - BizType: {req.BizType}")
    print("\nCalling API...")

    # 调用API
    resp = client.TextModeration(req)

    print("[OK] API call successful!")
    print("\nResponse details:")
    print(f"  - Suggestion: {resp.Suggestion}")
    print(f"  - Label: {resp.Label}")
    print(f"  - Score: {resp.Score}")

except TencentCloudSDKException as e:
    print(f"\n[ERROR] API call failed - Tencent Cloud SDK Exception")
    print(f"\nError details:")
    print(f"  - Error code: {e.code}")
    print(f"  - Error message: {e.message}")
    print(f"  - RequestId: {e.requestId if hasattr(e, 'requestId') else 'N/A'}")

    # 根据错误代码提供具体建议
    print("\nPossible causes and solutions:")

    if "SecretId" in e.message:
        print("""
1. Sub-account sf2025 API key may not be correctly created or is disabled
   - Solution: Visit https://console.cloud.tencent.com/cam/capi
   - Confirm sf2025 API key status is "Enabled"

2. Permission assignment may not have taken effect (needs 5-10 minutes)
   - Solution: Wait 10 minutes and retry
   - Confirm QcloudTMSFullAccess policy is correctly associated with sf2025

3. Content Safety service not activated
   - Solution: Visit https://console.cloud.tencent.com/cms/text/overview
   - Confirm service status is "Activated"
   - If showing "Not activated", main account needs to activate first

4. Sub-account may not be able to use Content Safety service (some services have restrictions)
   - Temporary solution: Test with main account API key
   - If main account works, it's a sub-account permission issue
        """)
    elif "permission" in e.message.lower():
        print("""
Permission insufficient:
1. Confirm QcloudTMSFullAccess policy is associated with sf2025
2. Wait for permission to take effect (5-10 minutes)
3. Check if policy is correctly associated (check in CAM console)
        """)
    else:
        print(f"""
Other errors:
- Error code: {e.code}
- Error message: {e.message}
- Suggestion: Check Tencent Cloud official documentation or contact technical support
        """)

    sys.exit(1)

except Exception as e:
    print(f"\n[ERROR] API call failed - Unknown error")
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {str(e)}")
    sys.exit(1)

print("\n" + "=" * 80)
print("[OK] Diagnostic complete - All tests passed!")
print("=" * 80)
