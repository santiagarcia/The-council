# Limitations and risks of the local Council

Written to be read before trusting anything this system produces.

## 1. The hardware is not what the plan assumed

The plan specified an RTX 5070-class GPU. This machine has a **Quadro RTX
4000 with 8 GiB**, on driver 470.256.02, which predates the CUDA 12 runtime
Ollama ships — so the card is driven through **Vulkan**, not CUDA.

Consequences, all measured:

- A 12B–20B "main reasoning model" **does not fit**. The 32B present runs at
  **3.86 tok/s** with most layers on the CPU: a 500-token answer takes two
  minutes. It is an overnight tool.
- The practical ceiling is the 7B at **42.9 tok/s**, which is a competent
  extractor and not a reasoner.
- Updating the driver would likely restore CUDA and raise throughput, but it
  is a privileged, system-wide change on a shared lab machine and was **not
  attempted**. It needs approval.

## 2. The models are unreliable from memory, and that is structural

All three models were asked one recall question — the 37 arguments of the
UMAT interface — and all three answered confidently and wrongly. The 1.5B
invented an interface; the 7B dropped `STRESS` and invented `ENGR` and `HFLD`;
the 32B gave sixteen correct names then drifted into UEL arguments.

The package answers this by never asking for recall. But the mitigation is a
*prompt discipline*, not a guarantee: a model that is shown the right text can
still misread it. On the very first grounded call, with the interface quoted
in the prompt, the 7B still reported `argument_count: 30` for a 37-argument
list. **Treat every count from a local model as a hypothesis.**

## 3. The benchmark's ceiling is the registry's correctness

Scores are against `corpus_registry.json`, which is a pipeline product, not
ground truth from an oracle. Where the registry is wrong, a model that agrees
with it scores well. Two known soft spots: `props_count` and `nstatv` are
non-null on only 168 and 170 of 391 records, and the family labels are
keyword-derived for most of the corpus.

A model scoring highly here is demonstrated consistent with this project's
established answers — not demonstrated correct.

## 4. The sandbox is bubblewrap, not a VM

Verified: no network, no `/home`, no view of either repository, and hard CPU,
memory, file-size and wall-clock limits. Not claimed: protection against a
kernel exploit, a bubblewrap escape, or a side channel. There is no Docker and
no Podman on this machine, so there is no second layer.

> The containment tests initially **passed for the wrong reason.** An
> `RLIMIT_NPROC` of 64 — which counts every process the UID owns, not the
> children of one — made `bwrap` fail to create its namespace, so every escape
> attempt returned empty output and the emptiness read as containment. The
> tests now assert that a command ran before asserting what it could not
> reach, and `SandboxResult.isolated` reports what was actually achieved. The
> general lesson is worth more than the fix: **a security test that can pass
> when the mechanism is absent is not a security test.**

## 5. Policy depends on classification being kept current

`.councilignore` refuses what it is told to refuse. A restricted tree that
nobody adds is a tree a model will read, because the default for unmatched
paths is `internal` — analysable. That default is deliberate (an
`open`-by-default would be worse) but it means **the exclusion list is a
maintained artefact**, and a new collaborator directory is unprotected until
someone writes the line.

The list cannot cover what it cannot see: restricted material pasted into a
prompt, or placed outside the classified roots, is not protected by anything
here.

## 6. Prompt injection is mitigated, not solved

Scraped comments and READMEs are passed to a model as data. The prompts frame
them as material to analyse, outputs are schema-constrained, and no local
output is executed. But a sufficiently crafted comment can still steer a 7B
model's *answer*. The protections that matter are downstream: a local model
cannot merge, cannot push, cannot adopt a memory, and cannot mark anything
verified. **Assume the answer can be manipulated; rely on the fact that the
answer cannot act.**

## 7. What the delegation figures do and do not say

`claude_tokens_avoided` is deliberately not computed. Any such figure rests on
an assumption about what a reviewer would otherwise have read, and that
assumption always flatters the tool. What is measured is local cost, summary
compression, and the acceptance rate over runs a reviewer actually judged.

Until that acceptance rate exists over a meaningful sample, **the saving is
unproven.**

## 8. Scope not yet built

- **No fine-tuning**, by instruction. Examples are collected; nothing trains,
  and no held-out set exists.
- **The research cycle has no fetcher.** Its policy, budget and corroboration
  rules are tested offline; network egress is the caller's decision and no
  caller supplies one yet.
- **All ten members now load a versioned identity**, since the ten-member
  roster was merged. Nico is special and the speciality is enforced in code:
  his role refuses to build a prompt that names the task, because a cold read
  is worthless once the reader has been told what the document was meant to
  achieve. The one prompt it will build carries his disposition and the
  intended audience only.
- **This package cannot guarantee Nico's isolation, only its own half of it.**
  It controls what goes into the prompt it builds. It cannot stop a caller
  adding text, cannot sandbox the model's pretrained knowledge, and shares one
  server with every other member. If isolation is not enforced by the host,
  `docs/reader-review.md` is explicit that no genuine cold read may be
  claimed, and that applies here.
- **The 1.5B tier is unproven for anything but screening.**
- **Residual Assembler tasks are implemented but unbenchmarked.**
  `audit_conventions` and `explain_interface_contract` exist and are wired
  into the bridge, but there is no registry field to score them against, so
  their accuracy on this codebase is unmeasured. Treat their output as a
  reading aid, not a finding.

## 9. The failure mode to watch for

Not a wrong answer — those are visible. The risk is a **plausible, well-cited,
wrong** answer that agrees with the registry on the fields that are scored and
is wrong on the one that is not. The structural defences are that every claim
carries an openable `path:line`, that a citation to a path which does not
exist escalates automatically, and that the builder and the judge never share
a context.

None of that makes a local answer a finding. It makes it a claim a reviewer
can check quickly, which is the whole of what this system is for.
