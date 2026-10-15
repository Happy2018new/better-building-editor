# Isolated R21 Native Lectern Body Candidate

This candidate is prepared only in `.runtime/projects/book-r20`. The repository's
business sources, default gates, book geometry and global clipping predicates
have not been changed. No new Minecraft process has been launched for it.

## Ownership

`lectern_body.py` has a closed `CANDIDATE_ENABLED` flag. Offline checks enable it
only in the test process. The prepared material remains native
`minecraft:lectern`; there is no substitute mesh. All known registry states are
included in the experiment, including both powered values. This is structural
coverage, not appearance qualification for those states.

The complete-palette, incremental-document and local-batch builders emit the
selected lectern body and its rendered actor once in its own overlay. Packed
neighbors exclude that body and actor. An extra layer retains its existing
context route. A lectern absent from the target palette never emits an overlay.
Rendered actor positions are cloned and rebased using the existing NBT helper.
The saved logical document and its full NBT remain unchanged.

`geometry_palette.native_actor` returns the renderer portion of a lectern actor
envelope. The real public empty and book fixtures both supply `{}` to native
body generation. `BookPreview` and `BookProjection` read the full logical
document independently; target, hidden/layer and occupancy filtering stays on
that existing route. The runtime host asserts identical native material/actor
inputs for the real empty and book lecterns, and a book appearance only for the
logical book lectern.

## Offline Results

- `offline-report.json`: 86 tests passed, zero errors/failures/skips.
- Seven candidate tests include all eight native states across three builders,
  six neighbors including above and below, cross-chunk targets, absent targets,
  extra-layer preservation, rendered actor rebasing, opaque nested data, support
  occupancy/removal/restoration and logical book ownership.
- Three public world preparation tests use a paired real public empty/book
  fixture with upper, lower and side neighbors. Full and missing routes emit
  two native bodies and one book group; initially present lecterns emit neither
  body nor book; hiding the lectern layer and restoring it keeps both owners
  synchronized. Native-body renderer inputs remain empty, and closing releases
  the book owner.
- Existing table, native actor, context cache/bank, book owner, resource and
  qualification tests were run against the clone's loaded `projection` package.
- `offline-first-harness-failure.*` preserves an initial harness-only import
  error: the runner lacked the repository root on `sys.path`. After correcting
  the runner, the complete suite passed. It is not native runtime evidence.
- Scoped MCP review parsed both changed business files successfully. Its single
  warning is the existing large `ContextPaletteBuilder.__init__` signature.

## Shared Shader Contract

The candidate does not change the shared shader or occupancy shader. Vertex
initialization sets `renderContext=vec4(0)`. For an actor tagged by slot 4's
`19487` and slot 1's `19490`, only material transparency values `.25/.75`
activate the local packed-context decoder and set `renderContext.w=1`.
The independent overlay uses `.125/.625`; it bypasses that decoder and retains
`renderContext.w=0`. The fragment's center-cell predicate therefore does not
discard its overhang. The material bank still decodes to bank 1/2 respectively;
stale material banks continue to be hidden.

`overlay-shader-report.json` executes the unchanged real vertex and fragment
stages in GLES 100 and 300, both plain and alpha/blend/transparency variants.
All 224 pixel checks passed. Synthetic quads include Y overhang `.581528254`
and `.653281482`, Z overhang `.653281482` and a negative-side control `-.58`.
Packed context rejects those overhangs; active overlay keeps them; stale banks
remain blank. This is SwiftShader synthetic raster evidence. It does not prove
the native engine's generated lectern mesh or real book/body pixels.

## Prepared Runtime Experiment

`probe_runtime.py` uses an already assigned exact owner/session/project, the
verified single-frame WGC helper and ordinary public projection entry points.
It never launches or activates a game. Its scenario matrix is:

| Scene | Real Source | Candidate Phases |
| --- | --- | --- |
| Plain | Empty and real item-used book lecterns, cyan supports below | Body only, full with book owner, missing, hidden target, present target |
| Upper | Same pair with stone immediately above | Same phases |
| Side | Same pair with a central stone side neighbor | Same phases |

Each phase uses four fixed cameras. Raw native inputs for empty/book bodies
must match and have `{}` renderer payloads. Native Combine receipts distinguish
context/overlay parts. Already-present and hidden targets must emit zero native
lectern body indices and zero custom book groups; selected targets must emit
exactly two native body indices outside packed context. Saved logical source
must remain unchanged. Original session fields, candidate flag, player, world,
camera and environment are journaled for restoration.

The cyan-only positive control remains a separate run of
`tools/probe_native_palette_body_r16.py --block minecraft:cyan_concrete
--context-control`, after this candidate's runtime state is restored.

This host is compiled and its expanded runtime templates have been checked
offline. It has not been run against a game. A cold launch, source-bound actual
captures, visual inspection and lifecycle checks are still required. Main and
candidate book geometry must not be changed to conceal native body clipping.
