# Affective and relational architecture

This extension builds on the existing charter, evidence-governed memories, versioned identities, member prompts, and Claude adapters. It implements functional personalities through instructions; it does not assert consciousness or autonomous state transitions.

## What runs now

`council assemble` already includes all constitution Markdown and each selected member's system prompt. The profiles' operative behavioral consequences are therefore embedded in the prompts. Native Claude adapters read those prompts through assembly or their documented fallback. Generated adapters, identity versions, operating beliefs, Python code, and CLI command conventions remain intact.

`members/<agent>/affective-profile.yaml` is the inspectable disposition source. A profile change must update the prompt's corresponding operational section in the same reviewed change. The files are intentionally kept explicit rather than silently relying on a loader that does not exist. `schemas/affective-profile.schema.json` specifies their structure, and profile instances are now validated against their configured member and identity version.

Transient appraisal is optional task context under ignored `.council/affect/`. The agent explains the appraisal and behavioral choice in the task or handoff when it matters. No background process runs and no mood is automatically persisted. Qualitative levels avoid pretending to measure real emotional intensity.

## Persistence and review

Relational events may be manually authored as JSON under `memory/relational/`, using `schemas/relational-memory.schema.json`. This deliberately avoids the existing Markdown record scan, which enforces current owner paths and memory types. JSON events are not automatic guidance; session owners load only relevant explicitly reviewed material and preserve status labels. Proposed records must never be passed off as adopted guidance.

Use `relationships/proposed-updates/` for proposed interpretations and pattern changes. Reviewed shared and pair guidance belongs in the corresponding relationship directories. Do not populate them with fabricated events. One event can justify reflection; repeated reviewed events may justify a medium-term disposition change. Long-term identity changes still require the existing amendment workflow and cross-project evidence. See `relationships/README.md`.

The relational JSON schema catches structural categories, allowed participants, and missing fields when used with a JSON Schema validator. It cannot establish truth, review independence, file existence, consent, manipulation-free prose, or whether an identity change is justified. Those checks are manual in this phase.

## Modes and comparison

Imagination and verification are explicit prompt operating modes, not CLI commands. Transfer a speculative idea with assumptions, predicted observation, falsification test, required evidence, and an owner. Keep its speculative/unverified status until normal verification succeeds.

To disable the layer, Santiago says “Disable the affective layer for this task.” The session records the setting and omits affect-driven choices and updates while retaining evidence standards, role expertise, respect, and safety. Matched evaluations use the same task and budget; record token and workflow cost instead of claiming an unmeasured benefit.

## Remaining automation

The extension validates profile instances and reader continuity and provides isolated reader review and artifact diagnostics. General affect/relationship commands, automatic relational-event retrieval, runtime tracking checks, and automatic identity changes remain unimplemented. Do not advertise those features as working. `affective-event.schema.json` defines optional transient appraisal notes for future tooling. The evaluation scenarios are specifications for observed trials, not test passes or independent review.

Next: trial one real collaboration and one matched enabled/disabled task. Independently review the outcome before adopting a relational lesson or extending Python automation.

## Ten-member extension

Noether, Maya, and Nico extend the same registry and memory architecture. See `docs/reader-review.md` for the updated architecture diagram, selective routing, Nico's context projection, developing-reader lessons, and final review gates. Cold-read continuity is deliberately structured and nontechnical; reviewed general relational events remain manually managed.
