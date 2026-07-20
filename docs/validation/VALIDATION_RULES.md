# Validation Rules

Run repository-defined commands only.

Expected categories:

## Backend

- Format
- Lint
- Type check
- Tests

## Frontend

- Lint
- Type check
- Build

## Runtime

- Docker Compose configuration
- Task-specific runtime validation

Rules:

- Run task-specific checks first.
- Run full validation before commit.
- Do not claim success without execution.
- Do not weaken tests.
- Record exact commands in the progress log.