"""Offline, source-bound partition reconstruction for a strict host candidate.

This does not certify pixels and never edits original MC observations.  The
product modules are imported only from an explicitly verified frozen project.
JSON transport makes the document a lossy shadow of the original Py2 types;
that boundary is named below.  All original cache/native wire checks remain
byte-for-byte in lineage_host.py and are not replaced by this reconstruction.
"""
import hashlib
import json
from pathlib import Path
import sys


def shadow_key(value):
    """Typed structure, with only Py2 UTF8 bytes/text folded at JSON boundary."""
    if value is None:
        return ('null',)
    if type(value) is bool:
        return ('bool', value)
    if type(value) is int:
        return ('int', str(value))
    if type(value) is float:
        return ('float', value.hex())
    if type(value) is bytes:
        return ('text', value.decode('utf8', errors='strict'))
    if type(value) is str:
        return ('text', value)
    if type(value) in (tuple, list):
        return ('tuple' if type(value) is tuple else 'list', tuple(shadow_key(v) for v in value))
    if type(value) is dict:
        return ('dict', tuple(sorted((shadow_key(k), shadow_key(v)) for k, v in value.items())))
    raise AssertionError('unsupported source reconstruction scalar/container')


def json_shadow(value):
    if isinstance(value, bytes):
        return value.decode('utf8', errors='strict')
    if isinstance(value, (list, tuple)):
        return [json_shadow(v) for v in value]
    if isinstance(value, dict):
        return {json_shadow(k): json_shadow(v) for k, v in value.items()}
    return value


def source_materials(source):
    """Resolve full numeric chunk snapshots through their own complete palette.

    Old retained empty regions may have a shorter unused palette.  Comparing
    its numeric buffer through the current palette would conceal an alias.
    """
    palette = source['palette']
    assert type(palette) is tuple and type(source['chunks']) is tuple
    cells = []
    region = source['region']
    keys = tuple(sorted(set(tuple(member[i] + offset[i] for i in range(3))
        for member in region[3] for offset in
        ((0, 0, 0), (1, 0, 0), (-1, 0, 0), (0, 1, 0),
         (0, -1, 0), (0, 0, 1), (0, 0, -1)))))
    assert len(keys) == len(source['chunks'])
    for key, chunk in zip(keys, source['chunks']):
        assert type(chunk) is tuple and len(chunk) == 2
        tag, values = chunk
        assert tag in ('constant', 'IntegerBuffer-values')
        assert type(values) is int if tag == 'constant' else type(values) is tuple
        if tag == 'constant' and values == 0:
            continue
        assert tag == 'constant' or len(values) == 4096
        for index in range(4096):
            identity = values if tag == 'constant' else values[index]
            assert type(identity) is int and 0 <= identity < len(palette)
            if identity:
                pos = (key[0] * 16 + (index & 15), key[1] * 16 + (index >> 8),
                       key[2] * 16 + ((index >> 4) & 15))
                cells.append((pos, palette[identity]))
    return shadow_key((source['context'], source['region'], tuple(sorted(cells))))


class Box:
    pass


