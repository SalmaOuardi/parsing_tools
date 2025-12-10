## Parsing Playbook (Index)

Use this as the front door for the docs set—what lives where and when to update it. Canonical content is split so we avoid repetition.

### Where things live
- `parser_overview.md` — mission, scope, corpus, tooling, configuration, current status, and phase plan (canonical).
- `parser_experiments.md` — run history, coverage snapshots, parser reliability notes, GPT benchmark details (canonical log).
- `parser_clause_comparison.md` — clause-aware chunking rationale and examples.
- `parser_strategy.md` — short decision snapshot + near-term actions (see overview for the full plan).
- `todo.md` — active task list.
- `weekly_updates_*.md`, `progress_*.md` — dated status reports (add new ones; don’t edit old ones).

### How to log an experiment
1. Run a parser via the CLI with `RUN_LABEL` / `RUN_NOTES` set.
2. Payloads and metrics auto-save (see `parser_overview.md` for exact paths).
3. Append a row in `parser_experiments.md` with date, label, parser, env, key params, results, and file paths when relevant.

### When to update which file
- Plan changes? Update `parser_overview.md` (mission/status) and, if needed, `parser_strategy.md` (decision snapshot).
- New run? Update `parser_experiments.md`; if it affects clause handling, also note in `parser_clause_comparison.md`.
- New tasks? Update `todo.md`.
- Weekly sync? Add a new `weekly_updates_<date>.md` or `progress_<date>.md`.
