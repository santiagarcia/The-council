# Memory policy

Use episodic memory for bounded events, semantic memory for generalizable knowledge, procedural memory for workflows, and self_model memory for behavior and failure modes. A memory has one owner, one author, scope, project, evidence, limitations, confidence, reviewers, and explicit contradictory or superseding references.

Lifecycle: proposed -> verified -> adopted. A commit records a candidate; verification reviews evidence; adoption makes it future guidance. The CLI requires each transition separately. Confidence is a calibrated author estimate, not a substitute for evidence or a numeric promotion threshold. A weak observation normally remains project-scoped and proposed.

Deprecate or supersede rather than delete. Set reciprocal supersedes/superseded_by references and preserve the old record. Contradictions remain visible in assembled context even if a linked candidate is unreviewed. Status in front matter is authoritative; files retain their stable creation paths. The proposed/verified/deprecated folders are organizational entry points, not duplicate status indexes. Retrieval scans records directly.

By default assemble includes relevant adopted guidance and distinctly labeled verified observations; it excludes proposed, deprecated, and superseded records from guidance. It never includes another agent's personal memory as ordinary context. Amendments and reviews must document cross-owner changes explicitly.
