# Flat Frame Item Contract

This candidate contract is frozen before comparing the single-bone candidate.
It accepts only an explicitly measured item/aux/profile. Bitmap capability does
not certify native block items, enchanted items, banners, or dynamic renderers.

- Actual reference frames are created with native player item use in an owned
  empty region. The reference item is inserted with native player item use.
  Client block replication and typed server Item NBT are recorded before use.
- Empty native reference is the same frame before filling. Its support and
  camera stay identical. Item pixels are the filled-versus-empty difference.
- The built-in test.entities.appearances source and its item, pose, and NBT stay
  unchanged. Explicit diagnostic copies may test other facings/rotation steps.
- Every capture uses owner-bound, fresh Windows.Graphics.Capture at native
  resolution. Foreground activation, synthetic fallback and image resizing are
  prohibited. Actual camera readback and same-session cube calibration are
  mandatory for world comparisons.
- Candidate empty controls retain identical document NBT and frame body while
  disabling the provisional renderer profile. Item content must exceed 80
  difference pixels in the actual editor viewport and both full/missing paths.
- At the identical world camera, native and candidate item masks must each have
  at least 100 pixels for the existing native appearance comparison. Two-pixel
  silhouette recall and precision must each reach
  0.85; intersecting interior colour agreement must reach 0.65.
- Opacity 0.2 must have contrast gain within 0.05 of 0.2, with relative blend
  residual at most 0.12. At opacity 0, the item region may retain at most two
  pixels differing from the hidden-actor background by more than 12 levels.
- Native verification includes six facings and eight 45-degree rotation steps,
  full and missing projection, occupied-stone suppression and recovery, source
  nonmutation, bank replacement, page close and stop cleanup. A successful SDK
  setter or a nonblank frame body does not satisfy an item gate.
- Unknown Item/NBT stays in the document, archive, transforms and history. An
  unsupported renderer can omit its appearance only; it cannot discard data.
