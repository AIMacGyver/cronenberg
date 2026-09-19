---
name: cronenberg-lock
description: >
  Lock a Cronenberg task before implementation by defining its goal, scope,
  compatibility risks, and observable completion criteria. Use when starting
  a code change, planning a pull request, or narrowing a requested slice.
---

# Cronenberg task lock

Write the task card in the conversation before editing repository files.

## Task card

Complete every field:

**Goal** — one observable end state, not a list of implementation steps.

**In scope** — the behavior, files, or interfaces this task may change.

**Out of scope** — adjacent work and cleanup that this task will not include.

**Compatibility risks** — identify any possible effect on public Python APIs,
CLI output or exit codes, configuration behavior, notebook analysis, Flake8
integration, result ordering, or exception behavior. Write "none expected"
only after considering each relevant boundary.

**Done** — observable completion criteria. Name the expected behavior or
artifact and the commands that will verify it.

## Lock rules

1. Keep the card to one task and one pull request.
2. If the goal or completion criteria are ambiguous, ask one focused question
   or state a narrow interpretation before implementation.
3. Treat compatibility changes as in scope only when the task explicitly
   requests them.
4. Do not include opportunistic refactors, repository-wide cleanup, or new
   tooling.
5. Stop after the card unless the user has already requested implementation;
   then follow the [Cronenberg ship skill](../cronenberg-ship/SKILL.md).
