# Entity Visual Controls, Round Eight

This checkpoint records new, independently frozen positive and negative controls
for the unchanged public oak hanging-sign fixture and three public chest source
cells. It changes verification tools only. It does not close the full entity
visual matrix or justify merging the unaccepted chest UV proposal `008ca89`.

## Scope And Provenance

- Game: `NEMC 3.9.0.401155`.
- Palette dump SHA-256:
  `6b2d9e961e934a745f5ab30d697cf22fb463fd3792d371a6dd42cb4342062f01`.
- Worktree: `.runtime/r8-entities`, branch `codex/r8-entities`, base `67dfc74`.
- Owned instance: `0b3b5a21a6bf431e97a3e56624c56678`, owner `p0-entities-r8`.
- All accepted captures use reliable, native-resolution background WGC.
  No activation, desktop input, foreground input, or resize was used.
- Each run freezes production and relevant verification tool byte hashes before
  capturing and verifies them again after restoring state.
- The frozen production list includes `block_registry_data.py`. The pack verifies
  its bytes against every run's freeze and checks its embedded `SOURCE_VERSION`
  and `SOURCE_SHA256` against the actual palette dump. Native sign reports and
  captured chest documents also record matching runtime registry metadata.
- The registry manifest and dump were not separate capture-time freeze entries;
  their recorded provenance is checked through the frozen generated registry.

The machine-readable record is
`tools/data/entities_visual_acceptance_r8.json`. It contains seven accepted runs
and ten preserved runs, including repeat confirmations and all three new failed
attempts. Every original report, freeze artifact, PNG and capture sidecar has a
byte fingerprint. `tools/data/entities_visual_viewed_frames_r8.json` separately
lists the 34 actual frames opened and inspected by the agent.

## Hanging Sign Text

The public `hanging_front_back` fixture uses an oak hanging sign with glowing
green front text and non-glowing half-alpha red back text. The unchanged
production fixture supplies text, style, attachment and camera parameters.

The new opt-in `wood_rectangle` oracle finds the largest solid wood rectangle
from a blank frame. It fixes the R7 detector's merging of board and brown terrain.
The original `row_spans` detector remains the default, so old failures remain
reproducible. This is an oracle change, not a production rendering fix.

All original limits remain fixed: channel delta `20`, color response `20`,
normalized glyph IoU at least `.45`, relative layout center `.1` and size `.2`.
New controls are stricter: repeated blank frames must have zero board pixels
above delta `20`, and shown-versus-blank pixels outside the native text bounds,
with a two-pixel margin, must also have zero pixels above `20`.

| View | Actual Editor Glyph IoU | World Projection Glyph IoU | Layout | Blank And Outside-Text Controls |
| --- | ---: | ---: | --- | --- |
| Front | 0.9760935910 | 1.0000000000 | Pass | Pass, zero changed pixels |
| Back | 0.6007390121 | 0.7563462339 | Pass | Pass, zero changed pixels |

These results are from `sign-hanging-r8-frozen-front-back-v2`. The separate
`sign-hanging-r8-frozen-missing-front-back-v3` run repeats both views in missing
mode against actual air targets and passes with the same IoUs. Front-only v1
also passes. Camera, renderer, source document and native palette/style are
recorded before and after each frame and remain unchanged.

## Actual Occupied Lifecycle

`sign-hanging-r8-actual-occupied-v3` tests world projection only. It writes actual
stone into a reserved air target; it does not override the occupancy observer.
The native/world positive blank board and visible text are captured first.

Both front and back pass dynamic hiding, initial generation over the occupied
target, and recovery after clearing. The occupancy tracker records `state=2`,
`rendered=2`, cache slot `-1`, settled mesh work, and unchanged document/history
while occupied. Both occupied visibility pairs have zero changed board pixels.
Recovered text has IoU `1.0` and exact layout against the pre-occupancy reference.
Positive front/back coverage is 11,915 and 3,598 pixels respectively.

The earlier v2 also passed and remains preserved. V3 freezes the corrected
`verify_shulker_orientations.py` camera-helper dependency. The failed v1 used a
different camera convention and failed before occupied screenshots; its original
report remains failed. The lifecycle evidence is independent from the actual
editor viewport text evidence above.

