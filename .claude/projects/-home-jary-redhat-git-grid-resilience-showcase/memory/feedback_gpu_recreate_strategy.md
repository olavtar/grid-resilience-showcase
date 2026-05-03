---
name: GPU workloads need Recreate strategy
description: All GPU deployments must use strategy type Recreate, not RollingUpdate
type: feedback
---

All deployments that request `nvidia.com/gpu` must use `strategy: type: Recreate`. RollingUpdate deadlocks when there's only one GPU per node — the new pod can't schedule while the old pod holds the GPU.

**Why:** The default RollingUpdate waits for the new pod to be ready before terminating the old one. With a single GPU, the new pod can never schedule because the old pod holds the only GPU.

**How to apply:** Every deployment that has `nvidia.com/gpu` in its resource requests must have `spec.strategy.type: Recreate`.
