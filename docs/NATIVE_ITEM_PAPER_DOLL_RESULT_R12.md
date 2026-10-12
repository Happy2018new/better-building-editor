# Native Attached Item UI Result R12

The single reviewed V4 diagnostic establishes ordinary attached-item inclusion on an isolated entity-ID PaperDoll rendering the native local player. All three plain frames visibly contain a diamond sword; all three initial and restored empty frames contain no sword. Both flag-only and actual typed-enchantment controls show changing blue-purple sheen. These are narrow UI observations: production rendering, editor frame content, and glint acceptance remain false.

## Evidence

The [compact archive](evidence/native-item-paper-doll-r12-v4/archive-index.json) retains all 15 unmodified native PNGs, the offline score, owner visual review, result supplement, source inventory, and original artifact inventory. The separate [complete archive](evidence/native-item-paper-doll-r12-v4/complete-archive-index.json) retains all 129 exact indexed files plus the original artifact inventory, including the raw 88-entry RPC journal, runtime and health reports, capture receipts, and frozen probe, wrapper, and dependencies. It is self-contained for evidence verification without the external session directory. The original artifact inventory SHA256 is `b337f9aeb070bb4c9015d7eae38ff9675a98d607ccc5ac3f57f30ae0282652a2`; the original immutable files also remain at `C:/Users/Happy2018new/.pyreact-debug/instances/773c643b5cf344918e04d8b4eef2657a/artifacts/` under prefix `native-item-paper-doll-r12-v4`.

Archive-scoped Git attributes disable text conversion so the indexed source and JSON bytes survive checkout unchanged.

| Control | Stable Pixels Outside Baseline Motion | Temporal Pixels Inside Shared Item Interior, Excluding Plain Motion |
| --- | ---: | ---: |
| Plain | 110,072 | N/A |
| Flag-only enchanted | 115,470 | 98,093 |
| Actual typed enchantment | 116,115 | 93,424 |

The actual item preserved typed Short enchantment ID 9 and level 3. Both the frame owner and entities reviewer opened all 15 original PNGs. The scorer alone remains conservative and returns `native_bound_item_ui_inclusion_proven: false`; only the subsequent visual review and supplement assert this narrow inclusion result.

The four fixed native marker rectangles support one common scale and translation, fitted from the first empty capture and unchanged across all 15 frames. The two holdouts and every marker edge/center passed the one-pixel limit; maximum error was 0.1884882791 physical pixels. The original API-only uniform mapping check still failed on every frame. It was preserved separately and never relaxed. The crop stayed `[517, 71, 1478, 1032]`.

## Boundaries And Cleanup

The 240 by 240 logical PaperDoll contains an oversized player. The sword overlaps the head, has fragmented-looking edges, and extends past the declared control rectangle; the torso extends below it. This diagnostic does not establish block-body shared depth, production clipping, composite alpha, material identity, GLINT defines, texture inputs, or shader time. It does not justify removing, displacing, or weakening the native frame body.

The finite attempt completed and restored in 38.31 seconds, with 88 recorded RPC entries and zero raw `isError` responses. Three sequential attachment binds each returned recycled ID 0; each exact owned ID was removed successfully before reuse and verified removed at final cleanup. Item dictionaries remained unchanged. Navigation, document, profiles, and camera were restored, and fresh client/server identity, advancing client clocks, and server timer callbacks passed. No shader, pack, world, inventory, player-position, or foreground mutation occurred.

Reviewed pins: probe `7d4496ef5d616998d281a802c1dff3ef343808c1e6c1e9f4a26f49a7daf00e1a`; plan `67d61cfc9ddd437c40bd1d970242750b20a4af82a5328c3a2f8429df6d83322b`; owner wrapper `1390f778a20b5c0350b7cfebc40b4462a701fac16ce2240d2cecc50cb9399820`; 90-file source index `90cf427b83a2130e14146b5c3a8c70bde3270956f19bfc2b739830fb62bfbb94`. Source validation passed 24 probe tests, four owner tests, and read-only CLI validation. Independent QA verified all 129 artifact bytes/hashes and the acceptance boundaries.
