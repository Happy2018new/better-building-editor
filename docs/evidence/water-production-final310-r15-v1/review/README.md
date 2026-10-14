# Water Review Set

This compact review includes contacts, measured results, launch hash manifests
and outcome summaries. It intentionally omits full source ZIPs, raw screenshots
and temporal-burst frames. `index.json` hashes all 13 generated payloads and
identifies the retained original captures, receipts, reports and source ZIPs.
This explanatory README and the index itself are not included in that payload
hash list. No original capture or failed analysis is overwritten.

## Read First

- `alpha-contact.png`: fixed alpha 0/0.25/0.45/0.75/1/default in all three paths.
- `body-contact.png`: submerged fence and rear gold contribution controls.
- `biome-contact.png`: plains/swamp/mangrove with unchanged geometry and source.
- `pure-water-contact.png`: pure editor water, four projected cells, one occupied
  virtual cell hidden, and four virtual cells restored after clearing.
- `alpha-analysis.json`, `direction-analysis.json`, `biome-analysis.json`: final
  visible measurements and their negative-control results.
- `pure-geometry-analysis.json`: nine source/low/pool wet/dry pairs, all pass.
- `outcome.json`: completion, restoration, source stability, session identities
  and pure-water occupancy publication values.

The initial 80%-of-all-pixels biome metric remains in
`biome-initial-80pct-analysis.json`; its rejection is superseded only by the
explicitly documented product contribution rule. Same-color, 2-level-noise and
outside-region negative tests reject unchanged or irrelevant pixels. See the
original biome README for its measured differences and numerical rationale.

## Provenance And Limits

The alpha/direction/pure-water snapshot is `a01f2884026ddd1797baabe3df368b77dae3eec823a5e2ed012bbefcbdc3e5d1`.
The latest multi-owner biome snapshot is `fb2dccac3c3eba6616b7ed8cbb0abdec6e66ee43493fe67e49e7b94af3f1bf38`.
Both are exact NEMC 3.10 live runs with independent same-session calibration.
The later snapshot cold-starts the current root BP/RP; its only post-start
change is the host reader for selecting water from combined projection owners.

All actual captures remain locally available at the paths in the index. Full
numerical replay requires those raw inputs; this compact set alone is not a
standalone replay archive. Original reports, receipts, PNGs and source ZIPs
are retained and hashed rather than silently replaced by thumbnails.

The current acceptance still has these explicit coverage limits:

- All live tests install the candidate profile explicitly. A cold startup with
  production qualification enabled by default has not been tested here.
- Side-face UV continuity across adjacent blocks has no new quantitative
  acceptance in this round. These results do not claim it is broken or passed.
- Final world motion checks cover eastward and falling water; other cardinal
  world checks are historical. The post-native-removal editor checks cover all
  four horizontal directions and falling, individually, in a restored partial
  batch whose failed world capture remains excluded from overall acceptance.
- This is declared product-style acceptance, not exact vanilla texture, RGB or
  future-version parity. Enabling production remains the root integration task.

No new game was started after the biome instance was restored and stopped.
