# Normal-TIME native portal product acceptance

R22 adds a product route that can select the native world surfaces independently
of the editor preview. `native_world_candidate_profile()` keeps the existing UI
aliases and selects the measured native world aliases for explicitly qualified
families. The proposed first family is `end_gateway`; `end_portal` retains its
existing world alias until its own complete normal-TIME matrix is available.
Its cache identity includes this family scope and differs
from both the legacy profile and the all-native candidate. `production_profile()`
prefers the all-native qualified profile, then the separately qualified native
world profile, then the existing profile. Each world family has its own
`NATIVE_WORLD_QUALIFICATIONS` row with a boolean and evidence SHA-256; enabling
the gateway row cannot admit the portal row. Both rows and the all-native gate
remain false pending actual review and default cold validation. No shared
registry or material change is required.

The current private v13 clone derives from the successfully observed v12 frozen
closure. It incorporates the two previously missing host dependencies directly
into the frozen tools directory. Deep document readback uses JSON in the new
probe itself; it does not repeat the failed nested RPC transport. Shader, mesh,
texture and native `portal.material` bytes remain unchanged from v12. No fixed
TIME source, color correction, density fitting or native material override is
introduced.

The bounded acceptance probe is
`tools/probe_portal_native_acceptance_r22.py`. It takes one already bound session
and captures 48 original WGC images, 24 for each family:

- Editor baseline, opposite yaw, high pitch at reduced scale, and rotated source.
- Candidate and actual native finite surfaces at the same front and oblique
  cameras, three normal-TIME samples per route and pose.
- Missing projection in empty, fully occupied and restored source cells.
- Projection opacity 0.45, 0 and 1, followed by rotated full and missing views.

Every source load checks complete document equality, including typed actor data.
Occupancy checks actual published portal surface counts and the complete target
cell states, allowing zero surface groups while fully occupied. Owned server
writes and player support platforms have restoration journals. Camera, profile,
document, workspace, projection options and player restoration run in `finally`.
Available commit is sampled before/after client calls, server calls and captures;
physical free RAM is recorded without imposing another gate. The runtime budget
is 600 seconds, after which restoration still runs.

`tools/analyze_portal_native_acceptance_r22.py` measures the existing eroded finite
surface masks. Three-frame means retain absolute brightness, cyan coverage and
nonblack coverage; no phase, spatial or exposure fit is permitted. A 0.8–1.25
ratio screen only identifies large distribution differences. It does not grant
qualification. Native magenta particles remain in the statistics. Within-route
pixel changes establish visible animation but cannot alone establish direction
or speed equivalence. Independent examination of original images is required.

The runtime host is an ignored private entry at
`.runtime/portal_r22_v13_host.py`; default execution and `verify` perform only
offline source/import/fixture verification. `start`, `capture`, `close` and
`finalize` are separate operations for the root agent's runtime schedule. It
enforces the five-process total budget, at least 6 GiB available commit,
process-local `OPENBLAS_NUM_THREADS=1`, four disabled reload flags and the exact
noactivation toolchain. A new owner watcher runs until 2026-10-16 13:30 +08:00.
The start process retains an exact exit observer. Close issues one ordinary
request; finalize only runs after both exact process identities have exited.
No activation, resize, desktop input or forced stop is used.

The v13 run captured all 24 gateway views, then stopped on the 30th capture after
the user foreground changed during WGC. It restored its complete scene and
player state with unchanged frozen sources and no cleanup errors. The failed
capture was fresh and had no activation fallback, but its foreground guard was
false, so it is excluded from product evidence. The incomplete End portal family
does not qualify through the gateway result. Native/candidate gateway three-frame
mean ratios are 1.1011 luminance / 1.0951 cyan coverage / 1.0927 nonblack coverage
in front view, and 0.8742 / 0.8932 / 0.9212 in oblique view. Both routes show actual
normal-TIME pixel changes. No fitting or particle deletion was performed.

The analyzer also reports the native route's measured temporal minimum,
maximum, population standard deviation and actual sample span. The v13 native
front luminance spans 11.5457–12.4349, while the candidate three-frame mean is
13.2124; oblique native spans 14.0977–15.0764, while the candidate mean is 12.6822.
Thus these candidate means are outside the measured native intervals. Native
front samples span about 5.59 seconds, compared with 10.10 seconds for candidate
front; the two routes also use different normal-TIME windows. This small,
unequal sample cannot establish that the differences are explained by native
self-variation. Observed ranges are diagnostics, not post-hoc acceptance bounds.
The proposed next sampling plan must be fixed before capture and cover matched
time spans, with a separate native reference repeat. No native gate is admitted
by the current ratios.

