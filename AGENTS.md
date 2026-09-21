# Cronenberg contributor policy

Cronenberg modernizes Radon's packaging and development workflow without
silently changing Radon behavior.

## Compatibility boundary

Unless a task explicitly changes them, preserve:

- public Python APIs;
- CLI output and exit codes;
- configuration behavior;
- result ordering; and
- exception behavior.

Call out any intentional compatibility change in the task card and pull
request.

## Project authority

- Treat `pyproject.toml` and `uv.lock` as authoritative.
- Use `uv`, Ruff, pytest, pre-commit, and the existing `just` recipes. Do not
  introduce duplicate tooling.
- Add concise Google-style docstrings for new or changed public APIs. Do not
  enable repository-wide Ruff `D` rules against legacy code.

## Delivery policy

- Keep each pull request focused on one purpose.
- Make logical, independently working commits with a Conventional Commit
  prefix: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, or
  `build`.

## Skills

For implementation work, follow these skills in order:

1. [Cronenberg task lock](.agents/skills/cronenberg-lock/SKILL.md) — define the
   task card and observable completion criteria before editing.
2. [Cronenberg ship](.agents/skills/cronenberg-ship/SKILL.md) — implement the
   smallest compatible diff, verify it, and prepare the handoff.
