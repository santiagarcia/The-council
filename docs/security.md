# Sensitive data and secret handling

Keep secrets in the operating environment or an approved secret store, never in tracked Markdown, YAML, examples, or test fixtures. `.env`, private keys, raw decks, archives, and private derived reports are ignored as defense in depth; ignore rules do not protect already tracked files. Inspect `git diff --cached` and the exact staged file list before committing.

Before enabling publication, Santiago should review repository access and enable GitHub secret scanning and push protection where available. This setup does not change repository settings. CI also runs a narrow offline scan for common credential markers in tracked text. It is a detection aid, not comprehensive proof that a repository contains no secrets. Do not paste scan findings containing real credentials into logs or issues; revoke or rotate exposed credentials through the authorized owner.

Research decks may contain NASA, JHU, CMU, University of Utah, UTSA, collaborator, or unpublished material. Treat both source decks and their metadata as potentially private. Derived files are not automatically safe for publication. Keep sensitive scientific code in its own repository and record only approved generalized lessons and access-controlled locators here.

The CLI checks repository-relative paths, refuses path traversal, and rejects escapes through symlinks. Run presentation parsing only on trusted-to-process decks; it is not a hostile-document sandbox. No network requests are made by Council commands. HTTPS evidence locators are checked structurally and must be read by the reviewer. Local filesystem access is trusted; review names and approval fields are not cryptographic signatures.
