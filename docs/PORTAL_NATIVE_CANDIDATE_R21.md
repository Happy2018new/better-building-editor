# Native Portal Candidate R21

The new native candidate is opt-in through `native_candidate_profile()` in
`portal_profile.py`. `NATIVE_PRODUCT_QUALIFIED` remains `False` and
`native_production_profile()` returns `None`. The existing profile and its
`PRODUCT_QUALIFIED=True` flag are preserved for compatibility. That older flag
does not close the reopened native appearance issue.

The candidate reuses `PortalProfile`, `PortalPreview`, `PortalProjection` and
the existing four-cell render plan, ownership, suppression and cleanup paths.
Only four new resource aliases select the candidate UI/world shader pair.
No separate renderer or event listener is introduced.

## Retained Inputs

- The v10 world vertex is copied byte-for-byte, including normal `TIME/256.0`.
- `viewRay=(WORLD*entityPoint).xyz` remains unchanged; the measured correction
  uses `parallaxPositionInWorld=t*viewRay` without adding `VIEW_POS`.
- The observed 16 quantized native plane depths, reverse palette order,
  preceding clear plane, native starfield texture and original native fragment
  are retained. The wrapper only renames its local header include.
- `One/SourceAlpha`, `LessEqual`, point/repeat sampling and the existing
  depth-write contract are retained without density, color or exposure fitting.
- UI geometry retains the established coordinate transform and preview-depth
  clip. Its plane normal uses the same signed axis permutation as the geometry.
  Its view-origin ray is pulled from `WORLDVIEW` back through that matrix's
  linear inverse into preview entity axes. This retains arbitrary affine
  rotation, scale and translation without assuming `WORLD` is identity or
  passing rotated normals to the native axis-mask operation. Actual UI matrix
  bindings, orthographic appearance and runtime pixels remain unqualified.
  Singular or near-singular linear maps hide the affected frame and retain a
  finite zero ray, including an initial zero preview scale.

The expanded UI shader was exercised with 816 host WebGL2 transform-feedback
and encoded-plane pixel fixtures: six signed face normals, 17 plane layers,
identity, translation, rotation, nonuniform scale, shear, reflection, zero
scale and near-zero scale. Against an independent `numpy.linalg.solve`
reference the maximum ray error is 0.000002334066039111349. Encoded normal and
layer-depth pixels are exact. This verifies the affine calculation and its
degenerate guard; it does not observe the native game's UI uniform bindings.
The separate UI/world compiler check covers 16 cases, retaining the installed
GLES100 skinning header's preexisting unsupported `mat3x4` limitation.

The v11 changes were diagnostic only: its candidate literal `TIME=64`, its
fixed native vertex and the vanilla `portal.material` override are absent from
the candidate. No vanilla portal material is installed by the generator.

## Fixed-Time Observation

The v11 gateway north/front experiment captured and actually opened four full
WGC images. Candidate and native each had two frames separated by more than
two seconds. The same eroded north-face polygon contains 41,616 pixels.
Both within-route repeated frames are byte-identical in that polygon.

Candidate/native mean luminance is 0.9989830198224627, cyan coverage is
0.9988272087568414 and nonblack coverage is 0.9977410947002606. Exact RGB
pixels are 0.8879757785467128 of the polygon; 0.9290657439446367 are within one
channel value and 0.035298923490965015 have a channel difference above four.
No phase, spatial or exposure fit, or particle deletion, was used.

The root agent independently opened all four full images and independently
recomputed the north polygon/11-pixel erosion with PIL/NumPy. Its values match
the frozen analyzer. Native later-frame purple particles overlap another
lower face; they do not overlap this sampled upper north face. No conclusion
about other faces or particles follows from this restricted result.

The run restored editor, camera, player and owned platforms with unchanged
sources. Normal close timed out; exact retained handles later recorded game
exit `0xC0000409` and MCDK exit `0`. Both exact identities were absent before
ordinary metadata finalization. No force stop was used. This is not an
accepted normal-exit result.

Private raw images and analysis remain at
`.runtime/portal-fixed-time-observed-r21-v11/` and
`.runtime/portal-fixed-time-control-r21-v11/fixed-time-analysis.json`.

## Narrow Cold Run

The next opt-in run captures only one editor pose plus near full and empty-world
missing mode for each of gateway and End portal, six images in total. It records
the actual source, owner readiness, camera, native model groups and WGC receipts.
The world interior detector checks the actual starfield rather than support
blocks. UI visibility still requires opening its actual screenshots.

All four reload flags stay false. The process-local BLAS limit is one thread.
Launch requires no live or uncertain MC process, available system commit of at
least 6 GiB, exact owner-bound assertion coverage, noactivation inputs and an
immediately retained exit observer. Runtime samples use `CommitLimit-CommitTotal`;
physical free RAM is recorded but is not an additional gate.

Budget: one cold startup up to 180 seconds, roughly 60-120 seconds for the six
views and restoration, then one normal-close request and exact exit observation.
No further angle matrix, native pair, opacity or animation-speed run is included.
Missing-mode occupancy transitions, other faces, distant fog, UI normal space,
animation speed/direction, opacity and full lifecycle acceptance remain open.

## Rebuild

```powershell
python -B -X utf8 tools/generate_portal_native_candidate_r21.py --output .runtime/portal-native-candidate-fresh --install
python -B -X utf8 -m unittest discover -s tests -p test_portal_native_candidate.py -v
```

Use a fresh output path. The generator verifies the committed v10 raw evidence
manifest and unchanged skeleton/palette dependencies before generating aliases.
