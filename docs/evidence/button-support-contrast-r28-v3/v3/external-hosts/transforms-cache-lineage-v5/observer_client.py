# -*- coding: utf-8 -*-
"""Private delegating observer; exports complete bytes, computes no hashes in MC."""
from __future__ import unicode_literals
import base64
import copy
import json
import sys
import time
import zlib

from modern_projection.projection.cell import freeze, encode as encode_cell
from modern_projection.projection.bridge import _native_palette
from modern_projection.projection.large_preview import build_preview
from modern_projection.projection.kelp_render import palette_parts
from modern_projection.projection.native_render_profile import for_preview, profile_identity
from modern_projection.projection.liquid_render_ownership import identity as liquid_identity
from modern_projection.projection.preview_regions import regions
from modern_projection.projection.storage import integer_types


def wire(value, compressed=False):
    raw = repr(freeze(value, budget=[1000000, 64 * 1024 * 1024])).encode('utf8')
    return {'codec': 'cell.freeze-repr-utf8-zlib-base64' if compressed else 'cell.freeze-repr-utf8-base64',
            'base64': base64.b64encode(zlib.compress(raw, 1) if compressed else raw).decode('ascii'),
            'bytes': len(raw)}


def raw_repr(value):
    raw = repr(value).encode('utf8')
    return {'codec': 'python2-repr-utf8-base64',
            'base64': base64.b64encode(raw).decode('ascii'), 'bytes': len(raw)}


def source_wire(source):
    # IntegerBuffer.__repr__ only contains its address. Preserve that repr as
    # an auxiliary observation, and separately export every numeric cell.
    context, region, palette, chunks = source
    return wire({'context': context, 'region': region,
        'palette': tuple(encode_cell(value) for value in palette),
        'chunks': tuple(('constant', value) if isinstance(value, integer_types)
                        else ('IntegerBuffer-values', tuple(value)) for value in chunks)}, True)


def halo_keys(region):
    return tuple(sorted(set(tuple(member[i] + offset[i] for i in range(3))
        for member in region[3] for offset in
        ((0, 0, 0), (1, 0, 0), (-1, 0, 0), (0, 1, 0),
         (0, -1, 0), (0, 0, 1), (0, 0, -1)))))


def relevant(pos, low, high, size):
    if not all(0 <= pos[i] < size[i] for i in range(3)):
        return False
    outside = 0
    for i in range(3):
        if low[i] <= pos[i] < high[i]:
            continue
        if pos[i] not in (low[i] - 1, high[i]):
            return False
        outside += 1
    return outside <= 1


def snapshot_cells(source):
    context, region, palette, chunks = source
    size, low, high = context[0], region[1], region[2]
    keys = halo_keys(region)
    assert len(keys) == len(chunks)
    cells = []
    for key, chunk in zip(keys, chunks):
        if isinstance(chunk, integer_types) and not chunk:
            continue
        for index in range(4096):
            identity = chunk if isinstance(chunk, integer_types) else chunk[index]
            if not identity:
                continue
            pos = (key[0] * 16 + (index & 15),
                   key[1] * 16 + (index >> 8),
                   key[2] * 16 + ((index >> 4) & 15))
            if relevant(pos, low, high, size):
                cells.append((pos, encode_cell(palette[identity])))
    return tuple(sorted(cells))


def source_body(key):
    region = s.tiles.regions[key]
    low, high = region[1], region[2]
    document = s.editor.document
    return {'size': document.size, 'biome': document.biome, 'region': region,
            'profile_visibility_context': s.preview_signature()[2:],
            'cells': tuple(sorted((pos, encode_cell(value)) for pos, value in document.blocks.items()
                          if relevant(pos, low, high, document.size)))}


