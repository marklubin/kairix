**Beta  Test Final MVP Backlog**

| # | Feature | Design/Details | Effort Estimate |
|---|---------|----------------|-----------------|
| 1 | **Manual testing on a fresh instance** | Full run-through on clean install; catch config rot and true first-time bugs. | 1 day |
| 2 | **Insight/Next Move nudge** | Prompt-based, rule-driven hints for stuck/looping users; tweak text, no context engine. | 1 hour |
| 3 | **Containerized deployment** | Each user/server runs in a Docker Compose stack, manual spin-up, reverse-proxy routing. | 1–1.5 days |
| 4 | **Unify app state in SQLite DB** | Per-instance DB; migrate current state, minimal schema, robust for demo scale. | 1 day |
| 5 | **Backend event observability** | Basic log/error/event surfacing; CLI or file dump, no dashboards. | 4 hours |
| 6 | **Structured logging** | Per-instance logs, structured/greppable, surfaced for debugging, no external shipping. | 2 hours |
| 7 | **User authentication** | Simple auth: per-user

**Deferred / Post-Demo Backlog**

| # | Feature | Design/Details | Why Deferred? |
|---|---------|----------------|---------------|
| 1 | Graph visualization | In-app render of the knowledge graph/state; helpful for debugging, demo “wow,” not core to function. | Polish/demo clarity, not demo-blocking. |
| 2 | UX polish | Multiline input, markdown output, config pane tweaks. | Quality-of-life, not functional gating. |
| 3 | Deeper memory system revamp | Structural rethink of memory/context engine. | Complex, not MVP critical. |
| 4 | Full hands-free voice mode | Voice commands/input for chat and control. | Nice-to-have for accessibility, not needed for F&F demo. |
| 5 | Real-time collaborative canvas edits | Multiple users editing/sharing the same canvas live. | Major lift, not a P0 feature. |
| 6 | Eval/test cases | Automated, reproducible user journeys/tests. | Improves reliability, can test manually for demo. |
| 7 | Self-updating system parameters | Dynamic tuning/config that updates without redeploys. | Flexibility for scaling, not demo-essential. |
| 8 | Automated user