# Pre-release Checklist

## Quality Gates

- [ ] `CI` workflow passed (root check + backend gate + frontend build)
- [ ] `Automated Tests` fast lane passed
- [ ] Required full tests completed (`backend-tests-full` / matrix) for release branch

## Regression and Safety

- [ ] API smoke regression passed:
  - `tests/api/test_session_endpoints.py`
  - `tests/api/test_analysis_endpoints.py`
  - `tests/unit/api/test_output_intent_file_upload.py`
- [ ] No new unallowlisted findings in `security-baseline-report.json`

## Code Quality

- [ ] Ruff gate passed for backend + tests scope
- [ ] No unresolved flaky test entries without target fix date

## Documentation

- [ ] `README_TESTING.md` updated when workflow/threshold changed
- [ ] `CHANGELOG.md` includes release notes for CI/quality-impacting changes
- [ ] `Release Signoff` issue created from template and fully signed
