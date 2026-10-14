# R15 native rendering profile evidence

The qualified production subset for NEMC `3.10.0.420447` is ordinary, copper, and ender **single chests in world projections**, plus flower pots on the existing terrain/context path. Each cell still requires the captured actor schema. Runtime version alone never admits a cell. The 3.9 registry and saved block/NBT identities are unchanged.

Production editor previews retain chest proxies. Native chest bodies pass frontal visibility but fail shared depth against terrain at oblique angles. The independent-name control in `56-unique-native-oblique/frame.png` versus `58-unique-fallback-oblique/frame.png` establishes that regression. Earlier repeated geometry names could retain GPU resources and must not be treated as a valid native/proxy comparison. The tool now gives each submitted geometry an independent diagnostic name and retains both requested and actual names.

## Accepted production evidence

All of the following PNGs were manually inspected. Captures use background WGC with an owned no-activation game; raw before/after state, source scripts, tool receipts, and actual Combine material/actor names accompany each run.

| Evidence | Result |
| --- | --- |
| `43-restarted-default-status/01_status/result.json` | Fresh production Session initialized the measured profile without diagnostic assignment; bridge/runtime version both 3.10.0.420447. This preceded the additional editor scope restriction. |
| `69-scoped-default-editor/frame.png` | Final scoped profile: three chest proxies render above their supports in an oblique editor view; pot and poppy remain visible. Combine receipts contain chest proxy material names and only the flower-pot native actor. |
| `71-scoped-default-full/frame.png` | Prepared world data retains the native three chest actors and potted poppy at the intended positions. Bed remains the existing independent proxies. |
| `74-scoped-default-occupied/frame.png` | Real stone occupants suppress all four admitted bodies; support strips and neighboring fences remain. |
| `76-scoped-default-restored/frame.png` | Removing the exact temporary occupants restores the four bodies. Restore receipts verify the original air cells. |
| `16-full-context/frame.png` | Negative coordinate control: packed context duplicates/displaces native chest bodies. These bodies therefore use model-local selected-cell batches. |

Final scoped qualification used owner `native-render310-r15`, copied project `D:/bbe-r15-native-production`, game PID `47968`, game identity `134364256401523988`, MCDK port `51296`, session `60695c6595894ffcbe4c9fca5e36be0e`. Initial coordinate experiments used the same owner in session `05484e4fa33f444693455d58252b7fe9` (PID 49836). Addon reload hit a native `DisabledSkinScreenController` assertion; the background guard rejected subsequent execute calls. Only that owned instance was stopped and replaced. No desktop activation was used.

## Explicit limits and ongoing candidates

- Beds are injectable candidates, not production native bodies. The source capture is one head-piece actor. Duplicating that actor into both halves yielded suspect repeated pillow bands and uncertain partial-occupancy appearance (`34-full-mixed`, `37-missing-bed-head`, `40-missing-bed-foot`). Existing proxies remain selected.
- Patterned standing/wall banners use the actual item-placement capture from `r15-solo-runtime/banners-v4`, preserving Base 4 and patterns `bs/1`, `ts/14`. `59` through `67` are candidate runs only. The first wall fixture had a support directly under the hanging fabric, occluding its lower stripe. No production banner admission follows from these runs.
- Head fields, empty shulker actors, shelves, and frame item contents are not admitted by this profile. Body routes do not imply item companion support.
- Final accepted controls cover the recorded actor states and geometry placement. They do not establish all directions, all plants, double chests, animated openness, or all UI clipping planes.

## Reproduction and tests

`tools/audit_native_coordinates_r15.py` exercises the ordinary Session load, bridge geometry, full projection, and missing projection entry points in an explicitly supplied owner/session. `--route production` verifies the active production profile without replacing it. Candidate routes require an explicit `--route model_local`, `context`, or `mixed`. `--family banners` uses the separate real banner capture.

The focused suite includes exact payload/name gates, immutable profile identities, preservation of actor fields and typed saved NBT, selected-only cross-chunk batches, explicit context batches, Session/geometry/tile cache invalidation, production Scene filtering, and prepared world snapshots. The new bridge regression verifies Scene uploads chest proxies while prepared world uploads native chest actors. See `qualification.json` for the current count and source hashes.
