# Camera Image Generation Prompts

> [!NOTE]
> This project was developed with assistance from AI tools.

These prompts generate realistic fixed-camera perspectives for the Grid Resilience Operations Center demo. All images should be **1024x768** or **1280x720**, representing what actual pole-mounted or substation security cameras would capture.

**Critical constraints:**
- Ground-level or pole-height perspectives — NOT aerial/drone
- Fixed camera angle — slight motion blur and compression artifacts add realism
- Piedmont NC setting — rural/suburban distribution corridor, deciduous trees, red clay soil
- Winter/overcast lighting for storm scenario images

## Image 1: `cam_p037_baseline.jpg`
**Camera:** CAM-P037 (pole-mounted, looking at crossarm)
**Expected finding:** None (baseline, no defects)

> A fixed security camera view from a wooden utility pole looking directly at a wooden crossarm on a distribution power pole. The crossarm is in good condition with two porcelain insulators mounted on it. Three aluminum conductors pass through the insulators. The pole is weathered gray wood. Background shows overcast sky with bare deciduous trees. Rural North Carolina setting. Clear day, no damage visible. Realistic utility infrastructure photography, slight lens distortion from a wide-angle security camera.

## Image 2: `cam_p037_cracked.jpg`
**Camera:** CAM-P037 (same camera, later frame during storm)
**Expected finding:** `cracked_crossarm`, critical

> A fixed security camera view from a wooden utility pole looking directly at a wooden crossarm showing a visible longitudinal crack. The crack runs parallel to the wood grain, approximately 30cm from the pole attachment point, extending through most of the crossarm depth. Frost and light ice accumulation visible on surfaces. Two porcelain insulators are mounted on the crossarm with aluminum conductors. Overcast winter sky, light freezing rain. The crack is clearly visible but realistic — not exaggerated. Utility infrastructure monitoring camera perspective.

## Image 3: `cam_p041_baseline.jpg`
**Camera:** CAM-P041 (pole-mounted, concrete crossarm)
**Expected finding:** None

> A fixed security camera view from a utility pole looking at a concrete/fiberglass crossarm on a distribution pole. The crossarm is in good condition — no cracks, no damage. Three polymer insulators are mounted on it supporting aluminum conductors. Light overcast sky, bare winter trees in background. Rural residential area in North Carolina. Light frost on the crossarm surface. Utility monitoring camera perspective with slight wide-angle distortion.

## Image 4: `cam_p052_veg1.jpg`
**Camera:** CAM-P052 (span monitor, looking along conductor)
**Expected finding:** `vegetation_encroachment`, major

> A fixed camera view looking along power line conductors from one pole to the next, spanning approximately 120 meters. Tree canopy from a large deciduous tree (bare branches, winter) is encroaching within approximately 1.5 meters of the upper conductor on the right side of the frame. The branches are close enough to be a clear hazard. Overcast sky, wet conditions. Rural North Carolina distribution line corridor. The vegetation encroachment is obvious — branches nearly touching the conductor. Utility span monitoring camera perspective.

## Image 5: `cam_p052_veg2.jpg`
**Camera:** CAM-P052 (same camera, adjacent span)
**Expected finding:** `vegetation_encroachment`, major

> A fixed camera view looking along power line conductors showing vegetation encroachment from multiple trees on both sides of the right-of-way. Pine and deciduous trees with branches extending within 2 meters of the conductors on two adjacent spans. Overcast, damp conditions. The conductors show slight sag. Rural North Carolina setting with mixed forest along the distribution corridor. Utility span monitoring camera perspective, slight compression artifacts.

## Image 6: `cam_sub_a_baseline.jpg`
**Camera:** CAM-SUB-A (substation security camera, transformer bank)
**Expected finding:** None

> A substation security camera view looking at a distribution substation transformer bank. A large pad-mount transformer with cooling fins is centered in frame, sitting on a concrete pad within a gravel yard. Chain-link fence visible in background. Multiple bushings and insulators on top of the transformer. Wet ground from recent rain. Overcast sky. All equipment appears in normal condition — no damage, no discoloration, no leaks. The view matches a typical substation perimeter security camera angle — elevated, looking down slightly. Rural electrical substation in North Carolina.

## Image 7: `cam_p063_ice.jpg`
**Camera:** CAM-P063 (pole-mounted, ice accumulation)
**Expected finding:** `ice_loading`, major

> Close-up photograph from a fixed pole-mounted monitoring camera aimed along three parallel aluminum ACSR conductors extending away from the camera toward the next pole 120 meters away. The camera is mounted at crossarm height on a weathered wooden utility pole, looking outward. Each conductor has a thick transparent glaze ice coating approximately 8-10mm radial thickness, making the normally 12mm diameter wires appear 28-30mm. The ice is smooth, clear, and glossy — classic freezing rain glaze, not rough rime ice. The three conductors are spaced roughly 30cm apart horizontally on a simple wooden crossarm with standard porcelain pin-type insulators. The conductors sag noticeably under the ice weight. In the background, bare deciduous hardwood trees are completely coated in ice, branches glistening. Dark overcast sky, visibility reduced. Small ice droplets visible on the camera lens. The scene is photographed in low contrast winter light. No text overlays. Photorealistic, documentary style, shot on a wide-angle utility monitoring camera with slight barrel distortion and JPEG compression artifacts.

---

## File naming convention

Save generated images to `data/images/base/` with the filenames listed above. The Camera Simulator will map camera IDs to these filenames.

After generation, run the Cosmos Transfer 2.5 augmentation pipeline to create weather-augmented variants in `data/images/augmented/`.
