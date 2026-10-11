# Native Window PNG Capture

`window_capture.cpp` and `window_capture.h` are derived from MCDevTool v1.6.1,
commit `cefdfb5ce220e0cc3e9df6d80b2ff87be8b98802`, under the included BSD
3-Clause license. Original source: https://github.com/GitHub-Zero123/MCDevTool/tree/v1.6.1/src

The WGC window binding, frame pool, D3D11 readback, physical client crop,
resource cleanup, MTA thread and implementation-module pin are preserved.
Capture-module changes replace the 480p JPEG encoder with original client-size
24-bit PNG encoding, rename the exported helper function, and require a frame's
compositor QPC time to be at least the current request start time.
The result is SDR RGB; alpha and HDR are not acceptance targets. Timing uses
`Direct3D11CaptureFrame.SystemRelativeTime`, documented as compositor QPC time:
https://learn.microsoft.com/en-us/uwp/api/windows.graphics.capture.direct3d11captureframe.systemrelativetime

`main.cpp` additionally checks the bound HWND, PID and process creation time
before and after capture, refuses minimized windows, and creates a fresh file.
It never activates, restores, resizes, raises or simulates input to a window.
There is no screen-region fallback. Failed or black captures are unaccepted.

Build with Visual Studio 2022 and a Windows SDK providing C++/WinRT:

```powershell
cmake -S tools/native_wgc -B .runtime/native_wgc/build -G 'Visual Studio 17 2022' -A x64
cmake --build .runtime/native_wgc/build --config Release
```

Use `tools/capture_native_window.py` to validate the instance owner and process
identities before invoking the executable. The wrapper records source/binary
hashes, PNG dimensions, variance and the foreground-window observations.
The native executable's numeric CLI is an implementation detail, not a way
to bypass the session binding in acceptance tools.

Set `MCDEV_NATIVE_CAPTURE_HELPER` to the absolute path of
`tools/capture_native_window.py` for `SignCheck` native captures. Optionally set
`MCDEV_NATIVE_CAPTURE_EXE` to an existing compiled binary. Without the explicit
helper setting, `SignCheck` retains its background PrintWindow path.
