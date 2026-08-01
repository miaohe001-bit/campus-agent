# Campus Agent Coding Instructions

## Product

Campus Agent is a web-based AI assistant for campus recruitment planning.

The implementation must follow:

- `docs/EngineeringSpec.md`
- PRD files under `docs/prd/`

If documents conflict, `docs/EngineeringSpec.md` has priority.

## Architecture Rules

- Use a single Loop Agent for MVP.
- Do not implement Multi-Agent.
- Do not implement long-term memory for MVP.
- The database is the source of truth.
- Planner must not access the database directly.
- Planner only reads or writes through tools.
- Runtime only orchestrates loops and tool calls.
- Deterministic logic belongs in Business Services.
- Recruitment Events are append-only.
- Write tools must be idempotent.

## Development Rules

- Implement one milestone at a time.
- Do not add product features not defined in the specs.
- Before large changes, provide a short implementation plan.
- After changes, report modified files, validation run, and remaining assumptions.
- Keep backend, frontend, runtime, tools, and business services separated.
