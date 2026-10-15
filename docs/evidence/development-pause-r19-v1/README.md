# R19 development pause, 2026-10-15

The user requested a pause because the AI API was unstable. All agents and host
test orchestration are stopped. The two identity-bound Minecraft/MCDK process
pairs are deliberately retained; no game command was executed to create this
snapshot. The scheduled 2026-10-16 07:00 hibernate task is disabled.

`instances.json` contains only process identities, owner/session **paths**,
localhost ports and report metadata. It does not contain session credentials.
The recorded Git HEAD is the checkpoint available when the snapshot was taken,
before this documentation commit. A live process does not establish render
readiness: neither retained game currently exposes a usable enumerated window.

The item side-v6 test did not finish and has four cleanup errors. Its projection,
fixture journal, camera, blueprint and profile must be inspected and restored
before reuse. The front-v6 report has 14 captures and completed without cleanup
errors, but has not had pixel acceptance analysis. Neither grants product
qualification. The raw reports and images remain at their recorded local paths.

Resume only after the user asks to continue. First read the current top section
of [CONVERSATION_HANDOFF.md](../../CONVERSATION_HANDOFF.md), then the sole TODO
[IMPLEMENTATION_GAPS.md](../../IMPLEMENTATION_GAPS.md). Verify session owner,
native process creation identities and window availability before contacting a
retained game. Do not bypass the protected execution guard, reactivate historical
agents, replay old world writes or assume saved `state=ready` is current.
