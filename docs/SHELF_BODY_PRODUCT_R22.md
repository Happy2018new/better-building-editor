# Shelf visible-body candidate, round 22

The product defect is an invisible shelf body in the editor and world
projection. This candidate routes the shelf body through the existing common
block palette, while the original document remains the owner of its three item
slots. It introduces no independent body overlay, shader change, scalar lighting
correction, or screen-height fit.

`shelf_body.BODY_ENABLED` starts false pending the short runtime smoke test.
Native ambient-occlusion parity is a separate unresolved appearance issue and
does not block accepting a visible body with correctly placed item contents.

The generated resource set contains 240 solid block models and corresponding
hidden block definitions: twelve woods, four cardinal directions, and five
front appearances. Every model uses the installed NEMC `3.10.0.420447` 32×32
shelf texture and the preserved reference in
`tools/data/shelf_body_java_1.21.9_reference.json`. The generator emits a hash
manifest when invoked; it appends only the shelf entries in the two shared
resource registries.

The installed 384 semantic states are read through the authoritative block
registry. Supplied states must match the registry exactly, including bool/int
NBT types. Conflicting records retain the original native route. Powered front
roles follow the existing restored four-case native observation in
`.runtime/shelf-role-matrix-r20-v3/report.json`: type 0 unconnected, type 1 right,
type 2 center, type 3 left. Unpowered states share the unpowered appearance.
Those observations identify artwork; their normalized diagnostic scores do not
qualify lighting.

The adapter replaces common-layer material IDs at their existing indices and
suppresses the replaced shelf actor in the render palette. The original
document, actor NBT, extra layer, logical volume, context packing, target
ownership, and item-slot planning retain their existing behavior. The narrow
item predicate initially admits only oak shelf aux 0, facing south; the Item
agent owns the independent per-item production qualification for apple aux 0
plain and diamond sword aux 0 plain/enchanted.

Offline checks currently pass: all 384 states resolve to 240 registered models;
conflicting and mistyped records are retained; Scene, full and missing context
preserve body positions and target ownership; occupied neighbor content cannot
become a visible target; hidden layers remain absent; all three original slots
survive; non-shelf actors and the extra layer remain intact; ordinary bookshelf,
chiseled bookshelf, lectern and enchanting table produce unchanged results.
The old shelf diagnostic regression tests also pass with the candidate gate
disabled.

The four oak unpowered direction models are exactly equal to the original
bone-rotation `*_ao` resources in the committed
`docs/evidence/shelf-direction-r21-v1/candidate-inputs` package, except for their
render-only identifier. The native oak atlas is byte-identical. The failed
baked, reverse and native-axis experiments are not used. The original west/east
native and proxy raw images were reopened: the front artwork and silhouette are
preserved, while the proxy remains visibly brighter. The old four-direction
unshifted silhouette IoU was south 0.998633, west 1.0, north 0.998556, east 1.0;
these values do not qualify lighting.

The runtime probe does not launch or close MC. After the root grants an owned
`shelf-r22-*` session covered by the current assertion watcher, the probe enables
the candidate in memory and uses one compact document. It takes three temporal
shown frames and one body-only control for each of these conditions:

1. Scene with all three shelves, then a layer selection hiding the upper shelf.
2. The selected layer after editor rotation.
3. Full world projection with two visible three-slot shelves.
4. Missing projection in air.
5. Missing projection with the neighboring shelf cell occupied by real stone.
6. Missing projection after restoring that confirmed-air cell.

An additional empty west-facing shelf is present on the selected layer. One
extra item-hidden Scene capture looks toward that body, and the acquisition
report checks that its west proxy actually reached a native geometry submission.
No west-facing item contents are admitted.

The exact three slots are plain apple, plain diamond sword, and the observed
real diamond sword enchantment `(9, 3)`. The upper shelf and the occupied
neighbor provide visibility controls; item-hidden captures expose the body and
depth relationship. Captures require the owned process identity and at least
6 GiB available system commit at every boundary. The probe restores its world
cell, session profile, candidate gate, document and environment, and verifies
the cold resource hashes. The root owns the subsequent one normal close and
exact process exit observation.

Default enablement follows raw image review of visible body, native texture,
slot placement, depth, hidden-layer absence and missing-mode occupancy. This
smoke test does not claim all wood/orientation pixels or native AO parity.
