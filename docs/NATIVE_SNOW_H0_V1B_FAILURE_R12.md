# Original H0 V1B First Attempt

The one authorized original-texture cold start completed at 2026-10-13
08:52:29 Asia/Shanghai after 94.653 seconds. Native and projection h0 pixels
remain unobserved. There was no automatic replay or relaunch; the alpha
condition was not released or run.

Executed plan SHA256 was
`7c40ca997c887940128de002e312bb6ee6028b984b7ae745b153a22d44ce4b16`.
Session was `488a64a8deca487dadf6956fcbc80c0e`, owner `snow-r12-h0-native`.
Game PID 64132 had creation identity `134363262623458150`; MCDK PID 10564
had identity `134363262621583841`. The launcher finished at parent T82.479
with exit code 0 and `ready=true`.

The first scheduled image was black and retained. The first post-SDK-ready
image passed owned identity, fresh native WGC, physical 1994x1105 dimensions,
before/after ready-manifest, TCP-pair and nonblank checks. It was opened and
visually inspected: it still showed the Minecraft loading overlay. The
wrapper's `first_post_ready_passed=true` describes those machine checks;
it does not establish the required actual world-frame prerequisite. That
prerequisite is false for this attempt and the original image is preserved.

The phase's one-time server preflight successfully read loaded air in both
front and extra layers at fixed `(6,117,6)` and support `(6,116,6)`, dimension
0. Player foot was `(0.5,-60,0.5)`, flight false. The next client command
failed in the existing `CLIENT` prefix with `Workspace is not initialized`;
the modern-projection session had not yet been initialized by UiInitFinished.
No `INSTALL_PROBE` body, native fixture setup, camera mutation or state
capture executed. The phase contains zero native/projection rows.

The recorded `mutation_attempted=true` is an intent flag set before sending
INSTALL_PROBE. It does not prove that mutation ran: the prefix assertion
failed before the probe body. Server cleanup found no saved fixture and
returned an empty list. Client cleanup used the same unavailable prefix and
failed again; this diagnostic cleanup error remains in both raw receipts.

The parent still attempted normal close, then terminated only the same
verified owned game/MCDK identities. Final alive/mismatch lists were empty,
both were independently found absent after cleanup, and the 240-second
deadline was not exceeded. Both scripts and config match all three original
backup hashes, own flower-override absence is restored, original native
texture is unchanged, and all 1432 BP/RP files exactly match the pre-run
inventory. Process/host-byte cleanup success is separate from the retained
client cleanup error and failed pixel diagnostic.

Archive `tools/data/snow-h0-native-r12-v1b-failure` contains 92 original
copies of run receipts/captures/handle samples/backups, final historical
manifest/logs/config/world pack references, the exact v1b freeze and pinned
inputs. The generated post-cleanup verification records the loading-frame
finding explicitly. Originals remain intact.

- Archive index SHA256:
  `b7cffc0ebca587c3ce23559eb45084559c6cc1b8c2bdfa466f6172857749b826`.
- Post-cleanup verification SHA256:
  `cf6970a245fdcc34e582e4d6d8288cbec479033f878bfc4cc568983287d6a84d`.

A subsequent control needs a separately frozen semantic readiness gate for
the actual modern-projection client session before selecting its one
post-ready capture. That gate must stay finite, preserve this original
failure, and stop without a new matrix if its first selected frame fails.
This report grants no plant/alpha/snow/offset/position or resource acceptance.
