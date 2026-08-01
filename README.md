# Campus Agent

Campus Agent is a web-based AI assistant for campus recruitment planning.

It helps users:

- Set job search goals.
- Track recruitment campaigns.
- Manage applications.
- Generate an AI daily plan.
- Track schedules and reminders.

## MVP

The MVP uses a single Loop Agent. The database is the source of truth. The Planner reads current business state through tools and generates today's todos.

## Project Structure

```text
backend/      Backend service
frontend/     Web dashboard
docs/         Product and engineering specs
tests/        Cross-project tests
work/         Scratch files and experiments
```

## Development Rule

Read `AGENTS.md` and `docs/EngineeringSpec.md` before implementation.
