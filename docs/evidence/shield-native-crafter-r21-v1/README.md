# Native Patterned Shield Through Crafter

NEMC 3.10.0.420447. Owner `shield-r20-v6-crafter`. This batch establishes
authentic native crafting output and its typed item schema. It performs no
rendering comparison, takes no WGC image, and enables no product renderer.

The fixture places a north-facing crafter, a chest at its output, a downward
hopper above it, and a short redstone pulse. The 64-cell guard region was air
before placement. Inputs are placed through the documented hopper container
API; no crafter or target shield NBT is injected. Native NBT is read back.

An oak-log-to-four-oak-planks positive succeeds first. After clearing that
output, an ordinary shield plus a blue aux-4 banner with three ordered
patterns is fed through the same hopper. Before power, the hopper is empty,
the native crafter holds exactly those two items with count one, disabled
slots are zero, and the output chest is empty. Banner `tag.Patterns` retains
`bo:1`, `cr:14`, `mc:11`; the input shield has no Base/Patterns tag.

The native output is one `minecraft:shield`, outer aux 0, durability 336.
`GetContainerItem(..., True).userData` exactly equals the output container's
`Items[0].tag`, including integer-typed `Base=4`, integer-typed `Damage=0`,
and the three ordered typed patterns. `records/authentic-shield.json` retains
both views; `12-server-pulse_on.json` retains the pre-power native input state.
The plain scalar fields originally supplied to the banner have become native
typed NBT before crafting. This is authentic schema evidence, not a guessed
synthetic shield payload.

Sixteen complete execute-code records retain exact source and SHA256. Input,
placement, positive output, target output, resources and restoration are
preserved. All 64 guard cells, inventory, selected slot and player foot
position are restored. Camera, FOV, HUD and workspace remain unchanged.
The frozen BP/RP source closure remains unchanged. The provenance inventory
includes the earlier registry's default-NBT evidence version; live native
states and outputs, rather than that earlier version label, gate this run.

Ordinary stop first timed out. No force or repeated close was used while the
exact process remained live. The read-only observer retained the original
native game/MCDK handles, creation identities and executable paths before the
fixture. It recorded game exit `0xC0000409` and MCDK exit 0. A later ordinary
stop finalized the already exited session as stopped. This is an abnormal
game exit and does not pass lifecycle acceptance. Its cause is unclassified.

Replay offline from the portable package:

```powershell
python host/shield_crafter_verify_r21.py .
```

The verifier checks native input/output correspondence, exact Item.tag/schema,
positive control, restoration, source-code hashes and exact exit evidence.
`manifest.json` binds all package files. No session routing token is included.
Editor/PaperDoll visibility, correct shield item/frame pose and thickness,
blue base and pattern pixel parity, common depth/occlusion, full/missing
projection, opacity and normal lifecycle remain open. Banner item geometry
and its short lower stalk are a separate unfinished route.
