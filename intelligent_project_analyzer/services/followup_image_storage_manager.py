"""
追问图片存储管理器 - 永久保存追问对话中的图片

负责：
1. 保存追问对话中的图片到 data/followup_images/{session_id}/
2. 生成缩略图（400px，JPEG 80%）
3. 维护 metadata.json 索引
4. 支持 Vision API 分析（可选）

Author: Claude Code
Created: 2025-12-30
Version: v7.108
"""

import io
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from PIL import Image
from fastapi import UploadFile


class FollowupImageStorageManager:
    """
    追问图片永久存储管理器

    与 ImageStorageManager 类似，但专门用于追问对话中的图片。
    图片不受 Redis Session TTL (72h) 影响，永久保存。
    """

    BASE_DIR = Path("data/followup_images")
    THUMBNAIL_MAX_SIZE = 400  # 缩略图最大边长（像素）
    THUMBNAIL_QUALITY = 80    # JPEG 压缩质量

    @classmethod
    async def save_image(
        cls,
        image_file: UploadFile,
        session_id: str,
        turn_id: int
    ) -> Dict[str, Any]:
        """
        保存追问图片到文件系统（原图 + 缩略图）

        Args:
            image_file: FastAPI UploadFile 对象
            session_id: 会话ID
            turn_id: 对话轮次ID

        Returns:
            图片元数据字典：
            {
                "type": "image",
                "original_filename": str,
                "stored_filename": str,
                "thumbnail_filename": str,
                "url": str,
                "thumbnail_url": str,
                "width": int,
                "height": int,
                "format": str,
                "file_size_bytes": int,
                "upload_timestamp": str
            }

        Raises:
            Exception: 文件保存失败时抛出
        """
        try:
            # 1. 读取图片数据
            image_bytes = await image_file.read()
            img = Image.open(io.BytesIO(image_bytes))

            # 2. 提取图片元信息
            width, height = img.size
            format_name = img.format or "JPEG"  # 默认JPEG
            file_size = len(image_bytes)

            # 3. 生成文件名（防止冲突）
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            ext = cls._get_file_extension(image_file.filename, format_name)
            stored_filename = f"{turn_id}_original_{timestamp}.{ext}"
            thumb_filename = f"{turn_id}_thumb_{timestamp}.jpg"

            # 4. 创建会话目录
            session_dir = cls.BASE_DIR / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            # 5. 保存原图
            original_path = session_dir / stored_filename
            with open(original_path, "wb") as f:
                f.write(image_bytes)

            logger.info(f"✅ [FollowupImage] 保存原图: {stored_filename} ({file_size} bytes, {width}x{height})")

            # 6. 生成并保存缩略图
            thumbnail = cls._generate_thumbnail(img)
            thumb_path = session_dir / thumb_filename
            thumbnail.save(thumb_path, "JPEG", quality=cls.THUMBNAIL_QUALITY)

            thumb_size = thumb_path.stat().st_size
            logger.info(f"✅ [FollowupImage] 生成缩略图: {thumb_filename} ({thumb_size} bytes)")

            # 7. 构建元数据
            metadata = {
                "type": "image",
                "original_filename": image_file.filename,
                "stored_filename": stored_filename,
                "thumbnail_filename": thumb_filename,
                "url": f"/followup_images/{session_id}/{stored_filename}",
                "thumbnail_url": f"/followup_images/{session_id}/{thumb_filename}",
                "width": width,
                "height": height,
                "format": format_name,
                "file_size_bytes": file_size,
                "upload_timestamp": datetime.now().isoformat()
            }

            # 8. 更新索引文件
            await cls._update_metadata_index(session_id, turn_id, metadata)

            return metadata

        except Exception as e:
            logger.error(f"❌ [FollowupImage] 保存图片失败: {e}")
            raise

    @staticmethod
    def _generate_thumbnail(img: Image.Image) -> Image.Image:
        """
        生成缩略图（保持宽高比）

        Args:
            img: PIL Image 对象

        Returns:
            缩略图 Image 对象
        """
        # 创建副本（避免修改原图）
        img_copy = img.copy()

        # 转换为 RGB 模式（确保可保存为 JPEG）
        if img_copy.mode in ('RGBA', 'LA', 'P'):
            # 创建白色背景
            background = Image.new('RGB', img_copy.size, (255, 255, 255))
            if img_copy.mode == 'P':
                img_copy = img_copy.convert('RGBA')
            background.paste(img_copy, mask=img_copy.split()[-1] if img_copy.mode in ('RGBA', 'LA') else None)
            img_copy = background
        elif img_copy.mode != 'RGB':
            img_copy = img_copy.convert('RGB')

        # 使用 thumbnail 方法保持宽高比
        img_copy.thumbnail((FollowupImageStorageManager.THUMBNAIL_MAX_SIZE,
                           FollowupImageStorageManager.THUMBNAIL_MAX_SIZE),
                          Image.Resampling.LANCZOS)

        return img_copy

    @staticmethod
    def _get_file_extension(filename: str, format_name: str) -> str:
        """
        从文件名或格式获取扩展名

        Args:
            filename: 原始文件名
            format_name: PIL 格式名（如 "JPEG", "PNG"）

        Returns:
            文件扩展名（不含点）
        """
        # 优先从文件名提取
        if filename and '.' in filename:
            ext = filename.rsplit('.', 1)[-1].lower()
            if ext in ('jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'):
                return ext

        # 从格式名映射
        format_map = {
            'JPEG': 'jpg',
            'PNG': 'png',
            'GIF': 'gif',
            'BMP': 'bmp',
            'WEBP': 'webp'
        }
        return format_map.get(format_name, 'jpg')

    @classmethod
    async def _update_metadata_index(
        cls,
        session_id: str,
        turn_id: int,
        image_metadata: Dict[str, Any]
    ):
        """
        更新 metadata.json 索引文件

        Args:
            session_id: 会话ID
            turn_id: 对话轮次ID
            image_metadata: 图片元数据
        """
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

        # 追加新图片（包含 turn_id）
        image_entry = {
            "turn_id": turn_id,
            **image_metadata
        }
        index_data["images"].append(image_entry)
        index_data["updated_at"] = datetime.now().isoformat()

        # 保存索引
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ [FollowupImage] 更新索引: {index_path}")

    @classmethod
    async def get_session_images(cls, session_id: str) -> list[Dict[str, Any]]:
        """
        获取会话的所有追问图片元数据

        Args:
            session_id: 会话ID

        Returns:
            图片元数据列表
        """
        index_path = cls.BASE_DIR / session_id / "metadata.json"

        if not index_path.exists():
            return []

        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        return index_data.get("images", [])

    @classmethod
    async def delete_turn_images(cls, session_id: str, turn_id: int) -> bool:
        """
        删除指定轮次的图片（原图 + 缩略图）

        Args:
            session_id: 会话ID
            turn_id: 对话轮次ID

        Returns:
            删除是否成功
        """
        try:
            images = await cls.get_session_images(session_id)
            target_images = [img for img in images if img.get("turn_id") == turn_id]

            if not target_images:
                logger.warning(f"⚠️ [FollowupImage] 未找到 turn_id={turn_id} 的图片")
                return False

            # 删除文件
            session_dir = cls.BASE_DIR / session_id
            for image in target_images:
                # 删除原图
                original_path = session_dir / image["stored_filename"]
                if original_path.exists():
                    original_path.unlink()
                    logger.info(f"✅ [FollowupImage] 删除原图: {image['stored_filename']}")

                # 删除缩略图
                thumb_path = session_dir / image["thumbnail_filename"]
                if thumb_path.exists():
                    thumb_path.unlink()
                    logger.info(f"✅ [FollowupImage] 删除缩略图: {image['thumbnail_filename']}")

            # 更新索引
            index_path = session_dir / "metadata.json"
            if index_path.exists():
                with open(index_path, "r", encoding="utf-8") as f:
                    index_data = json.load(f)

                index_data["images"] = [img for img in index_data["images"] if img.get("turn_id") != turn_id]
                index_data["updated_at"] = datetime.now().isoformat()

                with open(index_path, "w", encoding="utf-8") as f:
                    json.dump(index_data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            logger.error(f"❌ [FollowupImage] 删除图片失败: {e}")
            return False
