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

The current Round 18 replacement reports bind the independent book-owner and
water-factory integration to the exact source bytes used during capture.
`candidate/report.json` contains 96 captures, including matched native-shell
controls. `default/report.json` contains 78 captures from the ordinary default
session profile. Both runs completed, restored their fixtures, kept sources
unchanged and reported no cleanup errors. Each matrix includes another capture
0.5 and 1.5 seconds after hiding or sectioning, without resubmitting the model.

The schema-3 analyses pass 36 focused badge differences and 36 retained-support
checks per run. Qualification now verifies the declared case/route/visibility
labels and every delayed frame, rather than accepting a matching count alone.
Negative tests reject substituted cases, unanalyzed delayed frames, animated
terrain, incorrect marker colors and blank hidden scenes. All eight focused
review sheets were inspected directly; the generated review sheets and capture
receipts are also retained here.

Original PNGs remain locally in `.runtime/spawner-owner-r18-candidate-v1`,
`.runtime/spawner-owner-r18-default-v1` and
`.runtime/spawner-product-r18-qualified`. This compact committed record is not
an independent raw-pixel replay bundle; the qualification and receipts retain
the original PNG fingerprints. The previous evidence is backed up in
`.runtime/spawner-product-r16-before-owner-r18`.

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
