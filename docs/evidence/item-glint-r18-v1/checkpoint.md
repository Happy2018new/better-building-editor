# Item Glint R18 Checkpoint

Source freeze: 2026-10-15 12:45 Asia/Shanghai. No production gate is opened.

## Source

- Final fragment SHA256: `3c288ec16d18d66b908393c34dd84b6bb4a884ca52b8a2e1039a94a392a3da87`.
- Generated resource contract: `515be879b61fc352b3e00e66d063f8da6e05036a8cd7d83aa54db563fb86815e`.
- `generate_item_icon_catalog.py` and catalog metadata describe center, rotation, offset, recenter, scale. The installed 3.10 shader confirms that transform order. Custom TIME offsets .4/-.2 before .5 UV scale retain the established .2/-.1 texture cycles per second. Both advance by integer periods over the 210s wrap.
- Native engine UV_OFFSET and UV_ROTATION values are not supplied on this custom route. There is no claim to exact native phase speed or rotation. Exploratory 80/-20 fits remain diagnostic and are not promoted.
- The unverified TILE_LIGHT_COLOR addition was removed. The custom material and native frame retain different lighting; the candidate is visibly brighter.
- Shader, generator, catalog, generated item data, focused tests and analyzers are the scoped source changes. ItemControls and shared render owners are unchanged.

## Archive Provenance

- Published `report.json` is a credential-redacted copy, not the original capture bytes. The MCDK authentication fields `$.session.token` and `$.camera_calibration.session.token` are replaced with `REDACTED`; these are the only semantic report changes.
- The original report remains only in git-ignored `.runtime/item-glint-final-static-r18-v2/report.json`, SHA256 `55abd9faf76581c27eda9b845769a963c67ede24ed885e5721c394d08e51daa2`. Its original analysis remains in the same directory's `review-v1/analysis.json`. Neither original is distributed in this package.
- `sanitization.json` binds those local originals to the published report and analysis, records the two redacted field paths, and distinguishes original hashes from transformed-copy hashes. `manifest.json` records the published file hashes and sizes.
- `tools/analyze_visible_items_r16.py` was rerun with the published redacted report as input. Every measurement matches the original analysis. The published analysis binds `source_sha256` to the redacted report and uses archive-relative paths for the four GIFs. Regenerated GIF hashes match the original GIFs; published screenshots, capture receipts, GIFs and frozen item source files are unchanged.

## Analysis Semantics

- Sparse capture scores visible temporal contrast only. `native_glint_visibility_accepted` is distinct from `native_glint_accepted`, which stays false without continuous evidence.
- The centroid of a thresholded bright region is not texture phase velocity. Its previous ratios remain diagnostic. A sparse centroid threshold cannot accept or reject actual animation speed.
- Verified dense timelines require at least 7s, increasing QPC times, no gap over .25s, visible RGB change over 5% of the observed body within every overlapping 1s window, ordinary-item stability, and frozen/empty negative controls.
- These checks establish continuous visible evolution, not exact native timing or 60fps smoothness. They do not grant full product admission.
- Missing observed item bodies now produce a failed measurement instead of an analyzer KeyError.

## Evidence

- `.runtime/item-glint-static-r18-v3`: completed source-bound older baseline, all body checks pass and actual native reference visible. Fragment `a9f7167664189befaceee6afe50c4b115fd141b7be34db1361323a5bd09fba4a`.
- `.runtime/item-depth-dense-motion-r17-v4/review-r18-semantics` and `dense-r18-semantics`: older-source evidence passes body, visibility, continuous evolution, plain and frozen/empty controls. This does not qualify final fragment 3c288e.
- `.runtime/item-glint-corrected-r18-v1`: orchestration completed, editor bodies absent after addon reload. `review-missing-body-v3` records all_bodies_passed=false and visibility=false. Preserved as failure.
- `.runtime/item-glint-ui-recovery-r18-v1`: native UI model IDs 54,55,56 existed across invalidate/reopen, but bodies remained absent. Native model readiness alone is not pixel proof.
- `.runtime/item-glint-known-visible-source-r18-v1/receipt.json`: freezes exact known-visible baseline bytes and binds them to the original capture hash.
- `.runtime/item-glint-ui-known-visible-cold-r18-v1`: identical known-visible shader cold start restores both visible bodies. The precise reload-resource failure remains unknown.
- `.runtime/item-glint-known-visible-dense-r18-v1`: world dense capture rejected, maximum gap 945.4338ms, 33 valid of 35 attempted frames. No acceptance; cleanup errors empty. The .25s limit was not widened.
- `.runtime/item-glint-final-static-r18-v1`: final fragment visible in editor, then failed world camera drift. Source unchanged and cleanup errors empty. Preserved as failure.
- `.runtime/item-glint-final-static-r18-v2`: final same-byte editor/world/missing/native closeup capture completed with unchanged sources, native reference restored, and empty cleanup errors. `review-v1/analysis.json` reports evidence_valid=true, all_bodies_passed=true, reference_valid=true, and native_glint_visibility_accepted=true. Ordinary/empty controls pass on all four routes. Native_glint_accepted remains false; no final-byte uninterrupted dense evidence exists. SDK camera pitch/yaw locks now match the independent calibration approach and unlock during cleanup.
- Visual inspection of `world_occupied.png` confirms the central enchanted sword is fully covered by the actual stone while the adjacent ordinary sword remains visible. `editor_cutaway.png` removes the frame layer and both item bodies; restoration captures restore them. These are bounded visual observations, separate from the automated body/contrast score.

## Verification

- 37 tests passed: item icon catalog, dense evidence association, item glint motion negative controls, item sprite pixels.
- `.runtime/item-glint-final-source-r18-v1/shader-compile.json`: 16 GLES100/300 UI/world/overlay combinations compile and link. This is offline syntax/link evidence only.
- Root generated item data was synchronized to resource contract 515be879 after the final visible capture. `python -X utf8 tools/generate_item_icon_catalog.py --check --install D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447` passes. No --register invocation was used.

## Fixed Remaining Work

1. Final fragment's same-byte editor/full/missing/native closeups and visible contrast are complete. Broader orientation/depth/opacity coverage still belongs to the full item product matrix.
2. Obtain final-fragment uninterrupted four-route dense evidence under the unchanged 250ms capture limit. No old-source evidence substitution. Current round's failed 945ms timeline remains failed; continuous and production qualification remain closed.
3. Flat catalog breadth is 425 identifier candidates / 6066 identifier+aux observations, not comprehensive visual support. Final integrated resource/body tests need representative aliases, auxiliary variants, all frame/glow-frame poses, section/depth/occupancy and side/zoom checks.
4. Shelf three-slot and campfire four-slot content have separate implementations and tools. Their own final-resource pixel and restoration gates cannot be enabled by item-frame acceptance.
5. Special-item families remain separate: patterned shields/banners, filled-map world pixels, charged crossbows, tridents/spears, skull variants/player skins, tinted potion/leather/spawn eggs, clocks/compasses and other dynamic content. Offline asset classification does not establish authentic userdata, native frame model/pose, dynamic atlas or world pixel source, or editor/full/missing parity.

Owned final runtime: session `94a9edbe99ee4b9389fc56b6de961a98`, owner `item-glint-r18`, project `D:/bbe-r18-item-glint`, game PID27236 identity134365081890856867, MCDK PID21896 identity134365081888949578, port19366. Session is stopped and both process identities are gone. No capture or analysis process remains running. User games and root instances were not touched.
