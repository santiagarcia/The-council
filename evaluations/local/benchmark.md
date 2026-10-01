# Local model benchmark

Scored against the corpus registry's established labels.

| model | cases | fields | accuracy | wrong | missing | hallucinated citations | schema valid | grounded | s/case |
|---|---|---|---|---|---|---|---|---|---|
| `qwen2.5-coder:7b` | 48 | 172 | **54.1%** | 48 | 31 | 0.0% | 85% | 80% | 39.8 |
| `qwen2.5-coder:1.5b` | 48 | 172 | **38.4%** | 66 | 40 | 0.0% | 79% | 62% | 13.0 |

## Per task

- `qwen2.5-coder:7b` classify_umat: 50.8% of 118 fields, 747s
- `qwen2.5-coder:7b` extract_umat_contract: 61.1% of 54 fields, 1163s
- `qwen2.5-coder:1.5b` classify_umat: 43.2% of 118 fields, 254s
- `qwen2.5-coder:1.5b` extract_umat_contract: 27.8% of 54 fields, 371s
