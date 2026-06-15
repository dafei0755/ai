from pathlib import Path


SERVER_SOURCE = Path("intelligent_project_analyzer/api/server.py")
LEARNING_SCHEDULER_SOURCE = Path("intelligent_project_analyzer/services/learning_scheduler.py")
PROJECT_TYPE_EXPANSION_SOURCE = Path("intelligent_project_analyzer/services/project_type_expansion.py")
PROJECT_TYPE_SCHEMA = Path("intelligent_project_analyzer/learning/database_schema.sql")
OLD_EXTERNAL_DATA_ROUTE = Path("intelligent_project_analyzer/api/external_data_routes.py")
OLD_CRAWLER_MONITOR_ROUTE = Path("intelligent_project_analyzer/api/routes/crawler_monitor_routes.py")
ADMIN_LAYOUT_SOURCE = Path("frontend-nextjs/app/admin/layout.tsx")
PROJECT_TYPES_ADMIN_PAGE = Path("frontend-nextjs/app/admin/project-types/page.tsx")
CRAWLER_ADMIN_PAGE = Path("frontend-nextjs/app/admin/crawler-monitor/page.tsx")
CRAWLER_ADMIN_BACKUP_PAGE = Path("frontend-nextjs/app/admin/crawler-monitor/page.tsx.corrupted_bak")
EXTERNAL_DATA_ADMIN_PAGE = Path("frontend-nextjs/app/admin/external-data/page.tsx")


def test_backend_startup_does_not_register_crawler_runtime_surfaces():
    source = SERVER_SOURCE.read_text(encoding="utf-8")

    retired_runtime_markers = [
        "JobSchedulerService",
        "爬虫定时调度器已启动",
        "external_data_system.api",
        "外部数据采集监控路由已注册",
        "外部数据搜索推荐路由已注册",
        "crawler_monitor_routes",
        "prefix=\"/api/crawler\"",
        "爬虫监控管理路由已注册",
    ]

    for marker in retired_runtime_markers:
        assert marker not in source


def test_learning_scheduler_does_not_scan_crawler_data():
    source = LEARNING_SCHEDULER_SOURCE.read_text(encoding="utf-8")

    assert "type_expansion_scan" not in source
    assert "scan_crawler_data" not in source
    assert "扫描爬虫知识库" not in source


def test_project_type_expansion_keeps_user_candidates_but_not_crawler_scan():
    source = PROJECT_TYPE_EXPANSION_SOURCE.read_text(encoding="utf-8")

    assert "collect_from_session" in source
    assert "async_infer_type_with_llm" in source
    assert "scan_crawler_data" not in source
    assert "crawler_" not in source
    assert '"source": "crawler"' not in source


def test_project_type_candidate_sources_do_not_expose_crawler_origin():
    schema = PROJECT_TYPE_SCHEMA.read_text(encoding="utf-8")
    page = PROJECT_TYPES_ADMIN_PAGE.read_text(encoding="utf-8")

    assert "user_input / crawler / manual" not in schema
    assert "crawler: '爬虫数据'" not in page
    assert "爬虫数据" not in page


def test_admin_sidebar_does_not_link_to_crawler_management():
    source = ADMIN_LAYOUT_SOURCE.read_text(encoding="utf-8")

    assert "/admin/crawler-monitor" not in source
    assert "外部数据管理" not in source


def test_retired_crawler_admin_pages_are_removed():
    assert not CRAWLER_ADMIN_PAGE.exists()
    assert not CRAWLER_ADMIN_BACKUP_PAGE.exists()
    assert not EXTERNAL_DATA_ADMIN_PAGE.exists()


def test_retired_backend_crawler_route_modules_are_removed():
    assert not OLD_EXTERNAL_DATA_ROUTE.exists()
    assert not OLD_CRAWLER_MONITOR_ROUTE.exists()
