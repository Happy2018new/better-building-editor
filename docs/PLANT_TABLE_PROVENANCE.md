# Plant Table Provenance

`geometry_palette.prepare_palette` validates generated `plant_proxy_data`
before reading its mushroom/fungus render IDs or native texture alpha heights.
The table schema must be 1; its game version and palette SHA-256 must match
the active `block_registry`. Missing schema, stale version or dump mismatch
raises an explicit regeneration error. This check also precedes the client
bridge's geometry cache and both missing-context preparation routes.

`block_traits.is_snow_coverable` applies the same schema/version/dump guard
before consulting generated snow eligibility. `generate_block_traits.py`
validates native metadata, snow and water source exports against one registry;
the generated file retains their source fingerprints. The boolean editing
allowlist remains the same 29 names and still queries by name.

`block_traits.snow_capability((name, aux))` separately reports `supported`,
`unsupported` or `unknown` for the exact canonical state under the same guard.
The generated `SNOW_SUPPORTED_AUX` table comes from the 232 immediate/delayed
layered readbacks in `native_snow_states_nemc_3.9.0.401155.json`: 29 states at
eight snow heights. `SNOW_UNSUPPORTED_AUX` comes from the eight verified lower
states in `native_paired_snow_nemc_3.9.0.401155.json`, where `SetSnowBlock`
returned false and the complete supported lower/upper fixture stayed unchanged.
Both observation sources retain generated SHA-256 fingerprints. These statuses
describe eligibility within those recorded fixtures, not visual acceptance or
behavior in every context.
The positive-source validator also checks the completed/restored probe state,
recorded cold biome, support materials and delayed-readback interval.

The original 148-name seed export contains API-return booleans without state
readbacks; its 119 negative names do not become observed negative states.
An unmeasured name, invalid or unmeasured aux, paired upper half, and unmeasured
crop growth state report `unknown`. In particular, the paired pitcher-crop
negative applies only to measured lower aux 14, not its default aux or upper
half. The query does not change editing, rendering or production plant defaults.
Aux values must be integers; booleans and floats cannot alias measured states.

The four static plant proxies come from the versioned
`tools/data/static_plant_sources_nemc_3.9.0.401155.json` snapshot and
`generate_static_plant_proxies.py`. Native texture identities, alpha bounds,
template and evidence are checked by the generator. Grass/fern and leaf
proxy mappings in `geometry_palette.py`, together with their existing models,
are hand-authored approximations, not dump-generated plant mesh tables. They
do not acquire native mesh or random-offset authority from the generated
table's provenance metadata.

The generated table also retains the native source manifest hash and
`STATIC_PLANT_ACCEPTANCE`, with a separate acceptance schema. Each material
records the hashed original acceptance manifest, runtime version, fixed
native target, measured views, snow heights and independent controls.
Brown/red mushrooms retain only the public shape-comparison view; the R7
right/tilted camera calibration does not accept mushroom shapes at those
views. Crimson/warped fungus retain public/right. The generator rejects a
changed acceptance manifest before emitting these records. All four records
explicitly deny acceptance at other positions or versions and deny native
mesh or random-offset authority. These records describe evidence limits;
they do not disable the existing approximate rendering outside those limits.

Runtime metadata matching is a deployment compatibility check, not a new
native pixel acceptance. It neither verifies installed resource bytes nor
proves engine behavior for another game version, cell or view. Version
upgrades still require source diff, regeneration, offline checks and targeted
native smoke tests. Existing geometry, offsets, biome presets and fixed
plant acceptance scopes remain unchanged.
