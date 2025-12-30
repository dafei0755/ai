"""
图片存储管理器 - 文件系统存储

负责将概念图保存到文件系统，并维护metadata.json索引。

Author: Claude Code
Created: 2025-12-29
Version: v1.0
"""

import os
import json
import base64
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from loguru import logger


class ImageStorageManager:
    """
    概念图文件存储管理器

    负责：
    1. 保存图片文件到 data/generated_images/{session_id}/
    2. 维护 metadata.json 索引
    3. 删除和查询图片
    """

    BASE_DIR = Path("data/generated_images")

    @classmethod
    async def save_image(
        cls,
        base64_data: str,
        session_id: str,
        deliverable_id: str,
        owner_role: str,
        filename: str,
        visual_prompt: str,
        aspect_ratio: str = "16:9"
    ) -> dict:
        """
        保存图片到文件系统并更新索引

        Args:
            base64_data: Base64编码的图片数据（Data URL格式）
            session_id: 会话ID
            deliverable_id: 交付物ID
            owner_role: 角色ID
            filename: 文件名
            visual_prompt: 生成图片的提示词
            aspect_ratio: 宽高比

        Returns:
            图片元数据字典
        """
        try:
            # 1. 创建会话目录
            session_dir = cls.BASE_DIR / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            # 2. 解码Base64数据
            if "," in base64_data:
                # 格式: data:image/png;base64,iVBORw0KGgo...
                image_bytes = base64.b64decode(base64_data.split(",")[1])
            else:
                # 纯Base64
                image_bytes = base64.b64decode(base64_data)

            # 3. 保存图片文件
            file_path = session_dir / filename
            with open(file_path, "wb") as f:
                f.write(image_bytes)

            # 4. 构建元数据
            file_size = len(image_bytes)
            url = f"/generated_images/{session_id}/{filename}"

            metadata = {
                "deliverable_id": deliverable_id,
                "filename": filename,
                "url": url,
                "owner_role": owner_role,
                "prompt": visual_prompt,
                "aspect_ratio": aspect_ratio,
                "file_size_bytes": file_size,
                "created_at": datetime.now().isoformat()
            }

            # 5. 更新metadata.json索引
            await cls._update_metadata_index(session_id, metadata)

            logger.info(f"✅ [ImageStorage] 保存图片: {filename} ({file_size} bytes)")
            return metadata

        except Exception as e:
            logger.error(f"❌ [ImageStorage] 保存图片失败: {e}")
            raise

    @classmethod
    async def _update_metadata_index(cls, session_id: str, new_image: dict):
        """更新metadata.json索引文件"""
        index_path = cls.BASE_DIR / session_id / "metadata.json"

        # 加载现有索引
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
        else:
            index_data = {
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "images": []
            }

        # 追加新图片
        index_data["images"].append(new_image)
        index_data["updated_at"] = datetime.now().isoformat()

        # 保存索引
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

    @classmethod
    async def get_session_images(cls, session_id: str) -> List[dict]:
        """获取会话的所有图片元数据"""
        index_path = cls.BASE_DIR / session_id / "metadata.json"

        if not index_path.exists():
            return []

        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        return index_data.get("images", [])

    @classmethod
    async def delete_image(cls, session_id: str, deliverable_id: str) -> bool:
        """删除指定交付物的概念图"""
        try:
            images = await cls.get_session_images(session_id)
            target_image = next((img for img in images if img["deliverable_id"] == deliverable_id), None)

            if not target_image:
                logger.warning(f"⚠️ [ImageStorage] 图片不存在: {deliverable_id}")
                return False

            # 删除文件
            file_path = cls.BASE_DIR / session_id / target_image["filename"]
            if file_path.exists():
                file_path.unlink()
                logger.info(f"✅ [ImageStorage] 删除文件: {target_image['filename']}")

            # 更新索引
            index_path = cls.BASE_DIR / session_id / "metadata.json"
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)

            index_data["images"] = [img for img in index_data["images"] if img["deliverable_id"] != deliverable_id]
            index_data["updated_at"] = datetime.now().isoformat()

            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            logger.error(f"❌ [ImageStorage] 删除图片失败: {e}")
            return False
