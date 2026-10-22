# R28 declared resources and Scene owner syntax

Source commit: `b70ce7bf13ad6a4472f2b089ac812c162b174861`. No SDK import, Minecraft launch, production change or qualification was performed.

`map.json.xz` losslessly preserves the complete map, including 56 exact Git blob/SHA256 pins, 28 declared model rows, material inheritance and shader include boundaries, and the five original owner effect source excerpts. `independent-review.json` records a second verification that fetched every input separately with `git cat-file blob COMMIT:path` and checked model/material entries against their own generation contracts.

All 28 model definitions and their declared material entries match current registrations. All 48 distinct directly named local resource files exist. Four contracts each retain old hashes for two shared registries; those eight whole-file hash differences do not mean their own registered entries differ. Engine parent `entity_for_skeleton_alpha` and shader include resolution remain external/unproven. This covers four contracts and includes frozen/diagnostic variants; it is not a complete resource graph, production selection proof, or runtime input closure.

`map-source.py` and `review-source.py` archive the exact scripts run under `.runtime/round-20261023/`. Their relative-root/output assumptions refer to that original location; they are source archives, not standalone package entrypoints. Preserve the pinned commit and use a fresh output directory for a replay. Read the map with Python standard-library `lzma.decompress` and JSON.

The initial analyzer incorrectly normalized CRLF in raw output hashes, including PNG, and reported 21 differences. That original local source/output is preserved and pinned in the review receipt. Correct raw-byte checks leave eight shared-registry differences only; no generation contract or asset was rewritten.

Manual issue closures: 0. Completed product refactors: 0. The map supplies a bounded next-cycle implementation/revalidation plan.
