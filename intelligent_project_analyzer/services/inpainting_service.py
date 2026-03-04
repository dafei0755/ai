"""
图像编辑/Inpainting服务

使用 OpenAI DALL-E 2 Edit API 实现像素级精确编辑
支持基于Mask的区域编辑，自动保留未编辑区域

Version: v7.62
Author: AI Assistant
Date: 2025-12-19
"""

import asyncio
import base64
import io
import logging

from PIL import Image
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# 尝试导入 OpenAI SDK
try:
    from openai import AsyncOpenAI, OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("️ OpenAI SDK 未安装，Inpainting 功能将不可用。请运行: pip install openai>=1.0.0")
    OPENAI_AVAILABLE = False


class InpaintingResult(BaseModel):
    """图像编辑结果"""
    success: bool = Field(description="是否编辑成功")
    edited_image_url: str | None = Field(default=None, description="编辑后图像URL")
    edited_image_data: str | None = Field(default=None, description="编辑后图像Base64数据")
    original_prompt: str | None = Field(default=None, description="使用的提示词")
    model_used: str | None = Field(default=None, description="使用的模型")
    error: str | None = Field(default=None, description="错误信息")
    fallback_used: bool = Field(default=False, description="是否使用了降级方案")


class InpaintingService:
    """
    图像编辑服务 - DALL-E 2 Edit API
    
    核心功能：
    - 接收原始图像 + Mask图像 + 文本提示词
    - 调用 OpenAI DALL-E 2 Edit API
    - 返回编辑后的图像（保留未Mask区域）
    
    Mask格式要求：
    - PNG图像
    - 黑色区域 = 保留不变
    - 透明区域 = 编辑此区域
    - 必须与原图尺寸相同
    
    降级策略：
    - 无 OPENAI_API_KEY → 返回错误提示
    - API调用失败 → 回退到Vision+生成（方案C）
    """
    
    DEFAULT_MODEL = "dall-e-2"  # DALL-E 2 支持 Edit
    SUPPORTED_SIZES = ["256x256", "512x512", "1024x1024"]
    MAX_FILE_SIZE_MB = 4  # OpenAI限制
    
    def __init__(self, api_key: str | None = None, timeout: int = 120):
        """
        初始化 Inpainting 服务
        
        Args:
            api_key: OpenAI API Key（必需）
            timeout: API超时时间（秒）
        """
        self.api_key = api_key
        self.timeout = timeout
        
        # 检查 API Key
        if not api_key:
            logger.warning("️ 未提供 OPENAI_API_KEY，Inpainting 功能将不可用")
            self.client = None
            self.async_client = None
        elif not OPENAI_AVAILABLE:
            logger.error(" OpenAI SDK 未安装，无法使用 Inpainting 功能")
            self.client = None
            self.async_client = None
        else:
            try:
                self.client = OpenAI(api_key=api_key, timeout=timeout)
                self.async_client = AsyncOpenAI(api_key=api_key, timeout=timeout)
                logger.info(" InpaintingService 初始化成功")
            except Exception as e:
                logger.error(f" InpaintingService 初始化失败: {e}")
                self.client = None
                self.async_client = None
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.client is not None and self.async_client is not None
    
    def _validate_and_convert_image(
        self, 
        image_data: str, 
        image_type: str = "original"
    ) -> io.BytesIO | None:
        """
        验证并转换图像为BytesIO对象
        
        Args:
            image_data: Base64编码的图像数据 或 URL
            image_type: 图像类型（"original" 或 "mask"）
        
        Returns:
            BytesIO对象，失败返回None
        """
        try:
            # 1. 检测是URL还是Base64
            if image_data.startswith('http://') or image_data.startswith('https://'):
                logger.error(" 暂不支持URL格式图像，请使用Base64")
                return None
            
            # 2. 解码Base64
            # 移除可能的前缀（如 "data:image/png;base64,"）
            if ',' in image_data:
                image_data = image_data.split(',', 1)[1]
            
            image_bytes = base64.b64decode(image_data)
            
            # 3. 验证文件大小
            size_mb = len(image_bytes) / (1024 * 1024)
            if size_mb > self.MAX_FILE_SIZE_MB:
                logger.error(f" {image_type} 图像过大: {size_mb:.2f}MB > {self.MAX_FILE_SIZE_MB}MB")
                return None
            
            # 4. 验证是否为有效图像
            img = Image.open(io.BytesIO(image_bytes))
            
            # 5. 转换为PNG格式（OpenAI要求）
            if img.mode not in ('RGB', 'RGBA'):
                if image_type == "mask":
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')
            
            # 6. 保存到BytesIO
            output = io.BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            
            logger.info(f" {image_type} 图像验证成功: {img.size}, {img.mode}, {size_mb:.2f}MB")
            return output
            
        except Exception as e:
            logger.error(f" {image_type} 图像验证失败: {e}")
            return None
    
    def _validate_mask(self, mask_bytes: io.BytesIO, original_size: tuple) -> bool:
        """
        验证Mask图像格式
        
        Args:
            mask_bytes: Mask图像BytesIO
            original_size: 原始图像尺寸 (width, height)
        
        Returns:
            是否有效
        """
        try:
            mask_bytes.seek(0)
            mask_img = Image.open(mask_bytes)
            
            # 1. 检查尺寸是否匹配
            if mask_img.size != original_size:
                logger.error(f" Mask尺寸不匹配: {mask_img.size} != {original_size}")
                return False
            
            # 2. 检查是否有透明通道
            if mask_img.mode not in ('RGBA', 'LA', 'P'):
                logger.warning(f"️ Mask模式: {mask_img.mode}，建议使用RGBA")
            
            mask_bytes.seek(0)
            return True
            
        except Exception as e:
            logger.error(f" Mask验证失败: {e}")
            return False
    
    async def edit_image_with_mask(
        self,
        original_image: str,
        mask_image: str,
        prompt: str,
        size: str = "1024x1024",
        n: int = 1
    ) -> InpaintingResult:
        """
        使用Mask编辑图像（异步）
        
        Args:
            original_image: 原始图像Base64
            mask_image: Mask图像Base64（黑色=保留，透明=编辑）
            prompt: 文本提示词，描述如何编辑
            size: 输出尺寸（256x256, 512x512, 1024x1024）
            n: 生成数量（默认1）
        
        Returns:
            InpaintingResult 对象
        """
        logger.info(" [v7.62 Inpainting] 开始图像编辑")
        logger.info(f"   提示词: {prompt[:100]}...")
        logger.info(f"   尺寸: {size}, 数量: {n}")
        
        # 1. 检查服务可用性
        if not self.is_available():
            error_msg = "Inpainting服务不可用：未配置OPENAI_API_KEY或SDK未安装"
            logger.error(f" {error_msg}")
            return InpaintingResult(
                success=False,
                error=error_msg,
                fallback_used=False
            )
        
        # 2. 验证尺寸
        if size not in self.SUPPORTED_SIZES:
            logger.warning(f"️ 不支持的尺寸 {size}，使用默认 1024x1024")
            size = "1024x1024"
        
        try:
            # 3. 转换原始图像
            logger.info(" 转换原始图像...")
            original_bytes = self._validate_and_convert_image(original_image, "original")
            if not original_bytes:
                return InpaintingResult(
                    success=False,
                    error="原始图像验证失败",
                    fallback_used=False
                )
            
            # 获取原图尺寸
            original_bytes.seek(0)
            original_img = Image.open(original_bytes)
            original_size = original_img.size
            original_bytes.seek(0)
            
            # 4. 转换Mask图像
            logger.info(" 转换Mask图像...")
            mask_bytes = self._validate_and_convert_image(mask_image, "mask")
            if not mask_bytes:
                return InpaintingResult(
                    success=False,
                    error="Mask图像验证失败",
                    fallback_used=False
                )
            
            # 5. 验证Mask
            if not self._validate_mask(mask_bytes, original_size):
                return InpaintingResult(
                    success=False,
                    error="Mask格式验证失败：尺寸不匹配或格式不正确",
                    fallback_used=False
                )
            
            # 6. 调用 OpenAI DALL-E 2 Edit API
            logger.info(" 调用 OpenAI DALL-E 2 Edit API...")
            
            response = await self.async_client.images.edit(
                image=original_bytes,
                mask=mask_bytes,
                prompt=prompt,
                n=n,
                size=size,
                response_format="url"  # 或 "b64_json"
            )
            
            # 7. 解析响应
            if response.data and len(response.data) > 0:
                edited_image_url = response.data[0].url
                
                logger.info(" [v7.62 Inpainting] 图像编辑成功")
                logger.info(f"   图像URL: {edited_image_url[:80]}...")
                
                return InpaintingResult(
                    success=True,
                    edited_image_url=edited_image_url,
                    original_prompt=prompt,
                    model_used=self.DEFAULT_MODEL,
                    fallback_used=False
                )
            else:
                logger.error(" API返回数据为空")
                return InpaintingResult(
                    success=False,
                    error="API返回数据为空",
                    fallback_used=False
                )
        
        except Exception as e:
            error_msg = f"Inpainting API调用失败: {str(e)}"
            logger.error(f" {error_msg}")
            return InpaintingResult(
                success=False,
                error=error_msg,
                fallback_used=False
            )
    
    def edit_image_with_mask_sync(
        self,
        original_image: str,
        mask_image: str,
        prompt: str,
        size: str = "1024x1024",
        n: int = 1
    ) -> InpaintingResult:
        """
        使用Mask编辑图像（同步版本）
        
        仅在无法使用async的环境中使用
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环已运行，创建新任务
                import nest_asyncio
                nest_asyncio.apply()
                return loop.run_until_complete(
                    self.edit_image_with_mask(original_image, mask_image, prompt, size, n)
                )
            else:
                # 创建新事件循环
                return asyncio.run(
                    self.edit_image_with_mask(original_image, mask_image, prompt, size, n)
                )
        except RuntimeError:
            # 如果仍然失败，使用新事件循环
            return asyncio.run(
                self.edit_image_with_mask(original_image, mask_image, prompt, size, n)
            )


# 全局单例（可选）
_inpainting_service_instance: InpaintingService | None = None


def get_inpainting_service(api_key: str | None = None) -> InpaintingService:
    """
    获取 InpaintingService 单例
    
    Args:
        api_key: OpenAI API Key（首次调用时必需）
    
    Returns:
        InpaintingService 实例
    """
    global _inpainting_service_instance
    
    if _inpainting_service_instance is None:
        if not api_key:
            logger.warning("️ 首次调用需提供 api_key")
            return InpaintingService(api_key=None)  # 返回不可用实例
        
        _inpainting_service_instance = InpaintingService(api_key=api_key)
    
    return _inpainting_service_instance
