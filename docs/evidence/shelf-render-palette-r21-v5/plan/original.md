# Full Shelf Render Palette V5

Offline candidate only. Owner: `root-shelf-r20-render-palette-v5`.
No game launch is authorized by this file.

One oak/south/unpowered custom block uses the existing traced model and native
32x32 artwork with `use_ao=true`. The pure helper replaces only the prepared
main palette identity, preserving body/support indices and volume. Original
Document/NBT and independent item-slot ownership stay intact. Only matching
shelf actors at replaced indices are removed. Extra layer and unrelated actors
survive. The helper recurses through already-filtered full/missing context
batches without adding targets or changing packed coordinates.

Eight focused tests cover immutable source data, three item slots, occupied
context-only shelf neighbors, hidden layers, both native layers, metadata and
unrelated actors. They do not qualify runtime AO or visual clipping.

The source is the frozen v1 native control clone. Exactly six paths are overlaid:
one BP block, one model, one texture, blocks registry, terrain texture registry,
and the existing common-block fragment. Its private marker 19491 returns COLOR
after the original context/preview discard. Unmarked and product marker 19487
remain unchanged. No terrain, Skeleton, original source or production route
is modified.

Root reviews and schedules this minimal single-window acquisition:

```powershell
python -B -X utf8 .runtime/shelf-render-palette-r21-v5/run.py preflight
python -B -X utf8 .runtime/shelf-render-palette-r21-v5/run.py start --scheduled-by-root
python -B -X utf8 .runtime/shelf-render-palette-r21-v5/run.py capture
```

Zero prior live MC processes, 6 GiB available commit, noactivation, all four
reload flags false, OPENBLAS_NUM_THREADS=1 and the exact observer are required.
The start process waits on both exact process identities after readiness.
Capture runs separately and admits phases for at most 150 seconds.

Exactly three raw images under `captures/south-full-palette`:

1. Native world shelf on cyan support.
2. One full combined proxy/support geometry, normal shader path.
3. The same combined geometry with COLOR readback marker 19491.

Both real shelf and real support are cleared and their replicated air is
confirmed before the combined geometry is attached. The support is inside the
same palette, so it is not a separate overlay or duplicate depth surface.
Fixture, player, camera, environment and workspace restore in `finally`.

```powershell
python -B -X utf8 .runtime/shelf-render-palette-r21-v5/run.py stop
python -B -X utf8 .runtime/shelf-render-palette-r21-v5/run.py finalize
```

Stop uses force=False. Preserve normal-close timeout, wait for both observed
identities to exit, then finalize. No process forcing or window intervention.
The result can establish whether support neighbors affect custom block COLOR.
It cannot close the independent directional shade discrepancy or qualify all
woods, states, UI, packed contexts, item contents or production integration.