V14 freezes `tools/data/portal_native_time_plan_r22.json` before launch (SHA-256
`a66b19a88051fcded2783a47e76cada16f00eab4e47db7742eeb54f74da26918`).
Its 78-image run first completes the portal's 24-image matrix, then captures
gateway native A, candidate, native B, each at front and oblique poses with nine
frames on a four-second schedule (32-second target span). Actual QPC spans must
be 30–36 seconds and differ by at most three seconds across routes for each
pose; an out-of-range series makes this experiment inconclusive. The plan
preserves all pixels and absolute metrics. A candidate metric mean outside
pooled native extrema is not explained by measured phase variation; being
inside only establishes consistency with that observed variation and cannot
itself qualify a renderer. These rules do not change after examining results.

The v14 frozen source digest is
`4ea3395510977dcf4d4dc6176bc9ec6e039e3c25e602b4655ddd2cf1c90e4071`
for 3,697 source files. Its separately bound sampling-plan hash is checked by
the host before launch. The previously missing exact exit observer is included
and imported in the offline closure check (114 host modules, zero runtime
operations). Both family qualification rows remain false.

All 24 original gateway images from v13 have now been opened for visual review, including
the four editor poses, both front/oblique three-frame sequences, all missing
states, opacity states and rotated full/missing views. The finite surfaces remain
visible at the tested poses; actual occupancy removes them and restoration
returns them. Opacity zero removes the whole projected fixture, while one
restores it. The intermediate transparent volume exposes rear layers and remains
a visual limitation to assess independently of the opaque comparison.

The first exit observer command failed because its root host tool was absent
from the old frozen project. The unchanged separately bound root observer was
then started before capture and retained both exact identities. One ordinary
close timed out; the observer recorded game `0xC0000409` and MCDK `0`, followed by
successful metadata finalization. Watcher status retains one cumulative startup
manifest `Errno 13`; later ready-session coverage succeeded. These operational
failures remain in the original control directory and are not normal-exit proof.

The previous v12 evidence and its cumulative startup `Errno 13` and abnormal game
exit remain unchanged. Native UI equivalence,
distant fog, beams, particles, and teleportation remain outside any proposed
finite-world-surface qualification. A default cold smoke run is still required
after any supported route is admitted.

## R25 independent review of the completed v14 run

On 2026-10-21 the root agent independently rehashed all **78** v14 originals
against both their capture report and the unchanged analyzer output: zero
mismatches. The run contains the portal's 24-view matrix and the gateway's
54 matched-span reference images, rather than another complete gateway UI and
lifecycle matrix. Completed, restored, source-unchanged and empty cleanup-error
fields were checked in the original report. This is a review of the historical
3,697-file source contract, not a new cold run on the integrated R25 source.

The root viewed both [portal overview pages](evidence/portal-v14-r25-review-v1/portal-page-1.jpg)
([second page](evidence/portal-v14-r25-review-v1/portal-page-2.jpg)) and all 54 gateway
face crops ([front](evidence/portal-v14-r25-review-v1/gateway-front.jpg),
[oblique](evidence/portal-v14-r25-review-v1/gateway-oblique.jpg)). Gateway crops
retain every projected finite-face corner plus a fixed 15-pixel border; original
PNGs remain unchanged. These JPEG sheets are display aids only and are not used
for image metrics. The [index](evidence/portal-v14-r25-review-v1/evidence-index.json)
binds all original hashes, source contract, report, analyzer and review sheets.

The portal surface is visible in the tested editor poses, occupied missing
cells remove it, and restoration returns it. Opacity zero hides the complete
projected fixture; opacity one restores it. Candidate/native mean luminance,
cyan coverage and nonblack coverage ratios are 0.936957 / 0.974461 / 0.967888
front and 0.956991 / 0.945605 / 0.975107 oblique. These absolute metrics use
different normal-TIME phases and remain diagnostic.

For the gateway, actual native A / candidate / native B spans are
31.8358404 / 31.781286 / 32.0115998 seconds front and
32.0722025 / 32.138889 / 31.9631112 seconds oblique. Both pass the predeclared
sampling comparability rule. Candidate mean luminance is 12.69346 front,
within pooled native observed extrema 11.21525–15.77905, and 13.16860 oblique,
within 12.01080–17.15562; cyan and nonblack means are also within the respective
observed extrema. The interpretation remains exactly
`consistent_with_measured_native_phase_variation_only`. Observed extrema
are not an equivalence interval, and individual frames are not required to
fall within them. All native magenta particles remain in the statistics.

No direction or speed equivalence, actual UI matrix binding, current integrated
cold qualification, distant fog, beams, particles or teleportation is closed by
this review. Both native-world family gates and the native UI gate remain
false. New manual closures: **0**. The legacy default's compatibility flag is
unchanged and still does not close the user's reopened appearance report.
