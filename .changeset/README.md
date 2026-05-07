# Changesets

Fipro uses [Changesets](https://github.com/changesets/changesets) to track release-worthy changes and auto-generate `CHANGELOG.md`.

## For contributors (human or agent)

When you make a user-visible change, add a changeset:

```bash
# write a markdown file in this directory named anything.md
cat > .changeset/<slug>.md <<'EOF'
---
"fipro": minor
---

One-sentence summary of the change.
EOF
```

Bump type options:
- `patch` — bug fix, docs, chore
- `minor` — new feature, backwards-compatible
- `major` — breaking change

Pre-commit hooks do not require changesets; they are optional per PR.

## For release maintainer

See [RUNBOOK.md](../RUNBOOK.md#release-procedure) for the release command sequence.
