# Authoring and reviewing memories

Create records with `remember` rather than copying IDs. The front matter is the authoritative structured lesson; use the Markdown body for reproduction detail and interpretation. Examples under `templates/examples/` are illustrative and never part of retrieved memory.

Choose the smallest scope supported by evidence. An event is `episodic`; generalized knowledge is `semantic`; a reusable method is `procedural`; behavior or failure-mode learning is `self_model`. An initial observation normally stays project-scoped. `--shared` selects shared ownership; otherwise the author owns the personal record. Another member's memory requires an explicit reviewed change proposal outside the initial CLI.

Every record includes ID, owner, author, type, project, scope, status, ISO creation date, tags, confidence in [0,1], observation, evidence, limitations, reviewers, and contradictory/superseding references. The project must exist. Evidence should include revision, input, command, environment, output, tolerance, and claim scope either directly or in a linked artifact. A locator alone is not verification.

An independent reviewer adds a record like this, after actually reviewing the cited evidence:

```yaml
reviewers:
  - agent: vera
    decision: accept
    date: '2026-09-29'
    evidence_refs:
      - projects/umat-oti/findings.md
    notes: 'Describe actual reproduction, independence from the builder, and bounded acceptance.'
```

Do not copy this as a fictional review. Evidence references must match declared evidence. Use `request-changes` for unresolved issues. Resolve the recorded review explicitly with a Git history rather than silently removing dissent. The accepting reviewer cannot be the author. For shared records, the author identifies the builder responsible for the claim; disclose other contributors so independence can be assessed.

Run validate before promotion. Transition proposed -> verified -> adopted with separate `promote-memory` invocations. Neither high confidence nor a commit can replace review. When a lesson fails, deprecate it with a reason, or supersede it with reciprocal references in both records. Keep contradictory records and their statuses visible. Re-run validation and inspect assembled context after any lifecycle change.

For identity changes, collect cross-project evidence and use `propose-identity-change`. Version, trial, approval, and rollback fields are required. Active identity remains unchanged by that command. The initial CLI deliberately cannot apply an amendment or grant new permissions.
