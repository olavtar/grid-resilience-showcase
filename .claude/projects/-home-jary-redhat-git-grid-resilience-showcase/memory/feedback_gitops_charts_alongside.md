---
name: Helm charts alongside services
description: Build Helm charts when each service becomes deployable, not deferred to a late phase
type: feedback
---

Infrastructure charts should be built alongside each service as it becomes deployable. Don't defer all Helm/GitOps work to Phase F.

**Why:** This is a GitOps-driven showcase. Argo CD reconciles from the repo, so charts are part of the deliverable — not packaging done after the fact.

**How to apply:** When a service reaches a runnable state (has a Containerfile, endpoints, etc.), create its Helm chart in `infrastructure/helm/<service>/` at the same time. Include the ArgoCD ApplicationSet entry if the structure is ready.
