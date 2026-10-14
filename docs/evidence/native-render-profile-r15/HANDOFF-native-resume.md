# Native rendering handoff — 2026-10-14 13:45 Asia/Shanghai

Paused immediately at the user's request to preserve context and terminate sessions for a model change. No new tests, shared edits, reloads, or game launches should continue in this chat.

## Ownership and uncommitted work

- Root owns shared production wiring and checkpoint commits. The first qualified profile remains three single chest names in world-only model-local routing plus flower pot in world/editor context routing. Banner/head production defaults have **not** been expanded.
- This agent owns `native_render_profile.py`, `render_context.py`, native tests, own tools/evidence. Neither production file nor `tests/test_native_render_profile.py` was changed after root requested the checkpoint.
- New uncommitted host tool: `tools/audit_native_heads_r15.py`. It binds every runtime call to the supplied instance and owner, uses real inventory placement, checks an empty extra-block palette, journals source-world changes, restores inventory, and captures through background WGC. It does not alter production code.
- New local evidence after root's selected first-subset checkpoint: banner runs 77–89 and head runs 90–95 below. Earlier evidence selection/commit is root-owned.
- Five user-owned untracked `tools/p0_palette*_probe.py` files were not touched.

## Live instance to stop or resume

- Owner: `native-render310-r15`
- Session: `C:/Users/Happy2018new/.pyreact-debug/instances/60695c6595894ffcbe4c9fca5e36be0e/session.json`
- Ordinary independent project copy: `D:/bbe-r15-native-production`
- Game PID: `47968`; creation identity: `134364256401523988`
- MCDK PID: `39864`; port: `51296`
- Engine: `3.10.0.420447`; state was ready; guarded no-activate window, foreground remained ChatGPT.
- Do not stop or touch other owners' instances. If stopping this one, use owner/session-bound `instances.py stop --force`.
- Current game has the raw, unique-name four-head comparison entity (`owner.astra_dynamic`) and a camera aimed at source/projection rows near z20–24. The source-world fixture is still present, journaled on **server** `api._native_head_items`; inventory slot 35 was restored successfully. Real stones/heads are at x0,3,6,9; source head y-56,z20, supports y-57. `audit_native_heads_r15.py restore` restores source journal and removes comparison entity if resuming before shutdown. Do not perform new cleanup testing after the user's stop request without a new continuation.
- Prior failed native addon reload triggered `DisabledSkinScreenController` assertion in a previous owned instance. That instance was stopped; use explicit Python reload in this current instance rather than addon reload.

## Completed banner observations

- `81-banner-raised-full/frame.png`: measured actual-item standing and wall banners both show the correct three colored bands under candidate `model_local` world routing. Wall source fixture was raised to local `(10,2,1)` with support `(10,2,2)` to avoid ordinary y0 support hiding its bottom.
- `84-banner-raised-occupied/frame.png`: both native bodies suppressed correctly under missing-mode occupancy.
- `86-banner-raised-restored/frame.png`: both return with correct bands after restoring air.
- `89-banner-context-negative/frame.png`: packed context produces roughly five displaced/duplicated banners. This route is invalid.
- `79-banner-front/frame.png`: Scene native wall banner's upper fabric is hidden by support, a depth limitation analogous to native chests. No Scene qualification claimed.
- All five images above were actually viewed in the previous continuation.
- Source payload is real item-placed `docs/evidence/r15-solo-runtime/banners-v4/report.json`, stored in `tests/data/native_banner_310_r15.json`. Base4, patterns `bs` color1 and `ts` color14; standing actor direction8, wall direction2.

## Banner direction risk and root's selected next approach

`entity_render.native_actor()` refreshes sign/bed/head fields, but currently returns raw banners unchanged. Existing material transforms can therefore leave stale `bannerDirection` even though material aux/states rotate. Do **not** solve this by upgrading the 3.9 block registry or changing saved actor/NBT data.

Root rejected permanently excluding valid transformed banners. Next continuation should implement a render-only banner actor copy that refreshes `bannerDirection` from the current material's `ground_sign_direction`/`facing_direction`, following `native_sign_actor()` and `_bed_actor()`. Preserve saved payloads and the existing registry contract. Coordinate `entity_render.py` ownership with root before editing. Root also requested that final support not permanently hardcode only bs/ts patterns; current count2 candidate gate is still provisional.

Only after adapter tests and fresh runtime captures should standing/wall banners be considered for production **world-only model_local** routing; Scene remains excluded pending independent depth evidence.

## Genuine item-placed heads — in progress

New host tool `tools/audit_native_heads_r15.py` places `minecraft:piglin_head`, `minecraft:player_head`, `minecraft:skeleton_skull`, and `minecraft:dragon_head` with `PlayerUseItemToPos(support, INVENTORY, 35, 1)` on floor supports. MCP docs for placement, item spawn, Facing.Up and palette capture were checked first.

- `90-head-item-setup/report.json`: source area common blocks were all air and `extra={}`; all four inventory spawns and uses returned true. Readback exact block names, aux1 and facing_direction1. Typed NBT idSkull, Rotation0.0, SkullType255 for all four; inventory restored true.
- `91-head-item-raw`: failed host-tool prefix used an unbound factory global; no comparison was attached. Fixed by binding client factory/level explicitly.
- `92-head-item-raw`: unique-name receipt proxy changed returned geometry name, tripping name equality assertion. Fixed by using the saved underlying real factory for this raw diagnostic, keeping independent unique requested names.
- `93-head-item-raw/report.json`: successful original-palette native Combine and attachment; assert extra remains empty; tagged raw palette recorded. This is raw native evidence, **not production editor acceptance**.
- `94-head-item-camera/report.json`: camera receipt saved.
- `95-head-item-frame/frame.png` plus report: WGC capture and before/after state saved. **This screenshot had NOT been viewed when the user stopped work. No pixel result or head-native support claim is made.**

Next continuation: first view 95 and parse raw actors in 93. If raw native bodies appear, test actual production editor/full/missing using measured route and payload gates; if absent, retain current head fallback and document clean true-item negative evidence. Do not treat old heads-v4 as definitive because it had extra-water contamination.

## Existing qualified first subset

`qualification.json` and `README.md` record the first subset independently, with final screenshots69/71/74/76, negative depth controls56/58, source/runtime hashes at qualification, and 207 scoped tests passed. Root independently viewed69/71/74/76 and ran96 related tests plus MCP native-profile review clean before checkpointing. New unfinished head work must not rewrite those qualification hashes or be described as accepted.
