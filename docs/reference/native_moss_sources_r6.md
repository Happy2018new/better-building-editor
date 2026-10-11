# Native Moss Sources, Round Six

The current sources establish every native state and the texture assets, but do
not establish a native moss mesh or its UV mapping. No production proxy has been
accepted. Existing carpet and hanging-moss pixel failures remain failures.

## Version And State Source

The bounded SDK probe reported `1.21.120.0` on both client and server. Its managed
executable was `MinecraftPE_Netease/3.9.0.401155/Minecraft.Windows.exe`; the owner
and loaded project remained `p0-entities-r6-isolation` and `p0-entities-r4`.

`docs/reference/block_palettes/nemc_3.9.0.401155.json` is the authoritative native
dump. SHA-256: `6b2d9e961e934a745f5ab30d697cf22fb463fd3792d371a6dd42cb4342062f01`.
`tools/data/block_registry_manifest.json` points to that file, and
`block_registry_data.py` embeds the same source fingerprint. Offline comparison
decoded each generated moss record and compared its aux and typed states directly
with the dump. All records match; no aux arithmetic or alias replacement was used.

| Native Name | Canonical States | Properties |
| --- | --- | --- |
| `minecraft:pale_moss_carpet` | 162, aux 0 through 341 with gaps | Four cardinal `pale_moss_carpet_side_*` values, each `none`, `short`, or `tall`; `upper_block_bit` is a byte boolean |
| `minecraft:pale_hanging_moss` | 2, aux 0 and 1 | `tip` is a byte boolean |

The carpet dump covers all `3^4 * 2` property combinations. This proves state
enumeration only. The probe observed carpet aux 0 and 8 and both hanging aux
values; it did not measure every carpet state's Clip or its visible faces.

## Installed Texture Assets

Matching-install sources are under
`D:/MCStudioDownload/game/MinecraftPE_Netease/3.9.0.401155/data/resource_packs/vanilla`.
`blocks.json` uses format `1.21.40` and binds carpet to `pale_moss_block`, with
`carried_textures` set to `pale_moss_carpet_side`. It binds hanging moss to
`pale_hanging_moss`. `textures/terrain_texture.json` maps these atlas keys to:

| PNG Under `textures/blocks/` | SHA-256 |
| --- | --- |
| `pale_moss_block.png` | `d42269319e529043472f214e1a7a76ff5ddbe578ed4ac81864f0a7ed6f7b4812` |
| `pale_moss_carpet_side_base.png` | `bb4b3313d3a13c02c9655bae0786f3ca1b1e7164172b3d53ca4022984b40353a` |
| `pale_moss_carpet_side_tip.png` | `76442ac3d0736ddc959549d35c47be66f99fd92c7be7737728e10a4ba5ea71bf` |
| `pale_hanging_moss_middle.png` | `b8b73cb7c973d2137987c7edbdaa39c7999882bac8572fe5a8b21ab9bdb277be` |
| `pale_hanging_moss_tip.png` | `78ef7d80518eb200f140f06ad02744e9d8bb5012a3e6e5c0e755f9c88027119c` |

All five PNGs are 16 by 16 RGBA. Their texture-set files describe color and
material channels, without face coordinates or UV rules. The images were viewed
in a nearest-neighbor texture sheet; their alpha boundaries were not used to
infer mesh dimensions. `blocks.json` SHA-256 is
`cb3aad2d0d012bfb63a462ec9a5d8af54128c8afc26d74ac6f4ae074c9d50faa`;
`terrain_texture.json` SHA-256 is
`9ce3e389999a7aff19968a60fd21dad1811cf63ec3edd6afac0af0df649e212c`.

The installed vanilla `contents.json` lists moss textures, material channels and
sounds. A content search of all 11,213 JSON files under installed resource-pack
`models` directories, including 36 experimental block models, found no exact
`pale_moss_carpet` or `pale_hanging_moss` reference. This bounded search does not
claim to inspect the engine's native renderer implementation.

The installed behavior feature `pale_hanging_moss_feature.json` describes a
downward chain and a head with `tip: true`. It provides no render geometry.
MCP asset results agree with the local atlas bindings. MCP API keyword searches
for `GetBlockGeometry`, `GetVertices`, and `GetBlockRenderShape` found no result.
`ChangeBlockTextures` is documented for ordinary square blocks without special
rendering; it does not provide a verified moss mesh export or replacement.

## Native Box Evidence

Five saved observations contain all nine source cells and seven stone controls:
immediate server setup, client/server first read, and client/server later read.
Original names, aux, typed semantic states and boxes agree across these reads.

| State | Clip in Cell Coordinates | Default Collision |
| --- | --- | --- |
| Carpet aux 0, all sides `none`, lower cell | `(0,0,0)` to `(1,1/16,1)` | Same bounds |
| Carpet aux 8, east `short`, lower cell | `(0,0,0)` to `(1,10/16,1)` | `(0,0,0)` to `(1,1/16,1)` |
| Hanging aux 0, `tip: false` | `(0,0,0)` to `(1,1,1)` | Absolute zero box at world origin |
| Hanging aux 1, `tip: true` | `(0,1/8,0)` to `(1,1,1)` | Absolute zero box at world origin |

`GetBlockCollision(..., True)` returned `{"collision": []}` for every source
and stone control in every read. The stone controls have valid default unit
boxes, so the empty envelopes are uninformative for mesh shape and cannot be
counted as negative render evidence.

The initial host validator rejected that native envelope after saving all five
observations. Its original report remains `completed: false`; the corrected
offline parser reports successful evidence verification without replaying world
placement. Cleanup verified all 78 reserved cells as AIR on server and client.
An independent audit found all 20 markers clear on each side, with player and
camera exactly unchanged. The instance was returned before offline research.
`tools/data/native_moss_boxes_r6.json` records the normalized results and hashes.
The frozen pixel comparison settings remain threshold 16 and minimum 80 pixels.

## Production Blocker

Missing facts are native face coordinates and thickness, plane orientation,
double-sided behavior, the mapping of side/base/tip textures and UVs for each
state, upper-cell behavior, and neighbor-dependent face culling. AABBs and texture
alpha do not determine these facts. Copying a fern cross model or constructing a
box from Clip would add an unverified visible approximation.

Once a matching native mesh source or independently verified mesh extraction is
available, the existing `block_registry.aux_values` and `states` APIs can enumerate
every canonical state for generation. `geometry_palette._proxy_foreground` is
the existing render-only substitution point; it leaves document/world identities
intact. Any future candidate must preserve original states and pass independent
editor, full projection, dynamic occupancy and initial occupancy pixel acceptance.

Full state/source audit: `.runtime/moss-native-sources-r6.json`, SHA-256
`9cbd119bdb53712fc5c8a2d8992c49f0e82d8e2cb45cd3979540096217a9d2b6`.
Texture review sheet: `.runtime/moss-native-textures-r6.png`, SHA-256
`03ecb3818d40e8c2e1085ed0d81b07c273e0dbd89e78bb4edcb540bdb97e2000`.
