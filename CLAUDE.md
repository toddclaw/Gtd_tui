# CLAUDE.md — AI Assistant Guide for Gtd_tui

## Project Overview

**Gtd_tui** is a terminal user interface (TUI) application implementing the GTD (Getting Things Done) productivity methodology. The project is written in Rust and is currently in its early initialization stage.

- **Language:** Rust
- **Paradigm:** TUI (Terminal User Interface)
- **Methodology:** GTD (Getting Things Done) task/project management
- **Repository:** toddclaw/Gtd_tui

---

## Repository Status

This project was recently initialized. As of the initial commit, only a `README.md` exists. There is no source code, Cargo manifest, or build configuration yet. When implementing features, follow the conventions below from the start.

---

## Development Setup

### Prerequisites

- Rust toolchain (stable channel recommended): install via [rustup](https://rustup.rs/)
- Cargo (bundled with Rust)

### Getting Started

```bash
# Clone the repository
git clone <repo-url>
cd Gtd_tui

# Build (once Cargo.toml exists)
cargo build

# Run
cargo run

# Run tests
cargo test

# Check for issues without building
cargo check

# Format code
cargo fmt

# Lint
cargo clippy -- -D warnings
```

---

## Expected Project Structure

When source code is added, follow this conventional Rust project layout:

```
Gtd_tui/
├── CLAUDE.md               # This file
├── README.md               # User-facing documentation
├── Cargo.toml              # Package manifest and dependencies
├── Cargo.lock              # Locked dependency versions (commit this)
├── .gitignore              # Rust gitignore (target/, etc.)
├── src/
│   ├── main.rs             # Application entry point
│   ├── app.rs              # Core application state and event loop
│   ├── ui.rs               # TUI rendering logic
│   ├── gtd/                # GTD domain logic
│   │   ├── mod.rs
│   │   ├── task.rs         # Task data structures
│   │   ├── project.rs      # Project groupings
│   │   └── context.rs      # GTD contexts (@home, @work, etc.)
│   └── storage/            # Persistence layer
│       ├── mod.rs
│       └── file.rs         # File-based storage (JSON/TOML/SQLite)
└── tests/                  # Integration tests
    └── integration_test.rs
```

---

## Technology Choices (Recommended)

### TUI Framework

Prefer **[ratatui](https://github.com/ratatui-org/ratatui)** — the actively maintained fork of tui-rs. It provides a retained-mode widget system with a crossterm backend.

```toml
[dependencies]
ratatui = "0.29"
crossterm = "0.28"
```

### Event Handling

Use **crossterm** for keyboard/mouse event polling, paired with ratatui's rendering loop.

### Storage

Start with a simple file-based approach (JSON or TOML) using **serde**:

```toml
[dependencies]
serde = { version = "1", features = ["derive"] }
serde_json = "1"
# or
toml = "0.8"
```

Consider **SQLite via rusqlite** if relational querying of tasks/projects is needed.

### Error Handling

Use **[anyhow](https://github.com/dtolnay/anyhow)** for application-level errors and **[thiserror](https://github.com/dtolnay/thiserror)** for library/domain errors.

```toml
[dependencies]
anyhow = "1"
thiserror = "2"
```

---

## GTD Domain Concepts

When implementing the GTD methodology, respect these core concepts:

| Concept | Description |
|---|---|
| **Inbox** | Uncategorized capture of all incoming tasks/ideas |
| **Project** | Any outcome requiring more than one action step |
| **Next Action** | The immediate physical/digital action to move a project forward |
| **Context** | Location/tool tags for actions (e.g., `@computer`, `@phone`, `@errands`) |
| **Waiting For** | Items delegated to others, pending their response |
| **Someday/Maybe** | Low-priority items not actively being pursued |
| **Reference** | Non-actionable information stored for future use |
| **Weekly Review** | Regular review of all lists to keep the system current |

---

## Code Conventions

### General Rust Style

- Follow standard Rust formatting (`cargo fmt` enforced)
- No `clippy` warnings (`cargo clippy -- -D warnings`)
- Use `snake_case` for functions, variables, modules
- Use `PascalCase` for types, traits, enums
- Use `SCREAMING_SNAKE_CASE` for constants
- Prefer `Result<T, E>` over `unwrap()`/`expect()` in library code; `expect()` is acceptable in `main` for unrecoverable startup failures

### Error Handling

- Domain errors: define with `thiserror`
- Application/glue code: propagate with `anyhow`
- Never silently swallow errors with `let _ = ...` unless explicitly intentional and commented

### Modules

- Keep modules focused and single-purpose
- Prefer `mod.rs` files to re-export a clean public API from submodules
- Mark internal types/functions as `pub(crate)` rather than `pub` when not part of the public API

### TUI Architecture Pattern

Follow the **Elm Architecture** (Model-Update-View) pattern common in ratatui apps:

```rust
// State
struct App { /* ... */ }

// Event handling → state mutation
impl App {
    fn handle_event(&mut self, event: Event) -> anyhow::Result<()> { /* ... */ }
}

// Pure rendering from state
fn ui(frame: &mut Frame, app: &App) { /* ... */ }
```

Keep rendering (`ui`) and state mutation (`handle_event`) strictly separated.

### Testing

- Unit test domain logic (GTD data structures, filtering, sorting)
- Integration test storage layer
- TUI rendering tests are optional but welcome (ratatui provides test utilities)
- Run `cargo test` before every commit

---

## Git Workflow

### Branching

- Development happens on feature branches: `claude/<description>-<id>`
- Do not push directly to `master`/`main`

### Commit Messages

Use clear, imperative commit messages:

```
Add inbox task capture with keyboard shortcut
Fix project deletion leaving orphaned tasks
Refactor storage layer to use serde traits
```

### Pre-commit Checklist

- [ ] `cargo fmt` — code is formatted
- [ ] `cargo clippy -- -D warnings` — no lint warnings
- [ ] `cargo test` — all tests pass
- [ ] `cargo check` — project compiles

---

## Key Files Reference

| File | Purpose |
|---|---|
| `README.md` | User-facing project description |
| `CLAUDE.md` | This file — AI assistant conventions |
| `Cargo.toml` | Rust package manifest (add here) |
| `src/main.rs` | Entry point — keep thin, delegate to `app.rs` |
| `src/app.rs` | Application state, event loop |
| `src/ui.rs` | All ratatui rendering logic |

---

## Notes for AI Assistants

- This project is in its **initialization phase** — no source code exists yet. When asked to implement features, scaffold the Rust project structure first (`Cargo.toml`, `src/main.rs`).
- Always run `cargo check` (or suggest it) after adding/modifying Rust source files.
- Prefer **minimal, focused changes** — avoid adding speculative abstractions before the design stabilizes.
- When adding dependencies to `Cargo.toml`, check that versions are recent and the crates are actively maintained.
- Storage format decisions (JSON vs TOML vs SQLite) should be confirmed with the user before implementation, as they affect migration complexity later.
- Default data directory should follow XDG conventions (`~/.local/share/gtd_tui/` on Linux, platform-appropriate on macOS/Windows) using the `dirs` crate.
