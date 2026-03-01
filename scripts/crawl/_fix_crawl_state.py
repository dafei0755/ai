"""临时脚本：验证状态文件修复"""
import json
from pathlib import Path

f = Path(__file__).parent / "data" / "crawler_state" / "schedule_state.json"
state = json.loads(f.read_text(encoding="utf-8"))
print("phase:", state.get("phase"))
print("running_task:", state.get("running_task"))
print("stop_requested:", state.get("stop_requested"))
