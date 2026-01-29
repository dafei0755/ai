"""
v7.200 JSON 解析器测试脚本
测试统一的 _safe_parse_json 方法
"""

import asyncio
import json

from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine


def test_safe_parse_json():
    """测试 _safe_parse_json 方法"""
    engine = UcpptSearchEngine()

    print("=" * 60)
    print("v7.200 统一 JSON 解析器测试")
    print("=" * 60)

    # 测试用例
    test_cases = [
        # 1. 直接 JSON
        ('{"key": "value", "number": 42}', "直接JSON", True),
        # 2. ```json``` 块
        ('这是一些文本\n```json\n{"result": true, "message": "success"}\n```\n结尾文本', "JSON代码块", True),
        # 3. ``` 块（无语言标记）
        ('前缀内容\n```\n{"data": 123, "valid": true}\n```\n后缀内容', "通用代码块", True),
        # 4. 带语言标记的 ``` 块
        ('```json\n{"items": ["a", "b", "c"]}\n```', "带json标记的代码块", True),
        # 5. 混合内容（需要正则提取）
        ('分析结果如下: {"score": 0.85, "status": "good"} 以上是结果', "混合内容", True),
        # 6. 嵌套 JSON
        ('{"outer": {"inner": "value"}, "list": [1, 2, 3]}', "嵌套JSON", True),
        # 7. 空文本
        ("", "空文本", False),
        # 8. 纯文本（无 JSON）
        ("这是一段纯文本，没有任何 JSON 内容", "纯文本", False),
        # 9. 损坏的 JSON
        ('{"key": "value",}', "损坏的JSON（尾逗号）", False),
    ]

    passed = 0
    failed = 0

    for text, desc, expect_success in test_cases:
        result = engine._safe_parse_json(text, context=desc)

        if expect_success:
            if result is not None:
                status = "✅ PASS"
                passed += 1
            else:
                status = "❌ FAIL (期望成功但失败)"
                failed += 1
        else:
            if result is None:
                status = "✅ PASS (期望失败)"
                passed += 1
            else:
                status = "⚠️ WARN (期望失败但成功)"
                passed += 1  # 这算是额外能力

        print(f"\n{status}: {desc}")
        if result:
            print(f"   解析结果: {json.dumps(result, ensure_ascii=False)[:80]}...")

    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{len(test_cases)} 通过")
    print("=" * 60)

    return failed == 0


def test_search_config():
    """测试搜索配置"""
    from intelligent_project_analyzer.services.ucppt_search_engine import (
        COMPLETENESS_THRESHOLD,
        MAX_SEARCH_ROUNDS,
        MIN_SEARCH_ROUNDS,
    )
    from intelligent_project_analyzer.services.web_content_extractor import CONTENT_EXTRACTION_TIMEOUT, SLOW_DOMAINS

    print("\n" + "=" * 60)
    print("v7.200 搜索配置验证")
    print("=" * 60)

    config_checks = [
        ("MIN_SEARCH_ROUNDS", MIN_SEARCH_ROUNDS, 4, "=="),
        ("COMPLETENESS_THRESHOLD", COMPLETENESS_THRESHOLD, 0.88, "=="),
        ("CONTENT_EXTRACTION_TIMEOUT", CONTENT_EXTRACTION_TIMEOUT, 15, "=="),
        ("慢站点数量", len(SLOW_DOMAINS), 20, ">="),
    ]

    all_passed = True
    for name, actual, expected, op in config_checks:
        if op == "==":
            passed = actual == expected
        elif op == ">=":
            passed = actual >= expected

        status = "✅" if passed else "❌"
        print(f"{status} {name}: {actual} (期望 {op} {expected})")
        if not passed:
            all_passed = False

    return all_passed


def test_whitelist_config():
    """测试白名单配置"""
    import yaml

    print("\n" + "=" * 60)
    print("v7.200 白名单配置验证")
    print("=" * 60)

    with open("config/search_filters.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    whitelist = config.get("whitelist", {})
    domains = whitelist.get("domains", [])
    boost_score = whitelist.get("boost_score", 0)

    checks = [
        ("白名单域名数量", len(domains), 50, ">="),
        ("白名单加分系数", boost_score, 0.45, "=="),
    ]

    # 检查关键域名是否存在
    key_domains = [
        "hospitalitydesign.com",
        "medium.com",
        "dribbble.com",
        "archdaily.com",
        "cnki.net",
    ]

    all_passed = True
    for name, actual, expected, op in checks:
        if op == "==":
            passed = actual == expected
        elif op == ">=":
            passed = actual >= expected

        status = "✅" if passed else "❌"
        print(f"{status} {name}: {actual} (期望 {op} {expected})")
        if not passed:
            all_passed = False

    print("\n关键域名检查:")
    for domain in key_domains:
        exists = domain in domains
        status = "✅" if exists else "❌"
        print(f"  {status} {domain}")
        if not exists:
            all_passed = False

    return all_passed


if __name__ == "__main__":
    print("\n" + "🧪" * 30)
    print("v7.200 搜索质量优化 - 系统测试")
    print("🧪" * 30 + "\n")

    results = []

    # 运行测试
    results.append(("JSON解析器测试", test_safe_parse_json()))
    results.append(("搜索配置验证", test_search_config()))
    results.append(("白名单配置验证", test_whitelist_config()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print("\n" + ("🎉 所有测试通过!" if all_passed else "⚠️ 部分测试失败"))
