# Cauldron finite surfaces handoff — 2026-10-14 pause

User requested saving context and terminating agent conversations before switching models. Work is paused; no further runtime calls, launches, tests or shared integration were attempted after that instruction. Agent: `/root/r15_docs_resume`, parent `/root`.

## Scope and ownership

Implement measured finite cauldron water/potion/custom RGB/lava tops, reuse existing liquid lifetimes, validate native geometry and actual editor/full/missing product routes. Root owns all shared integration and final commit. Do not edit root-owned `bridge.py`, `session.py`, `geometry_palette.py`, `world_projection.py`, `occupancy.py`, `tiles.py`, `render_context.py`, `entity_render.py`, `scene.py`, or the four main documentation MDs without coordination. Root explicitly authorized cauldron-only model/material registry entries, which have already been installed. Root's last message says shared cauldron wiring has **not** been implemented yet.

Skills previously read and followed: `mod-workflow`, `mc-search`, `pyreact-debugging`, references `instances.md`, `runtime.md`, `setup.md`. Imports inspection completed for `cauldron_projection.py` depth 2; MCP confirmed one module, dependencies `cauldron_render_plan`, `liquid_projection`, and no direct callers yet. Final MCP review has **not** run.

## Stable hook contract (sent to root)

- `cauldron_profile.candidate_profile(max_groups=128)` will return candidate profile after generated data exists.
- `cauldron_render_plan.prepare_shells(common, states, actors, profile, biome)` returns detached `common, states`, replacing only supported nonempty cauldrons with empty render shells. Logical source and NBT remain untouched.
- `CauldronPreview(session, profile)` subclasses `LiquidPreview`; same `LiquidControls`, `LiquidModels`, `group_view` path, no duplicate lifecycle.
- `CauldronProjection(bridge, document, origin, profile, dimension, hidden=(), layer=None)` subclasses `LiquidProjection`, injecting its own plan factory. Shared renderer publication/opacity/retirement methods are inherited.
- Render group key `(origin, ('cauldron', texture, color, alpha), slot)`.
- Registered resources: `modern_projection_cauldron_water`, `modern_projection_cauldron_water_world`, `modern_projection_cauldron_lava`, `modern_projection_cauldron_lava_world`.
- Root plans `session.cauldron_profile = None` until actual product acceptance. **Do not enable by default from native-only evidence.**

## Files created/modified by this agent

Untracked runtime modules under `behavior_pack/modern_projection/projection/`:

- `cauldron_render_plan.py`: foreground only; target/visibility filters; immutable actors; same liquid payload/grouping; finite top mask 1. Render-only empty shell selection.
- `cauldron_projection.py`: shared world projection subclass.
- `cauldron_preview.py`: shared preview subclass with immutable snapshot.
- `cauldron_profile.py`: explicit 3.10 measured profile; six heights; signed typed CustomColor low 24-bit RGB; observed PotionId/Type typed shorts; lava white; plain water lookup by biome; unsupported actors retain native route.

**`cauldron_native_data.py` does not exist yet**, so `candidate_profile()` currently cannot load data. Need deterministic generator from measured JSON plus provenance hash, then profile/deployment tests.

Tools:

- `tools/audit_cauldron_surface_r15.py`: owner-bound fixture setup/fill/item/color/light/control/references/biome/view/capture/restore. Server journal preserves block/NBT/extra liquid. Restores rules/biome, but **does not yet reset client camera**. MCP documented `ResetCameraPos()` plus `UnDepartCamera()` (latter unlocks yaw/pitch) for eventual cleanup. Current fixture remains live.
- `tools/analyze_cauldron_surface_r15.py`: calibrated geometric fit from 125 SDK projection points + native red concrete cube calibration.
- `tools/analyze_cauldron_colors_r15.py`: simultaneous white/black same-UV color ratio; excludes crosshair. **Current exact equality of camera rotation rejects harmless float roll settling (~0.000007 degrees)** in v2 potion forms. Fix by explicit justified pose tolerance or wait for stable pose before capture; preserve failures. Older first supplemental captures with ~72-degree camera change are actually invalid and must stay rejected.
- `tools/generate_cauldron_resources.py`: dedicated copied cauldron-water atlas 32 frames / 2 ticks; lava 32 / 16; top-only meshes; source texture alpha; TOTAL_REAL_WORLD_TIME positive tick clock; inset .125; UV .125..875. Installed resources generated from `.runtime/cauldron-resources-r15-v1`.
- `tests/test_cauldron_render_plan.py`: 6 tests for grouping, immutable contents, targets, visibility, budgets, fallback, shell replacement. Existing `test_cauldron_appearance.py` 5 tests. Last targeted run **11 passed**. No later tests were run.
- `tools/data/cauldron_native_nemc310_v1.json`: incomplete measurement candidate; `water_colors={}`; potion effective pixel estimates 5..46; states from native read-final; `product_acceptance_claimed=false`.
- `tools/data/cauldron_resource_contract_nemc310_v1.json`: generated provenance with resource hashes and cadence; no product acceptance.
- New resources in `resource_pack/models/modern_projection/cauldron`, `resource_pack/textures/models/modern_projection/cauldron`, four cauldron GLSL files; only cauldron entries added to shared material/model registries.

