# Editor data QA, 2026-10-13 evening

This report covers independent host QA in `D:/bbe-r13e-qa`, based on
`52189693`. The parent names this evening checkpoint round 14 and the overnight
continuation round 15. No Minecraft instance was launched by this QA agent.
Native editor and projection rendering remain the parent and specialist agents'
responsibility. The shared implementation backlog and handoff are parent-owned.

## Concrete defects and fixes

| Commit | Reproduced defect | Final contract |
| --- | --- | --- |
| `08f0d54e` | Switching the edit layer with a stationary pointer reused the previous layer's hover target, mask error or just-placed cursor latch. | The scene hover key includes the edit layer and the cursor reset effect runs when the edit layer changes. Ordinary document revisions do not release the just-placed latch. |
| `39030992` | Small copy enlarged the displayed selection to finish a group without changing its selection revision. Large copy preserved the selection. | Copy closes groups only in the clipboard payload. The original displayed selection, bounds and revision remain unchanged. |
| `f583b045` | A small cut rejected by a locked group partner still replaced the previous clipboard and enlarged the selection. | Small cut uses the existing staged `EditJob`. A failed cut changes no data, clipboard, displayed selection or history. Successful cut preserves the displayed selection and creates one undo transaction. |
| `c9e92b97` | Small fill or strict background erase that required group completion enlarged the displayed selection outside history; undo retained the enlarged selection. | When group completion changes the edit scope, the small operation uses `EditJob`. Completion belongs to the edit, while the displayed selection stays unchanged. Ordinary small operations keep their existing fast path. |

These fixes use existing scene cache invalidation and edit transactions; no new
SDK interfaces or client/server imports were introduced. They are scoped to
`scene.py`, `model.py` and focused tests. The parent reviewed the intended
selection contract before the three model changes were implemented.

## Validation

| Test module | Test methods | Relevant evidence |
| --- | ---: | --- |
| `test_scene_layer_cursor.py` | 5 | Executes the actual production scene AST hover branch and reset effect with engine I/O stubbed; checks stationary foreground/background/automatic switching, placement target, masks, cursor latch, strict/automatic erasure and actor history. |
| `test_copy_selection_contract.py` | 3 | Uses public `Session.action` for small and large editors. Copies a foreground chest with typed inventory NBT and a background door across the Y=16 chunk boundary, then changes the source and pastes the preserved snapshot. |
| `test_cut_transaction_selection.py` | 3 | Verifies failed and successful cuts, exact layer/actor restoration, old clipboard identity, unchanged displayed selection, and retained redo after failure. |
| `test_group_closure_selection.py` | 4 | Checks automatic fill, strict background erase, locked-partner fill/erase rejection, exact undo/redo, and the ordinary small-fill fast path. |

All 15 focused methods passed. Additional existing regressions passed:
`test_edit_navigation` (8), `test_selection_history` (9),
`test_layer_groups` (16), `test_automatic_editor` (13), and `test_editor` (14).
The copy/cut fixtures exercise both `(32,32,32)` and `(64,128,64)` documents.
Typed root block-entity coordinates are rebased during paste; nested item
coordinates, binary values, tuples and large integers remain intact.

The group fixture intentionally stores a chest in front of a door. Automatic
foreground fill preserves that unrelated background door. A background lock
must reject a background write; it must not prohibit an unrelated foreground
write. This distinction is asserted by the final tests.

Scoped MCP architecture review reported only preexisting large scene/tick and
`_shape` advisories. The model and scene scope each included actual files;
passing `.py` to the scope selector would have incorrectly reviewed zero files.
`git diff --check` passed for the submitted changes.

## Other independent review

- The group specialist's one-to-one retained-part matching fixes duplicate
  foreground/background group instances and automatic promotion. The six
  targeted tests passed in the independent run. No definite blocker was found.
- The background specialist's mixed native-liquid archive replay was reviewed
  read-only. All 17 archive unit tests and 9 cold-directory integration tests
  passed. Original source and nonsource bytes are verified before derived
  import aliases are made; the replay has no checkout fallback. Original
  observations and failed rendering gates remain unchanged.

### Product water rules

