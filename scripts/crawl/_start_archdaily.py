"""
预扫描已在对话中确认：
  - 网站: archdaily.cn
  - 分类: 全部 8 个（住宅/文化建筑/商业建筑/教育建筑/办公建筑/体育建筑/工业建筑/基础设施）
  - 操作: 清空旧测试数据 → 重置爬取状态 → 触发全量爬取

运行方式: python _start_archdaily.py
"""
import os, sys, json, urllib.request, urllib.error

os.environ.setdefault("EXTERNAL_DB_URL", "postgresql://postgres:password@localhost:5432/external_projects")

SOURCE = "archdaily_cn"
API_BASE = "http://localhost:8000"

# ── Step 1: 清空旧数据 ─────────────────────────────────────────────────────
print("=" * 60)
print(f"Step 1/3  清空 {SOURCE} 旧数据")
print("=" * 60)
try:
    import sqlalchemy as sa
    engine = sa.create_engine(os.environ["EXTERNAL_DB_URL"])
    with engine.connect() as conn:
        img_del = conn.execute(sa.text(
            "DELETE FROM external_project_images WHERE project_id IN "
            "(SELECT id FROM external_projects WHERE source=:src)"
        ), {"src": SOURCE}).rowcount
        proj_del = conn.execute(sa.text(
            "DELETE FROM external_projects WHERE source=:src"
        ), {"src": SOURCE}).rowcount
        conn.commit()
        remaining = conn.execute(sa.text(
            "SELECT COUNT(*) FROM external_projects WHERE source=:src"
        ), {"src": SOURCE}).scalar()
    print(f"  已删除: {proj_del} 条项目, {img_del} 张图片")
    print(f"  {SOURCE} 剩余: {remaining} 条  {'OK' if remaining == 0 else '!! 仍有残留'}")
except Exception as e:
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        print(f"  {data.get('message', data)}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"  HTTP {e.code}: {body}")
except Exception as e:
    print(f"  [警告] 状态重置失败（后端可能未启动）: {e}")
    print("  → 将尝试直接修改状态文件...")
    # fallback: 直接写状态文件
    state_file = os.path.join(os.path.dirname(__file__), "data", "crawler_state", "schedule_state.json")
    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        if SOURCE in state.get("sources", {}):
            fc = state["sources"][SOURCE].setdefault("full_crawl", {})
            fc.update({
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "categories_done": 0,
                "total_categories": 8,
                "current_category": None,
                "target_categories": None,
                "baseline_count": None,
                "scan_at": None,
            })
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            print(f"  ✓ 已直接重置状态文件")
    else:
        print(f"  ⚠ 状态文件不存在: {state_file}")

# ── Step 3: 触发全量爬取 ──────────────────────────────────────────────────
print()
print("=" * 60)
print(f"Step 3/3  触发 {SOURCE} 全量爬取")
print("=" * 60)
try:
    payload = json.dumps({"source": SOURCE, "mode": "full"}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/api/crawler/schedule/trigger",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        print(f"  {data.get('message', data)}")
        print()
        print("  [OK] 全量爬取已加入队列")
        print(f"  监控地址: http://localhost:3001/admin/crawler-monitor")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"  HTTP {e.code}: {body}")
    if e.code == 409:
        print("  → 爬取任务已在运行中，无需重复触发")
except Exception as e:
    print(f"  [失败] 触发爬取失败: {e}")
    print("  → 请确认后端服务已启动: python -B scripts\\run_server_production.py")

print()
print("=" * 60)
print("完成")
