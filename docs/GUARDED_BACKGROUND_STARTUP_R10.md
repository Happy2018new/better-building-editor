# Guarded Background Startup R10

Observed 2026-10-12, approximately 08:40-08:48 Asia/Shanghai, in the owned
`snow-r10-background` instance. This is startup and capture evidence, not liquid
rendering acceptance.

## Exact Binaries

| Component | SHA256 |
| --- | --- |
| Patched MCDK v1.6.1 | `648e5d56b58cb4722235c17212411c633b7b48b6b8e93443a161d9aa87692c35` |
| Native focus guard DLL | `c22fa0cd0bdbfb7d9218d59573b61619111f9bd180562c9bd51c69276c11c178` |
| Native focus probe EXE | `0949668953866c4d4ade5d66bc4dbb17fe057b6ce00b20010979f473f838364d` |
| Native WGC capture EXE | `cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8` |

The patched MCDK is under
`.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/mcdk-noactivate/build-ninja-331/tools/mcdk/mcdk.exe`.
The DLL and probe are under
`.runtime/worktree-archive-r7/p0-integration/files/.runtime/native_focus_guard-final-r7/`.
The WGC EXE is under
`.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/`.
All paths are relative to the shared repository root, not the snow worktree.

The native probe passed both its main-thread and new-thread cases, preserving
the observed Edge foreground HWND `12390418`. The launcher validates explicit
DLL/MCDK hashes and markers before preparation and immediately before spawn.

## Owned Session

Manifest:
`C:/Users/Happy2018new/.pyreact-debug/instances/78a2769a6c8946989c1e42bdac3e66a8/session.json`

| Binding | Value |
| --- | --- |
| Owner | `snow-r10-background` |
| Game PID / creation identity | `16396` / `134362395421098041` |
| MCDK PID / creation identity | `18120` / `134362395417362033` |
| Game HWND | `14029754` |
| Foreground HWND / PID | `12390418` / `26876` |

The ready manifest records `window_noactivate=true`, `background_safe=true`,
`foreground_unchanged=true`, and `foreground_before_still_valid=true`.
PowerShell module enumeration of PID `16396` confirmed the exact approved DLL
loaded in the game process. No desktop input, window activation, resize,
foreground restoration, or focus-release helper was used.

## Fresh Background Frame

PNG:
`C:/Users/Happy2018new/.pyreact-debug/instances/78a2769a6c8946989c1e42bdac3e66a8/artifacts/snow-r10-background-preflight.png`

Its sibling `.capture.json` records a fresh, reliable, background-only WGC
frame at `1994 x 1105`. Frame QPC `2408440680624` exceeds request QPC
`2408440567404`; foreground before and after is Edge `12390418` / `26876`.
PNG SHA256:
`058aefc18cf6de4565a7686a6456149c0ba1efff928b4d8d6291b393a0aa90db`.
The PNG was opened and shows a nonblank plains world, HUD, and player hand.

## Same-Session Camera Calibration

`artifacts/camera-native-r10-v1.json` in the owned instance above records
`completed=true`, `passed=true`, `restored=true`, and no cleanup errors.
SHA256: `0164703d28e1694c0a73194ccac9ffb1e304816a85b23c31c865dc4c3ac41783`.
The unchanged reviewed SDK-only runner used native-resolution WGC, fixed
`--skyward-tilted --fixture-lift-y 30`, and three independent stone cube views.
The unified vertical FOV is `66.6`; reported native FOV `60` is not effective
for this full PNG projection. Common-FOV mask IoU is approximately
`0.981-0.987`, boundary RMS is at most `1.12` native pixels, and all
two-pixel outline precision/recall gates pass. The tilted PNG was opened and
shows the expected stone cube against sky. This calibrates projection only;
it does not accept liquid silhouettes, UVs, or animation cadence.

## Launcher Verification

Commit `6e37a62` contains the launcher contract, window observations, focused
tests, and guard documentation. The following command passed 11 tests:

```text
python -X utf8 -m unittest tests.test_noactivation_startup tests.test_native_wgc_capture
```

`git diff --check` passed. The tests include missing/incomplete/drifted binaries,
failure before spawn, failed-manifest preservation, reused or invalid window
identities, and focus/window contract failures. Native guard hooks have the
limitations documented in `tools/native_focus_guard/README.md`; this report
does not claim universal suppression of all native activation mechanisms.
