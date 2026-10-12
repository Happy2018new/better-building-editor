# Complement Coordinate Code R10B

This bounded continuation delivers reusable host marker generation, a frozen
geometry/phase plan, a synthetic-only analyzer and counterexample tests. It
does not launch a game, install a resource override or accept any native UV.
`native_ready`, `native_executed`, `marker_installed`, `native_uv_accepted` and
`production_accepted` are all false. The original evidence directory and ZIP
retain their exact bytes. The production liquid profile stays disabled.

## Concrete Frozen Design

The conventional flow bitmap remains 32 by 1024 RGBA, representing 32 square
frames with opaque alpha. The first 20 frames encode the five Gray-code bits
of full 32-texel X and Y addresses, each followed by its complement. All RGB
channels share levels 16 and 240. The remaining 12 frames alternate uniform
references. Every texel has a unique ten-bit coordinate signature. The
uniform frames do not independently identify the coordinate-bit frame.

The final v2 plan fixes the original source/control identities, six north/west
geometry sequences, origin and camera offset. Depth zero is training; depths
one and three are geometry holdouts. Each source surface retains the original
16-by-16 inset sample grid, including locations where pixel-center and
pixel-edge predictions differ. There are 240 fixed UV hypotheses for each of
the bilinear and nearest samplers, testing region, vertical basis and pixel
mapping. No observed pixels choose sample locations or exclusions.

The scorer requires agreeing green/blue complementary signed differences of
at least six RGB units at every declared bit/sample. Candidate source
predictions below 64 units are ambiguous: they cannot contradict observations
and prevent that candidate from passing. The selected candidate must have
zero contradictions and zero ambiguous bits on every sequence. Every
different value of each UV property must have at least one contradiction on
both training and holdout data, accounting for all samplers and orientations.
No gain, bias, transmission, UV shift, camera or geometry parameter is fitted.

The signed difference of a bit and its complement at the same native pixel
can cancel a fixed additive backdrop under stable positive gain. Stability
of light, alpha, camera and backdrop over each pair is therefore an explicit
native prerequisite, alongside independent camera calibration, source and
neighborhood checks, four dry/liquid controls, background-only exact WGC
payload binding, resource/world restoration and owned ordinary stop.

## Why Native Was Unexecuted

No audited provider can currently prove the sampled texture frame and its
interpolation fraction for each captured PNG independently of UV hypotheses.
MCP documentation describes `GetTextureAtlasUV` as atlas position/size lookup,
not animation frame state; the existing runtime had already reported this
lookup unavailable. A documentation search for texture-frame APIs did not
establish a supported water flipbook phase/mixture getter. These searches do
not prove that no such engine capability exists; they establish that this
experiment lacks a verified usable provider.

The phase plan forbids timing-only labels and UV-candidate phase inference.
It requires independent exact frame order and zero frame interpolation bound
to asset/PNG identities. Uniform reference frames may detect some changes
but cannot label the intervening ten bit identities. The implementation
rejects all evidence kinds except `synthetic_exact_frames` before scoring;
synthetic phase records can never authorize a native analysis.

A counterexample explains this boundary: swap X/Y bit-plane capture order and
assert the old synthetic phase labels. The resulting data fit a transposed UV
perfectly. Another counterexample mixes a bit with its complement at 50%:
the coordinate signal disappears. Using candidate-fit success or elapsed
ticks to claim phase would therefore permit a wrong UV acceptance. No sound
phase mechanism was proven before the 16:10 CST launch cutoff, so native
startup was not attempted and no restoration was needed.

An eventual native continuation needs one reviewed phase/mixture provider,
stable pair controls and a declared treatment of the active backend's
filtering. Installed TexelAA uses UV derivatives; the two current sampler
families remain bounded synthetic models rather than a complete native
filtering proof. The original raw-rank gates/reports are unchanged.

## Verification And Evidence

Nine new tests cover opaque grayscale coding and 1024 unique addresses,
nonuniform gain/background cancellation, incorrect holdout bits, absent or
swapped phase proofs, 50% interpolation, changing background/channel
disagreement, duplicate IDs, center-only mapping alias and changed frozen
geometry. The entire 29-test coordinate suite passes; the new tool and tests
compile. A synthetic replay using all six original geometry sequences selects
`nw/bottom/identity/edges` with nearest sampling and zero contradictions or
ambiguous source bits. Every acceptance field concerning native/production
remains false.

| Property | Minimum Wrong Training Bits | Minimum Wrong Holdout Bits |
| --- | ---: | ---: |
| Region | 1024 | 2048 |
| Vertical Basis | 1460 | 4208 |
| Pixel Mapping | 176 | 740 |

All paths below are relative to the liquid worktree, in the new private
`.runtime/coordinate-bitplanes-r10b-v2/` evidence root. V1 was an earlier
offline freeze and remains preserved; v2 adds strict synthetic CLI checking
of plan/source/marker hashes and exact geometry/control declarations.

| Artifact | SHA256 |
| --- | --- |
| `plan.json` | `acdd6f4482efa728de1d03dec922392146e8065a174cd4d4f925d2a40aaec043` |
| `assets/water_flow_grey.png` | `0f75784a869959c2f075cd48b9dcf49d2f48c28ef59d2e2636600f34612c33cf` |
| `synthetic-input-v1.json` | `5ffdfabbecb2a536e236a6c88627106c90c70c74771b2f8121154ba5b224fb46` |
| `synthetic-analysis-v1.json` | `3a930dc92d7c6dfd4e6c459b286d22f81a8085a0de4d9504f689c2c598de147e` |
| `synthetic-cli-replay-v1.json` | `625c0825752f31b84666230598f232181ada2f423f7613b94aae665f9d7fd1c3` |

The generator/analyzer is `tools/liquid_coordinate_bitplanes.py`, SHA256
`cc05e8ed6a10b08960fedb448100c6bc90a838832708bf4ff603d5287c38e1bf`.
The reviewed synthetic data generator is
`.runtime/run_bitplane_design_r10b.py`, SHA256
`0e33c2dd41416f7a9996a6c7b47a1e9b0dd33838796806c9df7350d03be3a59d`.
The final plan retains exact archive copies of its five host dependencies.
The previous geometry plan and evidence remain external immutable inputs.

Replay with a fresh output path:

```powershell
python tools/liquid_coordinate_bitplanes.py analyze-synthetic --input .runtime/coordinate-bitplanes-r10b-v2/synthetic-input-v1.json --output .runtime/coordinate-bitplanes-r10b-v2/synthetic-cli-replay-v2.json
```

The command verifies the frozen declarations before scoring. Subsequent tool
changes correctly reject this source freeze until a separately reviewed new
plan is created; no archive fallback or native mode is provided here.
