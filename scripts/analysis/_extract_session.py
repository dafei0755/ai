"""提取 analysis-20260225150039-3f37b06173c6 会话数据 v3 - 直接从 workflow.db"""
import sqlite3, json, sys, traceback, os
from pathlib import Path

TARGET_ID = "analysis-20260225150039-3f37b06173c6"
OUTPUT_FILE = "_session_extract_output.json"


def safe_query(db_path, fn):
    p = Path(db_path)
    if not p.exists():
        print(f"[SKIP] {db_path} 不存在")
        return None
    try:
        conn = sqlite3.connect(str(p))
        r = fn(conn)
        conn.close()
        return r
    except Exception as e:
        print(f"[ERROR] {db_path}: {e}")
        traceback.print_exc()
        return None


def check_archived(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT session_id, user_input, status, mode, analysis_mode, created_at, completed_at, progress, current_stage FROM archived_sessions WHERE session_id = ?",
        (TARGET_ID,),
    )
    row = cur.fetchone()
    if row:
        print("=" * 80)
        print("[FOUND in archived_sessions]")
        for l, v in zip(
            [
                "session_id",
                "user_input",
                "status",
                "mode",
                "analysis_mode",
                "created_at",
                "completed_at",
                "progress",
                "current_stage",
            ],
            row,
        ):
            print(f"  {l}: {str(v)[:200] if v else 'N/A'}")
        cur.execute("SELECT session_data FROM archived_sessions WHERE session_id = ?", (TARGET_ID,))
        sd = cur.fetchone()
        if sd and sd[0]:
            extract_all(json.loads(sd[0]))
        return True
    print(f"\n[NOT FOUND] 搜索近似...")
    cur.execute(
        "SELECT session_id, created_at, substr(user_input,1,60) FROM archived_sessions ORDER BY created_at DESC LIMIT 20"
    )
    rows = cur.fetchall()
    print(f"  archived_sessions 最近 {len(rows)} 条:")
    for r in rows:
        m = " <<<" if "20260225" in str(r[0]) else ""
        print(f"    {r[0]} | {r[1]} | {r[2] or ''}{m}")
    return None


def check_checkpoints_db(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"\n[checkpoints.db] tables: {tables}")
    for t in tables:
        try:
            cur.execute(f"PRAGMA table_info([{t}])")
            cols = [c[1] for c in cur.fetchall()]
            cur.execute(f"SELECT COUNT(*) FROM [{t}]")
            cnt = cur.fetchone()[0]
            print(f"  {t}: {cnt} rows, cols={cols}")
        except Exception as e:
            print(f"  {t}: error - {e}")
    for t in tables:
        try:
            cur.execute(f"PRAGMA table_info([{t}])")
            cols = [c[1] for c in cur.fetchall()]
            if "thread_id" in cols:
                cur.execute(f"SELECT DISTINCT thread_id FROM [{t}] WHERE thread_id = ?", (TARGET_ID,))
                if cur.fetchone():
                    print(f"  [FOUND in {t}]")
                cur.execute(f"SELECT DISTINCT thread_id FROM [{t}] WHERE thread_id LIKE ? LIMIT 10", ("%20260225%",))
                rows = cur.fetchall()
                if rows:
                    print(f"  同日 thread_ids in {t}: {[r[0] for r in rows]}")
                else:
                    cur.execute(f"SELECT DISTINCT thread_id FROM [{t}] ORDER BY thread_id DESC LIMIT 15")
                    rows = cur.fetchall()
                    print(f"  最近 thread_ids in {t}: {[r[0] for r in rows]}")
        except Exception as e:
            print(f"  {t} error: {e}")


def check_workflow_db(conn):
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f"\n[workflow.db] tables: {tables}")
        for t in tables:
            try:
                cur.execute(f"PRAGMA table_info([{t}])")
                cols = [c[1] for c in cur.fetchall()]
                print(f"  {t} cols: {cols}")
            except:
                pass
        if "checkpoints" in tables:
            try:
                cur.execute("SELECT DISTINCT thread_id FROM checkpoints WHERE thread_id = ?", (TARGET_ID,))
                if cur.fetchone():
                    print(f"  [FOUND in checkpoints]")
                else:
                    cur.execute("SELECT DISTINCT thread_id FROM checkpoints ORDER BY thread_id DESC LIMIT 10")
                    print(f"  最近: {[r[0] for r in cur.fetchall()]}")
            except Exception as e:
                print(f"  checkpoints query error: {e}")
    except Exception as e:
        print(f"  workflow.db error: {e}")


