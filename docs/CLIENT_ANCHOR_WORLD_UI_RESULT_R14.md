# Client anchor world / PaperDoll discriminator R14

The two original world `plain` pictures visibly contain the bound diamond sword; the two UI `plain` pictures contain only the unchanged corner markers and blank background. This is a useful route observation, while the frozen primary score remains **`invalid_controls`**. Production rendering, editor frame content, shared depth and enchantment glint remain unaccepted.

The one reviewed native attempt completed and restored in 44.73336170002585 seconds with no runtime, cleanup or raw RPC errors. It captured twelve original 1994 × 1105 WGC PNGs, two per state, in this order: `world_empty`, `ui_empty`, `ui_plain`, `world_plain`, `world_empty_restored`, `ui_empty_restored`. The owner created one custom client anchor three metres along the current camera's documented forward ray, bound one ordinary sword to its `root` bone using the Minecraft-model route, and retained the same binding ID `0` across UI and world views. Camera, player foot, world blocks, inventory, resources and shaders were not mutated.

| Frozen measurement | World | UI |
| --- | ---: | ---: |
| Stable plain pixels | 4771 | 0 |
| Empty-restored difference pixels | 66070 | 0 |
| Ordinary candidate threshold | 80 | 80 |
| Empty-restored gate | Failed | Passed |

All UI training and holdout corner markers pass the unchanged one-physical-pixel gate. The prospective ROI `[0, 111, 1994, 1105]` excludes the top debug band and was fixed before capture. It was not narrowed or recalibrated after inspecting images.

The world restoration score fails for concrete reasons visible in the originals. Initial `world_empty` pictures precede opening the probe page and include the normal hotbar and crosshair. Later world pictures retain the probe page with its own root hidden, so the normal HUD remains absent. Animals move across the background. A supplementary connected-component inspection, which is descriptive and does not replace the primary gate, attributes 64142 of the 66070 restoration pixels to the hotbar rectangle `[630, 1007, 1361, 1103]`. The plain difference has a 3746-pixel component at `[952, 417, 988, 590]`, visibly matching the sword, and a separate 1025-pixel cow component at `[1049, 552, 1084, 591]`. Both world `plain` originals show the same sword; all four world empty originals omit it. This supports the observed route distinction without promoting the invalid primary classification to a passed test.

`RenderEntity` returns `true` in all UI states and `GetModelId` remains `-1`. Binding ID `0` reports offset `(0, 0, 0)`, rotation `(0, 0, 0)` and scale `1.0` in both modes. The sword observation shows that the custom anchor and native binding can produce world pixels. UI submission, custom entity eligibility, visibility bounds and culling remain plausible causes for the UI blank; this capture does not distinguish them.

The exact binding was removed once with `SetBindBoneForBindItem(..., '', True)` returning `true`. The owned page was popped, owned actor destroyed and actor absence verified. Document, production profiles, camera, player foot and navigation were restored. The immediate post-restoration health check passed with advancing client/server clocks, the same runtime token and two owned server timer callbacks. Its timestamp is 2026-10-12 19:18 UTC, or 2026-10-13 03:18 Shanghai. At resumption, host status reports both recorded process identities dead despite its saved `ready=true`; no SDK command, new instance or cleanup replay was issued against the stale identities.

The [complete archive index](evidence/client-anchor-world-ui-r14-v1/complete-archive-index.json) covers all 164 original evidence files, 5123461 bytes, including PNGs, capture receipts, every raw RPC/HTTP request, runtime result, health result, source/config snapshots, visual inspection record and offline score. Every archived byte was verified against its original SHA-256. The original artifact index digest is `4ed18bb7f7ecdbf562cd5e0ab83dc3f325ebe5d1c3efd35f733e7cf32648ae40`; the complete archive index digest is `8cc07e41bd847199c9232df09c7d781b07f5e39826406344b55533f6b3899077`.

The frozen probe digest is `df0ef8e095aab50db5dfb073f26bb033ffdea532fdfd5b2b57d5964298de263a`, plan digest `3b9c2a9ea2a11c3d7c136b6c5f7c3b08ab599e93c2ffc5257781965a5fb258df`, owner wrapper digest `430bba6bf5a0883a862242a99d3c6056c693950c82ecc046d0bf4a9a06fb3613` and 127-file source index digest `d1a77a2967be274a160a69b093feb5a996ee6f0584635e840817ab0d1bb9096b`.

The next work is an offline source and official documentation comparison of `RenderEntity` / PaperDoll against the already positive player UI route. Another unchanged blank probe will not resolve the cause. A native attempt needs a concrete changed submission or resource hypothesis, fixed controls and a separate bounded owner plan before execution.
