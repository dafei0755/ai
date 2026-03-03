from __future__ import annotations

import argparse
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


def _parse_timestamp(line: str) -> Optional[datetime]:
    # 示例: 2026-03-02 20:40:35.219 | INFO ...
    m = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)", line)
    if not m:
        return None
    ts = m.group(1)
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    return None


def analyze_log(file_path: Path, last_hours: int = 24) -> dict:
    cutoff = datetime.now() - timedelta(hours=last_hours)

    decision_lines = 0
    step2_skips = 0
    step3_skips = 0
    shadow_count = 0

    flow_counter: Counter[str] = Counter()
    goto_counter: Counter[str] = Counter()
    reason_counter: Counter[str] = Counter()

    flow_re = re.compile(r"flow=([^\s]+)")
    goto_re = re.compile(r"goto=([^\s]+)")
    reason_re = re.compile(r"reasons=\[(.*?)\]")

    with file_path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue

            ts = _parse_timestamp(line)
            if ts and ts < cutoff:
                continue

            if "[SmartSkipDecision]" in line:
                decision_lines += 1
                if "shadow=true" in line:
                    shadow_count += 1

                fm = flow_re.search(line)
                if fm:
                    flow_counter[fm.group(1)] += 1

                gm = goto_re.search(line)
                if gm:
                    goto_counter[gm.group(1)] += 1

            if "[SmartSkip] Step2(雷达图)跳过" in line:
                step2_skips += 1
                rm = reason_re.search(line)
                if rm:
                    for token in [t.strip().strip("'\"") for t in rm.group(1).split(",") if t.strip()]:
                        reason_counter[token] += 1

            if "[SmartSkip] Step3(信息补全)跳过" in line:
                step3_skips += 1
                rm = reason_re.search(line)
                if rm:
                    for token in [t.strip().strip("'\"") for t in rm.group(1).split(",") if t.strip()]:
                        reason_counter[token] += 1

    total_skips = step2_skips + step3_skips
    skip_rate = (total_skips / decision_lines) if decision_lines else 0.0

    return {
        "window_hours": last_hours,
        "decision_lines": decision_lines,
        "shadow_count": shadow_count,
        "step2_skips": step2_skips,
        "step3_skips": step3_skips,
        "total_skips": total_skips,
        "skip_rate": skip_rate,
        "flows": flow_counter,
        "gotos": goto_counter,
        "top_reasons": reason_counter,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Smart Nodes Self-Skip logs")
    parser.add_argument("--file", default="logs/server.log", help="Path to server log file")
    parser.add_argument("--last-hours", type=int, default=24, help="Time window in hours")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        raise SystemExit(f"Log file not found: {file_path}")

    data = analyze_log(file_path, args.last_hours)

    print("=" * 72)
    print("Smart Nodes Self-Skip 观测报告")
    print("=" * 72)
    print(f"窗口: 最近 {data['window_hours']} 小时")
    print(f"决策日志条数: {data['decision_lines']}")
    print(f"Shadow 条数: {data['shadow_count']}")
    print(f"Step2 跳过次数: {data['step2_skips']}")
    print(f"Step3 跳过次数: {data['step3_skips']}")
    print(f"总跳过次数: {data['total_skips']}")
    print(f"跳过率(粗略): {data['skip_rate']:.2%}")

    print("\nFlow 命中分布:")
    if data["flows"]:
        for k, v in data["flows"].most_common():
            print(f"  - {k}: {v}")
    else:
        print("  (无)")

    print("\nGoto 分布:")
    if data["gotos"]:
        for k, v in data["gotos"].most_common():
            print(f"  - {k}: {v}")
    else:
        print("  (无)")

    print("\nTop reason codes:")
    if data["top_reasons"]:
        for k, v in data["top_reasons"].most_common(10):
            print(f"  - {k}: {v}")
    else:
        print("  (无)")

    print("\n建议阈值:")
    print("  - Shadow 阶段: 仅看分布稳定性，不看跳过率")
    print("  - 实跳阶段: 跳过率 > 35% 或 strategy_light_flow 占比异常上升时回滚")


if __name__ == "__main__":
    main()
