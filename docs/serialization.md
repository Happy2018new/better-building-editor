# Versioned Building Serialization

The current writers store semantic block states, both cell layers, and the complete
typed actor tree. New files resolve native states against the receiver's block
registry instead of assuming that `aux` numbers survive a Minecraft update.

## Versions and Migration

| Surface | Current writer | Accepted earlier versions |
| --- | --- | --- |
| Inline chunk configuration | 6 | Unversioned/sparse 1, chunk 2 and 4 |
| Ordered building packets | 4 | Unversioned/2, 3 |
| Paged archive index | 7 | 3, 5 |
| Archive page wrapper | 1 | Unversioned wrappers for old indexes |
| Clipboard | `MP4` | `MP2`, `MP3` |
| Clipboard segments | `MPS4` | `MPS2`, `MPS3` |
| User preferences | 2 | Unversioned/1 |

Every new semantic header contains `cellVersion: 1`, the source registry's
`version` and `sha256`, and, where chunks are present, `chunkEncoding: 1`.
The paged index and its packet header must agree on registry provenance.
The clipboard prefix and the contained packet version must also agree.

Old formats are read using their original interpretation and upgraded on the next
save/export. Aux-only old files do not record their historical registry, so they
cannot retrospectively recover a state if its aux meaning changed before import.
No additional game permission or inventory-reading channel is introduced by the
serialization format. Actor capture and world placement are separate concerns.

## Materials and Cells

The shared `materials` table contains one of these rows:

```json
["minecraft:oak_stairs", {"upside_down_bit": false, "weirdo_direction": 0}]
["minecraft:spruce_log", {"pillar_axis": "x"}, ["minecraft:log", 5]]
["example:custom_block", 17]
```

Native materials always use a canonical name and the complete exported state
dictionary. The optional third field preserves an old alias only if that alias's
current aux value still resolves to the exact semantic state. A stale alias hint
is discarded. Custom blocks without registry entries retain their opaque aux
pair. Native materials represented by an aux-only row are rejected in new data.

A cell palette references this shared material table:

```json
0
[1, 2]
[1, 0, ["dict", [[["text", "example"], ["int", "7"]]]]]
```

An integer is a foreground material with empty background and no actor. Two
integers preserve foreground/background layers. A third field stores the tagged
immutable actor tree used by `cell.py`, retaining bytes, Unicode text, large
integers, booleans, floats, lists, tuples, typed NBT wrappers, and nested dictionaries.
All actor keys are retained, including the versioned render/NBT envelope and an
explicitly empty `render` dictionary. The serializer does not derive actor fields
from visible geometry or discard inventory data.

Multiple source palette rows can resolve to one current cell after an upgrade.
The reader merges those cells and remaps every original chunk index. This avoids
rejecting a valid migration merely because aliases have converged. Missing native
states instead produce an error identifying the block, state dictionary, and
source registry version. No partially decoded document is published.

Unknown semantic library entries stay in the library until they can be adapted.
Library initialization retains the original legacy document data and does not
force a semantic rewrite. A legacy native aux value absent from the current table
can still be loaded using the old contract; exporting it as a new semantic file
requires adapting that state first. Unresolved legacy preference pairs are also
preserved when unrelated settings change.
Unknown preference palettes remain unchanged when unrelated settings are saved;
an intentional palette edit replaces them with the current semantic version.

## Chunk Encoding

A uniform occupied 16-cubed chunk remains a single cell-palette ID. Mixed chunks
use one of these payload prefixes, followed by Base64 of a zlib-level-6 stream:

| Prefix | Decompressed payload |
| --- | --- |
| `1u:` | 4,096 little-endian uint16 cell IDs |
| `1p:` | Local uint16 palette, exact bit width, tightly packed local indices |
| `1r:` | Little-endian uint16 `(run_length, cell_id)` pairs |
| `1s:` | Nonzero count and uint16 `(cell_index, cell_id)` pairs |

The writer compresses all four candidates and chooses the smallest actual byte
count, with a stable mode tie-break. A local palette alone can increase size when
each block has a distinct actor, which is why uint16, sparse, and RLE remain
available. Coordinate order is unchanged from the existing chunk store.

Inflation is bounded to 16,386 bytes. Readers validate exact lengths, bit widths,
IDs, local palette uniqueness, RLE totals, sparse positions, canonical Base64,
and a terminated stream sentinel. Truncated streams, trailing data, and oversized
inflation are rejected before they can publish a draft.

