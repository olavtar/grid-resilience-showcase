---
name: No silent deviations from the plan
description: Never defer, fall back, or deviate from the master plan without stopping to discuss first
type: feedback
---

Never silently defer work, switch to a fallback approach, or dramatically alter something from what docs/plan.md specifies. Stop and discuss it first.

**Why:** The user caught multiple cases where the Phase B plan silently deferred Kit substation work, replaced NeMo Guardrails with plain Python, and added unnecessary demo/live mode splits. These were all deviations from the master plan that should have been flagged for discussion.

**How to apply:** When hitting a blocker, complexity concern, or temptation to simplify/defer/fall back — surface it explicitly to the user before proceeding. Don't make the call unilaterally. This applies to: deferring scope, switching to a simpler implementation, dropping a product integration, adding artificial constraints (like demo mode), or changing the architecture.
