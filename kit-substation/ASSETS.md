# Kit Substation — Asset Procurement & Build

> [!NOTE]
> This project was developed with assistance from AI tools.

## Scene Asset Strategy

The Kit substation uses a dual-quality scene strategy. Both tiers share the same prim hierarchy so the data-driven extension works identically.

| Tier | Source | Container |
|------|--------|-----------|
| **high** (demos) | Purchased Fab asset pack | Private: `quay.io/jary/grid-resilience-kit-substation:high` |
| **standard** (open-source) | Code-generated primitives + CC0 textures | Public: `quay.io/jary/grid-resilience-kit-substation:standard` |

## High-Quality Asset Workflow

1. Purchase pack from [Fab](https://www.fab.com/) (~$30-$70)
   - Search: "Electrical Utility and Substation" or "Electrical Substation / 34 Assets"
   - Fab Standard License: demo/trade show YES, marketing YES, USD export YES
   - Raw assets in public git repo: NO

2. Export to FBX from Unreal or source tool

3. Convert FBX → USD via Omniverse Asset Converter

4. Arrange scene in USD Composer — establish prim hierarchy:
   ```
   /Substation/Transformer_01    ← maps to T-008
   /Substation/CircuitBreaker_01 ← maps to CB-F12
   /Substation/TieSwitch_01      ← maps to TS-04
   ```

5. Store raw assets in `.gitignore`'d directory (never committed)

6. Build container image with assets baked in:
   ```
   podman build -f kit-substation/Containerfile -t quay.io/jary/grid-resilience-kit-substation:high .
   podman push quay.io/jary/grid-resilience-kit-substation:high
   ```

## Prim Hierarchy (required for extension compatibility)

The extension maps asset IDs to prim paths in `scene_updater.py`:

- `T-008` → `/World/utu_substation_pack/node_00kV_Voltage_Transformer`
- `CB-F12` → `/World/utu_substation_pack/node_00kV_Circuit_Breaker_001`
- `TS-04` → `/World/utu_substation_pack/node_00kV_Disconnector_001`

The standard-quality scene (Phase E) must use the same prim paths.