def check_main_db(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"\n[intelligent_project_analyzer.db] tables: {tables}")
    for t in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM [{t}]")
            cnt = cur.fetchone()[0]
            cur.execute(f"PRAGMA table_info([{t}])")
            cols = [c[1] for c in cur.fetchall()]
            print(f"  {t}: {cnt} rows, cols={cols}")
        except Exception as e:
            print(f"  {t}: error - {e}")


def extract_all(state):
    print("\n" + "=" * 80)
    print("[STATE FULL DUMP]")
    if "channel_values" in state:
        state = state["channel_values"]
    keys = list(state.keys())
    print(f"  共 {len(keys)} 个字段: {keys}")

    print(f"\n--- 基础 ---")
    for k in [
        "session_id",
        "user_id",
        "user_input",
        "project_type",
        "analysis_mode",
        "created_at",
        "current_stage",
        "progress",
    ]:
        v = state.get(k)
        if v is not None:
            print(f"  {k}: {str(v)[:300]}")

    sr = state.get("structured_requirements")
    if sr:
        print(f"\n--- 结构化需求 ---")
        print(json.dumps(sr, indent=2, ensure_ascii=False)[:2000] if isinstance(sr, (dict, list)) else str(sr)[:2000])

    fa = state.get("feasibility_assessment")
    if fa:
        print(f"\n--- 可行性评估 ---")
        print(json.dumps(fa, indent=2, ensure_ascii=False)[:1500] if isinstance(fa, (dict, list)) else str(fa)[:1500])

    print(f"\n--- 问卷 ---")
    cq = state.get("calibration_questionnaire")
    if cq:
        if isinstance(cq, str):
            try:
                cq = json.loads(cq)
            except:
                pass
        if isinstance(cq, dict):
            qs = cq.get("questions", [])
            print(f"  calibration_questionnaire: {len(qs)} 个问题")
            for i, q in enumerate(qs):
                print(f"    Q{i+1}: {q.get('question', q.get('text', str(q)[:100]))}")
                opts = q.get("options", [])
                for o in opts:
                    print(f"        - {o}")
        else:
            print(f"  calibration_questionnaire: {str(cq)[:1500]}")

    ca = state.get("calibration_answers")
    if ca:
        print(f"\n  calibration_answers:")
        if isinstance(ca, dict):
            for k2, v2 in ca.items():
                print(f"    {k2}: {v2}")
        else:
            print(f"    {str(ca)[:1000]}")

    qr = state.get("questionnaire_responses")
    if qr:
        print(f"\n  questionnaire_responses:")
        if isinstance(qr, dict) and "entries" in qr:
            for e in qr["entries"]:
                print(f"    {e.get('id','?')}: Q={e.get('question','?')[:80]} A={e.get('value','?')}")
        else:
            print(f"    {str(qr)[:1000]}")

    qs2 = state.get("questionnaire_summary")
    if qs2:
        print(f"\n  questionnaire_summary: {str(qs2)[:800]}")

    for k in [
        "calibration_processed",
        "calibration_skipped",
        "progressive_questionnaire_step",
        "progressive_questionnaire_completed",
    ]:
        v = state.get(k)
        if v is not None:
            print(f"  {k}: {v}")

    print(f"\n--- 渐进式三步 ---")
    for k in [
        "extracted_core_tasks",
        "confirmed_core_tasks",
        "core_task_summary",
        "task_gap_filling_questionnaire",
        "gap_filling_answers",
        "task_completeness_analysis",
        "selected_dimensions",
        "selected_radar_dimensions",
        "radar_dimension_values",
        "dimension_weights",
    ]:
        v = state.get(k)
        if v is not None and v != {} and v != [] and v != "":
            print(f"\n  [{k}]:")
            if isinstance(v, (dict, list)):
                print(f"    {json.dumps(v, indent=2, ensure_ascii=False)[:2000]}")
            else:
                print(f"    {str(v)[:2000]}")

    print(f"\n--- 专家分配 ---")
    sa = state.get("strategic_analysis")
    if sa:
        if isinstance(sa, str):
            try:
                sa = json.loads(sa)
            except:
                pass
        if isinstance(sa, dict):
            print(f"  strategic_analysis keys: {list(sa.keys())}")
            roles = sa.get("selected_roles", [])
            print(f"\n  角色 ({len(roles)}):")
            for r in roles:
                if isinstance(r, dict):
                    print(f"    - {r.get('role_id','?')} ({r.get('display_name', r.get('name','?'))})")
                    print(f"      task: {r.get('assigned_task', r.get('task_description',''))[:200]}")
                    print(f"      weight: {r.get('weight', 'N/A')}")
                else:
                    print(f"    - {r}")
            td = sa.get("task_distribution")
            if td:
                print(f"\n  task_distribution:")
                print(f"    {json.dumps(td, indent=2, ensure_ascii=False)[:2000]}")
            eb = sa.get("execution_batches")
            if eb:
                print(f"\n  execution_batches ({len(eb)}):")
                for i, b in enumerate(eb):
                    print(f"    Batch {i+1}: {b}")
            eh = sa.get("expert_handoff")
            if eh:
                print(f"\n  expert_handoff:")
                print(f"    {json.dumps(eh, indent=2, ensure_ascii=False)[:1500]}")
            for k2 in sa:
                if k2 not in ["selected_roles", "task_distribution", "execution_batches", "expert_handoff"]:
                    v2 = sa[k2]
                    print(
                        f"\n  sa.{k2}: {json.dumps(v2, indent=2, ensure_ascii=False)[:500] if isinstance(v2, (dict,list)) else str(v2)[:500]}"
                    )
        else:
            print(f"  strategic_analysis: {str(sa)[:2000]}")

    for k in [
        "subagents",
        "execution_batches",
        "current_batch",
        "total_batches",
        "completed_batches",
        "active_agents",
        "completed_agents",
    ]:
        v = state.get(k)
        if v is not None and v != {} and v != []:
            print(f"  {k}: {json.dumps(v, indent=2, ensure_ascii=False)[:800] if isinstance(v, (dict,list)) else v}")

    dwp = state.get("deliverable_work_packages")
    if dwp:
        print(f"\n  deliverable_work_packages:")
        print(
            f"    {json.dumps(dwp, indent=2, ensure_ascii=False)[:2000] if isinstance(dwp, (dict,list)) else str(dwp)[:2000]}"
        )

    print(f"\n--- 专家结果 ---")
    ar = state.get("agent_results", {})
    if ar:
        print(f"  {len(ar)} 个专家:")
        for k, v in ar.items():
            print(f"\n  [{k}]:")
            if isinstance(v, dict):
                print(f"    keys: {list(v.keys())}")
                for sk, sv in v.items():
                    sv_s = json.dumps(sv, indent=2, ensure_ascii=False) if isinstance(sv, (dict, list)) else str(sv)
                    print(f"    {sk}: {sv_s[:400]}")
            else:
                print(f"    {str(v)[:500]}")
    else:
        print("  无结果")

    print(f"\n--- 质量 ---")
    for k in ["review_round", "best_score", "role_quality_review_result", "task_guard_result"]:
        v = state.get(k)
        if v is not None:
            print(f"  {k}: {json.dumps(v, indent=2, ensure_ascii=False)[:500] if isinstance(v, (dict,list)) else v}")

    fr = state.get("final_report")
    if fr:
        print(f"\n--- 最终报告 ---")
        if isinstance(fr, dict):
            print(f"  keys: {list(fr.keys())}")
            print(json.dumps(fr, indent=2, ensure_ascii=False)[:3000])
        elif isinstance(fr, str):
            print(f"  len={len(fr)}")
            print(fr[:3000])

    agr = state.get("aggregated_results")
    if agr:
        print(f"\n--- 聚合结果 ---")
        print(
            json.dumps(agr, indent=2, ensure_ascii=False)[:2000] if isinstance(agr, (dict, list)) else str(agr)[:2000]
        )

    print(f"\n--- 其他非空 ---")
    shown = {
        "session_id",
        "user_id",
        "user_input",
        "project_type",
        "analysis_mode",
        "created_at",
        "current_stage",
        "progress",
        "structured_requirements",
        "feasibility_assessment",
        "calibration_questionnaire",
        "calibration_answers",
        "questionnaire_responses",
        "questionnaire_summary",
        "calibration_processed",
        "calibration_skipped",
        "progressive_questionnaire_step",
        "progressive_questionnaire_completed",
        "extracted_core_tasks",
        "confirmed_core_tasks",
        "core_task_summary",
        "task_gap_filling_questionnaire",
        "gap_filling_answers",
        "task_completeness_analysis",
        "selected_dimensions",
        "selected_radar_dimensions",
        "radar_dimension_values",
        "dimension_weights",
        "strategic_analysis",
        "subagents",
        "execution_batches",
        "current_batch",
        "total_batches",
        "completed_batches",
        "active_agents",
        "completed_agents",
        "deliverable_work_packages",
        "agent_results",
        "review_round",
        "best_score",
        "role_quality_review_result",
        "task_guard_result",
        "final_report",
        "aggregated_results",
    }
    for k in keys:
        if k not in shown:
            v = state.get(k)
            if v is not None and v != "" and v != {} and v != [] and v != 0 and v != False:
                vs = json.dumps(v, indent=2, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
                print(f"  {k}: {vs[:400]}{'...' if len(vs)>400 else ''}")


def main():
    print(f"目标: {TARGET_ID}")
    print(f"Python: {sys.version}\n")

    # 直接从 workflow.db 提取（已确认数据在这里）
    db_path = "data/checkpoints/workflow.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 获取 checkpoint 数量
    cur.execute("SELECT COUNT(*) FROM checkpoints WHERE thread_id = ?", (TARGET_ID,))
    cnt = cur.fetchone()[0]
    print(f"checkpoints 数量: {cnt}")

    # 获取最新 checkpoint
    cur.execute(
        "SELECT thread_id, checkpoint_id, checkpoint_ns, type, metadata, checkpoint FROM checkpoints WHERE thread_id = ? ORDER BY checkpoint_id DESC LIMIT 1",
        (TARGET_ID,),
    )
    row = cur.fetchone()

    if not row:
        print("NOT FOUND")
        conn.close()
        return

    tid, cpid, cpns, tp, meta_raw, ckpt_raw = row
    print(f"thread_id: {tid}")
    print(f"checkpoint_id: {cpid}")
    print(f"checkpoint_ns: {cpns}")
    print(f"type: {tp}")
    print(f"metadata type: {type(meta_raw).__name__}, len={len(meta_raw) if meta_raw else 0}")
    print(f"checkpoint type: {type(ckpt_raw).__name__}, len={len(ckpt_raw) if ckpt_raw else 0}")

    # 解码 metadata
    result = {"_meta": {"target_id": TARGET_ID, "checkpoint_id": cpid, "checkpoints_count": cnt}}

    if meta_raw:
        if isinstance(meta_raw, str):
            try:
                result["metadata"] = json.loads(meta_raw)
                print(f"\nmetadata (JSON): {json.dumps(result['metadata'], indent=2, ensure_ascii=False)[:500]}")
            except:
                result["metadata_raw"] = meta_raw[:500]
        elif isinstance(meta_raw, bytes):
            try:
                import msgpack

                result["metadata"] = msgpack.unpackb(meta_raw, raw=False)
                print(f"\nmetadata (msgpack): {json.dumps(result['metadata'], indent=2, ensure_ascii=False)[:500]}")
            except ImportError:
                print("需要 msgpack")
            except Exception as e:
                print(f"metadata 解码失败: {e}")

    # 解码 checkpoint (核心数据)
    state = None
    if ckpt_raw:
        if isinstance(ckpt_raw, str):
            try:
                state = json.loads(ckpt_raw)
            except:
                pass
        elif isinstance(ckpt_raw, bytes):
            try:
                import msgpack

                state = msgpack.unpackb(ckpt_raw, raw=False)
            except ImportError:
                print("\n需要安装 msgpack: pip install msgpack")
            except Exception as e:
                print(f"\ncheckpoint 解码失败: {e}")
                # 尝试 JSON
                try:
                    state = json.loads(ckpt_raw.decode("utf-8"))
                except:
                    pass

    if state:
        # 处理 LangGraph checkpoint 格式
        if isinstance(state, dict) and "channel_values" in state:
            print(f"\ncheckpoint 顶层键: {list(state.keys())}")
            cv = state["channel_values"]
        elif isinstance(state, dict):
            cv = state
        else:
            print(f"\ncheckpoint 类型: {type(state).__name__}")
            cv = {}

        if cv:
            print(f"\nchannel_values 键 ({len(cv)}): {list(cv.keys())}")
            result["state"] = {}

            # 逐个提取关键字段
            for key in cv:
                val = cv[key]
                if val is not None and val != "" and val != {} and val != [] and val != 0 and val != False:
                    # 确保可 JSON 序列化
                    try:
                        json.dumps(val, ensure_ascii=False)
                        result["state"][key] = val
                    except (TypeError, ValueError):
                        result["state"][key] = str(val)[:5000]

    # 也获取 writes 数据
    cur.execute("SELECT COUNT(*) FROM writes WHERE thread_id = ?", (TARGET_ID,))
    wcnt = cur.fetchone()[0]
    print(f"\nwrites 数量: {wcnt}")
    result["_meta"]["writes_count"] = wcnt

    conn.close()

    # 保存完整结果到文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)

    fsize = os.path.getsize(OUTPUT_FILE)
    print(f"\n结果已保存到 {OUTPUT_FILE} ({fsize} bytes)")

    # 打印关键摘要
    if "state" in result:
        s = result["state"]
        print(f"\n{'='*60}")
        print(f"[摘要]")
        print(f"  user_input: {str(s.get('user_input','N/A'))[:200]}")
        print(f"  project_type: {s.get('project_type','N/A')}")
        print(f"  current_stage: {s.get('current_stage','N/A')}")
        print(f"  progress: {s.get('progress','N/A')}")
        print(f"  analysis_mode: {s.get('analysis_mode','N/A')}")
        print(f"  字段总数: {len(s)}")


if __name__ == "__main__":
    main()
