# Root Plant Snow Screening, Round 8

Raw unregistered Combine omits crimson roots, warped roots and nether sprouts.
The R8 fixed public-view dry/h0 batch completed, restored the native fixture
and navigation, and kept frozen source stable. All three dry controls have
visible native plants but zero full/missing proxy pixels. All three h0 controls
have zero independently exposed proxy plant pixels, and their independent
editor plant baselines are zero. Snow-only controls pass.

| Plant | Native Dry Pixels | Raw Dry Full/Missing Pixels | Native h0 Exposed Pixels | Raw h0 Exposed Pixels |
| --- | --- | --- | --- | --- |
| Crimson roots | 36,928 | 0 / 0 | 24,214 | 0 / 0 |
| Warped roots | 37,024 | 0 / 0 | 28,327 | 0 / 0 |
| Nether sprouts | 12,777 | 0 / 0 | 1,253 | 0 / 0 |

Nether sprouts h0 has overall-object recall about .95 because the snow covers
most of the silhouette, but the separate exposed-plant recall is zero. The
independent plant gate correctly preserves this failure.

Raw matrix:
`C:/Users/Happy2018new/.pyreact-debug/instances/093a29fa49aa4d2a8c1b3605cfb83797/artifacts/snow-roots-raw-screen-r8.json`

SHA256: `ea0faa8cb8dee8e97479b5d4e6ed01b0f2e727615942e0b8dc16aedd96837514`

Independent audit:
`C:/Users/Happy2018new/.pyreact-debug/instances/093a29fa49aa4d2a8c1b3605cfb83797/artifacts/snow-roots-raw-screen-r8-audit.json`

SHA256: `584d4d1e11daa7037e9af4b1a2d745bc51d39f851bf68ef6ab656ec3da2a1139`

The audit checks 72 unique original native PNGs, image encoding/dimensions,
nonblank frames, owner/process identity, fresh frame time and frozen sources.
It passes integrity while preserving failed visual verdicts. Two ordinary
switches between other applications are retained as diagnostics; the owned
game remained background and every frame remained reliable. All three
native/full/missing/editor contact sheets were actually opened.

The raw source freeze is
`.runtime/snow-r8-raw-roots-source-hashes.json`, SHA256
`eca3fd104dea939155249a21d708733829148ddbb175af50268a90dbfcd858fc`.
After this batch, the game and MCDK exited normally by owned WM_CLOSE. The root
agent observed approximately 523,242 game handles near 21:30 Shanghai; that is
a preserved diagnostic, not an accepted resource limit or a native mesh fact.

The rejected hypothesis uses the existing centered mushroom/fungus cross at
origin Y 0, height 16, pivot Y 8 and the full original V range. Native texture
identity and alpha bounds are measured facts; they do not establish native
mesh or random offset. No fitted XZ shifts, height guesses or changed UVs are
allowed. Candidates first require dry+h0 in both original views. Remaining
heights are eligible only after these controls pass. All six plant/view
combinations failed; no remaining-height matrix was started.

| Plant | View | Dry Recall / Precision | h0 Exposed Recall / Precision | Editor Controls |
| --- | --- | --- | --- | --- |
| Crimson roots | Public | .708 / .851 | .709 / .834 | Pass |
| Crimson roots | Right | .668 / .721 | .656 / .707 | Pass |
| Warped roots | Public | .692 / .818 | .716 / .828 | Pass |
| Warped roots | Right | .540 / .590 | .531 / .587 | Pass |
| Nether sprouts | Public | .628 / .762 | .532 / .552 | Pass |
| Nether sprouts | Right | .580 / .629 | .315 / .369 | Pass |

Full and missing metrics are identical within each row. The unchanged gate is
.75 recall and .75 precision, with three-pixel edge tolerance. Every dry
native ROI has zero clipped-boundary pixels. Editor controls demonstrate
standalone position and snow occlusion only; their passing result does not
certify native world geometry.

Candidate matrix:
`C:/Users/Happy2018new/.pyreact-debug/instances/5c273e2305404cfbb80d9362ba8b51c1/artifacts/snow-roots-candidate-screen-two-view-r8.json`

SHA256: `5f5587a4fd90c93e7cb564ecfa4e37e7a94320c5f923102a57e1d1ce05fe5563`

Candidate audit:
`C:/Users/Happy2018new/.pyreact-debug/instances/5c273e2305404cfbb80d9362ba8b51c1/artifacts/snow-roots-candidate-screen-two-view-r8-audit.json`

SHA256: `fe7984ae465b2ce73a1dbf6aedce5b0aae55836cb069e0ec93a568c49d72e34b`

The candidate audit independently verifies 138 original PNGs and passes
integrity while preserving all six failed visual verdicts. It retains 14
ordinary switches between other applications, all reliable and background
safe. All six two-row contact sheets were actually opened. Three raw and six
candidate reports were independently replayed from original PNGs and retained
their failed verdicts.

`tools/data/snow-static-roots-rejected-screening-r8.json` stores both evidence
partitions, original measurements, report hashes, replays, inspection sheets,
and unchanged gates. `tools/build_root_screening_r8.py` reconstructs this
checkpoint and rejects incomplete, unrestored, changed or unaudited reports.
No root/sprout candidate is accepted. Their registration, behavior/model
resources, texture atlas entries and generated render adapter rows were
removed; all existing production resources are byte-identical to the state
before the experiment.

Exact experimental source bytes, original frozen manifests, and process
resource diagnostics are preserved outside the worktree in the main
repository's `.runtime/snow-root-rejected-candidate-r8` evidence directory.
The fresh candidate game grew from 61,025 handles near early calibration to
226,464 near the end of screening; private memory grew from 2.56 GB to 3.03 GB.
These observations remain diagnostic. The guarded candidate game and MCDK
both exited normally by owned WM_CLOSE; no forced termination or foreground
activation was used. The earlier 60-second startup timeout is retained and
was resolved through a fresh protected launch with a 180-second readiness
wait, without bypassing session validation.

Final offline verification after removing the failed registrations:
`python -X utf8 -m unittest discover -s tests -q` passed all 1,215 tests.
`tools/check_version_bundle.py` passed all generator and native-version
checks, with 44 provenance files, 15,858 states and six transforms per state.
The final bundle report is `.runtime/version-bundle-snow-r8-final.json`,
SHA256 `0886a4c6eedc1a9c5fb827c01c8ff3ccc4043b7894d0394125166577bf303276`,
with a copy in the persistent evidence directory. Scoped Minecraft Python
review parsed the changed debug blueprint module and found no findings.
