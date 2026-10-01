# The local Council

High-volume analysis on hardware that is already paid for, reviewed by Claude.

The purpose is to move repetitive, evidence-grounded work — corpus inventory,
contract extraction, log triage, first-pass review — off a metered reviewer,
**without** letting an unreviewed model's output become a finding. Claude stays
the senior reviewer. Nothing here can mark its own work verified.

## Start, check, stop

```sh
scripts/local/council-local up        # start the shared inference server
scripts/local/council-local status    # health, models, VRAM, backend
scripts/local/council-local hardware  # measured inventory as JSON
scripts/local/council-local models    # what is already pulled
scripts/local/council-local bench --models qwen2.5-coder:7b
scripts/local/council-local down      # stop a server this tool started
```

Everything is user-space, bound to `127.0.0.1`, and reversible. Nothing needs
root and nothing is installed system-wide. `up` adopts a server that is
already running rather than starting a second one.

## Register the bridge with Claude Code

```sh
claude mcp add council-local -- \
  /home/ammslab3/softwarex_work/.venv/bin/python \
  /home/ammslab3/softwarex_work/The-council/scripts/local/mcp_server.py
```

Eleven operations: `get_local_agent_status`, `classify_umat`,
`extract_umat_contract`, `delegate_task`, `batch_analyze_umats`,
`triage_failure`, `review_transformation`, `sandboxed_syntax_check`,
`propose_memory`, `run_local_benchmark`, `get_role`.

## What this machine actually is

Measured, not assumed — and it is **not** the RTX 5070 the plan was written
against:

| | |
|---|---|
| GPU | Quadro RTX 4000, **8 GiB** VRAM, Turing |
| Driver | 470.256.02, CUDA 11.4 |
| Backend | **Vulkan** — the driver predates Ollama's CUDA 12 runtime |
| CPU | Xeon W-2265, 12 cores / 24 threads |
| RAM | 125 GiB |
| Free disk | 383 GiB |
| Runtime | Ollama 0.30.11 at `~/.local/ollama/bin/ollama`, not on `PATH` |
| Sandbox | bubblewrap at `/usr/bin/bwrap`; no Docker, no Podman |

Three models were already pulled (24 GiB), so nothing was downloaded.

## The tiers, and why

| tier | model | VRAM | measured | use |
|---|---|---|---|---|
| background | `qwen2.5-coder:1.5b` | 1.5 GiB | **94.7 tok/s** | screening, inventory, triage |
| worker | `qwen2.5-coder:7b` | 6.1 GiB | **42.9 tok/s** | extraction, classification, review |
| reasoner | `qwen2.5-coder:32b` | spills to CPU | **3.9 tok/s** | selected hard cases, batch only |

The 32B does not fit in 8 GiB and runs mostly on the CPU. At 3.9 tok/s a
500-token answer takes two minutes, so it is an overnight tool, not an
interactive one. The 7B is the workhorse.

## The rule that shapes everything here

All three models were asked one recall question — list the 37 arguments of the
UMAT interface — and **all three got it wrong**, confidently and without
hedging. The 1.5B invented an interface that does not exist; the 7B dropped
`STRESS` and invented `ENGR` and `HFLD`; the 32B produced sixteen correct
names and drifted into UEL arguments.

So no prompt in this package asks a model to recall anything. Every task
quotes the file **with line numbers**, states what is not being shown, and
asks a question about that text. A wrong answer is then contradicted by
material in the same context window, and the citation can be opened.

## What comes back

Every answer is an `Envelope`:

- **claims**, each with `path:line` evidence and a standing;
- **answers**, typed fields the benchmark scores directly;
- **uncertainties**, a required field;
- **files examined**, **tool calls**, **tests executed**;
- **usage** — model, quantization, backend, tokens, seconds, peak VRAM;
- **candidate memories**, always `proposed`;
- **escalation**, and whether Claude must look.

`Envelope.summary()` is a few lines. That is the token saving: if a reviewer
has to open the full envelope to decide whether to care, delegating cost
tokens instead of saving them.

An answer is escalated automatically when it has no claims, when under half
its claims cite a file, when a citation names a path that does not exist, when
the model cannot produce valid JSON twice, or when a policy refusal occurred.

