import subprocess, sys

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "pytest",
        "tests/api/test_analysis_endpoints.py::TestAnalysisStartEndpoint::test_start_analysis_success",
        "--tb=line",
        "--no-header",
        "-q",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
)
print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
print(result.stderr[-500:] if result.stderr else "")
