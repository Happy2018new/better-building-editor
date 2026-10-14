# NEMC 3.10 Cauldron Runtime Audit

This is an isolated NEMC `3.10.0.420447` / MCBE `1.21.130.0` native audit. It
does not mount the editor behavior or resource pack and does not claim that the
project cauldron overlay is complete.

## Evidence

- `content/result.json` records 60 native interactions and typed NBT readback.
- `project/result.json` records a clean client palette and a successful
  `CombineBlockPaletteToGeometry` plus `AddActorBlockGeometry` submission.
- `custom_color/result.json` records direct typed `CustomColor` writes and
  exact readback.
- `read-final/result.json` records water, lava, and powder-snow
  `fill_level=0..6` states.
- `cauldron-overview.png`, `cauldron-close*.png`, and
  `cauldron-projection*.png` are native captures. They show the vanilla shell,
  liquid levels, lava, powder snow and potion-colored rows; they are not
  editor/full/missing project acceptance images.

## Observed native behavior

- `minecraft:cauldron` accepts water aux `0..6`, lava aux `8..14`, and
  powder-snow aux `16..22`, with all three families mapping to
  `fill_level=0..6`.
- Water, lava, and powder-snow buckets filled a real cauldron through
  `PlayerUseItemToPos` and read back `fill_level=6`.
- Potion IDs `5..46` filled two levels per use and read back the requested
  `PotionId`. IDs `0..4` did not produce a filled potion cauldron in this
  interaction path. Ordinary, splash, and lingering potion types read back as
  `PotionType=0`, `1`, and `2`; IDs `43..46` were included in each form.
- Typed `CustomColor` values `-65536` and `16711680` were accepted by
  `SetBlockEntityData` and returned exactly by `GetBlockEntityData`. This proves
  storage, not the RGB/ARGB channel interpretation used by the renderer.
- Server inventory and world state, client projection actor, camera locks and
  player state were restored. `pixel_acceptance` remains false.

The production implementation should therefore use the native empty shell and
state/NBT decoder, then render a bounded versioned liquid surface for water,
lava, powder snow, potion colors and custom colors. It must not reuse the
full-cell world-liquid mesh for an inset cauldron surface.
