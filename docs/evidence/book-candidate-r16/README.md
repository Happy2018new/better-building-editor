# Book Appearance Investigation, Round 16

Engine: NEMC `3.10.0.420447`, MCBE `1.21.130`. This bundle is an investigation
and an isolated rendering candidate, not a product qualification.
`book_profile.production_profile` returns `None` for every engine.

## Native Observations

`native/report.json` records 19 reliable background captures through the normal
editor and full/missing projection paths. Its four contact sheets were opened
and inspected. The authentic source fixtures are
`test.dynamic.special/enchanting_table.default` and
`test.entities.visible_item_slots/lectern.empty` / `lectern.book`.

| Block | Observed Native Result | Authentic Source |
| --- | --- | --- |
| Enchanting table | Table body visible; no floating book in either editor or projection | Typed `EnchantTable` block NBT including `rott` |
| Empty lectern | Native lectern body visible with no book | Typed empty `Lectern` NBT |
| Lectern holding a book | Identical visible body to the empty lectern; book absent | Item-placed typed `book` and `hasBook=1`, captured by the earlier content-slot probe |

The native lectern palette actor is `{}` even when its source NBT contains a
writable book. The source NBT is retained. An empty native render payload does
not authorize inventing inventory contents or dropping the stored book.

## Candidate Implementation

The candidate owns four modules: `book_profile`, `book_render_plan`,
`book_preview` and `book_projection`. It reuses the established four-cell
transport and preview/world model owners. Native table and lectern bodies are
retained. Appearance is selected from the complete logical source and its
typed NBT; the target palette only selects which cells should be drawn.

The lectern parser reuses the versioned, observed content-slot schema. The
enchanting-table branch requires an authentic `EnchantTable` actor and treats
an absent actor as unsupported. The three focused tests cover that empty actor
case, empty versus occupied lecterns, source retention, target validation and
the disabled production gate. All three passed. MCP review parsed all four
modules without warnings or risks; its sole hint is the six-argument plan
interface shared with the existing companion infrastructure.

`generate_book_resources_r16.py` creates project book geometry using the
installed native 64 x 32 `enchanting_table_book` artwork. No native hardcoded
book mesh or exact native appearance is claimed. The enchanting-table book
has persistent floating and rotation; it does not react to player proximity.
The lectern book is static. Page text, interaction and particles are outside
this appearance candidate.

The isolated probe temporarily substitutes the portal companion classes and
profile only in its disposable game. Its `finally` block stops projection,
closes the editor, restores the camera and restores those three substitutions.
No repository lifecycle integration or product admission is implied by this
probe. It performs no world block writes.

`compile.json` checks 30 stage/version/flag combinations for the final v4
resources. Twenty-two compile successfully. Eight GLSL 100 skinned vertex
variants inherit the native `mat3x4` header failure, also reproduced by the
native baseline. These eight are unsupported inherited variants, not passes.
All custom shader float and varying precision is explicitly `highp`.

## Remaining Work

The first candidate completed 23 reliable captures and restored its temporary
state. Its enchanting-table companion was visible in the editor and both
projection modes, but its first mesh looked too flat. The occupied lectern
still had no clearly visible book despite a successful published group. This
is a rendering failure requiring mesh placement, inclination and depth review,
not evidence of native support. The final v4 candidate opens the book geometry
more clearly; it remains unqualified.

The v4 cold-start probe completed another 23 captures, restored all temporary
state, and its four review sheets were opened. Its floating enchanting-table
book, cutaway and layer hide/restore are visibly present. The occupied lectern
book is visible in full/missing world projection but remains absent in the
editor. That difference needs dedicated preview-depth/occlusion investigation.
The user's direct observations additionally identify incorrect book brightness,
floating height and rotation direction. These must be compared with a real
native table/book at the same camera and elapsed times before further admission.
Visible movement alone does not satisfy that comparison.

Product integration needs dedicated `book_profile`/preview/world lifetimes in
the shared owners. It must not replace the portal slots used by this isolated
probe. Before enabling it, qualify the public fixtures on the actual default
path, opposing cameras, native-body occlusion, cutaway and layers, scale,
lectern directions, table animation, full/missing projection, occupied-cell
restoration, opacity and cleanup. Do not admit it from group counts alone.

The repository retains authentic reports, individual capture receipts and
contact sheets. Full-resolution pixels and original probe call records remain
in ignored `.runtime/book-native-r16-v1`, `book-candidate-r16-v1` and
`book-candidate-r16-v2`. A fresh clone cannot replay raw-pixel analysis without
those local captures. No acceptance manifest exists for these books.
