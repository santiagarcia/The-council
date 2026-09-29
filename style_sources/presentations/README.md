# Private presentation evidence

Place approved-to-process `.pptx` files in `style_sources/presentations/private/`, including subfolders. Run `council style ingest style_sources/presentations/private`. Sources are read-only. No presentations are required for setup; an empty folder generates an honest empty profile.

Raw PPT/PPTX and ZIP files are ignored globally, and the private folder is ignored except for its marker. Derived reports are also ignored by default because metadata can still be sensitive. Ingestion exports hashes and style statistics, not slide text, notes, filenames, or images. It updates only the marked region in the tracked style guide; review that diff before committing.

For intentional publication, obtain Santiago's explicit approval for each file, inspect it for NASA/JHU/collaborator/unpublished content and metadata, and check the destination repository's access policy. Prefer Git LFS: install it locally, run `git lfs track '*.pptx'`, inspect `.gitattributes`, then stage only the individually approved file with `git add -f -- path/to/approved.pptx`. LFS is storage, not confidentiality. Never force-add the whole private folder or an unreviewed archive. Review `git diff --cached --name-only` before committing or pushing.

The existing OneDrive archive is preserved and ignored. It is not extracted or ingested automatically; choose and place intended decks in the private folder first.
