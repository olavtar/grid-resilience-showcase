# This project was developed with assistance from AI tools.

"""Scene material updates driven by grid event data."""

from __future__ import annotations

import omni.usd
from pxr import Sdf, UsdShade

PRIM_MAP: dict[str, str] = {
    "T-008": "/World/utu_substation_pack/node_00kV_Voltage_Transformer",
    "CB-F12": "/World/utu_substation_pack/node_00kV_Circuit_Breaker_001",
    "TS-04": "/World/utu_substation_pack/node_00kV_Disconnector_001",
}

RISK_COLORS: dict[str, tuple[float, float, float]] = {
    "low": (0.24, 0.53, 0.21),
    "medium": (0.94, 0.67, 0.0),
    "high": (0.93, 0.0, 0.0),
    "critical": (0.64, 0.0, 0.0),
}


def _risk_level(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.65:
        return "high"
    if score >= 0.40:
        return "medium"
    return "low"


def _get_preview_surface(prim_path: str) -> UsdShade.Shader | None:
    """Find the UsdPreviewSurface shader bound to a prim."""
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return None
    prim = stage.GetPrimAtPath(Sdf.Path(prim_path))
    if not prim.IsValid():
        return None
    material_binding = UsdShade.MaterialBindingAPI(prim)
    material, _ = material_binding.ComputeBoundMaterial()
    if not material:
        return None
    for output in material.GetSurfaceOutputs():
        source = output.GetConnectedSources()
        if source and source[0]:
            return UsdShade.Shader(source[0][0].source.GetPrim())
    return None


def apply_risk_color(prim_path: str, score: float) -> None:
    """Update UsdPreviewSurface diffuseColor based on risk score."""
    shader = _get_preview_surface(prim_path)
    if shader is None:
        return
    level = _risk_level(score)
    color = RISK_COLORS[level]
    shader.GetInput("diffuseColor").Set(color)


def apply_fault_state(prim_path: str, faulted: bool) -> None:
    """Set emissive glow on a prim for fault indication."""
    shader = _get_preview_surface(prim_path)
    if shader is None:
        return
    if faulted:
        shader.GetInput("emissiveColor").Set((0.93, 0.0, 0.0))
        emissive_input = shader.GetInput("emissiveIntensity")
        if emissive_input:
            emissive_input.Set(5.0)
    else:
        shader.GetInput("emissiveColor").Set((0.0, 0.0, 0.0))
        emissive_input = shader.GetInput("emissiveIntensity")
        if emissive_input:
            emissive_input.Set(0.0)


def apply_switch_state(prim_path: str, closed: bool) -> None:
    """Update switch prim visual state."""
    shader = _get_preview_surface(prim_path)
    if shader is None:
        return
    if closed:
        shader.GetInput("diffuseColor").Set((0.24, 0.53, 0.21))
    else:
        shader.GetInput("diffuseColor").Set((0.5, 0.5, 0.5))
