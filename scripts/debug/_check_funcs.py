import ast

tree = ast.parse(open("intelligent_project_analyzer/agents/requirements_analyst_agent.py", encoding="utf-8").read())
funcs = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
needed = [
    "_build_decision_reason",
    "_build_phase1_only_result",
    "_build_problem_solving_approach",
    "_calculate_two_phase_confidence",
    "_format_precheck_hints",
    "_infer_project_type",
    "_merge_phase_results",
    "_normalize_jtbd_fields",
    "_parse_json_response",
    "_phase1_fallback",
    "_phase2_fallback",
    "_weighted_info_status_vote",
    "build_requirements_analyst_graph",
    "should_execute_phase2",
]
for f in needed:
    status = "OK" if f in funcs else "MISSING"
    print(f"  {status}: {f}")
