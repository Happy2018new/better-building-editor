# Owned Client Anchor Item And Body Depth

This prospective finite probe follows the native-player V4 positive control.
It asks whether the exact owned `modern_projection:anchor` client actor includes
a plain native item in entity-ID PaperDoll rendering, then whether opaque body
geometry on that same actor shares useful depth with the item. V4 and its failed
API uniform-mapping gate remain unchanged. No glint input is part of this probe.

The documented `CreateClientEntityByTypeStr` returns a client entity ID or None.
`BindItemToMinecraftModel` requires `isClientEntity=True` for that actor and accepts
the anchor's existing `root` bone. Its plain diamond sword dictionary is derived
from the frozen native physical report. Offset, ZYX rotation and item scale remain
0/0/0, 0/0/0 and 1 throughout. The exact actor ID is the UI render target; UI scale
0.35, depth -50 and rotation 0/0/0 remain fixed. Player position is only read: an
unloaded sentinel height aborts preparation before native actor creation.

Eight states each receive two full native PNGs: empty, plain, body-only at Z -2,
combined at Z -2, body-only at Z +2, combined at Z +2, plain restored by hiding the
body, and empty restored. The plain state must first produce at least 80 stable
pixels outside empty-frame motion and pass all existing V4 marker checks. Only
then may the body stage dispatch. The body is one opaque 3x3x1 stone slab from
`GetBlankBlockPalette` and `DeserializeBlockPalette`, converted under a nonce-owned
geometry name. It uses `AddActorBlockGeometry` on the same actor; only its Z offset
changes. No world blocks, inventory, textures, shaders, materials or transparency
settings are changed. Matching body-only controls test whether the depth move
preserves the 2D silhouette before any occlusion interpretation.

Four markers retain V4 colors, native rectangles, TL/BR training and TR/BL holdouts.
Full captures are persisted before any layout or marker validation. Failed marker
checks are retained and never passed by using another ROI. The fixed pixel metric
uses the full physical width below the top ten percent to exclude debug text; this
is a separately declared ROI, never physical calibration or a crop inferred from
GetScreenSize. Offline scoring reproduces the frozen marker fit, receipts and
ordinary/depth masks. All production, editor, shared-depth and glint acceptance
flags stay false; candidate metrics require visual inspection.

The owner starts the normal 90-second deadline before client/network initialization.
The probe receives the cleanup deadline at +120 seconds, reserving 30 seconds after
the normal budget. The owner bounds actual opener dispatch, token reads, SDK RPCs,
captures, close and final checks inside an outer 150-second limit. No retries or new
game starts are permitted. All paths must be fresh before any dispatch.

The game-side nonce state and host report record attempts before actor creation,
binding, palette conversion, body attachment, offset/visibility changes, UI render,
pop and actor destruction. Partial initialization remains discoverable even if the
host sees a timeout. Cleanup removes only known owned attachment IDs, waits for the
owned transition, pops once only when the owned page is top, and destroys only the
exact returned owned actor. Pending attachment IDs may be disposed by destroying
that owned actor only after independent read-only absence is confirmed. A pending
creation with no returned ID remains unresolved; no guessed ID or global entity
enumeration is used. Unknown page or actor state is retained, not discarded.

`DestroyClientEntity` has no boolean return contract, so absence is confirmed with
the prospective `GetEngineTypeStr is None` criterion, followed by exact
navigation/document/camera/profile comparisons. The SDK entry does not document
that absence token: the live pre-destroy getter must be non-None, and the actual
post-destroy receipt must independently demonstrate None before this cleanup
criterion passes. An unexpected result retains owned state and fails restoration.
V2 records the positive getter result in nonce-owned state during readiness or
before destruction, and requires it in both absence and final restoration checks.
An always-None getter cannot qualify. Getter failure never prevents the single
exact-owned destroy attempt. V1 is preserved as an undispatched reviewed draft.
The nonce state is discarded only when these checks pass. Geometry has no documented
delete API in the queried SDK records: its unique small resource remains inert until
session exit after the sole owned actor is removed, and is never reused or overwritten.

The CLI only prepares and verifies offline files. Frame owns all SDK execution and
background captures in the existing healthy session. QA reviews the frozen source,
manifest, meaningful failure tests and owner wrapper before a single attempt.
The manifest pins the actual imported finite executor, V4 marker helper, anchor BP,
RP, geometry, controller and transparent texture. Owner staging compares those
resource bytes against the physically loaded pack without modifying them.
