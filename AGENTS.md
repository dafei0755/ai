<!-- CHANGE_SAFETY_START -->
## Change Safety And Rollback

Before editing tracked project files in this repository, establish a recovery boundary.

Required pre-edit protocol:

1. Run `git status --short`.
2. Identify whether target files already contain user or prior-session changes.
3. If the tree is dirty, do not assume all changes are yours.
4. For important or cross-module work, create or request a Git checkpoint before editing.
5. For important untracked files, add them to the checkpoint or record a separate backup/manifest before relying on rollback.
6. Edit only files in the stated task scope.
7. After editing, review `git diff -- <paths>` and run verification that matches the affected path.

Rollback discipline:

- Prefer Git checkpoints, commits, tags, branches, or worktrees over ad hoc file copies.
- Use backups only for important files not yet protected by Git.
- Never use `git reset --hard`, `git checkout -- .`, `git clean -fd`, `git clean -fdx`, `git stash -u`, or `git stash --all` without explicit user approval.
- Do not revert, overwrite, or delete changes you did not make.
- If a file or hunk must be reverted, target the exact path or hunk and confirm it is within the current task scope.

Detailed policy: `docs/development/CHANGE_SAFETY_AND_ROLLBACK_PROTOCOL.md`.
<!-- CHANGE_SAFETY_END -->



<!-- DIRTY_WORKTREE_START -->
## Dirty Worktree Governance

When `git status --short` shows many existing `M` or `??` entries, do not treat the whole tree as one task.

Required protocol:

1. Classify the tree by dirty level `G0-G4`.
2. Group files into intent buckets before staging or rollback.
3. Never use `git add .`, full-tree stash, full-tree clean, or broad restore in a dirty tree without explicit approval.
4. For G3/G4 states, prefer narrow edits, bucket-specific checkpoints, or a separate worktree for new feature work.
5. Treat important untracked docs, tests, schemas, registries, and `sf/` assets as project assets until classified.

Detailed policy: `docs/development/DIRTY_WORKTREE_GOVERNANCE_PROTOCOL.md`.
<!-- DIRTY_WORKTREE_END -->

<!-- WRITE_RELIABILITY_START -->
## Agent Write Reliability

Large file edits must be split into small, reviewable patches. Do not let one write method block the task.

Required write protocol:

1. Prefer narrow patch hunks for manual edits.
2. For large documents or broad mechanical rewrites, split by section or file and verify after each step.
3. If a write command appears stalled for more than 60 seconds, stop using that method and switch to a smaller patch or controlled BOM-free atomic write.
4. Before editing a dirty or untracked target file, read the relevant current content and preserve existing user or prior-session changes.
5. After each meaningful edit, run `git diff -- <paths>` or an equivalent targeted file check.
6. Avoid broad searches or huge command output while diagnosing a write issue; use targeted `rg`, CodeGraph, or file reads.
7. Never overwrite tracked source files with shell write commands when a small patch is sufficient.

Detailed policy: `docs/development/AGENT_WRITE_AND_RUN_RELIABILITY_PROTOCOL.md`.
<!-- WRITE_RELIABILITY_END -->

<!-- CODEGRAPH_START -->
## CodeGraph

Use CodeGraph as the default code-structure entry point when a task involves code understanding, symbol lookup, call paths, impact analysis, or refactoring safety.

Use CodeGraph for structure:

- Locate symbols, components, services, and API routes.
- Understand who calls a symbol and what it calls.
- Trace entry points to core services, templates, models, and output layers.
- Estimate upstream and downstream impact before refactoring.

Use `rg` or live file reads for literal text, configuration values, comments, Markdown, generated data, and non-symbol searches.

Discipline:

- Structure and relationships come from CodeGraph; exact code facts come from live files.
- Never edit solely from CodeGraph line numbers. Index line numbers can drift.
- If CodeGraph conflicts with live files, trust live files and check `codegraph status .`.
- For cross-module or core-flow changes, check callers and callees. For larger refactors, run impact analysis first.
- Tests should follow the affected chain, not only the edited file.

If there is no `.codegraph/` directory at the repo root, skip CodeGraph entirely.
<!-- CODEGRAPH_END -->
