# Python Performance Profile

- Job: `1a14031a1fe-1-23ccd246`
- Kind: `python.cpu`
- Storage: `disk`
- Captured: `2026-10-15T15:33:07Z`

## Summary

```json
{
  "capture_truncated": true,
  "captured_calls": 1045,
  "captured_functions": 512,
  "elapsed_seconds": 30.011000156402588,
  "kind": "python.cpu",
  "total_functions": 763
}
```

## Ranked Records

| # | Entry | Context | Total | Self |
| -: | --- | --- | ---: | ---: |
| 1 | _RuntimeEventHandler.on_game_render_tick | modern_projection.pyreact.host:83 \| client / _MainThread | 4.284 s | 10.405 ms |
| 2 | notify_game_render_tick | modern_projection.pyreact.host:973 \| client / _MainThread | 4.273 s | 50.359 ms |
| 3 | NavigatorScreen._pyreact_tick_animation_frames | modern_projection.pyreact.host:389 \| client / _MainThread | 3.287 s | 256.678 ms |
| 4 | NavigatorScreen._pyreact_flush | modern_projection.pyreact.host:283 \| client / _MainThread | 2.183 s | 13.460 ms |
| 5 | NavigatorScreen.Update | modern_projection.pyreact.navigator:832 \| client / _MainThread | 2.026 s | 8.409 ms |
| 6 | NavigatorScreen.Update | modern_projection.pyreact.host:219 \| client / _MainThread | 1.952 s | 17.324 ms |
| 7 | tick | modern_projection.projection.scene:306 \| client / _MainThread | 1.591 s | 316.921 ms |
| 8 | rerender_component | modern_projection.pyreact.reconciler:426 \| client / _MainThread | 1.479 s | 156.200 us |
| 9 | reconcile_children | modern_projection.pyreact.reconciler:303 \| client / _MainThread | 1.462 s | 59.897 ms |
| 10 | update_fiber | modern_projection.pyreact.reconciler:222 \| client / _MainThread | 1.462 s | 23.816 ms |
| 11 | _update_primitive | modern_projection.pyreact.reconciler:255 \| client / _MainThread | 1.462 s | 60.057 ms |
| 12 | _update_component | modern_projection.pyreact.reconciler:245 \| client / _MainThread | 1.373 s | 10.504 ms |
| 13 | tick | modern_projection.projection.widgets:404 \| client / _MainThread | 714.668 ms | 112.245 ms |
| 14 | layout_tree | modern_projection.pyreact.layout:1419 \| client / _MainThread | 617.854 ms | 458.500 us |
| 15 | tick | modern_projection.projection.widgets:738 \| client / _MainThread | 611.577 ms | 131.012 ms |
| 16 | LiquidControls.update | modern_projection.projection.liquid_viewport:53 \| client / _MainThread | 560.779 ms | 65.108 ms |
| 17 | _render_component | modern_projection.pyreact.reconciler:181 \| client / _MainThread | 556.265 ms | 23.618 ms |
| 18 | poll_clipboard | modern_projection.pyreact.debug:493 \| client / _MainThread | 525.224 ms | 11.907 ms |
| 19 | unmount_fiber | modern_projection.pyreact.reconciler:392 \| client / _MainThread | 475.394 ms | 3.150 ms |
| 20 | remove | modern_projection.pyreact.native:119 \| client / _MainThread | 452.958 ms | 341.100 us |
| 21 | is_shown | modern_projection.projection.widgets:221 \| client / _MainThread | 281.417 ms | 209.798 ms |
| 22 | _layout_and_apply | modern_projection.pyreact.layout:1473 \| client / _MainThread | 274.492 ms | 92.900 us |
| 23 | update_screen | modern_projection.pyreact.native:126 \| client / _MainThread | 254.632 ms | 263.100 us |
| 24 | _TASK | DEBUG_ENV_SCRIPT.IPCSystem:417 \| client / _MainThread | 248.249 ms | 681.400 us |
| 25 | _RUN_CLIENT_CODE | DEBUG_ENV_SCRIPT.IPCSystem:468 \| client / _MainThread | 244.202 ms | 219.800 us |
| 26 | _EXEC_CODE_RESULT | DEBUG_ENV_SCRIPT.IPCSystem:359 \| client / _MainThread | 243.982 ms | 1.481 ms |
| 27 | _EXEC_CODE_VALUE | DEBUG_ENV_SCRIPT.IPCSystem:328 \| client / _MainThread | 241.067 ms | 1.851 ms |
| 28 | Navigator._refresh_active_entry | modern_projection.pyreact.navigator:671 \| client / _MainThread | 216.641 ms | 52.614 ms |
| 29 | validate_uniforms | modern_projection.projection.liquid_transport:126 \| client / _MainThread | 214.741 ms | 32.566 ms |
| 30 | Action | modern_projection.projection.widgets:667 \| client / _MainThread | 206.788 ms | 19.107 ms |
| 31 | _EXEC_CODE_OBJECT | DEBUG_ENV_SCRIPT.IPCSystem:324 \| client / _MainThread | 194.704 ms | 2.541 ms |
| 32 | _layout_nodes | modern_projection.pyreact.layout:1488 \| client / _MainThread | 163.591 ms | 65.100 us |
| 33 | layout | modern_projection.pyreact.layout:770 \| client / _MainThread | 163.526 ms | 63.819 ms |
| 34 | Navigator._tick | modern_projection.pyreact.navigator:559 \| client / _MainThread | 160.826 ms | 9.723 ms |
| 35 | ModernProjectionClientSystem.render_tick | modern_projection.client_system:171 \| client / _MainThread | 156.727 ms | 38.975 ms |
| 36 | S | modern_projection.projection.widgets:77 \| client / _MainThread | 154.673 ms | 42.865 ms |
| 37 | validate | modern_projection.projection.liquid_render:56 \| client / _MainThread | 148.462 ms | 3.324 ms |
| 38 | Style.merge | modern_projection.pyreact.style:211 \| client / _MainThread | 137.308 ms | 79.222 ms |
| 39 | Navigator._top_snapshot | modern_projection.pyreact.navigator:658 \| client / _MainThread | 130.535 ms | 14.517 ms |
| 40 | Style.__init__ | modern_projection.pyreact.style:162 \| client / _MainThread | 122.132 ms | 89.527 ms |

## Notes

- The ranked table is intentionally bounded to 40 records.
- Query the job for paged server-side detail before drawing conclusions from this report.