The pure product policy in `2d268824` was independently reviewed in
`D:/bbe-r13e-rules`. Its 21 focused methods and the generator's `--check`
passed. No definite blocker was found in source-layer sampling, conditional
diagonals, below-neighbor flow, physical-vector UV orientation, version checks,
or preservation of old diagnostic traversal and floating-point ordering.

An additional independent continuity experiment checked 9,216 neighborhoods.
Two horizontally adjacent target water cells had every pair of saved depths
0 through 15. The two cells bordering their shared north corner independently
used air, stone, water depth 0, water depth 7, falling depth 8, or foreground
fence with background water depth 4. Each document used the actual product
provider. Both shared-edge corner heights were exactly equal, and both
internal faces were absent in every case. This is a continuity invariant,
not a claim that Java-style heights match native Bedrock pixels.

The provider intentionally caches complete-source samples. Callers must rebuild
it after changing the source document; keeping the same provider after edits
can reuse stale neighbors even if the requested target cell did not change.
Missing projection filtering must keep the complete source for that provider.

### Product connection matrix

The 19 supported fixture cases and live wrapper in `9129da98` were reviewed
read-only in `D:/bbe-r13e-groups`; all 12 new focused tests passed. The declared
stair transform literals, per-case perpendicular side cameras, scene-relative
editor pivot and body-only document isolation were checked. The editor signal
gate explicitly measures aggregate body visibility; independent editor shape
acceptance remains `None`. Generic missing-mode occupancy replaces the client
observation; the real-world chest and bed occupancy routes remain separate.

One new finalization risk was sent to the group specialist: if restoring the
saved grid raised, the wrapper skipped final source verification and report
publication, potentially leaving the underlying runner's `passed=true` and
`restored=true` report. It was fixed in `9a6d62f6`. Independent execution of all
15 focused methods passed, including injected restoration failure, source
drift, and missing initial report. Finalization now publishes fingerprints
and failed receipts even if grid restoration fails.

### Item sprite candidate

The private candidate integration in `71d0b7c7`, precision update `70586411`,
and shared projection companions were reviewed read-only. The 15 initial item
methods, 7 companion methods and resource generator `--check` passed
independently. Publication checks reject superseded generations and retain
failed release records for retry. The supported sprite family is currently
flat `diamond_sword`; unknown visual NBT and other item families are retained
as data rather than declared rendered. Production qualification remains false.

An actual frame-budget defect was reproduced: 4,095 non-frame source cells
followed by a frame were all scanned by the first `next()` call. Invisible
cells similarly bypassed budget yields. The item specialist fixed this in
`b3052c32`, yielding for every source cell before filtering. All 16 final item
methods passed independently; the added counter test verifies one scanned
cell after one step and 64 after 64 steps, including hidden cells.

### Centered snow plants

The product profile change `c42f9ad2` was independently reviewed read-only.
Version, dump and style validation, 27 generated centered profiles plus two
existing grass/fern profiles, cell bounds, alpha burial thresholds, strict
layer erasure and automatic promotion were checked. No definite production
blocker was found. All 24 methods matching `test_centered*.py` and the centered
generator's `--check` passed independently. No GPU result exists for these
new bytes; the dry shape, snow boundary, editor/full/missing and cutaway visual
suite remains pending.

The follow-up `fd4cb23a` includes the original short-grass and fern sources in
schema 2. Their existing 0.8-high meshes remain unchanged, with LF-normalized
source hashes, installed native texture hashes and alpha bounds. The generated
alpha top is scaled by the retained mesh height, giving 0.7 for short grass and
0.8 for fern. The visual tool now binds these two plants to the same versioned
source validation as the other 27. Independent execution of the profile,
centered visual and static proxy modules passed all 24 methods; the generator's
`--check` passed. These new source contracts have no live visual acceptance.

### Product water capture contracts

The bounded capture/replay tools in `35b51c1e`, with fixes `e08d2acb` and
`8e4c6150`, were reviewed read-only in `D:/bbe-r13e-liquid`. Independent final
execution passed all 40 methods from the analysis, managed registry, product
profile, blueprint and resource modules.

The review found and closed several concrete evidence defects:

- Requested world cameras previously lacked a verified interpolation wait.
  Each camera now waits for its requested pose and verifies before/after every
  frame. FOV, engine viewport and native capture size are bound to all three
  views of the same-session stone calibration.