## Chest Top View

`chest-top-r8-public-three-camera-player-plus8-v4` compares actual player-placed
native world chests with projections of unchanged public cells. It uses existing
production resources, not `008ca89`. Scope is the recorded top view only.

| Public Source | Direction | Shape IoU | Texture Cosine | Scale Error | Center / Boundary RMS |
| --- | --- | ---: | ---: | ---: | --- |
| `test.entities.classic`, single normal, `(9,1,3)` | South | 0.9621192053 | 0.9506789840 | 0.0084745763 | 0.7071 / 0.7071 px |
| `test.connections.context`, double normal, `(26,1,5),(27,1,5)` | North | 0.9773684211 | 0.9804695708 | 0 | 0 / 0 px |
| `test.connections.context`, default double copper, `(26,1,10),(27,1,10)` | North | 0.9997446374 | 0.9750559362 | 0 | 0 / 0 px |

Original gates remain unchanged: native signal at least 1,000 pixels, shape IoU
`.82`, relative scale error at most `.2`, texture cosine `.45`, center distance
at most three pixels, and boundary RMS at most four pixels.

The corrected fixture saves/restores player foot position, flight state and
rotation, moves the flying player to the declared top camera side, waits for
client replication, then reapplies the locked camera. Teleporting can reset the
camera, so each capture checks the recorded pose before and after.

Preserved failures:

- `chest-top-r8-baseline-plus8-v1`: native chest state existed but no visible
  chest was captured; the largest native signal was eight pixels, below 1,000.
- `chest-top-r8-camera-player-plus8-v2`: camera reset after teleporting and did
  not match the declared top view; timed out before capture.
- R7's original +16 native-control failure and unaccepted UV proposal remain
  unaccepted in the original R7 manifest.

## Pending Coverage

Chest actual editor-viewport acceptance remains pending. A custom native UI
PaperDoll control is not treated as equivalent to the product editor viewport.
Other chest species, wax/oxidation variants, directions, states and non-top views
remain outside this checkpoint. Other sign species, attachments, directions and
styles likewise require their own frozen controls. R7's original sign failures,
offline reports and failed attempts are linked without reclassification.

## Cleanup And Reproduction

All workflows restored their reserved world cells, camera, editor, workspace,
HUD/options, inventory where used, daylight and player state. The final read-only
audit confirms all temporary flags absent, no projection actors/mesh/work, no
jobs or navigation transitions, workspace closed, daylight cycle enabled,
can-fly true, flying false, and foot `[4.5,68,-6.5]`.

The first final audit, using the transient initial spawn y=69, failed solely on
the position comparison and remains preserved. The first chest v1 and final
chest v4 both independently saved/restored the grounded y=68 position. No
corrective teleport was applied to pass the read-only audit.

The owned instance stopped normally before the deadline. Session state is
`stopped`, `ready=false`; game PID `8312` and MCDK PID `33232` are absent. The
final manifest records the successful audit, failed earlier audit, settled-player
baseline source and stopped-session fingerprint.

For a newly owner-bound guarded instance, set `MCDEV_SESSION_FILE`,
`MCDEV_OWNER`, `MCDEV_MCP_URL`, `MCDEV_NATIVE_CAPTURE_HELPER`, and
`MCDEV_NATIVE_CAPTURE_EXE` explicitly. Use fresh output directories:

```powershell
python -X utf8 tools/verify_hanging_sign_controlled_holdout.py <new-sign-output> --view front --view back
python -X utf8 tools/verify_hanging_sign_controlled_holdout.py <new-missing-output> --view front --view back --projection-mode missing
python -X utf8 tools/verify_hanging_sign_occupied_visuals.py <new-occupied-output>
python -X utf8 tools/verify_chest_top_frozen_holdout.py <new-chest-output> --case-limit 3 --target-height-offset 8 --player-at-camera
python -X utf8 tools/verify_entity_visual_cleanup.py <audit.json> <recorded-x> <recorded-y> <recorded-z>
python -X utf8 -m unittest discover -s tests -p 'test_sign*.py'
```

The checkpoint passed 19 focused sign tests, compilation of changed host tools
and `git diff --check`. No production test suite is claimed for this test-only
change.
