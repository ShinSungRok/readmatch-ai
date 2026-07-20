# Development Workflow

For every Task:

1. Read instructions and current progress.
2. Run `git status`.
3. Review related code and tests.
4. Reuse existing components.
5. Implement only approved scope.
6. Add or update tests.
7. Run task-specific validation.
8. Run full validation.
9. Review `git status` and `git diff`.
10. Update progress log.
11. Commit only Task files.
12. Report and STOP.

Rules:

- One Task, one commit.
- Do not continue after completion.
- Do not overwrite unrelated changes.
- Do not weaken tests.
- Do not commit failing code.
- Review-only instructions must not modify files.