"""
P0 Bug修复验证测试

F1: category_info 变量提前引用修复
F2: CachedLLMWrapper 缓存命名冲突修复
F3: 补充任务动机推断修复
"""

import pytest
import inspect
from unittest.mock import MagicMock


# =============================================================================
# F1: category_info 变量提前引用修复
# =============================================================================


class TestF1CategoryInfoFix:
    """验证 category_info 不再在 for 循环之前被引用"""

    def test_no_category_info_before_loop(self):
        """F1: category_info 不应在 for 循环外被引用"""
        from intelligent_project_analyzer.services import core_task_decomposer

        source = inspect.getsource(core_task_decomposer.decompose_core_tasks_hybrid)

        # 查找 "Phase 2" 注释和 for 循环之间是否有 category_info 引用
        lines = source.split("\n")
        phase2_line_idx = None
        for_loop_line_idx = None

        for i, line in enumerate(lines):
            if "Phase 2" in line and "按" in line:
                phase2_line_idx = i
            if phase2_line_idx is not None and "for idx, category_info in enumerate" in line:
                for_loop_line_idx = i
                break

        assert phase2_line_idx is not None, "未找到Phase 2标记行"
        assert for_loop_line_idx is not None, "未找到for循环行"

        # 检查 Phase 2 和 for 循环之间没有 category_info.get 调用
        between_lines = lines[phase2_line_idx + 1 : for_loop_line_idx]
        for line in between_lines:
            assert "category_info" not in line, f"category_info 在 for 循环之前被引用: '{line.strip()}'"

    def test_category_info_only_inside_loop(self):
        """F1: category_info.get() 只在 for 循环内部使用"""
        from intelligent_project_analyzer.services import core_task_decomposer

        source = inspect.getsource(core_task_decomposer.decompose_core_tasks_hybrid)
        lines = source.split("\n")

        for_loop_started = False
        for i, line in enumerate(lines):
            if "for idx, category_info in enumerate" in line:
                for_loop_started = True
                continue
            # 在 for 循环定义之前不应有 category_info.get
            if not for_loop_started and "category_info.get(" in line:
                pytest.fail(f"Line {i}: category_info.get() 在 for 循环外使用: {line.strip()}")


# =============================================================================
# F2: CachedLLMWrapper 缓存命名冲突修复
# =============================================================================


