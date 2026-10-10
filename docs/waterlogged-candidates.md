# Waterlogged Candidate Evidence

`reference/waterlogged_candidates/neomega_1.21.120_nemc_3.9.0.401155.json`
is a versioned offline audit, not a runtime capability list. NEMC placement
verification must decide whether each foreground state can coexist with water.
Java property presence alone cannot make that decision.

## Sources

The generator reads the existing `neomega-blocks` Go module without changing it.
Its `preset/preset` contains universal, Java and Bedrock converters. Generator
filenames declare Java 1.21.9 and Bedrock 1.21.120 targets, but the binary has no
self-describing version metadata. Historical Java inputs and downgraded outputs
can coexist. The audit stores the Git revision and SHA-256 of relevant source
files and the binary dictionary.

The supplied preset has 20,810 Java output records and 20,565 Bedrock output
records. None of its Java outputs contains `waterlogged`. Exact reverse queries
with `waterlogged=true` or `waterlogged=false` also return no matches. This
does not mean its blocks cannot contain water; the supplied converter lacks the
evidence needed to infer that capability.

Two existing adjacent repositories provide additional evidence:

- `PowerNukkitX/src/main/resources/block_states.json`: per-state
  `canContainLiquid`. A record is linked to NEMC only when both its name and
  `blockStateHash` match the native dump's name and `network_id` exactly.
- `ViaBedrock/src/main/resources/assets/viabedrock/data/custom/blockstate_mappings.json`:
  explicit Java `waterlogged` properties in Bedrock-to-Java mappings. These are
  candidate evidence and can contain false positives, including double slabs.

Both additional inputs have content hashes and source revisions recorded. The
current ViaBedrock checkout has an unrelated pre-existing config modification,
so its repository dirty flag is true. The mapping file's content hash identifies
the input actually used. No source repository was modified by the generator.

## Current Audit

The NEMC 3.9.0.401155 dump contains 15,858 records and 1,340 names. All 1,320
Bedrock converter names are present. The remaining 20 native names include
`minecraft:micro_block` and 19 editor preview blocks.

The Bedrock capability source contains 14,160 records: 10,761 match the native
dump by name and state hash, and 3,399 do not. Of the matched records, 8,867 have
`canContainLiquid=true`, covering 425 names. States lacking a match remain
unknown. The Java mapping contributes 11,657 records with `waterlogged` out of
15,845 mappings. Together the sources produce 626 candidate names, 625 of which
exist in the NEMC dump; `minecraft:chalkboard` is absent.

There are 34 Java candidates whose complete set of matched native states has
`canContainLiquid=false`. These are explicitly retained in
`java_candidates_rejected_by_all_native_matched_states` for inspection and
native verification. They are not accepted as supported blocks.

## Format

`schema_version` is 1. All name lists and block rows are sorted. Each row retains
native state count and a native example, mapped universal/Java record counts,
Java names, and separate evidence from each source.

- `candidate_names`: union of all Java and Bedrock candidates, including names
  absent from the current native dump.
- `native_candidate_names`: that union restricted to native names.
- `native_capability_candidate_names`: names with at least one exact native
  state hash match having `canContainLiquid=true`.
- `blocks[].native_liquid_aux`: every native aux whose exact state hash match
  has `canContainLiquid=true`. This is a candidate test set, not proof of native
  support or a substitute for semantic states in saved builds.
- `native_capability_matched_count` and `native_capability_rejected_count`:
  coverage and false capability counts per native name.

`waterlogged_true_count` and `waterlogged_false_count` describe the neomega
forward table only. `java_mapping_waterlogged_*_count` separately describe the
ViaBedrock mapping. Detailed forward-table evidence is capped at two wet and
two dry examples; external Java mapping examples are capped at two per name.

## Regeneration

Use Go 1.23 or later and run from the `neomega-blocks` module directory. All
paths below may be absolute; the output must point into the editor repository.

```powershell
go run ../better-building-editor/tools/generate_waterlogged_candidates.go `
  -native ../better-building-editor/docs/reference/block_palettes/nemc_3.9.0.401155.json `
  -bedrock-capabilities ../PowerNukkitX/src/main/resources/block_states.json `
  -java-mappings ../ViaBedrock/src/main/resources/assets/viabedrock/data/custom/blockstate_mappings.json `
  -output ../better-building-editor/docs/reference/waterlogged_candidates/neomega_1.21.120_nemc_3.9.0.401155.json
```

The two additional source flags are optional. Without them the supplied preset
currently produces zero candidates and still records its complete name audit.
For a new MC release, retain the old JSON, regenerate with the new native dump
and source tables, review name/state coverage changes, and perform native
verification for new or changed candidates. Runtime policy must use the
verified result rather than import this candidate JSON automatically.
