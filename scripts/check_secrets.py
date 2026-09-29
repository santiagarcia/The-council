"""Flag common credential markers without printing potential secrets."""

import re
import subprocess
import sys
from pathlib import Path

PATTERNS = (
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    rb"\bAKIA[0-9A-Z]{16}\b",
    rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b",
    rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}\b",
)


def main() -> int:
    """Scan tracked text and return failure without revealing matching values."""
    result = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True)
    findings = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        path = Path(raw.decode("utf-8"))
        if not path.is_file():
            continue
        if path.stat().st_size > 2_000_000:
            findings.append(f"Manual large-file review required: {path}")
            continue
        data = path.read_bytes()
        if any(re.search(pattern, data) for pattern in PATTERNS):
            findings.append(f"Potential credential marker: {path}")
    print(
        "\n".join(findings) if findings else "No common credential markers found in tracked files"
    )
    return int(bool(findings))


if __name__ == "__main__":
    sys.exit(main())