- Editor controls now retain camera, pan, depth, cut plane, origin, size and
  the actual liquid controls' visibility, poses, positions and sizes, with
  before/after equality. Biome extra captures pass their newly ready scene
  state rather than omitting the frame's layout contract.
- Input snapshots now compare launch, before and after bytes across BP, RP,
  all top-level host Python tools and the debugging skill's Python scripts.
  The new `water_capture_contract.py` helper is included in that closure.
- Animation uses its declared RGB threshold 2, independently of the geometry
  threshold 8. The transparency ROI also requires positive dry body/rear and
  water-only signals before wet-minus-removed contributions can pass.
- Wet/dry alignment alone was insufficient for transparency. All controls,
  including liquid-only, water-only, rearless and empty, now share the wet
  control's scene pose or world camera.

An additional independent full-analyzer experiment changed each of the five
non-wet controls' poses while keeping every frame individually stable. All
ten editor/full-route negative cases rejected evidence and kept every observed
gate false; the aligned baselines remained valid. Synthetic opaque water also
fails the body/rear contribution gate. These checks validate rejection and
measurement logic; they do not establish actual water geometry, transparency
or animation. Product and historical native acceptance flags remain false.

### Scaffold native palette proof

The collector/derive review of `07454a5f` reproduced two false positives: an
upper cell with air foreground but background stone classified as supporting,
and `aux=False` compared equal to air's zero. The specialist fixed these in
`9933b4d0`, following the source archive change `335cbd3b`.

Classification now requires an integer air aux and an exact native dry palette
for the upper cell, while support palette and liquid values must remain
recursively typed-equal across the three measurement phases. Native state
material buckets are retained instead of assuming the whole bucket is empty.
Independent native-palette, runtime-catalogue, runtime-lifecycle, admission
and legacy single-air modules passed 22 methods. The actual background
agent's archived read-only palette observation was also parsed independently:

- Source: `D:/bbe-r13e-background/docs/evidence/background-startup-contrast-r14-v2/palette.json`
- SHA-256: `7d8c1e20bb11df8447a82c2d0a558718ddaef646b8520774f274a4b1559444dd`
- Observed air state encoding: `[[["minecraft:air", 0], {}]]`; common has the
  same material at index 0, and both extra buckets are empty.

The sequential wrapper `b690790d` was also reviewed. Its original source list
omitted the single-air modules imported by the supervisor; they and the
projection package initializer are now retained. Independent execution of the
collection module passed all nine methods. A default preparation was run in
`D:/bbe-r13e-qa/.runtime/scaffold-collector-qa-r14-prepared-v1/`; all 19 local
Python modules loaded in a fresh process had archived source pins, with no
missing current or archived bytes. The plan permits zero launches and remains
`prepared_not_executed`. Completed segment receipts are rehashed before union
and loaded one at a time; the original receipt remains the evidence source.

A further validator defect was independently reproduced: if both an actual
palette and the report-provided expected palette had background stone, the
original `valid(actual, expected)` accepted them as dry air. The real producer
rejected this encoding, but independent report validation did not. The final
`12de62f9` now validates the expected four typed buckets as dry air, checks
native volume axes are integers, and requires observation fingerprint format
in both catalogue and lifecycle validation.

All 24 final focused palette, catalogue, lifecycle and collection methods
passed independently. Eleven additional direct/report negatives rejected
matching background-stone palettes, invalid expected encodings, and missing,
short, nonhex or integer observation hashes in both validators. This closes
the reported isolation and evidence defects. No complete native catalogue or
editor/full/missing visual acceptance exists.

## Limits and integration

These results validate host data and control-flow contracts. They do not prove
engine palette writes, UI pixels, water transparency/UV animation, snowy
plant shape, sign text, item glint, or full/missing projection appearance.
Built-in editor blueprints do not replace separate projection acceptance.

Integrate the four scoped commits in order rather than merging this worktree's
whole branch. Root owns the final commits, shared backlog, native evidence,
23:30 checkpoint, and next-day 07:00 hibernation. Never report an old complete
test suite or historical screenshot as acceptance of the latest bytes.
