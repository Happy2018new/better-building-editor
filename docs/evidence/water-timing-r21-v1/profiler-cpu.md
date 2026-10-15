# Python Performance Profile

- Job: `1a140312105-0-55421fff`
- Kind: `python.cpu`
- Storage: `disk`
- Captured: `2026-10-15T15:32:34Z`

## Summary

```json
{
  "capture_truncated": true,
  "captured_calls": 851,
  "captured_functions": 512,
  "elapsed_seconds": 29.973999977111816,
  "kind": "python.cpu",
  "total_functions": 809
}
```

## Ranked Records

| # | Entry | Context | Total | Self |
| -: | --- | --- | ---: | ---: |
| 1 | _RuntimeEventHandler.on_game_render_tick | modern_projection.pyreact.host:83 \| client / _MainThread | 10.938 s | 15.625 ms |
| 2 | notify_game_render_tick | modern_projection.pyreact.host:973 \| client / _MainThread | 10.922 s | 62.500 ms |
| 3 | NavigatorScreen._pyreact_flush | modern_projection.pyreact.host:283 \| client / _MainThread | 9.875 s | 0.000 us |
| 4 | layout_tree | modern_projection.pyreact.layout:1419 \| client / _MainThread | 6.406 s | 31.250 ms |
| 5 | rerender_component | modern_projection.pyreact.reconciler:426 \| client / _MainThread | 3.375 s | 0.000 us |
| 6 | reconcile_children | modern_projection.pyreact.reconciler:303 \| client / _MainThread | 3.281 s | 93.750 ms |
| 7 | _update_primitive | modern_projection.pyreact.reconciler:255 \| client / _MainThread | 3.281 s | 46.875 ms |
| 8 | update_fiber | modern_projection.pyreact.reconciler:222 \| client / _MainThread | 3.281 s | 15.625 ms |
| 9 | _layout_and_apply | modern_projection.pyreact.layout:1473 \| client / _MainThread | 3.016 s | 0.000 us |
| 10 | NavigatorScreen._pyreact_tick_animation_frames | modern_projection.pyreact.host:389 \| client / _MainThread | 2.281 s | 187.500 ms |
| 11 | layout | modern_projection.pyreact.layout:770 \| client / _MainThread | 2.047 s | 734.375 ms |
| 12 | _layout_nodes | modern_projection.pyreact.layout:1488 \| client / _MainThread | 2.047 s | 0.000 us |
| 13 | NavigatorScreen.Update | modern_projection.pyreact.navigator:832 \| client / _MainThread | 1.844 s | 0.000 us |
| 14 | update_screen | modern_projection.pyreact.native:126 \| client / _MainThread | 1.797 s | 0.000 us |
| 15 | NavigatorScreen.Update | modern_projection.pyreact.host:219 \| client / _MainThread | 1.781 s | 31.250 ms |
| 16 | mount_fiber | modern_projection.pyreact.reconciler:126 \| client / _MainThread | 1.609 s | 15.625 ms |
| 17 | _update_component | modern_projection.pyreact.reconciler:245 \| client / _MainThread | 1.594 s | 15.625 ms |
| 18 | _mount_primitive | modern_projection.pyreact.reconciler:147 \| client / _MainThread | 1.531 s | 31.250 ms |
| 19 | _mount_component | modern_projection.pyreact.reconciler:137 \| client / _MainThread | 1.312 s | 0.000 us |
| 20 | _render_component | modern_projection.pyreact.reconciler:181 \| client / _MainThread | 1.047 s | 31.250 ms |
| 21 | apply | modern_projection.pyreact.layout:1314 \| client / _MainThread | 968.750 ms | 265.625 ms |
| 22 | tick | modern_projection.projection.scene:306 \| client / _MainThread | 921.875 ms | 203.125 ms |
| 23 | measure | modern_projection.pyreact.layout:376 \| client / _MainThread | 921.875 ms | 250.000 ms |
| 24 | apply_style | modern_projection.pyreact.renderer:29 \| client / _MainThread | 734.375 ms | 31.250 ms |
| 25 | set_layer | modern_projection.pyreact.native:88 \| client / _MainThread | 656.250 ms | 0.000 us |
| 26 | tick | modern_projection.projection.widgets:404 \| client / _MainThread | 625.000 ms | 31.250 ms |
| 27 | build_layout_tree | modern_projection.pyreact.layout:98 \| client / _MainThread | 515.625 ms | 0.000 us |
| 28 | _collect | modern_projection.pyreact.layout:120 \| client / _MainThread | 515.625 ms | 125.000 ms |
| 29 | get_control | modern_projection.pyreact.native:76 \| client / _MainThread | 453.125 ms | 31.250 ms |
| 30 | tick | modern_projection.projection.widgets:738 \| client / _MainThread | 437.500 ms | 62.500 ms |
| 31 | _measure_auto_container | modern_projection.pyreact.layout:535 \| client / _MainThread | 421.875 ms | 93.750 ms |
| 32 | poll_clipboard | modern_projection.pyreact.debug:493 \| client / _MainThread | 375.000 ms | 15.625 ms |
| 33 | Action | modern_projection.projection.widgets:667 \| client / _MainThread | 359.375 ms | 15.625 ms |
| 34 | unmount_fiber | modern_projection.pyreact.reconciler:392 \| client / _MainThread | 359.375 ms | 0.000 us |
| 35 | remove | modern_projection.pyreact.native:119 \| client / _MainThread | 343.750 ms | 0.000 us |
| 36 | _EXEC_CODE_RESULT | DEBUG_ENV_SCRIPT.IPCSystem:359 \| client / _MainThread | 328.125 ms | 0.000 us |
| 37 | _resolve_box_edges | modern_projection.pyreact.style:441 \| client / _MainThread | 328.125 ms | 203.125 ms |
| 38 | _RUN_CLIENT_CODE | DEBUG_ENV_SCRIPT.IPCSystem:468 \| client / _MainThread | 328.125 ms | 0.000 us |
| 39 | _TASK | DEBUG_ENV_SCRIPT.IPCSystem:417 \| client / _MainThread | 328.125 ms | 0.000 us |
| 40 | _EXEC_CODE_VALUE | DEBUG_ENV_SCRIPT.IPCSystem:328 \| client / _MainThread | 328.125 ms | 0.000 us |

## Notes

- The ranked table is intentionally bounded to 40 records.
- Query the job for paged server-side detail before drawing conclusions from this report.