## Native evidence accepted

Base folder `docs/evidence/cauldron-surface-r15`; original metadata `docs/evidence/cauldron-runtime-r15/content/result.json` and `read-final/result.json`.

Native runtime 3.10.0.420447 / MCBE 1.21.130.0:

- Registered block `minecraft:cauldron`: water aux 0..6, lava 8..14, snow 16..22. Six nonempty fills.
- Potion item aux 0 ordinary water gives fills 2/4/6, PotionId=-1 and PotionType=-1. IDs 1..4 empty. IDs 5..46 actual potion IDs. ordinary/splash/lingering types 0/1/2.
- Signed CustomColor -65536 and unsigned 16711680 both observed red. RGB channels observed. Two alpha-byte encodings agree, but do not claim universal alpha behavior without additional cases.
- `water1-calibrated`..`water6-calibrated` and `lava1-calibrated`..`lava6-calibrated` support heights `(5,7,9,11,13,15)/16`, inset 1/8. Maximum height residual < .004 blocks, edge residual about .25-.31 pixels. Calibration from `control/` native unit red concrete cube, pixel offset about (-.46755,-2.79865), cube residual .3798 pixels. Camera matrix fit .000115 pixels. Do not use earlier uncalibrated candidate fits.
- `lava6-uv.json`: 1020 texel edge observations; block-coordinate inset UV fractional error .02314 versus full-texture stretch .30084. Supports `.125..875`.
- Custom color `0x325060` RGB (50,80,96) simultaneous white/black references measured approximately (51,81,96), within ~1 byte. `color-calibration.json`, `color-mixed-reference`.
- All ordinary potion IDs 5..46 captured with intended overhead camera and expected NBT. `potion-colors.json` contains **effective native pixel estimates**, not exact extracted engine constants. Estimates per potion family differ by ~1 byte due texture/phase; no product parity yet.

## Plain water remains unresolved

Valid biome reruns completed at `biome-{plains,swampland,desert,ice_plains}-v2`; before/after exact same intended camera `(69.44392395, -179.99996948, -.00001366)`, client biome matches each requested biome. `biome-colors-v2.json` reports ratio against colored white/black references:

- plains (41,65,70)
- swampland (41,64,71)
- desert (42,65,71)
- ice_plains (40,64,71)

Per-texel spread is broad (~20 bytes), so **do not treat these as a measured native tint table**. Viewed `biome-plains-v2/detail.png`: plain water dark/translucent, CustomColor white much brighter, black almost black. This indicates different native material/opacity path or atlas behavior. Biome edits may not fully invalidate neighboring blend cache; do not generalize independence from these four cases.

Installed 3.10 `resource_packs/vanilla/blocks.json`:

```
cauldron textures: up=cauldron_top, down=cauldron_bottom,
  north=cauldron_side, south=cauldron_inner,
  west=cauldron_water, east=still_water_grey
lava_cauldron east=still_lava (west still cauldron_water)
```

Installed native texture statistics:

- cauldron_water.png: 16x512 RGBA, grayscale 197..238, alpha 168..226; flipbook ticks 2.
- water_still_grey.png: 16x512 RGBA, grayscale 154..247, alpha 240.
- lava_still.png: 16x512 RGB, cadence 16.

Exploratory `texture-fit-v1.json` uses native texel center samples and fits any adjacent-frame mix/transforms. Best RMSE around 2.1 plain and 2.34 custom white for water_still_grey, but cauldron_water fits ~2.2/~2.54 too, insufficient discrimination. **Not accepted proof**. Root was told a separate potion texture model may become necessary, but this was only a hypothesis, and no resource changes were made from it.

## Supplement potion form captures

Original `splash_potion-{5,43,44,45,46}` / `lingering_potion-{...}` and original `biome-*` captures had changed horizon camera and are invalid. Their raw evidence remains.

