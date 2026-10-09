"""Compare index-only Bedrock packing and Cell JSON; palette JSON is a surrogate."""
import base64
import json
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import codec, transfer
from projection.block_registry import states
from projection.cell import Cell, encode as encode_cell, make_cell
from projection.model import AIR, Document
from projection.storage import CELLS, IntegerBuffer


WIDTHS = (0, 1, 2, 3, 4, 5, 6, 8, 16)


def positions(values):
    return dict((((i & 15), (i >> 8), ((i >> 4) & 15)), value)
                for i, value in enumerate(values) if value != AIR)


def packed_indices(values, width):
    if not width:
        return b''
    per_word = 32 // width
    mask = (1 << width) - 1
    words = [0] * ((len(values) + per_word - 1) // per_word)
    for index, value in enumerate(values):
        if value > mask:
            raise ValueError('palette index does not fit selected width')
        words[index // per_word] |= value << ((index % per_word) * width)
    return b''.join(int(value).to_bytes(4, 'little') for value in words)


def width_for(palette_count):
    required = max(0, (palette_count - 1).bit_length())
    return next(width for width in WIDTHS if width >= required)


def old_cell_record(value):
    if not isinstance(value, Cell):
        return list(value)
    return {'foreground': list(value), 'background': list(value.background),
            'nbt': value._actor}


def serialized_size(data):
    raw = json.dumps(data, ensure_ascii=True, separators=(',', ':')).encode('ascii')
    return len(raw), len(base64.b64encode(zlib.compress(raw, 6)))


def palette_surrogate_sizes(palette):
    """Measure JSON count/name/state surrogates, not Bedrock NBT records."""
    count = len(json.dumps({'paletteCount': len(palette)}, separators=(',', ':')).encode('ascii'))
    entries = [{'name': value[0], 'states': states(value) or {}} for value in palette]
    records = len(json.dumps(entries, ensure_ascii=True, separators=(',', ':')).encode('ascii'))
    return count, records


def measure(name, values):
    document = Document((16, 16, 16), positions(values), name=name)
    store = document.blocks
    if len(set(values)) == 1:
        store.fill_chunk((0, 0, 0), values[0])
    chunk = store.chunks.get((0, 0, 0), 0)
    if isinstance(chunk, int):
        indices = [chunk] * CELLS
        old_payload = len(json.dumps(chunk))
    else:
        indices = list(chunk)
        old_payload = len(base64.b64encode(zlib.compress(IntegerBuffer('H', indices).tobytes(), 1)))
    width = 0 if len(set(indices)) <= 1 else width_for(len(store.palette))
    packed = packed_indices(indices, width)
    palette_count_json, palette_records_json = palette_surrogate_sizes(store.palette)

    compact_config = codec.to_data(document)
    compact_raw, compact_z = serialized_size(compact_config)
    compact_share = None
    if compact_config['version'] == 4:
        compact_share = len(list(__import__('projection.sharing_codec', fromlist=['encode_steps']).encode_steps(document))[-1]['text'])

    old_encoder, old_transfer_encoder = codec.encode_cell, transfer.encode_cell
    try:
        codec.encode_cell = old_cell_record
        transfer.encode_cell = old_cell_record
        dictionary_config = codec.to_data(document)
        dictionary_raw, dictionary_z = serialized_size(dictionary_config)
        dictionary_share = None
        if dictionary_config['version'] == 4:
            from projection.sharing_codec import encode_steps
            dictionary_share = len(list(encode_steps(document))[-1]['text'])
    finally:
        codec.encode_cell = old_encoder
        transfer.encode_cell = old_transfer_encoder

    return {
        'case': name,
        'cells': CELLS,
        'paletteEntries': len(store.palette),
        'legacy_u16_or_uniform_payload_bytes': old_payload,
        'bwo_index_only_scope': 'excludes palette NBT, subchunk headers and LevelDB keys',
        'bwo_index_only_bit_width': width,
        'bwo_index_only_packed_bytes': len(packed),
        'bwo_index_only_packed_zlib_base64_bytes': len(base64.b64encode(zlib.compress(packed, 1))),
        'palette_count_json_surrogate_bytes': palette_count_json,
        'palette_name_state_json_surrogate_bytes': palette_records_json,
        'compact_cell_config_json_bytes': compact_raw,
        'compact_cell_config_zlib_base64_bytes': compact_z,
        'dictionary_cell_config_json_bytes': dictionary_raw,
        'dictionary_cell_config_zlib_base64_bytes': dictionary_z,
        'compact_share_text_bytes': compact_share,
        'dictionary_share_text_bytes': dictionary_share,
    }


def cases():
    stone, dirt, glass = ('minecraft:stone', 0), ('minecraft:dirt', 0), ('minecraft:glass', 0)
    uniform = [stone] * CELLS
    low_entropy = [((stone, dirt, glass, ('minecraft:planks', 0))[i % 4]) for i in range(CELLS)]
    high_entropy = [('custom:palette_%04d' % i, 0) for i in range(CELLS)]
    mixed = []
    for i in range(CELLS):
        front = (stone, glass, dirt, ('minecraft:planks', 0))[i % 4]
        back = AIR if i % 2 else (glass, dirt, stone)[(i // 2) % 3]
        actor = None
        if i % 64 == 0:
            actor = {'id': 'Chest', 'x': i & 15, 'y': i >> 8, 'z': (i >> 4) & 15,
                     'pairx': (i & 15) + 1, 'pairz': (i >> 4) & 15,
                     'Items': [{'Slot': i % 27, 'Name': 'minecraft:apple', 'tag': {'x': 91}}]}
        mixed.append(make_cell(front, back, actor))
    return (('uniform', uniform), ('low_entropy_4_materials', low_entropy),
            ('high_entropy_4096_materials', high_entropy), ('mixed_front_back_nbt', mixed))


if __name__ == '__main__':
    print(json.dumps([measure(name, values) for name, values in cases()], indent=2))
