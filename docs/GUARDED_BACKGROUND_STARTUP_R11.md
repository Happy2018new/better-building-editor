# Guarded Background Startup R11

Observed 2026-10-12, 20:48-21:30 Asia/Shanghai. This is owned startup and
capture evidence, not acceptance of any block renderer.

## Rebuilt Launcher

The R10 executable did not include the tracked module-snapshot retry helper.
R11 rebuilt an isolated official MCDK v1.6.1 checkout at
`cefdfb5ce220e0cc3e9df6d80b2ff87be8b98802`, with MCDevLink submodule
`62ea1e48406a496057257a48692b0bead16db87a`. The checkout is under
`.runtime/mcdk-retry-r11/upstream`; the executable is under
`.runtime/mcdk-retry-r11/build/tools/mcdk/mcdk.exe`.

The rebuild applied the tracked `mcdk-v1.6.1.patch` and copied the tracked
`inject.hpp` to `tools/mcdk/include/mcdk/focus_guard.hpp`. Both header copies
have SHA256 `a85af27be793d227dfdb5038be3405c7534b8c652178840863e20a38d58a8f70`.
Only the pinned launch source differs from the official tracked checkout.
The first CMake attempt failed because embedded resources had not been
generated. After running the official `mods/generate.py`, Release/Ninja
completed, including the snapshot retry regression executable.

| Component | SHA256 |
| --- | --- |
| Rebuilt MCDK | `68cbff0f7a2454e37c823fab51a8bd3f4631f3e7c7c8e221b1b124add76d297f` |
| Existing focus guard DLL | `c22fa0cd0bdbfb7d9218d59573b61619111f9bd180562c9bd51c69276c11c178` |
| Snapshot retry test | `4c5718260684e899002b5db606445a2cf46d296504f4b3cb45a1754bb1c9f8ae` |
| Existing WGC helper | `cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bbfb5a8` |

The installed official executable, R10 executable, DLL and active agents'
loaded binaries were not overwritten. The retry still applies only to
`ERROR_BAD_LENGTH`, at most 50 attempts separated by 20 ms. Other errors
fail closed. Eleven launcher and WGC contract tests passed.

## Owned Smoke

Session manifest:
`C:/Users/Happy2018new/.pyreact-debug/instances/bd48f2f809fb4f0daf3ce560d5751adc/session.json`.
Owner `native-r11-retry-smoke`, project `.runtime/r11-native`.
Game PID/creation identity `17276` / `134362834338766836`; MCDK
`29104` / `134362834335292455`; game HWND `57476300`.
The session reached ready with background-safe and noactivation checks true.
The user switched from IDLE to Word during startup, so foreground-unchanged
is false; both observed windows belong to other applications.

The fresh native-resolution WGC frame is
`artifacts/retry-smoke-preflight-r11-v1.png` in that instance. Its SHA256 is
`8dc71626101a583a199cb227694656d403a8f36683969d1357c92a5aac4c2136`.
The sibling capture receipt reports reliable, background-only 1994x1105,
frame QPC newer than request QPC, and Word HWND/PID `44565462` / `23844`
before and after. The image was opened and shows a nonblank world, HUD,
hand and current game timestamp. No activation, desktop input or resize
was used.

The later scaffold fixture preflight rejected an existing stone cell in its
reserved region before setting its marker or writing blocks. Its report
records completed=false, restored=true; no support result was accepted.
Ordinary stop first exceeded its deadline, then both recorded processes
were independently absent and a second ordinary stop finalized stopped.
No forced stop was needed for this smoke.

## Diagnostic Boundary

A read-only creation-bound census found 168,927 game handles, predominantly
168,180 File objects, with 168,124 sharing access mask `0x0016019f`.
Three counts were approximately stable at 168,927/168,929/168,927.
The report is `.runtime/frame-material-review-r11/smoke-handle-types-2121-v1.json`.
File object type alone does not distinguish disk files from socket/device
objects. The process exited before name sampling; no cause is established.
Other owned R11 instances separately showed growth and were stopped after
fixture restoration. This does not prove a rendering or guard defect.
