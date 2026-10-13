# Item Sprite Native Acceptance, Round 14

Current status: **pending**. No item pixels have been accepted and the
production profile remains disabled. A successful model allocation or an
offline resource check is not treated as visible acceptance.

## First Background Launch

- Source: `cb04f900`, including private item integration `71d0b7c7` and bounded
  high precision glint phase `70586411`.
- Owner: `item-product-r14-v1`; session
  `835b8b01575148c384a47cd385208848`.
- Approved noactivation DLL SHA-256:
  `04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93`.
- MCDK SHA-256:
  `b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9`.
- The game exited before gameplay IPC binding. Managed discovery reported
  `Owned game creation identity changed; refusing to bind`.
- Windows Application Error at 2026-10-13 19:12:28 Asia/Shanghai associates the
  owned PID 35464 with `Minecraft.Windows.exe`, exception `0xc0000005`, offset
  `0x803a90`. Another startup at 19:10:37 reported the same offset; that is a
  clue for shared startup diagnosis, not proof of the root cause.
- No assertion dialog remained after cleanup. The observed foreground stayed
  on the user's application. There was no activation or foreground fallback.
- Exact owned game and MCDK identities were both absent after cleanup. The
  temporary worktree config was removed only after its fingerprint matched.
- Elapsed time: 34.51 seconds. No reliable editor/world pixels were obtained.

Raw evidence is preserved locally under `.runtime/item-product-r14-v1/` and the
managed session directory. The original manifest contains a temporary session
token; do not publish it verbatim. Runner `1ef222af` removes tokens and window
titles from future JSON exports. No automatic identical retry was attempted.

## Remaining Matrix

The public `test.entities.item_contents` blueprint supplies observed native
ordinary, enchanted and empty frame/glow-frame data. The prepared runner checks
actual Scene controls, three temporal compositor frames, editor removal and
undo. A follow-up must separately accept world full/missing filtering, depth,
cutaway, opacity and cleanup. Shelf filled-slot NBT remains unobserved.

Offline integration verification: **184 tests pass**, including 15 item
plan/resource/lifecycle tests and seven joint publication tests. Native failure
does not promote those tests into editor or world rendering acceptance.
