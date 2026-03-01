"""检查 ProjectDiscovery 表谷德分类"""
from intelligent_project_analyzer.models.external_projects import get_external_db
from intelligent_project_analyzer.external_data_system.models.external_projects import ProjectDiscovery

db = get_external_db()
with db.get_session() as s:
    rows = (
        s.query(ProjectDiscovery.url, ProjectDiscovery.category, ProjectDiscovery.source)
        .filter(
            ProjectDiscovery.source == "gooood",
            ProjectDiscovery.is_crawled == True,
        )
        .limit(11)
        .all()
    )
    for r in rows:
        cat = r.category or "(empty)"
        print(f"  cat=[{cat}]  url={r.url[:70]}")
    total = s.query(ProjectDiscovery).filter(ProjectDiscovery.source == "gooood").count()
    has_cat = (
        s.query(ProjectDiscovery)
        .filter(
            ProjectDiscovery.source == "gooood",
            ProjectDiscovery.category.isnot(None),
        )
        .count()
    )
    print(f"\nDiscovery: total={total}, has_cat={has_cat}, no_cat={total - has_cat}")