class TestF2CacheNamingFix:
    """验证 CachedLLMWrapper 不再与 BaseChatModel.cache 命名冲突"""

    def test_semantic_cache_field_exists(self):
        """F2: CachedLLMWrapper 应使用 semantic_cache 而非 cache 存储语义缓存"""
        from intelligent_project_analyzer.services.cached_llm_wrapper import CachedLLMWrapper

        # 检查 semantic_cache 字段存在
        fields = CachedLLMWrapper.__fields__
        assert "semantic_cache" in fields, "缺少 semantic_cache 字段"

    def test_cache_field_not_shadowed(self):
        """F2: CachedLLMWrapper 不应用 SemanticCache 实例覆盖 BaseChatModel.cache"""
        from intelligent_project_analyzer.services.cached_llm_wrapper import CachedLLMWrapper

        wrapper_fields = CachedLLMWrapper.__fields__
        if "cache" in wrapper_fields:
            field = wrapper_fields["cache"]
            # cache 字段的注解不应含 SemanticCache，应继承自 BaseChatModel
            annotation = (
                str(field.annotation) if hasattr(field, "annotation") else str(getattr(field, "outer_type_", ""))
            )
            assert "SemanticCache" not in annotation, f"cache 字段类型不应为 SemanticCache: {annotation}"

    def test_invoke_override_exists(self):
        """F2: CachedLLMWrapper 应覆写 invoke() 方法"""
        from intelligent_project_analyzer.services.cached_llm_wrapper import CachedLLMWrapper

        # invoke 方法应在 CachedLLMWrapper 中定义（非继承）
        assert "invoke" in CachedLLMWrapper.__dict__, "CachedLLMWrapper 缺少 invoke() 覆写"

    def test_ainvoke_override_exists(self):
        """F2: CachedLLMWrapper 应覆写 ainvoke() 方法"""
        from intelligent_project_analyzer.services.cached_llm_wrapper import CachedLLMWrapper

        assert "ainvoke" in CachedLLMWrapper.__dict__, "CachedLLMWrapper 缺少 ainvoke() 覆写"

    def test_invoke_delegates_to_inner_llm(self):
        """F2: invoke() 应直接委托给底层LLM，不触发BaseChatModel缓存机制"""
        from intelligent_project_analyzer.services.cached_llm_wrapper import CachedLLMWrapper

        source = inspect.getsource(CachedLLMWrapper.invoke)

        # 应直接调用 self.llm.invoke
        assert "self.llm.invoke" in source, "invoke() 应委托给 self.llm.invoke()"

        # 不应调用 _generate_with_cache 或 super().invoke
        assert "_generate_with_cache" not in source, "invoke() 不应调用 _generate_with_cache"

    def test_init_disables_inner_llm_cache(self):
        """F2: __init__ 应将底层LLM的 cache 设为 False"""
        from intelligent_project_analyzer.services.cached_llm_wrapper import CachedLLMWrapper

        source = inspect.getsource(CachedLLMWrapper.__init__)
        assert "self.llm.cache = False" in source or "self.llm.cache = False" in source, "__init__ 应禁用底层LLM的cache"

    def test_super_init_passes_semantic_cache(self):
        """F2: super().__init__ 应传递 semantic_cache 而非 cache"""
        from intelligent_project_analyzer.services.cached_llm_wrapper import CachedLLMWrapper
        import re

        source = inspect.getsource(CachedLLMWrapper.__init__)
        assert "semantic_cache=cache" in source, "super().__init__ 应传递 semantic_cache=cache"
        # 检查 super().__init__() 调用中不应有独立的 cache=参数（排除 semantic_cache= 和参数定义）
        super_call = re.search(r"super\(\).__init__\((.+?)\)", source, re.DOTALL)
        if super_call:
            super_args = super_call.group(1)
            # 移除 semantic_cache=cache 后检查是否还有单独的 cache= 参数
            cleaned = super_args.replace("semantic_cache=cache", "")
            assert not re.search(r"\bcache=", cleaned), "super().__init__ 不应有独立的 cache= 参数（会触发命名冲突）"


class TestF2LLMFactoryCacheInit:
    """验证 llm_factory.py 全局缓存初始化使用官方API"""

    def test_uses_set_llm_cache(self):
        """F2: 应使用 langchain.globals.set_llm_cache 而非直接赋值"""
        from intelligent_project_analyzer.services import llm_factory

        source = inspect.getsource(llm_factory)

        assert "set_llm_cache" in source, "应使用 langchain.globals.set_llm_cache()"

    def test_has_fallback_for_old_versions(self):
        """F2: 应有 ImportError 回退逻辑兼容旧版 LangChain"""
        from intelligent_project_analyzer.services import llm_factory

        source = inspect.getsource(llm_factory)

        assert "ImportError" in source, "应有 except ImportError 回退逻辑"


# =============================================================================
# F3: 补充任务动机推断修复
# =============================================================================


