# Guarded V5 Control

Use this sibling control for the reviewed explicit-state amendment. It uses
the exact same frozen clone, resources, owner, three images and lifecycle as
`../shelf-render-palette-r21-v5/RUN.md`. No game has been launched here.

The only changed host is `tools/shelf_render_palette_candidate_r21.py`.
The original helper is preserved byte-for-byte in this directory, and this
`frozen.json` records both original manifest and helper hashes. The original
v5 manifest, clone and compiler report remain unchanged. The runner is a
byte-exact copy of the original, using this directory for its state/output.

Thirteen focused tests pass, including the real `prepare_palette` boundary:
aux0 plus explicitly north-facing states survives preparation and must retain
its body, actor and opaque inventory. The same helper accepts only absent/
empty states or the exact south/unpowered typed record. Its remotely embedded
form is also exercised without additional module globals.

Root-scheduled commands, after zero prior live games and 6 GiB commit:

```powershell
python -B -X utf8 .runtime/shelf-render-palette-r21-v5-state-guard/run.py preflight
python -B -X utf8 .runtime/shelf-render-palette-r21-v5-state-guard/run.py start --scheduled-by-root
python -B -X utf8 .runtime/shelf-render-palette-r21-v5-state-guard/run.py capture
python -B -X utf8 .runtime/shelf-render-palette-r21-v5-state-guard/run.py stop
python -B -X utf8 .runtime/shelf-render-palette-r21-v5-state-guard/run.py finalize
```

Keep the start process's exact-exit watcher alive. Capture runs separately.
Normal stop is force=False; finalize requires both exact identities exited.
No new runtime direction/state matrix or separate body overlay is added.
