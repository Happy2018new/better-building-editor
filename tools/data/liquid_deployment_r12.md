# Liquid Deployment Candidate R12

This adapter installs original NEMC 3.9 water strips and distinct UI/world
resources. It is disabled by default: `PRODUCTION_QUALIFIED = False` and both
qualification fingerprints are absent. Explicit diagnostic injection selects
`candidate_profile(frozen=True)` without changing that gate.

The immutable resource contract is `liquid_deployment_r12_contract.json`, SHA256
`be45647fa7712336e725a9abba3b071d98642e688eea287ad1610a2b1793900e`.
The generation bundle remains under `.runtime/liquid-deployment-flow-top-r12-v2`
in the flow-top worktree. Independent shader/mesh/artwork bytes are installed exactly;
generated JSON model/material entries are merged with existing entries. The
deployment generator validates native metadata, artwork, source references,
generator identity, bundle outputs, and installed liquid entries before emitting
the closed runtime profile.

Candidate defaults are the existing `.45` water opacity and an explicitly chosen
flowing cadence of 1 tick with frame blending. Native flowing metadata declares
`replicate: 2` but omits cadence, so that choice is not native-verified. The side
template is NW quadrant, edge coordinates, bottom-anchored `v = 1 - height`.
The default still/side resources support rotation zero. A separate opt-in top
template supports all 256 angle codes. Host GLES parity is not native pixel acceptance.

The complete source document remains the neighborhood input, including occupied
neighbors, logical foreground/background layers and actors. Diagnostic support
includes `minecraft:water` and `minecraft:flowing_water`. Flowing-top direction,
lava, native side UV/filter parity, animation timing, projection memory, and whole
production acceptance remain unqualified. Mixed unsupported liquids retain the
existing explicit error behavior.

`candidate_profile(frozen=True, flowing_top=True)` explicitly injects the
versioned four-corner downhill hypothesis and separate top resources. The default
`flowing_top=False` retains the original profile, face grouping and source
geometry. The old still/side shader, mesh and artwork bytes are unchanged.
`native_liquid_flow_top_candidate_nemc_3.9.0.401155.json` records the source
limitations, full-frame centered half-size UV window and native acceptance plan.
Its native direction, UV and production flags are all false. Flat and saddle
surfaces have unknown native direction; keeping their still top is only the
candidate choice. See `docs/LIQUID_FLOW_TOP_CANDIDATE_R12.md` for the mathematical
contract and regeneration commands.

`probe_liquid_workspace.py --qualification-minimal --deployment-profile
--transparency-controls` captures exactly four opacity phases (0, .45, 1, default)
through Scene, full projection and missing projection with fixed source/body/water
geometry. Same-session independent stone camera calibration is required for world
ROIs. The replay requires both geometry-declared submerged-fence/rear-block ROIs,
at least 80 eligible pixels each, RGB RMSE at most 3, and body/water contributions
in at least 80 percent of eligible pixels. It checks applied alpha and unchanged
source/shape/models/body/tint. Report and imported analyzer sources are archived.
This twelve-PNG replay qualifies only visible alpha; side UV, animation and the
production gate remain false even when its alpha observations pass.

R12 four-epoch static cube/water diagnosis remains a failure in every declared FOV
pair. Its resources and evidence are frozen separately; this candidate does not
rewrite that result or claim the sampler has been identified.