class TestF3SupplementMetadataInference:
    """验证补充任务也会获得动机元数据"""

    def test_metadata_inference_after_supplement(self):
        """F3: 补充任务应触发 _infer_task_metadata_async"""
        from intelligent_project_analyzer.services import core_task_decomposer

        source = inspect.getsource(core_task_decomposer.decompose_core_tasks_hybrid)

        # 检查在补充机制之后有 motivation_type 检查和推断调用
        assert "tasks_needing_metadata" in source, "应有 tasks_needing_metadata 变量收集缺少元数据的任务"
        assert "not t.get('motivation_type')" in source, "应通过 motivation_type 字段过滤需要推断的任务"

    def test_metadata_inference_is_after_supplement_loop(self):
        """F3: 动机推断应在补充循环之后执行"""
        from intelligent_project_analyzer.services import core_task_decomposer

        source = inspect.getsource(core_task_decomposer.decompose_core_tasks_hybrid)
        lines = source.split("\n")

        supplement_end_idx = None
        metadata_check_idx = None

        for i, line in enumerate(lines):
            if "分批补充完成" in line:
                supplement_end_idx = i
            if "tasks_needing_metadata" in line and "motivation_type" in line:
                metadata_check_idx = i

        assert supplement_end_idx is not None, "未找到补充循环结束标记"
        assert metadata_check_idx is not None, "未找到补充任务元数据检查"
        assert metadata_check_idx > supplement_end_idx, "元数据推断应在补充循环之后执行"

    def test_metadata_inference_uses_decomposer(self):
        """F3: 应使用 decomposer._infer_task_metadata_async 进行推断"""
        from intelligent_project_analyzer.services import core_task_decomposer

        source = inspect.getsource(core_task_decomposer.decompose_core_tasks_hybrid)

        # 计算 _infer_task_metadata_async 被调用次数（应至少2次：初始+补充）
        count = source.count("_infer_task_metadata_async")
        assert count >= 2, f"_infer_task_metadata_async 应至少调用2次（初始+补充），实际 {count} 次"

    def test_metadata_inference_has_error_handling(self):
        """F3: 补充任务推断应有异常处理，不阻塞主流程"""
        from intelligent_project_analyzer.services import core_task_decomposer

        source = inspect.getsource(core_task_decomposer.decompose_core_tasks_hybrid)

        # P0-F3 块应包含 try/except
        f3_start = source.find("P0-F3")
        assert f3_start != -1, "未找到 P0-F3 标记"

        f3_block = source[f3_start : f3_start + 500]
        assert "try:" in f3_block, "P0-F3 块应有 try"
        assert "except" in f3_block, "P0-F3 块应有 except"
        assert "warning" in f3_block.lower() or "Warning" in f3_block, "P0-F3 异常应记录为 warning，不阻塞主流程"


# =============================================================================
# 综合集成验证
# =============================================================================


class TestP0Integration:
    """P0修复的集成级验证"""

    def test_all_three_fixes_present(self):
        """综合: 三个P0修复应同时存在"""
        from intelligent_project_analyzer.services import core_task_decomposer
        from intelligent_project_analyzer.services import cached_llm_wrapper

        # F1: core_task_decomposer 中无循环外 category_info 引用
        source_ctd = inspect.getsource(core_task_decomposer.decompose_core_tasks_hybrid)
        lines = source_ctd.split("\n")
        for_started = False
        for line in lines:
            if "for idx, category_info in enumerate" in line:
                for_started = True
            if not for_started and "category_info.get(" in line:
                pytest.fail("F1 未修复: category_info 在循环外使用")

        # F2: cached_llm_wrapper 使用 semantic_cache
        assert "semantic_cache" in cached_llm_wrapper.CachedLLMWrapper.__fields__

        # F3: 补充任务推断存在
        assert "tasks_needing_metadata" in source_ctd

    def test_wrap_llm_with_cache_still_works(self):
        """综合: wrap_llm_with_cache 函数仍可正常调用"""
        from intelligent_project_analyzer.services.cached_llm_wrapper import wrap_llm_with_cache

        # 不启用缓存时应返回原始LLM
        mock_llm = MagicMock()
        result = wrap_llm_with_cache(mock_llm, enable_cache=False)
        assert result is mock_llm

    def test_cached_wrapper_source_no_self_dot_cache_dot(self):
        """综合: CachedLLMWrapper 中不应有 self.cache.xxx（应改为 self.semantic_cache.xxx）"""
        from intelligent_project_analyzer.services.cached_llm_wrapper import CachedLLMWrapper
        import re

        # 获取所有方法的源码
        for method_name in ["_agenerate", "_identifying_params", "get_cache_stats"]:
            if hasattr(CachedLLMWrapper, method_name):
                method = getattr(CachedLLMWrapper, method_name)
                if callable(method) or isinstance(method, property):
                    try:
                        source = inspect.getsource(method.fget if isinstance(method, property) else method)
                        matches = re.findall(r"self\.cache\.", source)
                        assert len(matches) == 0, f"{method_name} 中仍有 self.cache. 引用: {matches}"
                    except (TypeError, OSError):
                        pass  # 跳过无法获取源码的方法