## Limits and Fragmentation

Packet order is `begin`, `materials`, `palette`/`palette_part`, `chunks`, `end`.
The entire shared material table must arrive before a cell palette or its first
fragment. Material/palette packets contain at most 64 rows; palette batches target
12,000 JSON characters. A large actor is split into `palette_part` packets and
reassembled before decoding that cell. Chunks are limited by their document bounds
and by a 16,000-character packet budget.

Clipboard text is capped at 8 MiB, inflated records at 16 MiB, and each record at
32 KiB. `MP4` permits 8,192 records; older clipboard readers retain the 2,048-record
limit. The encoder enforces the same record limit as its reader. Archive indexes
permit at most 1,024 pages of eight packets. An oversized save does not publish an
index that its own reader would reject. Partial archive pages may remain unreferenced
after cancellation or failure, as in the existing archive workflow.

Capacity failures are explicit; inventory/NBT is never silently shortened to fit
clipboard limits. The raw actor budget is 4 MiB in `cell.py`, with depth 64 and
65,536 tree nodes. The encoded per-cell budget is 24 MiB in `transfer.py` to allow
JSON Unicode escaping and tagged-tree overhead. Local/network fragments can
therefore carry a large cell even when clipboard export exceeds its total limit.

## Comparison With Bedrock Disk Encoding

The reference implementation is `bedrock-world-operator/chunk/encoding.go`,
`chunk/encode.go`, and `chunk/palette.go`. Its disk format stores semantic
`{name, states, version}` NBT, subchunk block layers, local palettes, and indices
padded into 32-bit words with widths 0/1/2/3/4/5/6/8/16. The editor adopts semantic
states and local palettes, then adds a shared document material table and an
adaptive layout for its JSON/clipboard transport.

`tools/benchmark_chunk_encoding.py` compares actual old/new editor config JSON and
clipboard output. Its `disk_padded` candidate uses the same local global-ID palette
references as the editor candidates to isolate bit packing. It is not a complete
BWO NBT disk archive, so this benchmark does not establish that either complete
storage format is smaller than the other.

Observed on Windows CPython 3.13.13 with the committed deterministic fixtures:

| 16-cubed fixture | Chosen layout | Old/new config bytes | Old/new share characters |
| --- | --- | ---: | ---: |
| Uniform stone | Integer | 181 / 354 | 269 / 429 |
| 62 sparse cells | RLE | 386 / 455 | 401 / 509 |
| Regular four materials | Tight palette | 329 / 450 | 397 / 497 |
| Random sixteen materials | Tight palette | 4,561 / 3,577 | 4,505 / 3,501 |
| 4,096 distinct chest actors | RLE | 881,392 / 724,174 | 39,913 / 35,881 |

For the sparse fixture, zlib6 candidate sizes are uint16 97, tight palette 70,
RLE 31, sparse 212, and controlled disk-padded 89 bytes. Random sixteen materials
produce 2,964 / 2,094 / 3,400 / 9,313 / 2,094 bytes in the same order. Distinct
actors produce 7,053 / 13,629 / 5,695 / 5,836 / 7,167 bytes.

Semantic provenance adds about 100-170 characters to tiny/simple examples. Random
sixteen-material clipboard output shrinks about 22.3%; distinct-actor output
shrinks about 10.1%, and its config JSON about 17.8%. Not every building becomes
smaller. This overhead buys interpretable states and layers across registry
updates, while adaptive chunks avoid a large penalty on unique actors.

The same host run measured mixed-chunk encoding at about 0.9-4.0 ms and decoding
at 0.08-1.12 ms per chunk. These are host Python 3 timings, not embedded Python 2.7
or mobile measurements. Runtime modules and the benchmark remain Python-2-compatible;
game acceptance must separately check actual frame scheduling and native config IO.

## Validation

`tests/test_semantic_serialization.py` checks all exported materials, simulated
aux renumbering on both layers, alias proof, duplicate-palette remapping, every
chunk layout and bit width, bounded malformed payloads, fragmented typed inventory,
more than 2,048 valid share records, unresolved configuration retention, and archive
capacity. Existing complete-cell tests retain explicit old-format fixtures for
configs, packets, archives, and clipboard exports.

Run the complete offline suite with `python -X utf8 -m unittest discover -s tests`
and reproduce host size comparisons with `python -X utf8 tools/benchmark_chunk_encoding.py`.
