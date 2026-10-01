#!/usr/bin/env bash
# Locate or install Ollama in user space. No root, no system service.
#
# On this machine it is already installed at ~/.local/ollama/bin/ollama and
# simply absent from PATH, which is why `which ollama` finds nothing. This
# script looks before it downloads, and refuses to download unless asked.
#
#   install_runtime.sh            # locate, report, do not download
#   install_runtime.sh --download # fetch the official tarball into ~/.local
set -euo pipefail

PREFIX="${COUNCIL_OLLAMA_PREFIX:-$HOME/.local/ollama}"
BIN="$PREFIX/bin/ollama"
URL="https://ollama.com/download/ollama-linux-amd64.tgz"

found=""
if command -v ollama >/dev/null 2>&1; then
  found="$(command -v ollama)"
elif [ -x "$BIN" ]; then
  found="$BIN"
fi

if [ -n "$found" ]; then
  echo "ollama: $found"
  "$found" --version 2>&1 | sed 's/^/  /' || true
  case ":$PATH:" in
    *":$(dirname "$found"):"*) ;;
    *) echo
       echo "It is not on PATH. Either add it:"
       echo "    export PATH=\"$(dirname "$found"):\$PATH\""
       echo "or ignore this -- council-local finds it without PATH." ;;
  esac
  echo
  echo "models already present:"
  find "${OLLAMA_MODELS:-$HOME/.ollama/models}/manifests" -type f 2>/dev/null \
    | sed "s|.*/manifests/||; s|/\([^/]*\)$|:\1|; s|^.*/||" | sed 's/^/  /' \
    || echo "  (none)"
  exit 0
fi

if [ "${1:-}" != "--download" ]; then
  echo "No ollama found on PATH or at $BIN."
  echo "Re-run with --download to fetch it into $PREFIX (about 1.5 GB)."
  echo "Nothing is installed system-wide and no service is registered."
  exit 1
fi

# Storage first: a half-extracted tarball on a full disk is worse than a refusal.
free_gib=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc '0-9')
if [ "${free_gib:-0}" -lt 5 ]; then
  echo "only ${free_gib} GiB free under $HOME; need at least 5. Refusing." >&2
  exit 1
fi

echo "downloading into $PREFIX ..."
mkdir -p "$PREFIX"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
curl -fsSL "$URL" -o "$tmp/ollama.tgz"
tar -xzf "$tmp/ollama.tgz" -C "$PREFIX"
chmod +x "$BIN"
echo "installed: $BIN"
"$BIN" --version 2>&1 | sed 's/^/  /' || true
echo
echo "To remove it again: rm -rf $PREFIX   (models live in ~/.ollama, kept)"