Second run `*-v2` completed all 10 forms, applying view again after each item write. Position stayed identical; pitch/yaw intended; roll settles from roughly -.0000065 to -.0000134 degrees during capture. Analyzer currently rejects strict camera_rotation inequality, so **these are not yet scored/accepted**. No `potion-form-colors-v2.json` was written because analysis aborted at first sample. Relax only subpixel float tolerance or recapture after settling; preserve native before/after points and quantify motion. Biome restored to plains in `biome-restore-plains-v3` before this run.

## Active runtime instances and pause state

**Clean native fixture (assigned ours, preserve parent gallery):**

- Session `C:/Users/Happy2018new/.pyreact-debug/instances/e150444343dd46f0a0f791b165872648/session.json`
- owner `clean-nemc310-runtime-audit-r15`
- game PID 13804, MCDK PID 44480, port 53471
- project `D:/bbe-r15-dynamic-runtime/.runtime/nemc-clean-310`
- server state `api._cauldron_surface_r15`: origin (6,-58,0), refs (8,-58,0)/(10,-58,0), full journal. Last native contents lingering potion 46, fill 6; biome plains; overhead camera detached/locked. Do not mutate gallery z>=8. Older parent water spill at x=0/3 is excluded and must not be arbitrarily deleted.
- No pending tools/captures on clean instance. Former exec sessions 7895 and 82127 are complete.

**New isolated product instance launched exactly once:**

- project `D:/bbe-r15-cauldron-production` (fresh source/resource copy; all auto_hot_reload options false)
- owner `cauldron-product310-r15`
- session `C:/Users/Happy2018new/.pyreact-debug/instances/bf6a4f16278246a3b549448e42e68d21/session.json`
- game PID **32868**, MCDK PID **34124**
- launch used same hash-pinned noactivation DLL/MCDK as clean. `MCDEV_ALLOW_USER_FOREGROUND=1` only exempts user focus; never activates.
- startup returned failed after 120-second readiness deadline, error `Readiness deadline reached before initialize`. No successful bound business call has run against it.
- Important log evidence: actual world initialization **finished late around 14:00:20**, after startup deadline. `mcdk.log` shows `modern_projection.pyreact.host SafeAreaProbeScreen`, `TerminalHudScreen`, `in_game_play_screen`; suggests process remained live and might be recoverable after identity/session validation. **Do not blindly relaunch or forge ready state.** Inspect owned status/log and use supported route recovery if any. Agent did not stop process because user explicitly said MC can be preserved.
- Launch stdout, stderr, exact source hashes stored at `D:/bbe-r15-cauldron-production/launch-stdout.json`, `launch-stderr.txt`, `launch-sources.json`.
- Copy was made before runtime DATA existed and before root shared wiring. Copy requires synchronized final modules/resources before product acceptance; cold resources versus updated source must be clearly evidenced.
- Exec session 53901 is complete (return code 1). No pending host processes were started by this agent afterward.

Other games: root native production PID47968 (`native-render310-r15`), unmanaged user3.9 PID40452 must be preserved. Root confirmed those + clean13804 were the only effective games before our start; water35392 stopped. Root gave cauldron and water agent one slot each under max5. Several old Windows process records are dead/no-window leftovers; do not kill them. Root/water may have since consumed the fifth slot. **Recheck capacity before any next launch.**

## Resume priorities

1. Recover/validate current product instance route and ownership without spawning extra games; coordinate root shared wiring readiness.
2. Finish native potion form camera-tolerant analysis; preserve real horizon failures.
3. Resolve ordinary water material/texture/opacity empirically, or leave unsupported plain water on existing native shell route. Do not fabricate RGB parity. Root explicitly approves validating measured potion/custom/lava first.
4. Emit deterministic `cauldron_native_data.py`; record incomplete acceptance honestly; profile/data/resource validation tests.
5. Verify actual product editor/full/missing lifecycle, source NBT preservation, hidden/solo layers, opacity, occupancy removal/restoration, cancellation/retirement. Native-only captures and FreeModel-only diagnostics do not satisfy product acceptance.
6. Add client camera restoration to fixture tool using documented APIs; eventually restore owned fixture server journal/rules/biome and camera, without disturbing root galleries.
7. Run targeted unittest and MCP imports/review on explicit changed scope (ensure files>0), then report result to root. No commit by this agent.

Known review points: actor payload merge by index in `prepare_shells` could combine non-cauldron actor maps; check native source invariants. Source texture alpha vs actual native rendering is still unqualified. Lava animation period 25.6 seconds does not divide TOTAL_REAL_WORLD_TIME 3600-second reset, so no seamless reset-continuity claim. Profile model selection may need dedicated potion asset if empirically justified, but stable class/lifetime contract need not change.
