# Matched Frontal Lectern Reference

NEMC 3.10.0.420447, 2026-10-15, managed session
`e6e8d0fb33464422b3823dfe337d7a51`, owner `book-r20-lectern-v1`.
The controlled arena probe aims from the north observation platform before
authentic item placement. The resulting real lectern is aux 2, north-facing;
the attached player view exposes the broad front page. Typed NBT records a
real writable book, hasBook 1, page 0 and totalPages 0.

All five captures completed, restored and retained identical installed
sources. Cleanup errors are empty. Player foot, rotation, inventory, world
cells, camera, UI, environment and temporary candidate profile were restored.
The native full-resolution image and all five exact crops in review-00.png
were actually inspected. The original full captures remain in
`.runtime/book-r20-frontal-lectern-v1` and are hash-bound by crops.json.

The unchanged page analyzer passes both candidate repetitions: precision
0.9982912068, recall 0.9903414971, native median RGB (211,200,157), candidate
(213,201,158), maximum channel delta 2. The original limits remain precision
and recall at least 0.98, three-pixel boundary tolerance and color delta at
most 8. Native repeated captures are stable.

This accepts only the matched stationary front-page surface. It does not
claim full-direction pixel parity or page interaction. The earlier aux 1
side/back-view failure is retained in `book-reference-r20-v1`, including its
different cover silhouette; it was not converted into a successful test.
