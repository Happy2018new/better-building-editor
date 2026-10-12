# Startup Capture DPI Coordinates

The V3 startup observer compared a physical WGC client bitmap against logical
client dimensions reported by a DPI-unaware Python thread. Its strict dimension
check therefore rejected all eight captures with 1994 x 1105 versus 1329 x 736.
The dimension check itself must remain exact; the guard must read the same
physical coordinate space as the approved native helper.

## Read-Only Evidence

The independent geometry probe inspected protected session
`773c643b5cf344918e04d8b4eef2657a`, game PID 44536, identity
`134362903316974407`, HWND 29102794. It did not launch a process, capture WGC,
call SDK, activate, resize, minimize, restore, or modify a game window.

`GetAwarenessFromDpiAwarenessContext` reported awareness 0 for the caller and
awareness 2 / Per-Monitor V2 for the window. `GetDpiForWindow` returned 144.
The same `GetClientRect` call returned 1329 x 736 in the original context and
1994 x 1105 inside a scoped Per-Monitor V2 context. The original thread context
was restored in `finally`; the subsequent guard again returned 1329 x 736.
The session manifest hash, both process identities, foreground HWND/PID, and
window ownership were unchanged.

Probe receipt: `.runtime/snow-dpi-geometry-r12-v1/geometry.json`, SHA-256
`878074c77d264ebc0873bd163c988b32ae82ec0a62d08db7b68d6ff09cbeb8e0`.

The existing successful frame capture for the same protected game also records
logical window dimensions 1329 x 736 and physical WGC dimensions 1994 x 1105.
Its older wrapper checked PNG versus native helper dimensions, but did not
compare native dimensions against the logical window dimensions.

The approved WGC source already sets Per-Monitor V2 only on its capture worker,
then obtains DWM physical frame bounds and the physical client crop.
For the inspected window, DWM bounds were `[281, 219, 2279, 1371]`, client origin
`[283, 264]`, and client size `[1994, 1105]`. This corresponds to a client crop
`[2, 45, 1996, 1150]` within the 1998 x 1152 DWM frame. No bitmap rescaling or
logical-to-physical multiplication is needed.

## Narrow Correction

The supervisor loads the exact SHA-bound DPI helper source into an isolated
module and wraps only the observer host's guard read in `physical_dpi_context`.
That context manager verifies entry into Per-Monitor V2 and restores the exact
original caller context even when geometry inspection raises. Entry or
restoration failure remains a failed observation. The frozen `_window.py`,
native focus DLL, WGC executable, and active frame sources are unchanged.

The observer still requires exact native frame/client dimensions, stable HWND,
stable PID creation identities and executable paths, fresh compositor QPC,
background/noactivate/unminimized windows, a real PNG, and nonblank variance.
The WGC process remains a bounded direct child. A one-pixel mismatch is rejected.

## Limits

The V3 receipts remain failed and immutable. The first six raw PNGs were black,
and the final raw PNG showed a loading screen. The startup launcher did not
become ready and no established owned TCP pair was observed. Correcting the DPI
coordinate comparison does not establish readiness, rendering acceptance, a
native alpha result, or any position/offset acceptance.

This correction was verified by offline tests and the geometry-only probe.
No new startup or WGC attempt was made for the correction. Another native phase
requires root coordination with changed preparation and its own finite budget.
