---
name: No artificial demo/live mode split
description: Services should target real inference directly — don't add demo mode fallbacks as a crutch
type: feedback
---

Don't add demo/live mode splits to services. The user has local GPU access and the target cluster has GPUs. Building dual-mode services adds complexity without value.

**Why:** The demo mode fallback pattern creates artificial constraints, doubles code paths, and the fallback results are never as good as real inference. GPUs are available.

**How to apply:** Build services that call their NVIDIA backends directly (CorrDiff NIM, vLLM/Cosmos Reason, cuOpt). Pre-staged data (GFS files, curated images) is fine for reproducible demos — that's different from a "demo mode" code path that skips inference.
