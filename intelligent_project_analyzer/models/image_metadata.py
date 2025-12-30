"""
图片元数据模型

定义概念图的元数据结构，支持文件系统存储和URL引用。

Author: Claude Code
Created: 2025-12-29
Version: v1.0
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ImageMetadata(BaseModel):
    """
    概念图元数据模型（文件系统存储模式）

    用于存储概念图的元数据信息，支持从Base64 Data URL迁移到文件系统存储。
    """

    deliverable_id: str = Field(
        ...,
        description="关联的交付物ID，如 '2-1_1_143022_abc'"
    )

    filename: str = Field(
        ...,
        description="图片文件名，如 '2-1_1_143022_abc_interior_20251229_143045.png'"
    )

    url: str = Field(
        ...,
        description="图片访问URL，如 '/generated_images/session_id/2-1_1_143022_abc.png'"
    )

    owner_role: str = Field(
        ...,
        description="生成该图片的角色ID，如 '2-1', '3-1'"
    )

    prompt: str = Field(
        ...,
        description="用于生成图片的视觉提示词（英文），如 'Modern minimalist living room...'"
    )

    aspect_ratio: str = Field(
        default="16:9",
        description="图片宽高比：16:9（横向）, 9:16（纵向）, 1:1（正方形）"
    )

    file_size_bytes: Optional[int] = Field(
        default=None,
        description="文件大小（字节）"
    )

    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="创建时间（ISO 8601格式）"
    )

    # 🔄 向后兼容字段（可选）
    base64_data: Optional[str] = Field(
        default=None,
        description="Base64 Data URL（已废弃，仅用于向后兼容）。新系统使用文件存储 + URL引用"
    )

    class Config:
        """Pydantic配置"""
        # 允许从字典创建实例
        from_attributes = True
        # JSON序列化示例
        json_schema_extra = {
            "example": {
                "deliverable_id": "2-1_1_143022_abc",
                "filename": "2-1_1_143022_abc_interior_20251229_143045.png",
                "url": "/generated_images/api-20251229-xxxxx/2-1_1_143022_abc_interior_20251229_143045.png",
                "owner_role": "2-1",
                "prompt": "Modern minimalist living room with natural light, warm wood furniture, neutral earth tones, professional interior rendering, photorealistic",
                "aspect_ratio": "16:9",
                "file_size_bytes": 2458967,
                "created_at": "2025-12-29T14:30:45"
            }
        }
