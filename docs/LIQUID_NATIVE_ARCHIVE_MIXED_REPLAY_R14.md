# Mixed liquid archive replay

The normal replay CLI now accepts the original R13 V4b mixed index directly.
It reproduces the original `OBSERVED` result, all pixels and all source/capture
gates without a separately edited index or copied source supplement. The original
UV, transparency, animation and production qualification flags remain false.
This closes the M07 mixed-index CLI compatibility gap recorded in
[the R13 handoff](ROUND13_HANDOFF.md); it does not qualify water rendering.

```powershell
python -X utf8 tools/replay_liquid_native_archive.py `
  --archive docs/evidence/liquid-native-write-r13-v4b `
  --closure archive-index.json `
  --expected native-write-analysis.json `
  --output .runtime/liquid-v4b-replay-fresh.json
```

All 193 original index records are checked for byte count and SHA-256 before
execution. Only the 117 records explicitly carrying a contained Python
`project_relative_path` enter the source closure. Given the original index's
absolute `frozen_project`, the helper derives the original project-reference
alias as `frozen_project + project_relative_path`. The recorded original and
frozen references continue to resolve to the exact same indexed bytes.
Traversal, absolute source paths, non-Python source declarations, duplicate
source paths and conflicting aliases are rejected. Captures and reports are
excluded from imports but remain subject to the original byte checks.

Derived aliases are runtime metadata, not an index rewrite. The replay report
is now schema 2 and contains a schema 1 `source_alias_manifests` entry with the
derivation rule, original index hash and all 117 source bindings. The old
three-archive V2 route and its schema 1 input archives remain supported. Input
schema 1 indexes without `frozen_project` retain the explicit source-list
requirements; undeclared rows cannot silently disappear from a source-only
closure.

Execution still occurs in an isolated `python -I` child, with exact source
bytes materialized in a fresh directory and imports restricted to that frozen
tree. The original geometry-plan references, nine pre-capture source bindings,
scorer bytes and dependency imports are checked. A changed plan and reindexed
plan hash cannot replace the original capture's bound plan hash. Missing
modules never fall back to the current checkout. Result comparison still
permits only the three top-level output filesystem paths to differ.

[The saved replay](evidence/liquid-native-archive-mixed-replay-r14-v1/replay.json)
and [verification record](evidence/liquid-native-archive-mixed-replay-r14-v1/verification.json)
bind the current helper, tests and unchanged original index. Twenty-six host
tests passed, including a cold directory containing only the copied helper and
V4b archive, plus the old V2 cold replay. Checks reject capture-byte changes,
source-newline changes in either direction, hash replacement, alias conflicts,
invalid source paths and missing dependencies. The V4b cold replay actually
imports 46 checked source files and leaves the original index hash
`d43ed2405aa85ce8cc184e39134a41d89a914088672ca1144d9866ecf6cde342`
unchanged.

No Minecraft, SDK or network operation was used. All historical archives,
including the original unsupported-CLI refusal and one-off derived-closure
experiment, remain unmodified. Future versions should add separately indexed
evidence rather than replacing frozen source or accepting revised thresholds.
