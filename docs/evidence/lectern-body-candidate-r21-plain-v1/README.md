# Native Lectern Body: Isolated Plain24 Candidate

This package records one real west-facing lectern state (`aux=1`, not powered),
seen from four fixed cameras. It does not establish four block directions.
Main business sources and admission gates have not changed.

## Native Result and Remaining Limits

The world contains an empty lectern and a genuinely item-used book lectern,
each on a cyan support. Native material/actor inputs are equal; both rendered
actors are `{}`. Full logical NBT remains in the document for the book owner.

All 24 v3 captures completed and restored unchanged sources, with zero cleanup
errors. Body-only, full and missing phases generate two target-only native
bodies outside packed context. Full/missing generate one custom book group;
body-only generates none. Hidden and already-present targets generate no
candidate body or book. The complete candidate top boards are visible from
south, north, east and west. The earlier packed-context notch is absent.

All four native-resolution review sheets were opened and inspected. The two
bodies overlap from east/west. Body-only shows no native duplicate book; full
and missing show a single custom book. This count does not prove book pixels:
the native world/present reference has no visible book from south/east while
the custom owner is visible there. Preserve that directional discrepancy.

The independent cyan-only clipping control, strict pixel boundary checks,
upper/side neighbors and separate cardinal block states remain open. There
is no whole-image IoU admission, no powered appearance admission and no main
candidate gate change. This is evidence for the isolated clipping candidate.

## Retained Host Failures

`failed-v1` has zero captures. Its host asserted a no-op air-to-air native write.
It restored world, inventory, camera, environment and Session successfully.
`failed-v2` retains four world captures. Its direct in-memory `to_data` /
`from_data` call hit Python 2 numeric scalar wire validation. It also restored
successfully. V3 adds the ordinary JSON encode/decode boundary. V2 also makes
air clearing idempotent and verifies actual block readback. The sealed base
host and business sources are unchanged; all three host files are retained.

## Shutdown and Reproduction

The ordinary managed stop returned 1. Exact retained process handles observed
game exit `0xC0000409` and MCDK exit `0`. No force stop was used. Scene restoration
passed; game shutdown is not a passed lifecycle check. Its cause is unclassified.

`lifecycle/launch.json` omits routing tokens and unrelated foreground details.
The existing handle watcher was used during startup with readiness checking
disabled only for reading the owner-bound session. It still validated each
retained native process handle's creation identity and executable before waiting.

`host/prelaunch-v1.json` binds all 3093 cold sources, configuration, the base
host and the earlier offline evidence manifest. `sources` freezes the scoped
business and shared shader inputs. `valid/report.json` records native palette
receipts, fixed camera states, WGC hashes and source hashes. No image alignment,
rescaling or recoloring is used for the individual review crops.

Run `python tools/pack_lectern_body_candidate_r21.py --verify <package>` to check
the self-contained payload, acquisition hashes, object counts and exit evidence.
Rebuild review crops using `host/review_plain.py valid/report.json --output
<fresh-review-directory>`. The JSON and PNG evidence also remain usable after
the original `.runtime` directory is removed.
