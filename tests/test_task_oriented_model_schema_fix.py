"""
测试任务导向模型Schema修复（v7.18.1）

验证 DeliverableOutput.content 字段的schema定义修复后：
1. 能够正确生成OpenAI兼容的JSON Schema
2. 能够通过结构化输出API验证
3. validator能够正确序列化dict和list为JSON字符串

日期: 2025-12-17
版本: v7.18.1
"""

import json
import sys
from typing import Any, Dict

# Windows终端UTF-8编码修复
if sys.platform == "win32":
    # Avoid replacing sys.stdout/sys.stderr with new wrappers: pytest (and loggers) may
    # later close the wrapper and accidentally close the underlying buffer.
    for _stream in (getattr(sys, "stdout", None), getattr(sys, "stderr", None)):
        if _stream is None:
            continue
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

from intelligent_project_analyzer.core.task_oriented_models import (
    CompletionStatus,
    DeliverableOutput,
    TaskOrientedExpertOutput,
)


def test_deliverable_output_schema():
    """测试1: 验证DeliverableOutput的JSON Schema生成"""
    print("🧪 测试1: 验证DeliverableOutput的JSON Schema")
    print("=" * 80)

    schema = DeliverableOutput.model_json_schema()

    # 验证content字段的类型定义
    content_schema = schema["properties"]["content"]

    print("✅ content字段schema:")
    print(f"   类型: {content_schema.get('type')}")
    print(f"   描述: {content_schema.get('description')}")

    # 关键验证：content必须是string类型（不能是anyOf）
    assert content_schema["type"] == "string", "❌ content必须是string类型"
    assert "anyOf" not in content_schema, "❌ content不应该包含anyOf"

    print("✅ 测试通过：content字段类型定义正确（纯string）")
    print()


def test_validator_with_dict():
    """测试2: 验证validator能够序列化dict为JSON字符串"""
    print("🧪 测试2: 验证validator能够序列化dict")
    print("=" * 80)

    # 创建包含dict的DeliverableOutput
    deliverable = DeliverableOutput(
        deliverable_name="测试交付物",
        content={"key1": "value1", "key2": ["item1", "item2"]},  # 传入dict
        completion_status=CompletionStatus.COMPLETED,
    )

    # 验证content已被序列化为JSON字符串
    print("✅ 原始输入: dict")
    print(f"✅ 序列化后类型: {type(deliverable.content)}")
    print(f"✅ 序列化后内容:\n{deliverable.content}")

    assert isinstance(deliverable.content, str), "❌ content应该被序列化为字符串"

    # 验证可以反序列化
    parsed = json.loads(deliverable.content)
    assert parsed["key1"] == "value1", "❌ 反序列化失败"

    print("✅ 测试通过：dict自动序列化为JSON字符串")
    print()


def test_validator_with_list():
    """测试3: 验证validator能够序列化list为JSON字符串"""
    print("🧪 测试3: 验证validator能够序列化list")
    print("=" * 80)

    # 创建包含list的DeliverableOutput
    deliverable = DeliverableOutput(
        deliverable_name="测试交付物",
        content=["item1", "item2", {"nested": "value"}],  # 传入list
        completion_status=CompletionStatus.COMPLETED,
    )

    # 验证content已被序列化为JSON字符串
    print("✅ 原始输入: list")
    print(f"✅ 序列化后类型: {type(deliverable.content)}")
    print(f"✅ 序列化后内容:\n{deliverable.content}")

    assert isinstance(deliverable.content, str), "❌ content应该被序列化为字符串"

    # 验证可以反序列化
    parsed = json.loads(deliverable.content)
    assert len(parsed) == 3, "❌ 反序列化失败"

    print("✅ 测试通过：list自动序列化为JSON字符串")
    print()


def test_full_expert_output_schema():
    """测试4: 验证完整的TaskOrientedExpertOutput schema"""
    print("🧪 测试4: 验证完整的TaskOrientedExpertOutput schema")
    print("=" * 80)

    schema = TaskOrientedExpertOutput.model_json_schema()

    # 验证schema中的content定义（嵌套在task_execution_report -> deliverable_outputs -> items -> content）
    task_exec_schema = schema["$defs"]["TaskExecutionReport"]
    deliverable_outputs_schema = task_exec_schema["properties"]["deliverable_outputs"]
    deliverable_output_ref = deliverable_outputs_schema["items"]["$ref"]

    print("✅ TaskExecutionReport.deliverable_outputs:")
    print("   类型: array")
    print(f"   items: {deliverable_output_ref}")

    # 验证DeliverableOutput定义
    deliverable_def = schema["$defs"]["DeliverableOutput"]
    content_type = deliverable_def["properties"]["content"]["type"]

    print("✅ DeliverableOutput.content:")
    print(f"   类型: {content_type}")

    assert content_type == "string", "❌ content类型必须是string"

    print("✅ 测试通过：完整schema定义正确，符合OpenAI API要求")
    print()


def test_openai_schema_compatibility():
    """测试5: 验证schema与OpenAI结构化输出API兼容性"""
    print("🧪 测试5: 验证OpenAI API兼容性（schema检查）")
    print("=" * 80)

    schema = TaskOrientedExpertOutput.model_json_schema()

    # 检查所有array类型的items定义
    def check_array_items(obj: Dict[str, Any], path: str = "root") -> list:
        """递归检查所有array类型的items定义"""
        issues = []

        if isinstance(obj, dict):
            if obj.get("type") == "array":
                items = obj.get("items")
                if not items:
                    issues.append(f"{path}: array类型缺少items定义")
                elif isinstance(items, dict):
                    if "type" not in items and "$ref" not in items:
                        issues.append(f"{path}: array.items缺少type或$ref定义")

            for key, value in obj.items():
                issues.extend(check_array_items(value, f"{path}.{key}"))

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                issues.extend(check_array_items(item, f"{path}[{i}]"))

        return issues

    issues = check_array_items(schema)

    if issues:
        print("❌ 发现schema定义问题:")
        for issue in issues:
            print(f"   - {issue}")
        raise AssertionError(f"Schema定义不符合OpenAI API要求: {len(issues)}个问题")

    print("✅ 测试通过：schema完全符合OpenAI结构化输出API要求")
    print("✅ 所有array类型的items都有明确的type或$ref定义")
    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("🚀 任务导向模型Schema修复测试套件 (v7.18.1)")
    print("=" * 80)
    print()

    try:
        test_deliverable_output_schema()
        test_validator_with_dict()
        test_validator_with_list()
        test_full_expert_output_schema()
        test_openai_schema_compatibility()

        print("=" * 80)
        print("🎉 所有测试通过！Schema修复成功！")
        print("=" * 80)
        print()
        print("📊 修复总结:")
        print("   ✅ DeliverableOutput.content 字段从 Union[str, Dict, List] 改为 str")
        print("   ✅ validator自动序列化dict/list为JSON字符串")
        print("   ✅ schema符合OpenAI结构化输出API要求")
        print("   ✅ 修复了 'items must have a type key' 错误")
        print()
        return 0

    except AssertionError as e:
        print("=" * 80)
        print(f"❌ 测试失败: {e}")
        print("=" * 80)
        return 1
    except Exception as e:
        print("=" * 80)
        print(f"❌ 测试异常: {e}")
        import traceback

        traceback.print_exc()
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
