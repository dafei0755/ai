"""回填谷德项目的 primary_category（从 ProjectDiscovery 表获取分类信息）"""
from intelligent_project_analyzer.models.external_projects import get_external_db, ExternalProject
from intelligent_project_analyzer.external_data_system.models.external_projects import ProjectDiscovery

db = get_external_db()
with db.get_session() as s:
    # 查找所有无分类的谷德项目
    no_cat = (
        s.query(ExternalProject)
        .filter(
            ExternalProject.source == "gooood",
            (ExternalProject.primary_category.is_(None)) | (ExternalProject.primary_category == ""),
        )
        .all()
    )
    print(f"无分类谷德项目: {len(no_cat)} 条")

    fixed = 0
    for p in no_cat:
        disc = s.query(ProjectDiscovery).filter(ProjectDiscovery.url == p.url).first()
        if disc and disc.category:
            print(f"  ID={p.id} [{disc.category}] {(p.title or '?')[:50]}")
            p.primary_category = disc.category
            fixed += 1
        else:
            print(f"  ID={p.id} 未找到发现记录或分类为空: {p.url[:60]}")

    if fixed > 0:
        s.commit()
        print(f"\n已修复 {fixed} 条记录")
    else:
        print("\n无需修复")
