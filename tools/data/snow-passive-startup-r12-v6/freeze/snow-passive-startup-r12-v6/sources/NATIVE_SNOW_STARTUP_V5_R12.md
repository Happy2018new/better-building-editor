# Native Snow Startup V5

V5 is preparation for one background startup. No game launch, SDK call, WGC
capture, input, or window change is performed while freezing or reviewing it.
The current protected frame session remains outside this work's ownership.

Relative to the executed V3, the two behavioral corrections are the exact
`e757ef5db11dab2a6e97718b6419b7c8f6635d38` readiness launcher and the scoped
PMv2 guard already reviewed in V4. The Git source equals transform commit
`ca82cc9f2bc12493d98304c3949a868e2b684646`; its LF bytes have SHA-256
`094188df49b1f733def68cc5dd1ceeaa3d4856bc3f426c96c3aada0366337712`.
The reviewed Windows CRLF launcher actually executed has SHA-256
`e485a7b24e8d5d3c645d1d39ffcfd3cefa6ba5a7f96c1f5c65034e696a43cfba`.
The root's latest budget contract also narrows the observation deadline from
120 to 110 seconds. This budget alignment is explicit in the new supervisor
source and plan; V1 through V4 and the failed V2/V3 receipts remain unchanged.

## Fixed Deadlines

| Boundary | Actual Origin And Limit |
| --- | --- |
| Parent T0 | Immediately before the first capacity check and preparation |
| Startup readiness | Launcher receives `--wait 90`; its internal deadline starts after its world preparation and owned MCDK spawn |
| Supervision | T0 + 110 seconds, including capacity checks, preparation, launcher time and passive observations |
| Cleanup reservation | 40 seconds after supervision, with earlier failure entering cleanup sooner |
| Parent deadline | T0 + 150 seconds; preparation or readiness never resets this deadline |
| One observation | At most 15 seconds, further clamped to T0 + 110 seconds |

The parent stops its owned launcher at the supervision boundary if it is still
running. `--wait 90` therefore does not grant 90 seconds beyond the parent
deadline. Samples remain at game creation ages 1, 15, 30, 45, 60, 75, 90 and 105
seconds, without overlaps or repeats. Late publication and unattempted samples
are retained explicitly. A late game creation can leave no post-ready sample.

There is one launch, no automatic retry, no activation fallback and no matrix.
Capacity must be below five independently verified live games before
preparation and immediately before launch, and at most five after owned game
publication. Cleanup targets only the owned executable and creation identities,
then restores original script/config/marker bytes with drift checks.

## Readiness And Current Texture

The launcher retains the first verified child and listener discovery, checks
both creation identities and the IPv4 listener owner around each network call,
and clamps each request to its original readiness deadline. It independently
retains discovery errors and full SDK errors. Readiness requires the runtime
PID/AppData and both client/server session markers. Those facts do not prove
world rendering or snow pixels.

V5 retains the native-alpha marker condition, flat creative config, archived
protected MCP client, MCDK binary, noactivation DLL and native WGC helper. Its
first post-ready image is the first scheduled sample with both `state_before`
and `state_after` equal to `ready`. The launcher must also have returned zero
and published `ready=true`. The observer must report `ok=true` and
`reliable=true`, exact physical client dimensions, stable owned HWND/PIDs,
fresh compositor QPC, a PNG and nonblank variance. The image must be opened and
visually show the world, rather than a loading screen. An unreliable, blank,
loading, missing or mistimed result is retained and reported as a failure;
later samples do not replace the predeclared first post-ready result.

No camera or snow fixture is added to this run. The existing full camera and
plant tools have budgets and child processes that do not fit the remaining
post-ready interval. A successful current-texture frame grants no alpha,
snow, offset, pivot, position-registry, or production acceptance.

## Next Native Snow Control

The minimal next pixel phase uses one predeclared calibration cell `(6,117,6)`
and public camera offset `(-2.0,0.15,-2.5)`. It compares native height-zero
snow-covered poppy, snow-only, plant-only and blank at the same cell and pose.
The covered/snow-only pair isolates the plant's visible contribution, while
plant-only/blank is the positive control. Host and replicated palette readback
must agree with the requested state before fresh background capture.

The two texture conditions are original native flower texture and the frozen
own marker preserving native alpha. There is no evidence that a same-session
texture switch refreshes the actual atlas. Declare two separately coordinated
cold starts, at most one launch per condition, with independently fixed finite
deadlines. Freeze the original/marker bytes, config, source, camera/physical
crop and cleanup before either start. Pin the same launcher and PMv2 adapter.
Use same-session camera qualification or the existing public world projection
path if that capability is actually present; do not reuse another session's
calibration as proof.

Reuse the existing `NATIVE_SETUP`, `NATIVE_NEAR_PLAYER`, `NATIVE_MUTATE`,
`NATIVE_SNOW`, `native_capture` and `NATIVE_CLEANUP` semantics from
`verify_snow_plant_visibility.py`. The full CLI is not authorized by this plan.
A future narrow adapter must bound every SDK wait and own WGC as a direct
child, following the startup observer. It must not use the unbounded capture
subprocess in `SignCheck`. The existing `verify_camera_projection.py` full
calibration is a source reference, not an executable phase in V5.

Do not expand to other heights, opaque markers, holdout cells, geometry fits or
the complete matrix. Existing acceptance gates and old failed evidence remain
unchanged. This deferred control is a proposal; its separate executable plan
and root-coordinated runtime slot are still required.
