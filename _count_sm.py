for f in [
    "intelligent_project_analyzer/api/session_routes.py",
    "intelligent_project_analyzer/api/image_routes.py",
    "intelligent_project_analyzer/api/monitoring_routes.py",
]:
    c = open(f, encoding="utf-8").read().count("_get_session_manager")
    print(f"{f.split('/')[-1]}: {c}")
