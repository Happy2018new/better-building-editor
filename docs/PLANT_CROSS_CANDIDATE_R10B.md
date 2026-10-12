# Plant Cross Candidate R10B

This is an experiment record, not production plant acceptance. The active
work list remains `IMPLEMENTATION_GAPS.md` (F01-S03 / M08).

`tools/prepare_plant_cross_candidates.py` creates reversible candidates for
poppy, crimson/warped roots, nether sprouts, short grass and fern. It snapshots
all previous bytes, records candidate hashes and refuses restoration if any
candidate file changed. Accepted mushroom/fungus model files are untouched.
The unit-height cross and fixed translations are hypotheses: native fern
selection-clip observations suggest X/Z `-7/60` and grass/fern Y `-7/75` at
the historical cell, but do not establish native mesh pivots, vanilla jitter
hashes or the offsets of another plant. Native texture identities and UVs
remain source-based. The tool temporarily edits candidate pack files and
runtime registration, then restores their previous bytes. None of these six
families is accepted or enabled in committed production defaults by this
experiment.

## First WGC Matrix

Owned session:
`C:/Users/Happy2018new/.pyreact-debug/instances/61335279333c47118ba694f0439e576e/session.json`.
Owner `snow-r10b-cross`, game PID `23152`, creation identity
`134362536245273622`. The approved guarded launcher preserved background
state. Same-session calibration `snow-camera-r10b-v2-wgc.json` completed,
passed and restored, with all three views using fresh WGC. Its SHA256 is
`9e8e2dbd748547b656d4caa70750e16ba379c8f32018a71d7a0730686d71b458`.
Earlier `snow-camera-r10b-v1.json` used PrintWindow and is excluded from
acceptance even though its geometry calibration passed.

The matrix `snow-cross-roots-poppy-screen-v1.json` in that session's artifacts
has SHA256 `4d3f3751c1f25aff2f094ceeeadef364e34bca9faa6d1d520c122d12238c9fc7`. It
captures dry, h0 snow and h0 covered controls at `(-47,117,-70)`, with public
`(-2,.15,-2.5)` and right `(2,.15,-2.5)` views. Editor, full and missing are
independent. Original limits remain recall/precision `.75/.75`, edge tolerance
3 pixels and fixed calibrated unit-cell ROI.

| Plant | View | Covered Exposed Recall | Precision | Result |
| --- | --- | ---: | ---: | --- |
| crimson_roots | public | .811101 | .903147 | Dry and h0 pass |
| crimson_roots | right | .834531 | .907204 | Failed dry ROI boundary: 138 pixels |
| poppy | public | .949298 | 1.0 | Dry and h0 pass |
| poppy | right | .951552 | 1.0 | Dry and h0 pass |

Full and missing give identical exposed-plant values. Covered editor controls
pass in all four cases. The complete matrix remains failed because crimson
roots right dry touches the original ROI boundary; no ROI expansion or
threshold change is used to reinterpret it. All four reports completed and
restored; cleanup errors are empty and source hashes remained stable.

`snow-cross-roots-poppy-screen-v1-audit.json` independently verifies 94 original
native PNG hashes, freshness, nonblank content and owner-bound background WGC.
Its SHA256 is `95a3e3cd12afc1a0a59a08958ef9f5d8bd0919d4faf6f9796f2eb11f952e8b45`.
Integrity passed with no errors. One ordinary switch between other desktop
applications is retained as a diagnostic; the owned game was background
before and after. All four generated contact sheets were actually opened.
The immutable frozen source is `snow-cross-candidate-v1-source-wgc.json`,
SHA256 `83cd0bbf025bb41522b69c4fa4341eafa31bd1e54c78394eef36877ebe7519bd`.
Candidate resources were also archived under `.runtime/cross-candidate-v1-source`
before restoration.

The game handle count rose from approximately 110,582 during calibration to
262,899 near the last case; private memory was then about 2.82 GB. The cause
is not established. After fixture restoration, normal identity-bound stop
closed game PID 23152 and MCDK PID 17168 without force. Candidate source was
restored exactly through `.runtime/cross-candidate-v1-snapshot.json`.

These observations justify further bounded experiments. They do not accept
remaining snow heights, another cell, a native geometry/offset contract or
production registration. The original failures and PrintWindow calibration
remain preserved.

## Second WGC Matrix

Session `9512c9895d48444580e48589f0f21812`, owner `snow-r10c-cross`, game PID
34536 / creation identity `134362554076102257`, completed a new same-session
WGC calibration before the other four plants. Calibration
`snow-camera-r10c-v1-wgc.json` completed, passed and restored; its tilted PNG
was opened. SHA256:
`86ab2d4a6151588bf3b04d8accc08708dc3d6fa426c9f7797f3721a54a8df1e5`.

`snow-cross-other-four-screen-v2.json`, SHA256
`0d27322d965a632e7ca2de1607fb1132140909dd9a0c7d7880be72552d50222b`,
completed all eight plant/view reports and restored every fixture. Source
hashes remained stable. All covered editor controls passed, but the matrix
remains failed with unchanged pixel and ROI gates.

| Plant | View | Independent h0 Exposed Recall | Precision | Result |
| --- | --- | ---: | ---: | --- |
| warped_roots | public | .840663 | .911314 | Dry and h0 pass |
| warped_roots | right | .840907 | .909874 | Failed dry ROI boundary: 34 pixels |
| nether_sprouts | public | .700718 | .790486 | Exposed-plant recall fails |
| nether_sprouts | right | .733369 | .838922 | Exposed recall fails; dry boundary 6 pixels |
| short_grass | public | .766827 | .501336 | Exposed precision fails; dry/green masks fail |
| fern | public | .779809 | .503301 | Exposed precision fails; dry/green masks fail |

