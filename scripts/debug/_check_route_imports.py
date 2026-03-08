"""检查4个路由模块的所有缺失导入（迭代方式）"""
import sys, importlib, traceback

mods = [
    "intelligent_project_analyzer.api.image_routes",
    "intelligent_project_analyzer.api.session_routes",
    "intelligent_project_analyzer.api.monitoring_routes",
    "intelligent_project_analyzer.api.analysis_routes",
]


def clear_cache():
    for k in list(sys.modules.keys()):
        if "intelligent_project_analyzer" in k:
            del sys.modules[k]


for mod in mods:
    name = mod.split(".")[-1]
    errors = []
    print(f"\n=== {name} ===")
    for _ in range(10):  # 最多迭代10次
        clear_cache()
        try:
            importlib.import_module(mod)
            print("  OK")
            break
        except Exception as e:
            msg = str(e)
            if msg in errors:
                print(f"  STUCK: {type(e).__name__}: {msg}")
                break
            errors.append(msg)
            print(f"  ERROR: {type(e).__name__}: {msg}")
            # 拿行号
            tb = traceback.extract_tb(sys.exc_info()[2])
            for frame in tb:
                if name in frame.filename:
                    print(f"    at {frame.filename}:{frame.lineno}")
            break  # 每次只报第一个错，需要人工修复后重跑
