# This project was developed with assistance from AI tools.

"""Scene material updates driven by grid event data."""

from __future__ import annotations

from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

PRIM_MAP: dict[str, str] = {
    "T-008": "/World/utu_substation_pack/node_00kV_Grid_Transformer_001",
    "T-006": "/World/utu_substation_pack/node_00kV_Circuit_Breaker_001",
    "P-080": "/World/utu_substation_pack/node_00kV_High_Level_Post_Insulator_002",
}

RISK_COLORS: dict[str, tuple[float, float, float]] = {
    "low": (0.24, 0.53, 0.21),
    "medium": (0.85, 0.55, 0.0),
    "high": (0.93, 0.15, 0.0),
    "critical": (0.75, 0.0, 0.0),
}

RISK_EMISSION: dict[str, float] = {
    "low": 0.0,
    "medium": 1500.0,
    "high": 2000.0,
    "critical": 3000.0,
}


def _risk_level(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.65:
        return "high"
    if score >= 0.40:
        return "medium"
    return "low"


def _get_stage():
    import omni.usd

    return omni.usd.get_context().get_stage()


def _create_material_input(mat_prim, name, value, type_name):
    import omni.usd

    omni.usd.create_material_input(mat_prim, name, value, type_name)


def _create_highlight_material(
    stage: Usd.Stage, mtl_path: str, color: tuple[float, float, float], emissive_intensity: float
) -> UsdShade.Material:
    """Create an OmniPBR highlight material with optional emissive glow."""
    mat_prim = stage.DefinePrim(Sdf.Path(mtl_path), "Material")
    shader_prim = stage.DefinePrim(Sdf.Path(f"{mtl_path}/Shader"), "Shader")
    material = UsdShade.Material.Get(stage, mat_prim.GetPath())
    shader = UsdShade.Shader.Get(stage, shader_prim.GetPath())

    shader_out = shader.CreateOutput("out", Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput("mdl").ConnectToSource(shader_out)
    material.CreateDisplacementOutput("mdl").ConnectToSource(shader_out)
    material.CreateVolumeOutput("mdl").ConnectToSource(shader_out)

    shader.GetImplementationSourceAttr().Set(UsdShade.Tokens.sourceAsset)
    shader.SetSourceAsset(Sdf.AssetPath("OmniPBR.mdl"), "mdl")
    shader.SetSourceAssetSubIdentifier("OmniPBR", "mdl")

    _create_material_input(
        mat_prim, "diffuse_color_constant", Gf.Vec3f(*color), Sdf.ValueTypeNames.Color3f
    )
    if emissive_intensity > 0:
        _create_material_input(mat_prim, "enable_emission", True, Sdf.ValueTypeNames.Bool)
        _create_material_input(
            mat_prim, "emissive_color", Gf.Vec3f(*color), Sdf.ValueTypeNames.Color3f
        )
        _create_material_input(
            mat_prim, "emissive_intensity", emissive_intensity, Sdf.ValueTypeNames.Float
        )

    return material


def apply_risk_color(prim_path: str, score: float) -> None:
    """Create a highlight material and bind it to all meshes/subsets under the prim."""
    stage = _get_stage()
    if stage is None:
        return
    root = stage.GetPrimAtPath(prim_path)
    if not root.IsValid():
        return

    level = _risk_level(score)
    color = RISK_COLORS[level]
    emission = RISK_EMISSION[level]
    mtl_path = f"/World/Looks/_Risk_{level}"

    if not stage.GetPrimAtPath(Sdf.Path(mtl_path)).IsValid():
        _create_highlight_material(stage, mtl_path, color, emission)

    material = UsdShade.Material.Get(stage, Sdf.Path(mtl_path))
    count = 0
    for prim in Usd.PrimRange(root):
        if prim.IsA(UsdGeom.Mesh) or prim.IsA(UsdGeom.Subset):
            binding_api = UsdShade.MaterialBindingAPI.Apply(prim)
            binding_api.Bind(material, UsdShade.Tokens.strongerThanDescendants)
            count += 1

    print(f"[kit-ext] Risk {level} ({score:.2f}) applied to {prim_path} ({count} meshes)")


def apply_fault_state(prim_path: str, faulted: bool) -> None:
    """Highlight a prim red for fault indication."""
    if not faulted:
        return
    stage = _get_stage()
    if stage is None:
        return
    root = stage.GetPrimAtPath(prim_path)
    if not root.IsValid():
        return

    mtl_path = "/World/Looks/_Risk_critical"
    if not stage.GetPrimAtPath(Sdf.Path(mtl_path)).IsValid():
        _create_highlight_material(stage, mtl_path, (0.75, 0.0, 0.0), 3000.0)

    material = UsdShade.Material.Get(stage, Sdf.Path(mtl_path))
    for prim in Usd.PrimRange(root):
        if prim.IsA(UsdGeom.Mesh) or prim.IsA(UsdGeom.Subset):
            binding_api = UsdShade.MaterialBindingAPI.Apply(prim)
            binding_api.Bind(material, UsdShade.Tokens.strongerThanDescendants)


def remove_all_highlights() -> None:
    """Unbind highlight materials from all mapped prims, restoring originals."""
    stage = _get_stage()
    if stage is None:
        return
    count = 0
    for prim_path in PRIM_MAP.values():
        root = stage.GetPrimAtPath(prim_path)
        if not root.IsValid():
            continue
        for prim in Usd.PrimRange(root):
            if prim.IsA(UsdGeom.Mesh) or prim.IsA(UsdGeom.Subset):
                binding_api = UsdShade.MaterialBindingAPI(prim)
                binding_api.UnbindAllBindings()
                count += 1
    print(f"[kit-ext] Removed highlights from {count} meshes")


def apply_restore_state(prim_path: str) -> None:
    """Highlight a prim green for restoration."""
    stage = _get_stage()
    if stage is None:
        return
    root = stage.GetPrimAtPath(prim_path)
    if not root.IsValid():
        return

    mtl_path = "/World/Looks/_Risk_restored"
    if not stage.GetPrimAtPath(Sdf.Path(mtl_path)).IsValid():
        _create_highlight_material(stage, mtl_path, (0.24, 0.65, 0.21), 1500.0)

    material = UsdShade.Material.Get(stage, Sdf.Path(mtl_path))
    for prim in Usd.PrimRange(root):
        if prim.IsA(UsdGeom.Mesh) or prim.IsA(UsdGeom.Subset):
            binding_api = UsdShade.MaterialBindingAPI.Apply(prim)
            binding_api.Bind(material, UsdShade.Tokens.strongerThanDescendants)
    print(f"[kit-ext] Restore state applied to {prim_path}")
