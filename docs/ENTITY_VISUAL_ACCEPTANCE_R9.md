# Actual Editor Chest Controls, Round Nine

This milestone accepts three unchanged public chest source cases in the ordinary
product editor `Scene` viewport, against player-placed native world chests.
Acceptance covers the recorded top view only. It changes diagnostic metadata and
verification tools; no production renderer, geometry or texture changes are
included, and the unaccepted UV proposal `008ca89` is not integrated.

| Public Source | Direction | Shape IoU | Texture Cosine | Scale Error | Center / Boundary RMS |
| --- | --- | ---: | ---: | ---: | --- |
| `test.entities.classic`, normal single `(9,1,3)` | South | .9731682147 | .8892927053 | .0374862810 | .260 / 1.257 px |
| `test.connections.context`, normal double `(26,1,5),(27,1,5)` | North | .9839121553 | .7815271921 | .0543559766 | .900 / 2.185 px |
| `test.connections.context`, default copper double `(26,1,10),(27,1,10)` | North | .9839121553 | .8828201304 | .0543559766 | .900 / 2.185 px |

All original gates remain fixed: native signal at least 1,000 pixels, shape IoU
at least `.82`, texture cosine at least `.45`, scale error at most `.2`, center
distance at most 3 pixels and boundary RMS at most 4 pixels. A separate native
and editor stone cube fixes uniform scale `.6400084629` and image centers before
chest frames. The cube contributes 18,906 native and 7,744 editor pixels; its two
axis ratios agree within the predeclared 2% limit. No chest pixels fit registration.

The native background is a predeclared 7 by 7 quartz plane four cells below the
chest target. This changes the background/support context from the original
public fixtures, while preserving their chest material, state, actor and pairing.
Both positive and empty native controls retain the same plane. Its 49 cells were
confirmed air before writing and restored to air. Editor empty controls keep the
same loaded document and camera and temporarily hide existing `PreviewTile`
surface controls; all visibility, camera and document state is restored.

`chest-editor-r9-public-v1` remains failed: the empty editor document introduced a
no-blocks indicator into the difference image. `chest-editor-r9-public-v2` remains
overall failed: natural forest background obscured the single chest signal.
Only `chest-editor-r9-public-v3` is accepted. The R7 failures, all ten preserved R8
runs, seven R8 accepted runs and the prior 34 viewed frames retain their original
records. The R9 index separately records 20 full captured frames actually opened,
including all 16 calibration and chest positive/empty frames from v3.

Every run freezes all behavior/resource files and relevant verification/capture
helpers before capture and verifies their bytes after restoration. Capture uses
native-resolution background Windows.Graphics.Capture without activation,
desktop input or resize. Runtime registry metadata matches the frozen generated
registry and palette SHA-256
`6b2d9e961e934a745f5ab30d697cf22fb463fd3792d371a6dd42cb4342062f01`,
NEMC `3.9.0.401155`, 15,858 states.

Owned instance `c0e9fe9f1e40453f8d8056092950877d`, owner `p0-entities-r9`,
restored its independently observed grounded foot `[.5,74,.5]`, rotation,
flight, camera, world, UI, options and daylight. The earlier read-only audit
against the previous instance's foot remains failed; no corrective teleport was
applied. Final read-only cleanup passed. After editor closure handles increased
from 189,142 to 192,497 in a quiet 30-second interval, so the instance was stopped
normally and both game and MCDK PIDs were verified absent before replacement.
This observation is runtime diagnostic evidence, not attribution to a specific
production component.

Machine-readable records: `tools/data/entities_visual_acceptance_r9.json` and
`tools/data/entities_visual_viewed_frames_r9.json`. The manifest fingerprints all
run artifacts, prior R8 records, cleanup, baseline and stopped session.
Remaining priorities are partial double-chest real occupied lifecycle, other
chest species/wax/oxidation/directions/non-top views, and practical head/frame/
banner visible-content boundaries. This milestone does not close those scopes.
