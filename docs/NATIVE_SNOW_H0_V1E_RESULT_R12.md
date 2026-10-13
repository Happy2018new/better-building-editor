# Native Snow H0 V1E: Visible Native Fixture, Projection Guard Stopped

The one released original-texture V1E run established a visible near-player
native cell and captured all four native states. Native covered h0 contains
both thin snow and a red poppy; snow-only removes the poppy, plant-only
removes the snow, and blank removes both. The first projected covered image
shows snow without a visible poppy. A strict full mesh-tuple equality guard
then stopped the matrix, so projection snow/plant/blank and the complete
native/projection comparison remain unavailable. The failure and original
images are retained. No alpha condition or retry ran.

Preparation `b5d1296a703e22533d41dfce2b4b2b9e3ae550f1` passed independent
incremental QA, 25 focused offline tests, both review-only plan validations,
and exact Git-byte verification of 42 indexed files, the index and three
live source files. V1D remained frozen and unrun.

| Pin | SHA-256 |
| --- | --- |
| Executed original plan | `14ec599ee4ad3b3bbe001521d4f60b70edcbbe4ac510f4dfe66569325f01385d` |
| Adapter | `5488bd6fcb856a89f67646091d582535e5fa9f80df84fa82f802388408a94b25` |
| Phase | `d1abff0a35445ff4e7fa3cb1f7753f8e8dd906cdc78416a56bfe67a35696bf76` |
| Freeze index | `caa25d7d2d487af618fd3fd8138406e40c02c8eb6f77ca3f7fb8447d1c01b63d` |
| Runtime archive index | `ddde977f4ae6757136db394e591841ae493ab2d637e8439aaef59f549ae9178d` |
| Post-cleanup verification | `f74921ba1b1b3c2c808523a00763ea36a9377372b5c438c1a8b5cdecb3e2da6c` |

Session `b4ca81720aa4443eb49915be098014be` owned game PID 54224 with creation
identity `134363303290096225` and MCDK PID 20380 with identity
`134363303287095657`. Actual live capacity was zero before launch; dead CIM
objects were excluded by exact liveness. The one launch finished rc1 after
114.31652799999574 seconds under unchanged 240/190/50/90 bounds, with no
deadline overrun, foreground fallback, resize or player mutation.

The scheduled first original is black and the SDK-ready first original is
the loading overlay. Read-only application queries reported uninitialized
at T72.2308959 and actual owner/session/bridge/ready/HUD at T74.1728306. The
separately locked first application original was opened during the owned
run and shows the grass world, horizon, chest, mobs, hand and HUD.

Target `(6,-48,6)`, support `(6,-49,6)` and player foot `(0.5,-60,0.5)` were
read back with loaded air preflight. Existing client chunk observations
included `(0,0,0)` and target section Y=-3; these are observations rather
than native section-mesh authority. The first predeclared yaw+180 candidate
matched its pose after actual render events and had official GetForward
cosine `0.9999999999998105`. The direct SDK candidate was never requested.
Actual camera was `(4.5,-47.349998474121094,4)`, FOV 60, SDK screen 499x277,
physical PNG 1994x1105. Actual public WorldToScreenPoint was unavailable;
the first stone/blank pair showed a visible stone over the retained support.
The frozen crop and threshold produced a qualified filled component of
113706 pixels, bounds `(306,115,683,455)`.

All ten produced original images were opened. Offline native-only
differences inside that fixed ROI are plant-minus-blank 12370 pixels,
snow-minus-blank 25956 pixels and covered-minus-snow 10344 pixels. Native
plant control therefore has visible signal above the frozen 80-pixel
threshold. These counts describe this original-texture cell; they do not
complete the missing projection or alpha controls.

The retained error contains both projection status snapshots. Actor,
model, world origin `(5,-49,5)`, parts and scales remained equal, but the
mesh tuple's final anchor changed from `(6.5,-47.5,6.5)` to
`(0.5,-59,0.5)`. The existing product `Bridge.follow_projection()` moves
the client actor into the player's loaded section and compensates its
geometry offset to preserve world coordinates. This source explanation
does not erase the executed full-tuple guard failure or establish that
each projected shape is correct. The runtime archive preserves the exact
error, first projected image and incomplete row.

Native fixture layers, biome, time/daylight and unchanged player state were
restored. Camera restoration kept the saved journal until actual readback
across new render events matched saved position, equivalent rotation,
unlocked pitch/yaw, FOV and player foot; the journal was then cleared.
The owned render listener was removed. Phase and supervisor cleanup errors
are empty. Normal close did not close the game, so exact owned process
handles were terminated, wait results were zero, and independent checks
confirmed both identities absent. Three original host files, own flower
override absence, unchanged native texture and all 1432 behavior/resource
file hashes were independently verified. WGC was immediately released.

Passive game handle counts were 658/672/710 before readiness, then a fresh
852 baseline and 866/863 at T84.887/T100.873. No growth trigger fired;
resource health and causality remain unaccepted. The archive retains 128
runtime/freeze/input/instance files plus index and cleanup verification.
Production, offsets, plant position profiles and the existing 29 positive /
232 height / 8 negative acceptance remain unchanged.
