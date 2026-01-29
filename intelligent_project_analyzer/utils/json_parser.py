"""
🆕 P1修复: 统一JSON解析器

提供容错的JSON提取和解析，支持：
1. Markdown代码块截取 (```json ... ```)
2. 多种引号格式修复
3. Pydantic模型验证与默认值回填
4. 降级策略
"""

import json
import re
from typing import Any, Dict, List, Optional, Type, TypeVar

from loguru import logger
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def extract_json_from_markdown(text: str) -> str:
    """
    从Markdown代码块中提取JSON

    支持格式:
    - ```json {...} ```
    - ``` {...} ```
    - {...} (裸JSON)

    Args:
        text: 原始文本

    Returns:
        提取的JSON字符串
    """
    text = text.strip()

    # 1. 尝试提取```json代码块
    json_block_pattern = r"```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```"
    match = re.search(json_block_pattern, text, re.DOTALL)
    if match:
        logger.debug("✂️ 从Markdown代码块中提取JSON")
        return match.group(1).strip()

    # 2. 尝试找到第一个完整的[]或{}
    json_arr_pattern = r"\[[\s\S]*\]"
    match = re.search(json_arr_pattern, text, re.DOTALL)
    if match:
        logger.debug("✂️ 从文本中提取JSON数组")
        return match.group(0).strip()

    json_obj_pattern = r"\{[\s\S]*\}"
    match = re.search(json_obj_pattern, text, re.DOTALL)
    if match:
        logger.debug("✂️ 从文本中提取JSON对象")
        return match.group(0).strip()

    # 3. 原样返回
    return text


def fix_json_quotes(text: str) -> str:
    """将常见的全角/花体引号规范化为标准ASCII引号"""

    if not text:
        return text

    replacements = {
        "“": '"',
        "”": '"',
        "„": '"',
        "‟": '"',
        "«": '"',
        "»": '"',
        "‚": "'",
        "‘": "'",
        "’": "'",
        "‛": "'",
    }

    for src, dst in replacements.items():
        text = text.replace(src, dst)

    return text


def parse_json_safe(
    text: str, *, extract_from_markdown: bool = True, fix_quotes: bool = True, default: Any = None
) -> Optional[Dict[str, Any]]:
    """
    🆕 P1修复: 安全解析JSON，支持多种容错策略

    Args:
        text: JSON字符串或包含JSON的文本
        extract_from_markdown: 是否从Markdown代码块中提取
        fix_quotes: 是否修复引号问题
        default: 解析失败时的默认值

    Returns:
        解析后的字典，失败返回default
    """
    if not text or not isinstance(text, str):
        logger.warning(f"⚠️ JSON解析输入无效: {type(text)}")
        return default

    # 1. 提取JSON
    if extract_from_markdown:
        text = extract_json_from_markdown(text)

    # 2. 修复引号
    if fix_quotes:
        text = fix_json_quotes(text)

    # 3. 尝试解析
    try:
        result = json.loads(text)
        logger.debug("✅ JSON解析成功")
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ JSON解析失败: {e}")
        logger.debug(f"原始文本: {text[:200]}...")
        return default

    except Exception as e:
        logger.error(f"❌ JSON解析异常: {e}")
        return default


def parse_json_to_model(
    text: str,
    model: Type[T],
    *,
    extract_from_markdown: bool = True,
    fix_quotes: bool = True,
    fill_defaults: bool = True,
) -> Optional[T]:
    """
    🆕 P1修复: 解析JSON并验证为Pydantic模型

    Args:
        text: JSON字符串
        model: Pydantic模型类
        extract_from_markdown: 是否从Markdown提取
        fix_quotes: 是否修复引号
        fill_defaults: 验证失败时是否尝试用默认值填充

    Returns:
        模型实例，失败返回None
    """
    # 1. 解析JSON
    data = parse_json_safe(text, extract_from_markdown=extract_from_markdown, fix_quotes=fix_quotes, default=None)

    if data is None:
        logger.error(f"❌ JSON解析失败，无法创建{model.__name__}模型")
        return None

    # 2. 验证模型
    try:
        instance = model.model_validate(data)
        logger.debug(f"✅ {model.__name__}模型验证成功")
        return instance

    except ValidationError as e:
        logger.warning(f"⚠️ Pydantic验证失败: {e}")

        # 3. 尝试用默认值填充
        if fill_defaults:
            logger.info("🔄 尝试使用默认值填充缺失字段...")
            try:
                # 获取模型字段定义
                filled_data = {}
                for field_name, field_info in model.model_fields.items():
                    if field_name in data:
                        filled_data[field_name] = data[field_name]
                    elif field_info.default is not None:
                        filled_data[field_name] = field_info.default
                        logger.debug(f"📝 填充默认值: {field_name} = {field_info.default}")
                    elif field_info.default_factory is not None:
                        filled_data[field_name] = field_info.default_factory()
                        logger.debug(f"📝 填充工厂默认值: {field_name}")
                    else:
                        # 必填字段但缺失
                        logger.warning(f"⚠️ 必填字段缺失且无默认值: {field_name}")

                # 重新验证
                instance = model.model_validate(filled_data)
                logger.success(f"✅ {model.__name__}模型验证成功（已填充默认值）")
                return instance

            except Exception as fill_error:
                logger.error(f"❌ 默认值填充失败: {fill_error}")
                return None

        return None

    except Exception as e:
        logger.error(f"❌ 模型验证异常: {e}")
        return None


def parse_json_list(
    text: str, *, extract_from_markdown: bool = True, fix_quotes: bool = True, default: Optional[List] = None
) -> List[Any]:
    """
    🆕 P1修复: 解析JSON数组

    Args:
        text: JSON字符串
        extract_from_markdown: 是否从Markdown提取
        fix_quotes: 是否修复引号
        default: 解析失败时的默认值

    Returns:
        列表，失败返回default或空列表
    """
    result = parse_json_safe(text, extract_from_markdown=extract_from_markdown, fix_quotes=fix_quotes, default=default)

    if result is None:
        return default if default is not None else []

    if not isinstance(result, list):
        logger.warning(f"⚠️ 期望JSON数组，实际得到: {type(result)}")
        return default if default is not None else []

    return result


# 向后兼容的别名
extract_json = extract_json_from_markdown
safe_json_loads = parse_json_safe
