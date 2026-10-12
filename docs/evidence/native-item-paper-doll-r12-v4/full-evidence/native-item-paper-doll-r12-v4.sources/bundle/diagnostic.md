# Native Attached Item In Entity-ID UI Rendering

This finite diagnostic tests whether a native item attached to the exact local
player's `head` is included by `RenderEntity({'entity_id': player, ...})` in an
isolated Pyreact `PaperDoll`. It does not establish the item-frame geometry
route, shared block depth, clipping, opacity, material identity or GLINT inputs.

## Documented Contracts

The MCP API records for `RenderEntity`, `BindItemToMinecraftModel`,
`SetBindBoneForBindItem`, `GetQueryableBoneOrientation` and `GetModelId` were
checked while preparing this probe. `RenderEntity` accepts `entity_id`, which
takes precedence over `entity_identifier`. The native player/head binding
example uses `isClientEntity=False`; the binding dictionary has
`newItemName`, `newAuxValue`, `isEnchanted` and `userData`. Removing an exact
attachment uses its returned ID and an empty bone name. `GetModelId` must not
be read immediately after rendering; it is recorded after UI readiness and a
delay and is never used as the item binding target. Bound-item inclusion in
entity-ID UI rendering is the hypothesis, not a documented guarantee.

## Frozen Inputs And Controls

`tools/data/native_item_contents_r11_raw.json` is required to have SHA256
`a853a88604aa5dc05a4cf60d0f18a43db66eda8c7cb012e28db0322548bc86fc`.
Its completed, restored native physical readback and client actor snapshot
must agree. The actual enchanted diamond sword retains all its typed item
data, including native Short (`__type__=2`) enchantment ID 9, level 3 and the
original `modEnchant` value.

The five states are `empty`, `plain`, `flag_enchanted`, `actual_enchanted`, and
`empty_restored`. Plain and flag-only dictionaries differ only in the boolean;
the actual dictionary retains the complete native `userData`. Each state has
three fresh background native-resolution captures, 0.4 seconds apart. The UI
uses one opaque square entity paper doll, the same player, scale 1, depth -50,
rotation 0/60/0 and a fixed opaque `F7F9FCFF` page background. A fresh UI tree
must confirm the exact owned doll, props and opacity for every capture.
Independent native `GetGlobalPosition`, `GetSize` and `GetPath` reads confirm
the owned root and doll rectangles plus the host viewport. Their bounds must
agree with the keyed UI snapshots. INSTALL records the native
`CreateGame(level).GetScreenSize()` result and freezes the positive square side
as `min(240, width - 32, height - 32)`. The native root must corroborate these
size inputs, and the same centered doll size is retained for the full matrix.
The API documentation calls these dimensions pixels; native v2 observations
were 499x277, matching the UI root instead of the 1994x1105 physical capture.
V3 preserves this observed value separately from the documented unit claim and
does not label it physical pixels. V4 records `GetScreenViewInfo` with its raw
offsets as additional evidence. Neither API result is assumed to define a
physical crop. All raw metrics and actual bounds must stay fixed across the
matrix. Client clock values must advance throughout.

V4 adds four fixed opaque 6x6 solid Image markers at eight-unit corner insets,
outside the centered doll, with cyan, magenta, yellow and green RGB colors.
Each STATUS independently records their native rectangles and cross-checks
their fixed positions, colors, opacity and bounds against keyed UI snapshots.
Full native PNGs are searched for all connected color components with fixed
per-channel tolerance 16. Each color must have exactly one component of at
least four pixels, with rectangle fill at least 0.95; ambiguity is rejected.
Only the top-left and bottom-right markers train one positive scalar and x/y
translation. The other two markers are independent holdouts, and all four
predicted centers and rectangle edges must agree within one physical pixel.
The first empty frame freezes this mapping for all later frames. Each frame
must pass all four marker checks with those same parameters before its native
doll bounds define the crop. No item or player pixels participate in fitting.

## Ownership And Restoration

Only the existing frame owner may invoke `execute_probe`. Importing the tool
and its preparation-only CLI make no game calls. The owner supplies its exact
session/window guard and the reviewed native capture wrapper/executable. The
owner must retain its `RecordedClient` request/response trace, including raw
MCDK `isError` and error text from token-binding reads before any requested
SDK command. A generic missing-return exception is not sufficient evidence.
The 150-second deadline reserves 30 seconds for cleanup; each SDK RPC is bounded
and there are no retries or new game starts. All report, PNG and receipt paths
are checked for freshness before any dispatch.

The probe creates one nonce-owned navigator page and removes only attachment
IDs returned to that nonce. It never clears another attachment. A timed-out
bind or invalid return leaves a pending row and reports restoration failure
without guessing an ID. Removal failures are recorded while other owned IDs
are still cleaned. Cleanup first waits within the finite reserve for the owned
navigation transition to settle, then dispatches its single owned pop. It never
repeats a bind, push or pop after an uncertain mutation. Popping refuses to
remove an unrelated page. The original
navigation, document, camera and profile values must compare exactly before
owned state is discarded. There are no world, inventory, shader or material
writes, and all production and glint acceptance flags remain false.

## Offline Evidence

`score_probe` verifies each capture against its immutable native receipt,
re-detects all marker components and reproduces the same frozen calibration
and actual doll crop. It excludes motion seen in the
six empty reference frames, intersects all attached-versus-empty differences,
and reports stable item candidates above 80 pixels. Temporal differences are
measured inside a shared eroded item candidate after excluding plain motion.
These are evidence metrics requiring visual review, not proof of material
selection or enchantment glint. The 24 offline tests cover native typed data,
target arguments, freshness, tampering, fixed layout, uncertain binding,
exact-ID cleanup, native snapshot differences, physical mapping/DPI rejection,
partial push settle/timeout, navigation/camera preservation and conservative
scoring. V2 superseded v1's snapshot-only crop and transition cleanup. V3 changes
only the frozen viewport-derived sizing and explicit observed screen units;
all original bundles are preserved. V4 declares a separate prospective marker
calibration rather than changing the old API-mapping or screenshot thresholds.
A 499x277 observed screen mapped to a 1994x1105 physical image still fails the
existing one-pixel API uniform-mapping tolerance. That failed flag is retained
in each marker report; successful independent markers do not overwrite it.
Tests cover missing/ambiguous markers, held-out position changes, frozen-map
drift, nonuniform scaling, receipt tampering, fixed native marker props and a
complete synthetic 15-frame run that calibrates before binding and reproduces
the mapping offline. No marker outcome establishes item or glint acceptance.

The owner should call `score_probe` only after runtime cleanup and a fresh
health check, preserving failed reports and captures without replay.
