# World Liquid Anchor Recovery

## Reproduced Failure

`WorldLiquidRenderer.follow` moves owned active and staging free models when
the world anchor changes. Previously, it recorded a model only after a
successful `SetFreeModelPos` and updated that model's anchor cache immediately.
A native setter that changed the position before returning false left the
failed model outside rollback. A setter that changed the position before
raising escaped the rollback path. Earlier successful models could already
advertise the target anchor while the remaining models retained the old one.

The focused host regression reproduced these failures before the change.
It also reproduced stationary requests skipping a refused restoration because
the old anchor caches already matched, and repeated close failing to retry
the native removal of a still-owned retired model.

## Scoped Contract

The existing world liquid owner records each attempted position write before
calling the native setter. The journal stores the record and its previous
anchor. Neither record anchor caches nor the global anchor is published until
every attempted write succeeds. A false result or supported adapter exception
restores attempted records in reverse order, including the failing record.
Recovery forces the native setter regardless of the cached anchor. A refused
recovery entry stays in the owner journal; exceptions and refused identities
remain available in diagnostics.

`follow`, `advance`, visibility and opacity controls, publication preparation,
preparation cancellation, and a new `begin` attempt position recovery before
continuing. An identical stationary anchor can therefore repair native state.
The shared `restore_publication` entry attempts visibility recovery and
position recovery independently, and reports success only when both journals
are empty. Position recovery clears only its own move/recovery error strings.

Retired records are never part of an anchor move. Their existing allocation
ownership remains intact until native removal is confirmed. Confirmed removal
prunes position entries for that exact model ID. A closed owner never replays
position setters; failed removals retain the exact retired ID and journal.
Second and later `close` calls retry native removal and release the retained
entries after confirmation.

This changes only the world free-model owner. The skeleton/UI owner,
allocation budget, active/staging selection, liquid coordinates, UV payloads,
resources, Scene wiring, and production profile gate retain their existing
contracts. Runtime code remains compatible with Python 2.

## Host Validation

| Focused Suite | Passing Tests |
| --- | ---: |
| `test_liquid_anchor_recovery.py` | 7 |
| `test_liquid_render.py` | 35 |
| `test_projection_pair.py` | 20 |
| `test_liquid_projection.py` | 18 |
| `test_projection_follow_transaction.py` | 13 |
| `test_projection_retirement.py` | 7 |
| `test_liquid_viewport.py` | 25 |

The seven new tests cover first/middle/last active or staging move failures
after native mutation, both false results and exceptions; deferred cache
publication observable inside native calls; reverse restoration including
the failed record; failed restoration retained across stationary requests;
all preparation and control guards; independent visibility/position recovery;
and exact retired ownership across close retries without position replay.

Independent read-only source review found no blocker in the scoped anchor
recovery implementation and tests. Scoped MOD review parsed two matching
files with no findings. `git diff --check` passed. The full integration suite
is owned by the parent task and was not run in this isolated worktree.

No game or native renderer operation was invoked. Mutating host adapters
establish failure-containment behavior; they do not establish native visual
acceptance. The production liquid profile remains disabled.
