# Native Frame Route R11

Observed 2026-10-12, approximately 20:40-22:00 Asia/Shanghai, in the isolated
`codex/r11-frame` worktree based on `f6d8e35`. Native rendering acceptance is
still false. All owned game and MCDK sessions are stopped; temporary marker
materials, registration files and shaders have been restored to baseline.

## Results

The stable editor baseline reproduces R10C: combined-minus-body and repeated
combined-minus-body both contain 0 item pixels, the isolated item contains
1,390 pixels, and the positive shulker contains 29,674 pixels. The first run
had a transient blank combined capture, so the stable second run is the
baseline. Both originals are preserved. Submitted frame and item cells remain
219 and 795 in native 8x8x17 versus logical 8x8x8.

An unconditional magenta fragment was bound to
`netease_block_as_entity_transparency:entity_alphatest_netease`. Its cold frame
editor marker remained absent, both without and with an explicit package
`common.json` registration. The registered world body and combined samples
also contain 0 magenta pixels. The opened PNG still shows the normal brown
frame and the sword. Missing package registration alone is not a demonstrated
cause, and no native frame matrix values were recovered.

The final cold experiment added an independent green fragment on the existing
`sign:entity_static` key while retaining the magenta native-transparency
fragment. The opened sign PNG shows a solid magenta sign body. After excluding
the inverse-color crosshair, it contains 68,693 magenta pixels and 0 green
pixels. This proves that the same material file and magenta fragment reach a
native sign draw, while the frame draw remains unmarked. It does not identify
the frame's actual material.

The original report's green positive control counted 240 pixels from the
inverse-color crosshair. That report was not rewritten. A separately hashed
offline score report corrects the observation. The route tool now excludes a
24-pixel radius around the native image center before scoring either color.

## Preserved Evidence

`tools/data/native_frame_route_r11.json` binds 216 artifact files across eight
owned sessions, including failed originals, PNG/capture receipts, exact frozen
source bytes and startup logs. Its initial SHA256 is
`e1fa7772c84323c23803c8569a78e7bc8938aa6b041d5d1c0a93f9fe5d012d92`.
Session manifests include process creation identities and final stopped state.

The useful final session is
`C:/Users/Happy2018new/.pyreact-debug/instances/dfde9240ce38406d9e70f76d462a029a`.
Its `frame-sign-route-cold-v1.json`, sibling `.sources` directory and
`frame-sign-route-cold-v1-score.json` preserve the source binding and corrected
analysis. Game PID/creation identity was `5264` / `134362865911626772`; MCDK was
`58960` / `134362865909063825`. After restored SDK state and a graceful stop
timeout, identity-bound forced stop completed; both processes were independently
absent. No foreground fallback, activation, resize or desktop input was used.

The R11 rebuilt MCDK SHA256 was
`68cbff0f7a2454e37c823fab51a8bd3f4631f3e7c7c8e221b1b124add76d297f`.
The existing approved focus-guard DLL and native WGC executable were unchanged.
The final ready session and all fresh native WGC receipts remained background
safe. Foreground Word remained the same across final startup and captures.

One broad base-material diagnostic session stalled after readiness before the
owner-binding read completed. No fixture mutation was reached. Its WGC receipt
was compositor-fresh while its visible in-game timestamp was old; that capture
does not establish a live engine or a material result. A later protected startup
failed with `Focus guard module snapshot failed` before a game identity. These
failures remain separate from route evidence and do not establish a shader or
socket cause.

## Next Native Gate

### Finite Opaque Family Attempt With Fixed IPC

The 22:25 cold session `4ddf0c3d571d4eb5af8ce126effc1918` used MCDK SHA256
`b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9` and the
generated IPC source matched upstream SHA256
`aa37dc422b869936d34380c23f81a8fb1b0ca3b8cd12aed781efa929c9c91e8c`.
It prepared inherited cyan `opaque_block`, yellow `opaque_block_color`, red
`opaque_block_color_uv2` and magenta transparency markers, retaining the normal
sign override. Startup verified both session tokens. The route tool's subsequent
client token read returned no value before entering the fixture body. No fixture
mutation or SDK restore was attempted; world cleanup was not independently
verified. The original report and exact candidate sources are unchanged.

A WGC receipt at 22:28:33 was fresh and background-safe, but its opened PNG
showed the in-game timestamp stuck at 22:26:17. This attempt is therefore neither
a family-material falsifier nor evidence that the IPC fix caused the stall.
All four generated hot-reload settings were true, and no source edits occurred
between startup and failure. The graceful stop timed out; creation-bound forced
stop completed and both game `28912` and MCDK `49956` were independently absent.
Temporary marker files were restored after the stop. The supplemental index
`tools/data/native_frame_route_r11_ipc_family.json` records this separate failure.

### Required Route And Native Checks

Prove a scoped frame material marker before using a matrix marker. Preserve
native skinning, glint, animation, lighting and texture processing when adapting
depth. Native actor coordinates may include bone placement and 1/16 scaling;
terrain Y recentering cannot be applied to them without measured units.
Body-only 8x8x8 versus combined 8x8x17 also needs a same-volume body control.
Acceptance still requires the original composite, alpha, full/missing,
facing/rotation, occupancy and cleanup checks with the frame body present.

## Verification

`python -X utf8 -m unittest tests.test_native_frame_route
tests.test_flat_frame_item_pixels tests.test_flat_frame_editor_trace` passed
16 tests. The new tests reject the inverse-crosshair color, blank matrix markers
and corrupt five-pixel cells. `py_compile` and `git diff --check` passed.
