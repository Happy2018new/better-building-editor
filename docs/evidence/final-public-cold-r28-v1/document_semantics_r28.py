"""Strict private wire-to-complete-cell comparison, independent of palette order."""
from __future__ import unicode_literals
import hashlib,json

HEADER_KEYS=frozenset(('version','cellVersion','chunkEncoding','registry','name','size','biome','blockCount'))
WIRE_KEYS=HEADER_KEYS|frozenset(('materials','palette','chunks'))


def complete_cell(value):
    from projection.cell import Cell,foreground,background,freeze
    return ['complete_cell',freeze(foreground(value)),freeze(background(value)),
            value._actor if isinstance(value,Cell) else ('null',)]


def serialized(value):
    return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'))


def semantic_document(wire):
    from projection.model import Document
    from projection.cell import freeze
    from projection import semantic_wire
    if type(wire) is not dict or set(wire)!=WIRE_KEYS:
        raise ValueError('Strict document compare requires the exact v6 wire field set')
    if type(wire['version']) is not int or wire['version']!=6:
        raise ValueError('Strict document compare requires v6')
    # This executes every original loader/header/material/palette/chunk/count guard.
    document=Document.from_data(wire)
    source=semantic_wire.validate_header(wire)
    materials=[semantic_wire.decode_material(row,source) for row in wire['materials']]
    palette=[]
    for row in wire['palette']:
        form='integer' if type(row) is int else 'sequence_'+str(len(row))
        palette.append([form,complete_cell(semantic_wire.decode_cell(row,materials))])
    chunk_rows=[]
    for row in wire['chunks']:
        kind='integer' if type(row[3]) is int else 'text'
        chunk_rows.append([freeze(row[:3]),kind])
    return {'header':freeze(dict((k,wire[k]) for k in HEADER_KEYS)),
        # Preserve all rows, including unused/duplicate material or palette entries.
        'declared_material_rows':sorted([freeze(row) for row in wire['materials']],key=serialized),
        'declared_typed_palette_rows':sorted(palette,key=serialized),
        'chunk_coordinates_and_payload_kinds':sorted(chunk_rows,key=serialized),
        # Include every position, foreground+aux, extra+aux and exact tagged actor.
        'complete_cells':[[list(point),complete_cell(document.get_cell(point))] for point in document.points()],
        'decoded_size':list(document.size),'decoded_name':document.name,'decoded_biome':document.biome,
        'decoded_nonair_count':len(document.blocks)}


def digest(value):
    return hashlib.sha256(serialized(value).encode('utf-8')).hexdigest()


def assert_same_document(actual,expected):
    a=semantic_document(actual);e=semantic_document(expected)
    assert a==e,'Complete typed document semantics changed'
    return {'comparison':'strict_v6_full_typed_cells_and_declared_tables',
        'actual_original_wire_sha256':digest(actual),'expected_original_wire_sha256':digest(expected),
        'wire_identical':actual==expected,'complete_semantics_sha256':digest(a),
        'complete_positions_checked':len(a['complete_cells']),'nonair_cells':a['decoded_nonair_count'],
        'exact_header_and_unknown_fields_checked':True,'unused_material_palette_rows_preserved':True,
        'full_actor_tag_types_and_extra_layers_checked':True}
