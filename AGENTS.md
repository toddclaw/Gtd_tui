# AI Agent Guidance for Gtd_tui

Primary conventions live in [CLAUDE.md](CLAUDE.md). This file highlights key process steps for agents.

## Before Starting

- **Branch sanity** — `git branch --show-current`, `git fetch origin`, `git pull origin <branch>`. See CLAUDE.md → Before starting work (branch sanity).

## After Substantive Work

- **Closing a body of work** — Reflect, propose 2–4 improvements, let the user pick one to implement next. Do not auto-implement suggestions without their choice. See CLAUDE.md → Closing a body of work (reflection and follow-up).

## Releases

- Merging the release PR does **not** finish the release — bump version on `main`, tag `vX.Y.Z`, push. Use **`gh pr merge --auto`** only after **`pre_push_check`** passes. See CLAUDE.md → Release Process.
