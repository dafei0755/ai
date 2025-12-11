"""
腾讯云内容安全API客户端
文档: https://cloud.tencent.com/document/product/1124
"""

import os
import json
import base64
from typing import Dict, Any, List, Optional
from loguru import logger

try:
    from tencentcloud.common import credential
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    from tencentcloud.tms.v20201229 import tms_client, models
except ImportError:
    logger.warning("⚠️ 腾讯云SDK未安装，内容安全功能将不可用")
    tms_client = None


class TencentContentSafetyClient:
    """腾讯云内容安全客户端"""

    def __init__(
        self,
        secret_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = "ap-guangzhou",
        timeout: int = 5
    ):
        """
        初始化腾讯云内容安全客户端

        Args:
            secret_id: 腾讯云SecretId（从环境变量读取）
            secret_key: 腾讯云SecretKey（从环境变量读取）
            region: 服务地域，默认ap-guangzhou
            timeout: 超时时间（秒）
        """
        if tms_client is None:
            raise ImportError("请先安装腾讯云SDK: pip install tencentcloud-sdk-python")

        self.secret_id = secret_id or os.getenv("TENCENT_CLOUD_SECRET_ID")
        self.secret_key = secret_key or os.getenv("TENCENT_CLOUD_SECRET_KEY")
        self.region = region or os.getenv("TENCENT_CLOUD_REGION", "ap-guangzhou")

        if not self.secret_id or not self.secret_key:
            raise ValueError("缺少腾讯云API密钥，请配置TENCENT_CLOUD_SECRET_ID和TENCENT_CLOUD_SECRET_KEY")

        # 初始化认证对象
        self.cred = credential.Credential(self.secret_id, self.secret_key)

        # 初始化HTTP配置
        httpProfile = HttpProfile()
        httpProfile.endpoint = "tms.tencentcloudapi.com"
        httpProfile.reqTimeout = timeout

        # 初始化客户端配置
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        # 创建客户端
        self.client = tms_client.TmsClient(self.cred, self.region, clientProfile)

        logger.info(f"✅ 腾讯云内容安全客户端初始化成功 (Region: {self.region})")

    def check_text(
        self,
        text: str,
        biz_type: str = "txt",
        user_id: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        文本内容安全检测

        Args:
            text: 待检测文本内容
            biz_type: 业务类型（BizType），默认txt
            user_id: 用户ID（可选，用于识别用户）
            device_id: 设备ID（可选，用于识别设备）

        Returns:
            {
                "is_safe": bool,
                "risk_level": "safe" | "low" | "medium" | "high",
                "violations": List[Dict],
                "suggestion": "Pass" | "Review" | "Block",
                "label": str,  # 违规标签
                "score": int,  # 置信度分数 0-100
                "keywords": List[str],  # 命中的关键词
                "raw_response": Dict  # 原始响应
            }
        """
        try:
            # 创建请求对象
            req = models.TextModerationRequest()

            # 文本内容需要Base64编码
            text_bytes = text.encode('utf-8')
            text_base64 = base64.b64encode(text_bytes).decode('utf-8')

            # 基本参数
            req.Content = text_base64
            req.BizType = biz_type or os.getenv("TENCENT_CONTENT_SAFETY_BIZTYPE_TEXT", "txt")

            # 可选参数
            if user_id:
                req.User = models.User()
                req.User.UserId = user_id

            if device_id:
                req.Device = models.Device()
                req.Device.DeviceId = device_id

            # 调用API
            resp = self.client.TextModeration(req)
            resp_dict = json.loads(resp.to_json_string())

            # 解析响应
            suggestion = resp_dict.get("Suggestion", "Pass")
            label = resp_dict.get("Label", "Normal")
            score = resp_dict.get("Score", 0)
            keywords = resp_dict.get("Keywords", [])

            # 判断安全性
            is_safe = suggestion == "Pass"

            # 判断风险等级
            if suggestion == "Pass":
                risk_level = "safe"
            elif suggestion == "Review":
                risk_level = "low" if score < 50 else "medium"
            else:  # Block
                risk_level = "high"

            # 构建违规信息
            violations = []
            if not is_safe:
                violations.append({
                    "category": self._label_to_category(label),
                    "label": label,
                    "score": score,
                    "keywords": keywords,
                    "severity": "high" if suggestion == "Block" else "medium",
                    "method": "tencent_cloud_api"
                })

            return {
                "is_safe": is_safe,
                "risk_level": risk_level,
                "violations": violations,
                "suggestion": suggestion,
                "label": label,
                "score": score,
                "keywords": keywords,
                "raw_response": resp_dict
            }

        except TencentCloudSDKException as e:
            logger.error(f"❌ 腾讯云内容安全API调用失败: {e.get_message()}")
            # 返回安全（避免误拦截）
            return {
                "is_safe": True,
                "risk_level": "safe",
                "violations": [],
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"❌ 腾讯云内容安全检测异常: {e}")
            return {
                "is_safe": True,
                "risk_level": "safe",
                "violations": [],
                "error": str(e)
            }

    def _label_to_category(self, label: str) -> str:
        """将腾讯云标签转换为内部分类"""
        label_map = {
            "Normal": "正常内容",
            "Porn": "色情低俗",
            "Abuse": "谩骂",
            "Ad": "广告",
            "Illegal": "违法犯罪",
            "Moan": "娇喘",
            "Terror": "暴恐",
            "Politics": "政治敏感",
            "Contraband": "违禁品",
            "Custom": "自定义违规"
        }
        return label_map.get(label, label)

    def batch_check_text(self, texts: List[str], biz_type: str = "txt") -> List[Dict[str, Any]]:
        """
        批量文本内容安全检测

        Args:
            texts: 待检测文本列表
            biz_type: 业务类型

        Returns:
            检测结果列表
        """
        results = []
        for text in texts:
            result = self.check_text(text, biz_type)
            results.append(result)
        return results


# 全局单例（懒加载）
_client_instance: Optional[TencentContentSafetyClient] = None


def get_tencent_content_safety_client() -> Optional[TencentContentSafetyClient]:
    """获取腾讯云内容安全客户端单例"""
    global _client_instance

    # 检查是否启用
    if not os.getenv("ENABLE_TENCENT_CONTENT_SAFETY", "false").lower() == "true":
        return None

    if _client_instance is None:
        try:
            _client_instance = TencentContentSafetyClient()
        except Exception as e:
            logger.warning(f"⚠️ 腾讯云内容安全客户端初始化失败: {e}")
            return None

    return _client_instance