def part_data(palette, origin):
    return (palette.common, palette.extra, palette.actor, palette.size, tuple(origin),
            id(getattr(s, 'item_profile', None)),
            profile_identity(getattr(s, 'native_render_profile', None)),
            getattr(getattr(s, 'cauldron_profile', None), 'identity', None),
            getattr(getattr(s, 'spawner_profile', None), 'identity', None),
            getattr(getattr(s, 'portal_profile', None), 'identity', None),
            liquid_identity(getattr(s, 'liquid_profile', None)),
            tuple(sorted(palette_parts(palette.palette_data(), s.editor.document, origin).items())))


def prepared_native(palette, origin):
    # Matches ClientBridge.geometry's no-context/no-prepared tiled path. Its
    # source SHA is bound by the external frozen manifest; native Deserialize
    # input is captured independently and must match this complete result.
    from modern_projection.projection.geometry_palette import prepare_palette
    source = palette.palette_data()
    complete = palette if hasattr(palette, 'blocks') else getattr(palette, 'source_document', None)
    kelp = palette_parts(source, complete, getattr(palette, 'source_origin', (0, 0, 0)))
    result = prepare_palette(source, overlay_base=palette.size[1] + 1,
        kelp_parts=kelp, render_origin=origin,
        item_profile=getattr(s, 'item_profile', None),
        native_render_profile=for_preview(getattr(s, 'native_render_profile', None)),
        cauldron_profile=getattr(s, 'cauldron_profile', None),
        biome=getattr(palette, 'biome', s.editor.document.biome),
        liquid_profile=getattr(s, 'liquid_profile', None),
        spawner_profile=getattr(s, 'spawner_profile', None),
        portal_profile=getattr(s, 'portal_profile', None))
    assert '_context_batches' not in result, 'This narrow observer has not qualified context batches'
    return _native_palette(result)


def install(config):
    assert not hasattr(sys, '_strict_cache_r27')
    assert hasattr(sys, '_blueprint_qa_saved')
    saved = {'config': config, 'records': [], 'stack': [], 'factory': b.factory,
             'geometry': b.geometry, 'had_geometry': 'geometry' in b.__dict__,
             'geometry_instance_value': b.__dict__.get('geometry'),
             'collect': collect, 'restore': restore, 'controls': controls}
    sys._strict_cache_r27 = saved

    class PaletteProbe(object):
        def __init__(self, target):
            self.target, self.input_bytes, self.accepted = target, None, None
        def __getattr__(self, name):
            return getattr(self.target, name)
        def DeserializeBlockPalette(self, data):
            self.input_bytes = wire(data)
            self.accepted = self.target.DeserializeBlockPalette(data)
            return self.accepted

    class BlockProbe(object):
        def __init__(self, target):
            self.target = target
        def __getattr__(self, name):
            return getattr(self.target, name)
        def GetBlankBlockPalette(self):
            target = self.target.GetBlankBlockPalette()
            return PaletteProbe(target) if target is not None else None

    class GeometryProbe(object):
        def __init__(self, target):
            self.target = target
        def __getattr__(self, name):
            return getattr(self.target, name)
        def CombineBlockPaletteToGeometry(self, palette, name, mode=0):
            assert isinstance(palette, PaletteProbe)
            record = {'serial': len(saved['records']) + 1, 'name': name, 'mode': mode,
                'palette_object_id': id(palette.target), 'deserialize_accepted': palette.accepted,
                'deserialize_input': palette.input_bytes,
                'native_serialized': wire(palette.target.SerializeBlockPalette()),
                'config': dict(config), 'nonce': sys._blueprint_qa_nonce,
                'fixture': sys._blueprint_qa_identity, 'editor_id': id(s.editor),
                'document_id': id(s.editor.document), 'signature': wire(s.preview_signature()),
                'signature_values': s.preview_signature(),
                'frame': copy.deepcopy(saved['stack'][-1]) if saved['stack'] else None,
                'legacy_records_before': len(sys._blueprint_qa_records)}
            started = time.time()
            try:
                # Preserve the exact native palette, requested name and mode.
                result = self.target.CombineBlockPaletteToGeometry(palette.target, name, mode)
                record['result'] = result
                return result
            except Exception as error:
                record['error'] = repr(error)
                raise
            finally:
                record['seconds'] = time.time() - started
                record['legacy_records_after'] = len(sys._blueprint_qa_records)
                saved['records'].append(record)

    class FactoryProbe(object):
        def __init__(self, target):
            self.target = target
        def __getattr__(self, name):
            return getattr(self.target, name)
        def CreateBlock(self, level):
            return BlockProbe(self.target.CreateBlock(level))
        def CreateBlockGeometry(self, level):
            return GeometryProbe(self.target.CreateBlockGeometry(level))

    def geometry(document, *args, **kwargs):
        name = kwargs.get('name')
        frame = None
        if name and name.startswith('modern_projection_chunk_'):
            assert not args and kwargs.get('prepared') is None and kwargs.get('context_document') is None
            key = s.tiles.key
            origin = tuple(kwargs.get('render_origin', (0, 0, 0)))
            body = source_body(key)
            frame = {'key': key, 'requested_name': name, 'origin': origin, 'size': document.size,
                'source_body': wire(body), 'source_cells': wire(body['cells']),
                'source_snapshot_repr': raw_repr(s.tiles.source),
                'source_snapshot_complete': source_wire(s.tiles.source),
                'source_snapshot_cells': wire(snapshot_cells(s.tiles.source)),
                'source_context': wire(s.tiles.source[0]),
                'source_region': wire(s.tiles.source[1]),
                'logical_palette': wire(document.palette_data()),
                'part_data': wire(part_data(document, origin)),
                'expected_native_input': wire(prepared_native(document, origin))}
        saved['stack'].append(frame)
        try:
            return saved['geometry'](document, *args, **kwargs)
        finally:
            saved['stack'].pop()

    saved['observer_factory'] = FactoryProbe(b.factory)
    b.factory = saved['observer_factory']
    b.geometry = geometry


