# Flaky Tests Registry

## Purpose

Track unstable tests separately from the main quality gate. Tests listed here should be marked with `@pytest.mark.flaky` and run by the isolated `flaky-isolated` job in `.github/workflows/tests.yml`.

## Current Status

- Total flaky tests: `0`
- Last updated: `2026-02-25`
- Verification: `pytest -m flaky` currently returns no collected flaky tests (expected for empty baseline).

## Add Rule

When adding a flaky test:

1. Add `@pytest.mark.flaky` to the test.
2. Register it in the table below with reason and owner.
3. Add a target fix date and keep status updated.

## Registry

| Test Path | Symptom | Root Cause | Owner | Target Fix Date | Status |
|---|---|---|---|---|---|
| _None_ | _N/A_ | _N/A_ | _N/A_ | _N/A_ | _Stable baseline_ |