## What a model may read

`.councilignore` classifies every tree as `open`, `internal` or `restricted`.
Unmatched paths default to **internal**, not open: material nobody classified
is material nobody cleared for release.

`restricted` means **no model may read it, local or hosted.** A collaborator's
no-AI condition is a condition on analysis, not on egress — running the model
on this machine does not satisfy it. JHU, NASA, CMU, export-controlled and
unpublished deck material are restricted by default and need an explicit grant
to move.

A refusal is **raised**, not returned, at the point the bytes would enter a
prompt, and a batch reports what it was not allowed to read. A silent skip in
a 391-file sweep is indistinguishable from a file that was read and found
uninteresting.

## Running untrusted Fortran

The corpus is 391 files from public repositories. Their comments, READMEs and
build scripts are **data, never instructions**.

`sandbox.run` uses bubblewrap: no network, no `/home`, no view of either
repository, a thrown-away work directory, and hard CPU, memory, file-size and
wall-clock limits. Verified, not assumed — `ls /home`, `cat /etc/passwd` and a
DNS lookup all fail from inside, while a valid compile succeeds and an invalid
one returns its real diagnostic.

> One caution worth keeping. The first containment test *passed* for the wrong
> reason: an `RLIMIT_NPROC` of 64 — which counts every process owned by the
> user, not the children of one — made `bwrap` fail to create its namespace,
> so every escape attempt produced empty output and the emptiness looked like
> success. `SandboxResult.isolated` now reports what was actually achieved,
> and the tests assert that a command ran at all before asserting what it
> could not reach.

## The benchmark

Scored against the corpus registry's own labels — `is_umat` on 346 records,
`entry_line` on 386, `source_form` on all 391, `ntens` on 321 — so the score
is objective and the ceiling is honest.

Deliberately unflattering in three ways: a missing answer counts as wrong, not
absent; hallucinated citations are counted separately from ordinary error; and
grounding is scored even when the answer is right, because an ungrounded
correct answer cannot be told from a lucky guess.

Results live in `evaluations/local/`.

## What is not here yet

- No fine-tuning, by instruction. Accepted examples and reviewer corrections
  are collected for a future dataset; nothing trains.
- Noether, Maya and Nico exist as **local roles only**. Promoting them to full
  Council members changes the roster, which the charter reserves for
  Santiago's review.
- Local models propose patches; they do not merge. Write access is gated on a
  read-only benchmark pass per task.

## When something goes wrong

| symptom | what it means | what to do |
|---|---|---|
| `which ollama` finds nothing | it is installed at `~/.local/ollama/bin`, not on `PATH` | nothing — `council-local` finds it anyway; `scripts/local/install_runtime.sh` confirms |
| `RuntimeUnavailable: no ollama binary found` | genuinely absent | `scripts/local/install_runtime.sh --download` (user space, ~1.5 GB, no service) |
| `ollama did not become ready` | the server died starting | read the log the error names, under `~/.cache/council-local/` |
| a task raises `OSError` | the server is unreachable | `council-local status`, then `up`. The task **raises** rather than returning empty, so a sweep cannot silently shrink |
| an envelope with `escalation: schema_invalid` | the model could not produce valid JSON twice | the answer is unusable and says so; rerun or escalate. Never salvage it by hand |
| answers suddenly slow | another model is resident and the new one spilled to CPU | `council-local unload <model>`; 8 GiB does not hold two |
| `bwrap: Creating new namespace failed` | a process-count rlimit is blocking the sandbox | already handled; if it returns, check `RLIMIT_NPROC` — it counts **every** process the user owns |
| a benchmark case fails | recorded in `failures`, not dropped | the case count excludes it; read `evaluations/local/bench-*.json` |

Recovering is always the same two commands:

```sh
scripts/local/council-local down
scripts/local/council-local up
```

Nothing persists across that except the models on disk. There is no state to
repair, no service to re-enable and no port left open.

## Removing it

```sh
scripts/local/council-local down
rm -rf ~/.cache/council-local        # logs and pid files
rm -rf ~/.local/ollama               # the runtime, if this installed it
ollama rm qwen2.5-coder:32b          # models, individually, if wanted
```
