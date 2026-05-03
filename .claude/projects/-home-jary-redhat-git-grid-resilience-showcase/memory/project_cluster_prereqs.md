---
name: Cluster prerequisites
description: NFD and GPU Operator are pre-installed on the target cluster — don't deploy them via GitOps
type: project
---

The target OpenShift cluster already has NFD Operator and NVIDIA GPU Operator installed. These are NOT managed by our GitOps repo.

**Why:** These operators are cluster-level infrastructure managed by the platform team, not per-project.

**How to apply:** Don't create Subscription manifests for NFD or GPU Operator. Our GitOps only manages AMQ Streams, Crunchy PGO, and the application workloads.
