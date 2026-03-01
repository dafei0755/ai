"""
ST-3a: LangGraph 图结构验证测试

目标：
  确保 main_workflow.py 中 add_conditional_edges 声明的所有路由目标
  以及 routing function 的 return 值都是已注册的节点名称，
  防止出现类似 ADR-001（analysis_review 死路由）的问题再次发生。

方法：
  静态解析源文件，无需启动任何服务或 LLM 连接。

验证范围：
  1.  `workflow.add_node(name, ...)` → 收集注册节点集合
  2.  `add_conditional_edges(src, fn, [targets])` 或 `{key: target}` → 收集声明目标
  3.  路由函数 `_route_*` 中 `return "..."` → 收集实际返回值
  4.  `goto="..."` 在 Command 中 → 收集 Command 跳转目标
  5.  断言：集合 2/3/4 - {"END"} ⊆ 集合 1

维护说明：
  当新增节点或路由函数时，此测试会自动覆盖（全解析）。
  无需手动更新节点白名单。
"""

from __future__ import annotations

import pathlib
import re

import pytest

# ──────────────────────────────────────────────────────────────
# 路径常量
# ──────────────────────────────────────────────────────────────
REPO_ROOT = pathlib.Path(__file__).parents[2]
WORKFLOW_FILE = REPO_ROOT / "intelligent_project_analyzer" / "workflow" / "main_workflow.py"
QUESTIONNAIRE_FILE = (
    REPO_ROOT / "intelligent_project_analyzer" / "interaction" / "nodes" / "progressive_questionnaire.py"
)


# ──────────────────────────────────────────────────────────────
# 静态解析工具
# ──────────────────────────────────────────────────────────────


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_comments(src: str) -> str:
    """
    移除 Python 单行注释（# ...），避免注释中的节点名被误解析。
    保留整行结构（只清空注释内容），保持行号不变。
    """
    result = []
    for line in src.splitlines():
        # 找到 # 的位置，处理字符串内的 # 不算注释
        in_str = False
        str_char = ""
        i = 0
        while i < len(line):
            ch = line[i]
            if in_str:
                if ch == str_char and (i == 0 or line[i - 1] != "\\"):
                    in_str = False
            else:
                if ch in ('"', "'"):
                    in_str = True
                    str_char = ch
                elif ch == "#":
                    line = line[:i]
                    break
            i += 1
        result.append(line)
    return "\n".join(result)


def extract_registered_nodes(src: str) -> set[str]:
    """
    提取 workflow.add_node("name", ...) 中的节点名称。
    同时包含框架内置终止节点。
    注意：先去除注释再解析。
    """
    clean = _strip_comments(src)
    pattern = re.compile(r'workflow\.add_node\(\s*["\']([^"\']+)["\']')
    nodes = set(pattern.findall(clean))
    # LangGraph 内置终止值
    nodes.add("END")
    nodes.add("__end__")
    return nodes


def extract_conditional_edge_targets(src: str) -> set[str]:
    """
    提取 add_conditional_edges(...) 中实际的目标节点名称（非 path 别名）。

    - 列表格式  ["node_a", "node_b"] → 直接是目标节点
    - 字典格式  {"alias": "node_a"}  → VALUES 才是目标节点，KEYS 是路由别名
    注意：先去除注释再解析。
    """
    clean = _strip_comments(src)
    targets: set[str] = set()

    # 列表格式：add_conditional_edges(..., ["a", "b", END])
    list_pattern = re.compile(
        r"add_conditional_edges\([^)]*?\[([^\]]+)\]",
        re.DOTALL,
    )
    for match in list_pattern.finditer(clean):
        for item in re.findall(r'["\']([^"\']+)["\']', match.group(1)):
            targets.add(item)

    # 字典格式：add_conditional_edges(..., {"key": "target"})
    # 只取 values（冒号右边的字符串）
    dict_pattern = re.compile(
        r"add_conditional_edges\([^)]*?\{([^}]+)\}",
        re.DOTALL,
    )
    for match in dict_pattern.finditer(clean):
        for item in re.findall(r':\s*["\']([^"\']+)["\']', match.group(1)):
            targets.add(item)

    return targets


