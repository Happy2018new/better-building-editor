# Sealed native liquid control diagnostics

`capture_pure_liquid_native_controls.py` uses the existing owner/session-bound
native path harness, same-session frozen camera calibration and reliable
background Windows Graphics Capture helper. It never starts or owns a game.
Run it only inside the existing owned `run_live_check.py` workflow.

Example arguments for the owner runner:

```text
tools/capture_pure_liquid_native_controls.py OUTPUT.json
  --cell-origin X Y Z
  --capture-helper CHECKPOINTED_SIGN_CHECK_HELPER.py
  --camera-calibration SAME_SESSION_CALIBRATION.json
  --case water_depth_0_foreground
```

An optional second `--case lava_depth_0_foreground` reuses the same location,
camera and sealed shell after clearing the entire cavity. No background-layer,
neighbor, flowing-state or uncontained scene is supported by this small runner.
Choose a new output path and prefix; earlier failed captures are preserved.

`--shell-block barrier` selects a barrier shell for a separate diagnostic of
otherwise occluded boundaries; the default remains glass. The chosen material
is recorded in every plan and must match both native readbacks. Invisible
containment still changes the neighborhood and does not make the observation
eligible for public geometry acceptance. This runner does not assign corners
or infer unseen heights for either shell.

The world source cell minimum corner is explicit. The isolated public document
focus maps to that cell, and requested source/support values come exclusively
from `source_document(case_id, isolated=True, control=...)`. The fixed public
world camera offset is `(-5, 4, -7)`. The native player must be on its camera side.

Before any mutation, the runner checks the entire reservation for foreground
and background air, saves a cleanup marker, then writes and verifies a closed
3 by 5 by 3 shell of the selected material. Its three-cell vertical inner cavity has the requested
source in the middle; the public support is the lower cavity cell. An air guard
and the player platform/headroom are also reserved. General `WorldAdapter.write`
uses the current full native palette with explicit common and extra layers.
Neither that setter nor neighbor-update suppression establishes tick freezing.
The runner does not change the global liquid-flow setting.

Four requested controls and their actual native snapshots remain separate:
`supported_positive`, `supported_negative`, `liquid_only` and `empty`. Each PNG
has server/client snapshots of the complete reservation immediately before and
after capture. These retain raw native palette data, including extra states,
as well as decoded foreground/background for every cavity, shell and guard cell.
Source drift, falling liquid, extra-layer residue, actors and unknown/missing
data fail the declared-context state gate. Values are never rewritten merely
to make the requested state match. Earlier completed captures are checkpointed
before attempting the next control, and failed capture artifacts remain listed.

The liquid-only/empty and supported/support-only differences have independent
pixel gates. They use the fixed unit-cell hull and exclude both adjacent cavity
cells with the existing 3px boundary guard. Support-only pixels are counted
separately and cannot pass a liquid gate. The unchanged glass shell is explicitly
part of the diagnostic context; a missing/occluded liquid positive signal stays
failed. There is no ROI widening, translation fit, automatic corner assignment,
flat-surface inference or version height rule. All four corners are unobservable.

Cleanup clears every nonshell reserved cell in both layers while the shell
still contains liquid ticks, then verifies two separated server/client samples.
Residual liquid or uncertain snapshots retain the shell and cleanup marker and
raise an error, so the parent harness cannot report `restored=True`. Only after
those checks does cleanup remove the shell and verify the entire reservation
twice, restore the player and delete its marker. Camera, visual settings, probe
and environment cleanup remain owned by the existing native path harness.

The added shell changes the public fixture context. Every report therefore has
`context_changed=True`, `public_controls_eligible=False`,
`native_geometry_accepted=False` and `accuracy_accepted=False`, even if independent
pixel and native-state diagnostics pass. `completed=True` means all requested
diagnostic captures were recorded; it does not accept public liquid geometry.
Live captures and native tick behavior still require the owner to verify them.
