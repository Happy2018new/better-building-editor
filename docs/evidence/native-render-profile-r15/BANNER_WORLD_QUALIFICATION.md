# Round 15 Native Banner World Qualification

Reviewed on 2026-10-14 at 15:10 Asia/Shanghai. Runtime: NEMC
`3.10.0.420447`, MCBE `1.21.130.0`. The selected route is world-only
`model_local` for standing and wall banners with complete normal-banner actor
payloads. Editor depth and banner waving remain unresolved.

The new source fixture uses actual inventory banner items placed through
`PlayerUseItemToPos`: base color 4, no patterns, three patterns
(`bo1`, `cr14`, `mc11`), and six patterns
(`bs1`, `ts14`, `ls11`, `rs3`, `cs8`, `bo0`). Both standing and wall variants
were read back from the server and client palette. Inventory restoration
succeeded; the extra layer is empty. Source records are in
`102-real-banner-payloads/report.json` and its stable runtime receipts.

The following native screenshots were actually opened and inspected:

| Screenshot | Qualified observation |
| --- | --- |
| `106-banner-identity-full-frame/frame.png` | Six bodies; plain, three-pattern and six-pattern colors and layers visible |
| `109-banner-rotate90-full-frame/frame.png` | Bodies follow the 90-degree material and support rotation |
| `112-banner-rotate_y180-capture/frame.png` | Bodies follow the 180-degree rotation; back-facing wall supports naturally occlude part of the cloth |
| `115-banner-rotate_y270-capture/frame.png` | Bodies follow the 270-degree rotation |
| `118-banner-mirror_x-capture/frame.png` | X mirror preserves patterns and changes positions and pose |
| `121-banner-mirror_z-capture/frame.png` | Z mirror preserves patterns and changes positions and pose |
| `123-banner-mirrorz-missing-frame/frame.png` | Missing mode initially shows all bodies |
| `125-banner-mirrorz-occupied-frame/frame.png` | All six occupied banner cells disappear; their unoccupied supports remain |
| `127-banner-mirrorz-restored-frame/frame.png` | Removing occupancy restores all six bodies and patterns |

Host document transformations call the actual editor `_transform` method.
The production `native_actor` render copy refreshes `bannerDirection` from
the resulting `ground_sign_direction` or `facing_direction`. It preserves
pattern fields, typed tags and the saved document. Admission validates the
repeated-field schema for any complete pattern count; it does not whitelist
the two old `bs`/`ts` patterns. Normal `bannerType=0` is the observed scope.

Every screenshot capture retained its owner, session, WGC helper identity,
before/after camera, foreground and projection status. Stable ready captures
have no pending preparation or projection error. Requested Combine names are
unique so old GPU resources cannot conceal a changed route.

Limitations are explicit. The source-world banners were absent while their
stone supports were visible, despite correct server and client readback.
Therefore this is positive projection pose, pattern and occupancy evidence,
not visual parity with a real-world banner. The capture was not designed to
prove cloth animation or arbitrary pattern artwork. Editor oblique cloth
occlusion and packed-context duplication from runs 79 and 89 remain open.

Two early extraction attempts (`100` and `101`) used the wrong native palette
volume order and failed their actor index assertions. Their failures remain
recorded; `102` fixes the volume order to `(z,x,y)`. They are not acceptance
evidence. The six real source cells and their supports were restored in
`128-banner-source-restored/report.json`. The owner-verified instance
`ca9f0882e1534a379f1ac96f54c3badc` was retired after its handle count approached
the 400,000 ceiling. The older head fixture was restored on both sides in
`98-head-owned-restore/report.json` before retiring that instance.