Short grass and fern also fail the right view. The independently isolated
plant checks reject cases whose combined snow silhouette passes. No fitting
or source change is applied based on these failures.

Audit `snow-cross-other-four-screen-v2-audit.json`, SHA256
`8cfda86d5cdbe49fe75176b07f3675b62a61fecdf42da469404b13d3426c85b9`,
passed integrity for 182 original native PNGs with no errors or foreground
switches. All eight contact sheets were actually opened. Frozen source
`snow-cross-candidate-v2-source-wgc.json` has SHA256
`d689891e7ae785f777ac6a8b90417e5f267905095ba3476d09798f1b36c7b59a`;
the exact candidate sources are archived at `.runtime/cross-candidate-v2-source`.

Handle count reached 286,790 and private memory 2.837 GB at final audit.
Normal owned stop closed game PID 34536 and MCDK PID 47904 without force.
Candidate resource bytes were restored through the v2 snapshot. The cause
of handle growth remains unknown.

The separately declared `poppy_candidate_remaining` profile retains the same
cell, views and candidate geometry and tests exactly h1..h7. It is disjoint
from the original h0 screen and grants no production acceptance by itself.

## Poppy Remaining Heights

Owned session `cb3974b48ff74f2ebb7f393a18eefc12`, owner `snow-r10d-poppy`,
game PID 31980 / creation identity `134362571527549278`, used the same poppy
candidate bytes and a new same-session background WGC calibration.
`snow-camera-r10d-v1-wgc.json` completed, restored and passed; SHA256
`a797700c30b4fdaec01e6b53b628ac416fb7e64d98e8f76f557f8a7c5540b022`.
The original tilted calibration PNG was opened.

`snow-poppy-seven-heights-r10d-v1.json` completed, restored and passed at both
declared views for h1..h7. SHA256:
`fa16f51fad2ec5a21eeb028d7ebd563127b9a50ebff866fcfb705be6aac83caf`.
All full/missing comparisons and independent covered-editor controls passed,
with unchanged `.75/.75`, 3-pixel and calibrated ROI gates. The exposed-plant
measurements below are identical between full and missing modes.

| Height | Public Recall | Right Recall | Precision | Exposure |
| --- | ---: | ---: | ---: | --- |
| h1 | .945587 | .950841 | 1.0 | Flower and stem exposed |
| h2 | .937965 | .943215 | 1.0 | Flower exposed |
| h3 | .939548 | .941860 | 1.0 | Upper flower exposed |
| h4 | .933560 | .953488 | 1.0 | Small flower tip exposed |
| h5..h7 | Not applicable | Not applicable | Not applicable | Native/proxy exposure and editor contribution all zero |

Independent audit `snow-poppy-seven-heights-r10d-v1-audit.json` passed for 218
original native PNGs with no errors. SHA256:
`612bd220f019b3b859321e8e382d0789601b2b015e297f50faead6abe42c98e9`.
Three ordinary switches between other applications are retained; the owned
game remained background before and after each capture. Both contact sheets
and right h4/h5 native/full original PNGs were actually opened. Four independent
offline PNG replays, covering h0 and h1..h7 at public/right, also passed.
Frozen source `snow-cross-candidate-v3-source-wgc.json` has SHA256
`1e1c1ac97a6c300bde5e8b9940b672d31dcb81c5a07d70e6f1a8e56bf4c96089`.

The exact 23-file candidate/tool archive is `.runtime/cross-candidate-v3-source`.
Normal owner-bound stop closed game PID 31980 and MCDK PID 23908 without force.
The v3 snapshot restored every modified resource byte and removed experimental
files; the worktree was clean immediately after restoration. This instance's
handle count was approximately 76,186 near completion and did not show the
earlier rapid growth. No cause is inferred from that difference.

`tools/build_poppy_candidate_evidence_r10b.py` preserves the finite union in
`tools/data/snow-poppy-candidate-all-height-evidence-r10b.json`. Isolated BP/model
and registration artifacts live only in `tools/data/plant_cross_candidate_r10b`.
The BP SHA256 is
`3bde8f63760f8d5762fa0fed28f7a516410c1102ebe58c23aa70f5e736ba9ca9`;
the model SHA256 is
`bc932ecfcb8a3c0a0ed7fd07289467a6e23647974334e108154221deb50e07a2`.
Both are identical across the h0 and h1..h7 partitions. The first mixed-family
matrix remains failed due to crimson roots right ROI contact; the second
matrix retains the warped-roots, sprouts, grass and fern failures.

This is measured candidate evidence only at `(-47,117,-70)`, public/right,
h0..h7 on NEMC `3.9.0.401155` / runtime `1.21.120.0`. Production defaults still
contain only two mushrooms and two fungi. The `(name, aux)` runtime table cannot
enforce that position scope. Native mesh/pivot and position-dependent random
offset contracts remain unrecovered, so `production_default_enabled=false`
and no poppy registration is retained in the production packs.

The M08 inventory separately contains 148 native names with `renderLayer13`
seed definitions. This is a seed-name inventory, not full state or layer
coverage, and does not establish geometry or offset authority for those names.