def controls():
    from modern_projection.pyreact.debug import _type_name
    host = navigator.top._host
    def walk(fiber):
        yield fiber
        for child in fiber.child_fibers:
            for item in walk(child):
                yield item
    scenes = [fiber for fiber in walk(host._root_fiber)
              if _type_name(fiber) == 'Scene' and fiber.props.get('session') is s]
    assert len(scenes) == 1
    rows = []
    for tile in walk(scenes[0]):
        if _type_name(tile) != 'PreviewTile':
            continue
        key = tile.props['identity']
        if key not in s.tiles.slots:
            continue
        dolls, surfaces, preview = tile.props['registry'][key]
        part = s.tiles.parts[key]
        visible = [ref.current.GetVisible() for ref in dolls if ref.current is not None]
        surface_visible = [ref.current.GetVisible() if ref.current is not None else None for ref in surfaces]
        rows.append({'key': key, 'owner': key in s.tiles.region_owners,
                     'name': part['name'], 'ready': preview.ready(part['name']),
                     'pending': preview.pending, 'front_name': preview.names[preview.front],
                     'front': preview.front, 'names': list(preview.names),
                     'surface_visible': surface_visible, 'tracked_visible': list(preview.visible),
                     'depth_hidden': getattr(preview, 'depth_hidden', False),
                     'suspended': getattr(preview, 'suspended', False),
                     'poses': list(preview.poses), 'visible': visible})
    return rows


