"""Run API tests and save result"""
import subprocess
import sys
import os

os.chdir(r"d:\11-20\langgraph-design")

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/api/", "--tb=line", "-q", "--no-header"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=r"d:\11-20\langgraph-design",
)

output = result.stdout + result.stderr
# Save full output
with open(r"d:\11-20\langgraph-design\_api_test_result.txt", "w", encoding="utf-8") as f:
    f.write(output)

# Print last 50 lines
lines = output.splitlines()
for line in lines[-50:]:
    print(line)
print(f"\nReturn code: {result.returncode}")
