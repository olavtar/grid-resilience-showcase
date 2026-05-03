---
name: No empty scaffold directories
description: Don't create placeholder directories or .gitkeep files for future work — create directories when they're actually needed
type: feedback
---

Don't pre-create empty scaffold directories (console/, infrastructure/, etc.) with .gitkeep files for future phases. By the time we reach those phases, the structure often changes.

**Why:** The user has seen this pattern lead to wrong directory names/structures that need to be redone. Premature scaffolding creates noise.

**How to apply:** Only create directories when writing actual files into them. Skip any "set up the folder structure" steps that create empty dirs.
