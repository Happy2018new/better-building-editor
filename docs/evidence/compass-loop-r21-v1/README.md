# Compass Loop Offline Review

This package freezes one compass loop and the lodestone-compass aux 0-15
aliases. No Minecraft instance was started for these checks. All native-frame,
editor, projection and production pixel gates remain false.

The exact NEMC 3.10.0.420447 vanilla compass_atlas.png is copied under native/;
the owned generated atlas is byte-identical. Its 32 vertical frames have 28
distinct bitmaps and identical binary alpha, allowing one existing thickness
mesh. The arbitrary two-second loop does not consult item tracking metadata.
The original item identifier still determines intrinsic glint independently
of the shared resource key.

Run `python -X utf8 verify_package.py` from any directory. It verifies the
manifest, captured baseline/current profile and registration comparisons,
the atlas/mesh contract, all 24 recorded compiled programs, all 20 fragment
pixel samples, and the false gates. Pillow is required for mesh regeneration.

Optional replay uses Playwright and a local Chromium-compatible browser:

```powershell
python -X utf8 verify_package.py --browser "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --replay-output FRESH_DIRECTORY
```

Replayed outputs are new files. The recorded reports are never overwritten.
The pixel check uses the actual fragment, native atlas and glint bitmap with
a fullscreen test vertex. It does not establish native mesh pose, UI depth,
lighting, occupancy, replacement or cleanup behavior.

static-assets.json records byte-for-byte comparisons of every preexisting
icon bitmap, mesh, shared shader, skeleton and glint bitmap against immutable
Git blobs identified by baseline_ref. The approximately 50 MB of unchanged
asset bodies are omitted. The smaller captured baseline/current dictionaries
and all newly generated assets are included for portable review. source.patch
contains the scoped current text diff, with the new binary atlas separately
included and fingerprinted. Baseline/current generators and compiler tools
are captured as exact source bytes. A checkout
at baseline_ref is required to independently retrieve omitted asset bodies.
