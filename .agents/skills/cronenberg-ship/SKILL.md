---
name: cronenberg-ship
description: >
  Deliver a locked Cronenberg task with the smallest compatible diff,
  incremental Ruff checks, pytest evidence, coherent commits, and explicit
  documentation decisions. Use when implementing or shipping a scoped change.
---

# Cronenberg ship

Implement the locked task card in the current checkout. Preserve the
compatibility boundary in `AGENTS.md` unless the card explicitly changes it.

## Before editing

1. Confirm the task card contains a goal, in-scope work, out-of-scope work,
   compatibility risks, and observable completion criteria. Write the missing
   fields before implementation if necessary.
2. Inspect the checkout and do not disturb unrelated local changes.
3. Select the smallest viable diff that can meet the completion criteria.

## Implement

- Keep implementation and tests focused on the locked behavior.
- Add or update tests whenever behavior changes or a defect is fixed.
- Add concise Google-style docstrings for new or changed public APIs.
- Do not combine feature work with unrelated formatting, modernization, or
  refactoring.
- Treat `pyproject.toml` and `uv.lock` as authoritative and use the existing
  `uv`, Ruff, pytest, pre-commit, and `just` setup.

## Verify incrementally

During iteration, run the narrowest useful tests:

```bash
uv run pytest path/to/relevant_test.py
```

For touched Python files, run Ruff only on those files:

```bash
uv run ruff check path/to/changed.py path/to/test_changed.py
```

The repository inherits 128 non-blocking Ruff findings. Do not hide them with
broad ignores or mix repository-wide cleanup into a feature pull request.

Before handoff, run the full test suite:

```bash
uv run pytest
```

Run relevant existing `just` recipes and pre-commit checks when the task
touches their scope. Validate `uv.lock` after dependency or project metadata
changes:

```bash
uv lock --check
```

## Documentation and changelog

- Update documentation when users or contributors need new instructions.
- Update the changelog for user-visible behavior changes when the repository's
  release practice calls for it.
- If neither is needed, state that decision in the handoff or pull request.

## Commit and hand off

- Commit frequently at coherent, independently working points.
- Give each commit one logical purpose and use an allowed Conventional Commit
  prefix from `AGENTS.md`.
- Do not commit a knowingly broken intermediate state.
- Stop when the task card is complete or a blocker prevents completion.
- Report the changed files, commit hashes, exact commands and results,
  compatibility impact, and documentation/changelog decision.
