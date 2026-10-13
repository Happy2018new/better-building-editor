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

### Pending specialist follow-ups

- Water probe review found unverified camera interpolation and paired-control
  framing, no complete launch/before/after resource freeze, and an unused
  declared temporal threshold. The specialist is implementing explicit pose
  waits, per-frame evidence, source equality gates and threshold 2 for animation.
  FOV/resolution stability, editor-control alignment and source-drift negative
  test independence need final verification.
- Scaffold collector review of `07454a5f` found that `classify` checked the
  upper cell's foreground and fluid but ignored its native palette. An upper
  non-fluid background stone still classified as supporting; `aux=False`
  also passed equality with zero. These must remain unknown unless the exact
  observed dry-air palette and integer aux are verified. Five catalogue and
  four native-palette methods passed independently, but these extra negative
  cases are pending specialist fixes.

## Limits and integration

These results validate host data and control-flow contracts. They do not prove
engine palette writes, UI pixels, water transparency/UV animation, snowy
plant shape, sign text, item glint, or full/missing projection appearance.
Built-in editor blueprints do not replace separate projection acceptance.

Integrate the four scoped commits in order rather than merging this worktree's
whole branch. Root owns the final commits, shared backlog, native evidence,
23:30 checkpoint, and next-day 07:00 hibernation. Never report an old complete
test suite or historical screenshot as acceptance of the latest bytes.
