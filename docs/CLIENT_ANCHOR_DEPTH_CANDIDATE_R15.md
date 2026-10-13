# Ordinary entity PaperDoll depth candidate R15

R14 visibly renders the native sword on the custom client anchor in the world and renders no sword on the same anchor's UI PaperDoll. Its primary score stays `invalid_controls`; the route observation motivates a changed UI submission experiment. This candidate changes the custom entity's UI `render_depth` from the player value `-50` to the documented ordinary entity value `-15`. It does not claim the change fixes the blank result.

MCP `minecraft_docs` searches on 2026-10-13 confirmed these official contracts:

- `api RenderEntity`: `entity_id` and `entity_identifier` are alternatives, and ID takes priority when both are present. The default depth is `-50` for players and `-15` for ordinary entities. The documentation explicitly says depth can solve UI occlusion/culling.
- `netease 纸娃娃`: wrong model size uses UI size or scale; model clipping uses `render_depth` or UI layer. The required renderer is `netease_paper_doll_renderer`.
- `api GetModelId`: this is a skeleton-model ID and returns `-1` for failure or absence. It must be read after a delay. It does not establish that all Bedrock entity draws must expose a skeleton model.
- `api BindItemToMinecraftModel`: client-created entities require `isClientEntity=True`; root is the default bone; attachment offset is foot-relative and rotation is in ZYX order.
- `api CreateClientEntity`: the documented creation API supports client entities and removes them at dimension changes or game exit.

The loaded anchor already has a tiny transparent cube, root bone and large `visible_bounds` of `192 × 192` offset by `[0,32,0]`. Pyreact maps entity props to the documented API names correctly. R13/R14 use scale `0.35`, zero initial rotations and depth `-50`. Positive player V4 uses scale `1`, initial Y rotation `60` and player depth `-50`. Different bounds, source entity type and UI culling are still hypotheses; this candidate changes only depth between sword controls.

The [offline preparer](../tools/prepare_client_anchor_depth_candidate_r15.py) adapts the archived, reviewed R14 snippets, validates all 164 original archive hashes and original plan digest, allocates a fresh nonce and creates an immutable 20-file bundle. It calls no game SDK, MCP, input, capture or process-start function. The plan pins the complete preparer bytes, source provenance, exact plain item bytes and generated programs. Its verification rejects modifications to any generated program or source.

Every capture uses the same visible owned page and the same PaperDoll at the same layout. The sequence is finite, with two original frames per state:

| State | Submission | Native item |
| --- | --- | --- |
| `ui_cow_positive` | `entity_identifier='minecraft:cow'`, depth `-15`, Y `60` | None |
| `ui_empty` | Exact owned anchor ID, depth `-15`, zero rotations | None |
| `ui_plain_depth15` | Exact owned anchor ID, depth `-15` | Bind one plain sword once |
| `ui_plain_depth50` | Same anchor ID, depth `-50` | Retain exact binding |
| `ui_plain_depth15_repeat` | Same anchor ID, depth `-15` | Retain exact binding |
| `ui_empty_restored` | Same anchor ID, depth `-15` | Remove exact binding once |
| `ui_cow_positive_restored` | Same cow identifier params as first state | None |

Identifier controls explicitly remove `entity_id` to avoid its documented priority. Their geometry is only a renderer positive control; they cannot carry the owned sword binding. They introduce no cow actor into the world. The sword controls retain scale `0.35`, zero initial rotations, zero attachment offset/rotation, unit item scale and root bone. The item dictionary remains byte-identical to the R14 ordinary item input, with original tag state untouched.

The candidate retains R14 exact ownership checks, attachment readbacks, delayed model-ID reads and owned actor destruction/absence verification. It performs no camera, player, world, inventory, resource or shader mutation. The page remains visible for every capture, so no HUD lifecycle change enters its predeclared UI ROI `[0,111,1994,1105]`. WGC must retain physical size `1994 × 1105`; unchanged V4 corner calibration and training/holdout gates remain required.

A release-ready owner must gate execution as follows. First verify session, process creation identities, token, background-only guards and current source/config snapshots. Capture the first cow state and require a visible cow with stable model pixels and passing corner markers before binding the sword. If cow is blank, stop the sword route and restore immediately; the page/renderer control failed. Capture all three sword states without rebinding. Compare both `-15` states to both empty states, with the unchanged 25-channel threshold and 80-pixel minimum. Require the removed empty UI state to match the original empty state. Require the final cow to recover. A `-15` positive / `-50` negative / `-15` repeat positive supports a depth-specific repair; both depths positive identifies another lifecycle difference; both blank leaves custom entity eligibility/bounds unresolved. No result accepts production rendering or glint.

The owner needs a 90-second normal deadline, cleanup by 120 seconds, 150-second outer supervisor, bounded real HTTP reads, one native attempt, no automatic retries, and write-ahead journaling of every mutation. It must preserve unsuccessful states and raw errors, run independent post-cleanup health, inspect every original PNG and archive every original byte. A new background instance is outside this bundle and still needs a separate reviewed launch plan, because the prior recorded game and MCDK identities are no longer alive and another task owns current WGC capacity.

At this preparation stage `sdk_dispatch_authorized=false` and `owner_runner_ready=false`. The bundle is concrete and reviewable, but no SDK dispatch occurred. Production, editor content, shared depth and enchantment glint remain false. A depth-positive ordinary item is only the prerequisite for the original bounded body/item shared-depth experiment, then real enchantment temporal pixels and existing production ownership gates.

Validation: five fake-native execution tests passed, exercising the generated programs through one binding, a `-15/-50/-15` transition, exact removal, wrong nonce, rejected binding, refusal to replay uncertain removal and generated-file tamper detection. The Mod Python reviewer does not select CPython `tools/` files (`files=0`, not counted as review); the 17 generated game snippets were copied to a temporary review fixture with an explicit `modMain.py`, and its actual `files=18` review parsed all 18 without findings. No fixture or review file was deployed.

Prepared bundle: `.runtime/client-anchor-depth-r15-v1`, plan digest `533521976e014d1c7606010060c2ad111e40aac8b3f1dcea64cd8f58a720e55a`. The source and tests are committed; the immutable run bundle stays outside production resources.
