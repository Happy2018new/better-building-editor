# Native Intrinsic Item Glint, R21

Engine: NEMC 3.10.0.420447, Minecraft 1.21.130.0.

The original 89-page census covers 1,907 loaded identifiers at auxiliary zero, representatives of each measured name/texture pair, and every measured auxiliary value 0 through 15 for the seven initial positive families and normal golden apple. The separate restored supplement adds debug_stick auxiliary values 1 through 15. Together these contain 2,835 false/true native UI pairs.

The authoritative classification is strict-analysis/summary.json: 128 positive pairs, 1,605 negative-in-this-probe pairs and 1,102 unresolved pairs. Eight families are positive at every measured auxiliary value 0 through 15: debug_stick, enchanted_book, enchanted_golden_apple, end_crystal, experience_bottle, lodestone_compass, nether_star and written_book. Unknown auxiliary values remain unconfirmed.

The original acquisition reports and bound sampler/analyzer source remain intact. The original residual-only classifier falsely accepted the weak blue animation of double_stone_block_slab2:2. The distinct stricter analyzer recomputes all screenshots, also requires both aggregate R/B and G/B ratios to be within 0.025 of the native glint control, and retains that prismarine alias as unresolved. This is the only changed classification.

The tests use paired SetUiItem false/true controls at a low UI layer. Three same-phase screenshots, actual UI readbacks, exact submitted code, restoration records, capture hashes, catalog bytes and project source manifests are retained. High-layer exploratory captures cannot prove 3D-block negatives.

Native UI behavior does not qualify editor or world rendering. Unresolved items, arbitrary NBT states and unmeasured auxiliary values have not been proven negative. Actual enchantment flags remain separate from intrinsic render glint. Indicator target, location and clock metadata are not read. Metadata-rich authored books still require separate support qualification.

All owned controls were restored and all frozen project bytes remained unchanged. The exact held-process watcher records game exit 0xC0000409 and MCDK exit 0. The game exit was abnormal; this package does not claim a clean shutdown or establish its cause. See exact-process-exit.json.

Verification: python -X utf8 verify_package.py
