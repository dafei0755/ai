"""运行 v8.0 测试并输出所有失败详情"""
import subprocess
import sys

test_files = [
    "tests/unit/services/test_project_specific_dimension_generator.py",
    "tests/integration/test_v8_radar_integration.py",
    "tests/regression/test_v8_radar_regression.py",
    "tests/e2e/test_v8_questionnaire_e2e.py",
]

results_lines = []
for test_file in test_files:
    results_lines.append(f"\n{'='*60}")
    results_lines.append(f"FILE: {test_file}")
    results_lines.append("=" * 60)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "--tb=short", "-q", "--no-header"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=180,
    )
    out = (result.stdout or b"").decode("utf-8", errors="replace")
    err = (result.stderr or b"").decode("utf-8", errors="replace")
    results_lines.append(out)
    if err:
        results_lines.append("--- STDERR ---")
        results_lines.append(err[:1000])
    results_lines.append(f"EXIT: {result.returncode}")
    print(f"{test_file}: EXIT={result.returncode}")

full = "\n".join(results_lines)
with open("_v8_test_results.txt", "w", encoding="utf-8") as f:
    f.write(full)
print("\nDone -> _v8_test_results.txt")