def extract_conditional_edge_path_keys(src: str) -> set[str]:
    """
    提取 add_conditional_edges(..., {"key": "target"}) 中的 KEYS（路由别名）。
    路由函数 return 的值是 key，不是实际节点名，因此需要单独提取来验证。
    注意：先去除注释再解析。
    """
    clean = _strip_comments(src)
    keys: set[str] = set()
    dict_pattern = re.compile(
        r"add_conditional_edges\([^)]*?\{([^}]+)\}",
        re.DOTALL,
    )
    for match in dict_pattern.finditer(clean):
        # 取 key（冒号左边的字符串）
        for item in re.findall(r'["\']([^"\']+)["\'](?=\s*:)', match.group(1)):
            keys.add(item)
    return keys


def extract_route_return_values(src: str) -> set[str]:
    """
    提取 `def _route_*` 函数体内 `return "..."` 字符串字面量。
    只收集路由函数（命名以 _route_ 开头）。
    """
    values: set[str] = set()
    # 找到所有 _route_ 函数的定义起点
    func_starts = [m.start() for m in re.finditer(r"def _route_\w+\(", src)]
    func_starts.append(len(src))  # 哨兵

    for i, start in enumerate(func_starts[:-1]):
        # 提取函数体（直到下一个同级 def）
        body = src[start : func_starts[i + 1]]
        for val in re.findall(r'return\s+["\']([^"\']+)["\']', body):
            values.add(val)

    return values


def extract_command_goto_targets(src: str) -> set[str]:
    """
    提取 Command(..., goto="target") 中的 goto 目标。
    """
    pattern = re.compile(r'goto\s*=\s*["\']([^"\']+)["\']')
    return set(pattern.findall(src))


# ──────────────────────────────────────────────────────────────
# 测试用例
# ──────────────────────────────────────────────────────────────


