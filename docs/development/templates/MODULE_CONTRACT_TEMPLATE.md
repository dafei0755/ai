# Module Contract Template

Use this template when creating or formalizing a governed module.

```text
module_id:
name:
status: candidate / governed / implemented / deprecated
current_version:
owner_paths:
feature_ledger_entry:
```

## 1. Purpose

```text
What user-visible or runtime capability does this module own?
What should never be handled by this module?
```

## 2. Public Contract

```text
inputs:
outputs:
error_codes:
state_transitions:
required_runtime_behavior:
forbidden_fallbacks:
```

## 3. Entry Points

```text
python_imports:
api_routes:
frontend_pages_or_components:
scripts:
```

## 4. Dependencies

```text
upstream_modules:
downstream_modules:
infrastructure:
registries_or_configs:
```

## 5. Version Chain

```text
current_authoritative_version:
base_commit:
head_commit:
rollback_target:
next_target_version:
```

## 6. Guard Tests

```text
unit_tests:
service_tests:
api_tests:
frontend_tests:
smoke_tests:
```

## 7. Change Rules

```text
allowed_changes:
requires_ledger_update:
requires_registry_update:
requires_migration_plan:
forbidden_changes:
```

## 8. Completion Evidence

```text
branch:
base_commit:
head_commit:
verification:
ledger_updated: yes/no
module_registry_updated: yes/no
rollback_target:
residual_risks:
```