"""配置管理 API"""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from ..auth_middleware import require_admin
from ...utils.config_manager import config_manager

router = APIRouter()


@router.get("/config/current")
async def get_current_config(admin: dict = Depends(require_admin)):
    """
    获取当前配置（脱敏）

    不返回敏感信息（API Key、密码等）
    """
    try:
        sanitized_config = config_manager.get_sanitized_config()
        return {"config": sanitized_config, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f" 获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/reload")
async def reload_config(admin: dict = Depends(require_admin)):
    """
    手动触发配置重载

    重新加载 .env 文件和配置对象
    """
    try:
        success = config_manager.reload()

        if success:
            logger.info(f" 管理员 {admin.get('username')} 触发配置重载")
            return {"status": "success", "message": "配置已重载", "timestamp": datetime.now().isoformat()}
        else:
            raise HTTPException(status_code=500, detail="配置重载失败")

    except Exception as e:
        logger.error(f" 配置重载失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/env")
async def get_env_content(admin: dict = Depends(require_admin)):
    """
    获取 .env 文件内容（脱敏）

    用于配置编辑器展示
    """
    try:
        env_path = Path(__file__).parent.parent.parent.parent / ".env"

        if not env_path.exists():
            raise HTTPException(status_code=404, detail=".env 文件不存在")

        with open(env_path, encoding="utf-8") as f:
            content = f.read()

        # 脱敏处理：隐藏敏感值
        lines = []
        for line in content.split("\n"):
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                # 隐藏 API Key、密码等敏感信息
                if any(sensitive in key.upper() for sensitive in ["KEY", "SECRET", "PASSWORD", "TOKEN"]):
                    lines.append(f"{key}=***HIDDEN***")
                else:
                    lines.append(line)
            else:
                lines.append(line)

        return {"content": "\n".join(lines), "file_path": str(env_path), "timestamp": datetime.now().isoformat()}

    except Exception as e:
        logger.error(f" 读取 .env 文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