class TestGraphStructure:
    """LangGraph 图结构一致性验证"""

    @pytest.fixture(scope="class")
    def workflow_src(self) -> str:
        assert WORKFLOW_FILE.exists(), f"找不到 main_workflow.py: {WORKFLOW_FILE}"
        return _read(WORKFLOW_FILE)

    @pytest.fixture(scope="class")
    def questionnaire_src(self) -> str:
        assert QUESTIONNAIRE_FILE.exists(), f"找不到 progressive_questionnaire.py: {QUESTIONNAIRE_FILE}"
        return _read(QUESTIONNAIRE_FILE)

    @pytest.fixture(scope="class")
    def registered_nodes(self, workflow_src: str) -> set[str]:
        nodes = extract_registered_nodes(workflow_src)
        assert nodes, "未能解析到任何注册节点，请检查 add_node 调用格式"
        return nodes

    # ── 测试 1：conditional_edges 声明目标必须是有效节点 ──────

    def test_conditional_edge_targets_are_registered(self, workflow_src: str, registered_nodes: set[str]):
        """
        add_conditional_edges 中列出的所有目标节点必须已通过 add_node 注册，
        或为 END。
        """
        targets = extract_conditional_edge_targets(workflow_src)
        assert targets, "未能解析到任何 add_conditional_edges 目标"

        unknown = targets - registered_nodes
        assert not unknown, f"add_conditional_edges 中存在未注册的目标节点: {unknown}\n" f"已注册节点: {sorted(registered_nodes)}"

    # ── 测试 2：路由函数 return 值必须可解析为有效路由键 ───────

    def test_route_function_return_values_in_registered_targets(self, workflow_src: str, registered_nodes: set[str]):
        """
        _route_* 函数中直接 return 的字符串必须满足以下之一：
        - dict 格式 conditional_edges 中的 path key（路由别名），如 "continue_workflow"
        - list 格式 conditional_edges 中的节点名，或已注册节点名

        背景：
        - 字典格式：route_fn 返回 key，边负责映射到实际节点
        - 列表格式：route_fn 直接返回节点名
        """
        return_values = extract_route_return_values(workflow_src)
        path_keys = extract_conditional_edge_path_keys(workflow_src)
        conditional_targets = extract_conditional_edge_targets(workflow_src)
        # 合法集合 = 路由别名 + 声明目标 + 已注册节点
        valid_targets = path_keys | conditional_targets | registered_nodes

        unknown = return_values - valid_targets
        assert not unknown, (
            f"路由函数返回了未声明的路由目标（既不是 path key 也不是注册节点）: {unknown}\n"
            f"path keys: {sorted(path_keys)}\n"
            f"合法节点: {sorted(registered_nodes)}"
        )

    # ── 测试 3：Command goto 目标必须是有效节点 ────────────────

    def test_command_goto_targets_are_registered_in_workflow(self, workflow_src: str, registered_nodes: set[str]):
        """
        main_workflow.py 中 Command(goto=...) 的所有跳转目标
        必须是已注册节点或 END。
        """
        goto_targets = extract_command_goto_targets(workflow_src)
        # 过滤掉明显是注释行或字符串变量（包含空格）的假阳性
        goto_targets = {t for t in goto_targets if " " not in t}

        unknown = goto_targets - registered_nodes
        assert not unknown, f"main_workflow.py Command goto 中存在未注册的节点: {unknown}\n" f"已注册节点: {sorted(registered_nodes)}"

    def test_command_goto_targets_are_registered_in_questionnaire(self, questionnaire_src: str, workflow_src: str):
        """
        progressive_questionnaire.py 中 Command(goto=...) 的所有跳转目标
        必须是 main_workflow.py 中注册的节点或 END。
        """
        registered_nodes = extract_registered_nodes(workflow_src)
        goto_targets = extract_command_goto_targets(questionnaire_src)
        goto_targets = {t for t in goto_targets if " " not in t}

        unknown = goto_targets - registered_nodes
        assert not unknown, (
            f"progressive_questionnaire.py Command goto 中存在未注册的节点: {unknown}\n" f"已注册节点: {sorted(registered_nodes)}"
        )

    # ── 测试 4：analysis_review 僵尸节点永不在路由目标中 ───────

    def test_analysis_review_is_not_a_route_target(self, workflow_src: str):
        """
        ADR-001 回归测试：确保 analysis_review 不再出现在任何路由 return 值中。
        此测试对应 P0/QW-1 修复，持续防止死路由复发。
        """
        return_values = extract_route_return_values(workflow_src)
        assert "analysis_review" not in return_values, (
            "检测到 analysis_review 重新出现在路由函数返回值中！" "该节点已在 ADR-001 中废弃，请参阅 sf/governance/adr/ADR-001.md"
        )

    def test_analysis_review_not_in_conditional_edge_targets(self, workflow_src: str):
        """
        确保 analysis_review 不在 add_conditional_edges 目标列表中。
        """
        targets = extract_conditional_edge_targets(workflow_src)
        assert "analysis_review" not in targets, (
            "检测到 analysis_review 重新出现在 add_conditional_edges 目标中！" "该节点已在 ADR-001 中废弃"
        )

    # ── 测试 5：节点注册基础健壮性检查 ────────────────────────

    def test_critical_nodes_are_registered(self, registered_nodes: set[str]):
        """
        确保核心节点均已注册，防止误删。
        """
        critical = {
            "requirements_analyst",
            "project_director",
            "batch_executor",
            "batch_aggregator",
            "batch_router",
            "detect_challenges",
            "result_aggregator",
            "pdf_generator",
        }
        missing = critical - registered_nodes
        assert not missing, f"关键节点未注册，可能被误删: {missing}"

    def test_no_orphan_route_functions(self, workflow_src: str):
        """
        确保 _route_after_analysis_review (ADR-001/QW-3 已删除) 不再存在。
        防止残留孤儿路由函数被意外引用。
        """
        assert "def _route_after_analysis_review" not in workflow_src, (
            "_route_after_analysis_review 孤儿函数重新出现，" "该函数已在 QW-3 中删除，见 sf/governance/adr/ADR-001.md"
        )