class FrozenSource:
    def __init__(self, manifest_path, manifest_sha256, decode, need):
        self.need, self.decode = need, decode
        self.path = Path(manifest_path).resolve()
        self.sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        need(self.sha == manifest_sha256, 'partition source manifest SHA differs')
        self.manifest = json.loads(self.path.read_bytes())
        self.project = Path(self.manifest['project']).resolve()
        for name, expected in self.manifest['files'].items():
            path = self.project / name
            need(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                 'partition frozen runtime file differs: ' + name)
        self.runtime = (self.project / 'behavior_pack').resolve()
        prefix = 'modern_projection.projection'
        for name, module in tuple(sys.modules.items()):
            if name == 'modern_projection' or name.startswith(prefix):
                actual = getattr(module, '__file__', None)
                need(actual is not None and Path(actual).resolve().is_relative_to(self.runtime),
                     'partition module already imported from a different source: ' + name)
        sys.path.insert(0, str(self.runtime))
        from modern_projection.projection.model import Document
        from modern_projection.projection.preview_regions import regions
        from modern_projection.projection.tiles import TiledPreview
        from modern_projection.projection.cell import encode
        from modern_projection.projection.large_preview import build_preview
        from modern_projection.projection.storage import integer_types
        self.Document, self.regions = Document, regions
        self.TiledPreview, self.encode = TiledPreview, encode
        self.build_preview, self.integer_types = build_preview, integer_types

    def __call__(self, snapshot):
        need, decode = self.need, self.decode
        need(snapshot['config']['source_manifest_sha256'] == self.sha,
             'partition snapshot/frozen manifest binding differs')
        doc = self.Document.from_data(snapshot['document'])
        partition = self.regions(doc)
        need(partition == decode(snapshot['document_regions']),
             'actual frozen planner/document region reconstruction differs')
        owners = set(region[0] for region in partition.values())
        need(owners == set(map(tuple, snapshot['owner_keys'])),
             'actual frozen planner owner census differs')
        cells = tuple(sorted((pos, self.encode(cell)) for pos, cell in doc.blocks.items()))
        assignment = {}
        for pos, cell in cells:
            hits = [key for key in owners if all(partition[key][1][i] <= pos[i] < partition[key][2][i]
                                                for i in range(3))]
            need(len(hits) == 1, 'source cell does not have exactly one disjoint planner owner')
            assignment[pos] = hits[0]
        parts = {tuple(part['key']): part for part in snapshot['parts']}
        need(set(parts) == owners, 'partition part census differs')
        need(bool(parts), 'partition proof requires at least one owner')
        first_context = decode(next(iter(parts.values()))['current_source_context'])
        signature = snapshot['signature_values']
        need(json_shadow(first_context) == [list(doc.size)] + signature[2:],
             'partition current visibility/profile signature differs')
        session = Box()
        session.editor = Box()
        session.editor.document = doc
        tiles = self.TiledPreview(session)
        tiles.context = (signature[0],) + first_context[1:]
        tiles.regions = partition
        tiles.source_palette = tuple(doc.blocks.palette)
        output = {}

        def relevant(pos, low, high):
            # Independently spell the documented six-face one-cell context:
            # exactly zero or one axis outside; no edge/corner diagonals.
            outside = [i for i in range(3) if not low[i] <= pos[i] < high[i]]
            return not outside or (len(outside) == 1 and
                pos[outside[0]] in (low[outside[0]] - 1, high[outside[0]]))

        hidden = set(signature[2])
        if signature[5]:
            hidden.update(range(signature[4] + 1, doc.size[1]))
        for key in sorted(owners):
            part, region = parts[key], partition[key]
            low, high = region[1:3]
            own = tuple((p, c) for p, c in cells if assignment[p] == key)
            body_cells = tuple((p, c) for p, c in cells if relevant(p, low, high))
            halo = tuple((p, c) for p, c in body_cells if assignment[p] != key)
            expected_body = {'size': doc.size, 'biome': doc.biome, 'region': region,
                             'profile_visibility_context': first_context[1:], 'cells': body_cells}
            need(shadow_key(decode(part['current_source_body'])) == shadow_key(expected_body),
                 'partition complete source body differs from document/context')
            for field in ('current_source_cells', 'source_snapshot_cells'):
                need(shadow_key(decode(part[field])) == shadow_key(body_cells),
                     'partition relevant source cells differ from document/context: ' + field)
            source = tiles.source_state(key)  # Actual exact product method.
            expected_source = {'context': source[0], 'region': source[1],
                'palette': tuple(self.encode(c) for c in source[2]),
                'chunks': tuple(('constant', c) if isinstance(c, self.integer_types)
                                else ('IntegerBuffer-values', tuple(c)) for c in source[3])}
            observed_source = decode(part['source_snapshot_complete'])
            source_comparison = {field: shadow_key(observed_source[field]) == shadow_key(expected_source[field])
                                 for field in ('context', 'region', 'palette', 'chunks')}
            full_source_equal = source_materials(observed_source) == source_materials(expected_source)
            need(part['source_snapshot_complete'] in part['cache_sources_complete'],
                 'partition full source missing from retained cache bank')
            palette = None
            for result in self.build_preview(doc, hidden,
                    signature[4] if signature[3] else None,
                    None, None, (low, high), True):
                if result is not None:
                    palette, origin, scale = result
            need(palette is not None and origin == low and scale == 1,
                 'partition actual build_preview region/scale differs')
            need(shadow_key(palette.palette_data()) == shadow_key(decode(part['logical_palette'])),
                 'partition actual build_preview complete logical palette differs')
            need(palette.count == part['current_count'], 'partition actual build_preview count differs')
            data = decode(part['current_part_data'])
            need(shadow_key(data[:5]) == shadow_key((palette.common, palette.extra, palette.actor,
                                                    palette.size, tuple(origin))),
                 'partition rebuilt current part source layers/region differ')
            output[key] = {'owned_count': len(own), 'halo_count': len(halo),
                'source_count': len(body_cells), 'logical_count': palette.count,
                'context_sources': [{'position': list(p), 'owner': list(assignment[p])}
                                    for p, c in halo],
                'actual_planner_reconstructed': True, 'actual_source_state_reconstructed': True,
                'full_cache_snapshot_reconstructed': full_source_equal,
                'full_cache_snapshot_numeric_layout_equal': all(source_comparison.values()),
                'actual_build_preview_reconstructed': True,
                'document_json_transport_shadow_compared': True,
                'original_wire_byte_comparisons_replaced': False}
        # Context may only be referenced from another disjoint actual owner.
        # Full lineage for its native model is still checked by Ledger.certify.
        for key, proof in output.items():
            for reference in proof['context_sources']:
                target = tuple(reference['owner'])
                need(target != key and target in output and output[target]['owned_count'] > 0,
                     'partition context source lacks a distinct populated owner')
                need(parts[target]['name'] is not None and parts[target]['current_count'] > 0,
                     'partition context source populated owner lacks a current model')
                target_part = parts[target]
                pos = reference['position']
                local = tuple(pos[i] - target_part['origin'][i] for i in range(3))
                sx, sy, sz = target_part['size']
                index = local[1] * sx * sz + local[0] * sz + local[2]
                logical = decode(target_part['logical_palette'])
                logical_matches = [material for material, indices in logical['common'].items()
                                   if index in indices]
                need(len(logical_matches) == 1,
                     'partition context source lacks exactly one logical foreground at its actual owner')
                prepared = decode(target_part['current_native_input'])
                prepared_matches = [material for material, indices in prepared[b'common'].items()
                                    if index in indices]
                need(len(prepared_matches) == 1,
                     'partition context source lacks exactly one prepared native foreground')
                records = [record for record in snapshot['records']
                           if record.get('result') == target_part['name']]
                need(bool(records), 'partition context source model lacks an original native creation')
                actual = decode(records[-1]['native_serialized'])
                common = actual.get('common', actual.get(b'common'))
                actual_matches = [material for material, indices in common.items() if index in indices]
                need(len(actual_matches) == 1 and
                     shadow_key(actual_matches[0]) == shadow_key(prepared_matches[0]),
                     'partition context source original native foreground differs from current prepared')
                reference.update(actual_native_index=index,
                    logical_material=json_shadow(logical_matches[0]),
                    prepared_native_material=json_shadow(prepared_matches[0]),
                    actual_native_material=json_shadow(actual_matches[0]),
                    actual_creation_serial=records[-1]['serial'])
        return output
