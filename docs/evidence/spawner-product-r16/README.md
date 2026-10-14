# Spawner Configuration Markers, Round 16

Qualified for NEMC `3.10.0.420447` only. Ordinary and trial spawners retain
their native shell. A white hollow marker means an explicitly empty spawn
configuration, green means a configured entity, and a rotated yellow marker
means the supplied data is insufficient. These are render-only markers; saved
cells, typed NBT, export data and inventories never contain marker blocks.

The source samples in `tools/data/spawner_configuration_nemc_3.10.0.420447.json`
come from native block placement and spawn-egg interaction. Configuration is
decoded from those measured fields, not inferred from currently spawned mobs.
Custom entity identifiers are accepted as configured entities. Unsupported or
partial payloads remain unknown rather than being reported as empty.

The public `test.entities.spawners` blueprint is available in the normal test
blueprint page. The host probe extracts its unchanged source cell, typed NBT
and support into a focused document. The reviewed matrix covers ordinary and
trial spawners, each empty/configured/unknown, in editor, full projection and
missing projection. Editor hiding, section and restoration, plus actual-world
occupation and restoration in missing projection, are included.

`candidate/report.json` contains 72 captures, including matched native-shell
controls. `default/report.json` contains 54 captures from the default session
profile in a fresh game. Both runs completed and restored their fixtures.
Their capture receipts and review sheets are retained here. Original PNGs are
preserved locally in `.runtime/spawner-product-r16-submitted-raw`, with the
original runtime captures also remaining in `.runtime/spawner-product-r16`.
This compact committed record is not an independent raw-pixel replay bundle;
the qualification and receipts retain original PNG fingerprints. The schema-3
analyses require 36 focused badge differences and 12 retained-support checks
per run. Negative tests reject animated terrain, incorrect marker colors and
blank hidden scenes. The nine default review sheets were inspected directly.

An earlier default run, retained locally at
`.runtime/spawner-product-r16/default-v1.json`, had one blank hidden-layer
frame despite a structurally ready model. It is not acceptance evidence.
A new cold start, including delayed captures without resubmitting the model,
and the complete replacement default matrix passed without runtime changes.
This narrows the observed failure but does not establish a native GPU fence;
the broader asynchronous preview limitation remains documented separately.

`qualification.json` binds the resource contract, implementation bytes and
capture hashes. Gate metadata is excluded from implementation hashes so an
isolated candidate can be admitted and then tested through default startup
without changing the renderer. Re-run qualification after relevant rendering
changes or engine upgrades. This evidence does not qualify creature models,
particles, spawning behavior, every trial-spawner gameplay state or mobile
hardware.
