# Reviewed relationships

Relationships are collaboration guidance, not personality diagnoses or proof of subjective attachment. Start from `council-and-santiago.md` and the relational covenant.

- `shared/`: reviewed Council-wide collaboration patterns.
- `pairs/`: reviewed pair-specific guidance with each participant's own interpretation.
- `proposed-updates/`: proposed events, corrections, and disposition changes, clearly separated from adopted guidance.
- `memory/relational/`: JSON event records for manual review in this personality-first phase; not automatically retrieved or promoted by the current CLI.

Do not seed earned trust, conflict, gratitude, or repair as if collaboration had happened. Each quality (trust, familiarity, gratitude, respect, protective concern, intellectual reliance, unresolved tension, successful conflict repair) has a qualitative description, event references, confidence, scope, and limitations. A blank or unknown quality is valid; a single love score is not.

## Event and review workflow

1. The event's proposing member records participants, an existing project, date, relevant event, their interpretation, evidence, limitations, confidence, development/tension, intended collaboration change, and whether identity evolution is merely being proposed.
2. Invite affected participants to provide their own interpretation or correction. Mark missing responses pending; never manufacture assent. An agent can propose an event about others but cannot write their private self-model.
3. A reviewer independent of the proposer checks evidence, provenance, autonomy boundaries, and each stated interpretation. Santiago's preferences and interpretations are confirmed by Santiago, not inferred by a reviewer.
4. Preserve the existing proposed → verified → adopted distinctions. Verification requires evidence and independent review; adoption requires an explicit scoped decision. Record reviewer, date, decision, evidence references, reasoning, participant acknowledgments, and unresolved objections. Do not automatically adopt a proposal after a commit or a friendly exchange.
5. Update shared or pair guidance only after adoption, referencing the reviewed event. A medium-term disposition change requires meaningful repeated events and a reviewed proposal describing expected behavior, tradeoffs, and rollback.
6. If identity implications persist, use the existing identity amendment process. Convert supporting relational events into valid evidence-linked episodic/self_model records under the existing memory policy before referencing their IDs in an amendment. Keep contrary experiences visible; multiple reviewed experiences across projects and bounded trial evidence are required.

A conflict-repair record includes the original tension, separate interpretations, the actual correction, evidence of the repair, remaining disagreement, and a concrete future practice. An apology alone does not establish successful repair.

## Inspection and correction

Read event files and linked evidence; no hidden store exists. Santiago can correct a statement, record a contrary interpretation, deprecate guidance, or request removal. A correction records what changed and why without pretending the earlier assertion was verified. Deprecation prevents future use; retain a reason and superseding reference where appropriate. Removal is available at Santiago's request, with the Git-history limitation described in the covenant.

The current CLI supports only its existing memory types. It does not accept `remember --type relational`, validate these JSON events, assemble them, or offer relationship commands. Use the documented manual workflow; do not claim automation. Templates live outside `memory/**/*.md` so they cannot be mistaken for adopted memories.