def collect():
    saved = sys._strict_cache_r27
    document, tiles = s.editor.document, s.tiles
    signature = s.preview_signature()
    assert not saved['stack']
    assert regions(document) == tiles.regions, 'Current document regions differ'
    assert tiles.context == signature[:1] + signature[2:], 'Current context differs'
    rows = []
    for key in sorted(tiles.region_owners):
        part = tiles.parts[key]
        low, size = tiles.region_bounds(key)
        high = tuple(low[i] + size[i] for i in range(3))
        palette = None
        for result in build_preview(document, s.preview_hidden(),
                s.editor.layer if s.solo_layer else None, None, None, (low, high), True):
            if result is not None:
                palette, origin, scale = result
        assert palette is not None and tuple(origin) == tuple(low) and scale == 1
        data = part_data(palette, origin)
        body = source_body(key)
        cache = part['cache'][part['bank']]
        source = part['source']
        rows.append({'key': key, 'name': part['name'], 'bank': part['bank'],
            'origin': part['origin'], 'size': part['size'], 'count': part['count'],
            'current_origin': origin, 'current_size': palette.size, 'current_count': palette.count,
            'pending': part['pending'], 'signature_values': part['signature'],
            'signature_current': part['signature'] == signature,
            'part_data': wire(part['data']), 'current_part_data': wire(data),
            'cache_data': wire(cache[0]), 'cache_model': cache[1],
            'cache_sources_repr': [raw_repr(item) for item in cache[2]],
            'cache_sources_complete': [source_wire(item) for item in cache[2]],
            'source_snapshot_repr': raw_repr(source),
            'source_snapshot_complete': source_wire(source),
            'source_snapshot_cells': wire(snapshot_cells(source)),
            'source_context': wire(source[0]),
            'current_source_context': wire((document.size,) + signature[2:]),
            'source_region': wire(source[1]), 'current_region': wire(tiles.regions[key]),
            'current_source_body': wire(body), 'current_source_cells': wire(body['cells']),
            'logical_palette': wire(palette.palette_data()),
            'current_native_input': wire(prepared_native(palette, origin))})
    empty = []
    for key in sorted(set(tiles.slots) - tiles.region_owners):
        part = tiles.parts[key]
        cache = part['cache'][part['bank']]
        empty.append({'key': key, 'name': part['name'], 'count': part['count'],
            'pending': part['pending'], 'palette_counts':
                [sum(len(values) for values in layer.values()) for layer in part['data'][:3]],
            'cache_current': cache[0] == part['data'] and cache[1] == part['name']
                and part['source'] in cache[2],
            'signature_current': part['signature'] == signature})
    return {'schema': 1, 'config': saved['config'], 'nonce': sys._blueprint_qa_nonce,
        'fixture': sys._blueprint_qa_identity, 'editor_id': id(s.editor),
        'document_id': id(document), 'signature_values': signature,
        'document': document.to_data(), 'parts': rows,
        'document_regions': wire(regions(document)),
        'records': saved['records'], 'controls': controls(), 'empty_slots': empty,
        'actual_render_keys': tuple(tiles.render_keys),
        'actual_scene_census': scene_census(),
        'slot_keys': tuple(sorted(tiles.slots)),
        'owner_keys': tuple(sorted(tiles.region_owners)),
        'note': 'All complete wire bytes come from MC; SHA256 is computed by the host only.'}


def scene_census():
    """Read actual Scene requests, child Fibers and registry, without UI writes."""
    from modern_projection.pyreact.debug import _type_name
    def walk(fiber):
        yield fiber
        for child in fiber.child_fibers:
            for item in walk(child):yield item
    scenes=[fiber for fiber in walk(navigator.top._host._root_fiber)
            if _type_name(fiber)=='Scene' and fiber.props.get('session') is s]
    assert len(scenes)==1
    models=[fiber for fiber in walk(scenes[0])
            if _type_name(fiber)=='PreviewModels' and fiber.props.get('session') is s]
    assert len(models)==1
    model=models[0]
    return {'scene_fiber_id':id(scenes[0]),'models_fiber_id':id(model),
            'model_requested_keys':tuple(model.props['keys']),
            'fiber_tile_keys':tuple(fiber.props['identity'] for fiber in walk(model)
                                    if _type_name(fiber)=='PreviewTile'),
            'registry_keys':tuple(sorted(model.props['registry']))}


def restore():
    saved = sys._strict_cache_r27
    assert not saved['stack'] and b.factory is saved['observer_factory']
    b.factory = saved['factory']
    if saved['had_geometry']:
        b.geometry = saved['geometry_instance_value']
    else:
        del b.geometry
    del sys._strict_cache_r27
