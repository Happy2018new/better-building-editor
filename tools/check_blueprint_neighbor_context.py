"""Offline audit of the built-in connected blueprint and missing-only inputs.

Exit 1 means a documented contract fails, including lost missing-only context.
This tool does not tessellate native geometry or claim pixel acceptance.
"""
import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.block_registry import states
from projection.cell import AIR, actor_data, background, foreground, make_cell
from projection.debug_blueprints import build
from projection.geometry_palette import prepare_palette
from projection.large_preview import SurfacePalette, build_preview
from projection.model import Document, Editor
from projection.occupancy import ProjectionOccupancy
from projection.occupancy_initial import prepare_chunk
from projection.preview_regions import regions
from projection.visible_actor import render_actor

FIXTURE = 'test.connections.context'
CASES = (
    ('stairs', (3, 1, 23), (4, 1, 23)),
    ('rail', (3, 1, 3), (4, 1, 3)),
    ('wall', (7, 1, 17), (7, 1, 16)),
    ('fence', (17, 1, 17), (18, 1, 17)),
    ('pane', (17, 1, 20), (17, 1, 21)),
    ('iron_bars', (22, 1, 20), (22, 1, 21)),
    ('chest', (27, 1, 5), (26, 1, 5)),
    ('copper_chest', (27, 1, 10), (26, 1, 10)),
)


def clone(source):
    document = Document(source.size, name=source.name, biome=source.biome)
    document.blocks = source.blocks.copy()
    return document


def point(index, size):
    sx, unused, sz = size
    return index // sz % sx, index // (sx * sz), index % sz


def native_cells(source, origin=(0, 0, 0)):
    data = prepare_palette(source.palette_data())
    result = {}
    for key in ('common', 'extra'):
        for value, indices in data[key].items():
            for index in indices:
                local = point(index, source.size)
                pos = tuple(origin[i] + local[i] for i in range(3))
                result.setdefault(pos, {'front': AIR, 'back': AIR, 'actor': None})[
                    'front' if key == 'common' else 'back'] = value
    for unused_name, entries in data['actor'].items():
        for index, actor in entries.items():
            local = point(index, source.size)
            pos = tuple(origin[i] + local[i] for i in range(3))
            result.setdefault(pos, {'front': AIR, 'back': AIR, 'actor': None})['actor'] = actor
    return result


def cell_record(document, pos):
    value = document.get(pos)
    return {'front': foreground(value), 'back': background(value),
            'states': states(foreground(value)), 'actor': render_actor(actor_data(value))}


def editor_context(document, keep, neighbor):
    partitions = regions(document)
    key = tuple(value >> 4 for value in keep)
    root, low, high, members = partitions[key]
    output = next(result for result in build_preview(document, region=(low, high), local=True)
                  if result is not None)[0]
    inputs = native_cells(output, low)
    requested = [pos for pos in (keep, neighbor) if document.get(pos) != AIR]
    return {'owner': root, 'members': members, 'bounds': [low, high],
            'input_cells': len(inputs), 'keep': inputs.get(keep),
            'neighbor': inputs.get(neighbor),
            'passed': all(pos in inputs for pos in requested),
            'scope': 'full display; no hidden-layer, section, or depth filter'}


def editor_case(source, label, keep, neighbor):
    editor = Editor(clone(source))
    editor.edit_layer = 0
    before = editor.document.blocks.copy()
    history_before = len(editor.undo_stack)
    erase_count = editor.paint_at(neighbor, erase=True, respect_selection=False)
    erased = editor.document.blocks.copy()
    erase_context = editor_context(editor.document, keep, neighbor)
    is_chest = label.endswith('chest')
    erased_correctly = (editor.document.get(neighbor) == AIR and
                        ((editor.document.get(keep) == AIR) if is_chest else
                         (editor.document.get(keep) != AIR)))
    before_keep, erased_keep = cell_record(source, keep), cell_record(editor.document, keep)
    reconciled = True
    if label == 'wall':
        reconciled = erased_keep['states']['wall_connection_type_north'] == 'none'
    elif label == 'rail':
        reconciled = erased_keep['states']['rail_direction'] != before_keep['states']['rail_direction']
    editor.undo()
    undo_exact = editor.document.blocks == before
    editor.redo()
    redo_exact = editor.document.blocks == erased
    editor.material = foreground(source.get(neighbor))
    placement_count = editor.paint_at(neighbor, respect_selection=False)
    placement_actions = 1
    if is_chest:
        # Chest pairing is an adjacency operation: placing a single chest does
        # not manufacture another chest. Recreate the second half separately.
        editor.material = foreground(source.get(keep))
        placement_count += editor.paint_at(keep, respect_selection=False)
        placement_actions += 1
    placed = editor.document.blocks.copy()
    placed_context = editor_context(editor.document, keep, neighbor)
    placement_correct = (foreground(editor.document.get(neighbor))[0] == foreground(source.get(neighbor))[0]
                         and editor.document.get(keep) != AIR)
    if is_chest:
        placement_correct = placement_correct and all(
            render_actor(actor_data(editor.document.get(pos)))['chestIsLargeChest']
            for pos in (keep, neighbor))
    for unused in range(placement_actions):
        editor.undo()
    placement_undo_exact = editor.document.blocks == erased
    for unused in range(placement_actions):
        editor.redo()
    placement_redo_exact = editor.document.blocks == placed
    passed = (erased_correctly and reconciled and undo_exact and redo_exact and placement_correct and
              placement_undo_exact and placement_redo_exact and
              len(editor.undo_stack) == history_before + 1 + placement_actions and
              erase_context['passed'] and placed_context['passed'])
    return {'category': label, 'keep': keep, 'neighbor': neighbor, 'passed': passed,
            'before_keep': before_keep, 'erased_keep': erased_keep,
            'erase_count': erase_count, 'placement_count': placement_count,
            'placement_actions': placement_actions,
            'neighbor_reconciled': reconciled,
            'erase_group_behavior': 'both chest halves erased' if is_chest else 'only clicked cell erased',
            'undo_exact': undo_exact, 'redo_exact': redo_exact,
            'placement_undo_exact': placement_undo_exact, 'placement_redo_exact': placement_redo_exact,
            'erase_native_context': erase_context, 'placement_native_context': placed_context}


class OccupancyRuntime:
    def __init__(self, occupied):
        self.occupied = set(occupied)

    def CreateBlockInfo(self, unused_level):
        return self

    def CreateBlock(self, unused_level):
        return self

    def CreateCamera(self, unused_level):
        return self

    def GetBlock(self, pos):
        return ('minecraft:stone', 0) if pos in self.occupied else AIR


def tracker(source, occupied):
    runtime = OccupancyRuntime(occupied)
    session = SimpleNamespace(editor=SimpleNamespace(document=source, layer=None),
                              preview_hidden=lambda: (), solo_layer=False)
    bridge = SimpleNamespace(factory=runtime, system=runtime, session=session,
                             level='offline', projection_serial=1, projection_occupancy=None)
    return ProjectionOccupancy(bridge, (0, 0, 0)), runtime


def missing_inputs(source, occupied, route):
    occupancy, runtime = tracker(source, occupied)
    if route == 'visibility_callback':
        data = source.palette_data(occupancy.initial_visible)
        output = SurfacePalette(source.size)
        for pos in source.blocks:
            if occupancy.state[occupancy.index(pos)] != 2:
                output.add(pos, source.get(pos))
        # Compare the callback palette directly, so a future output/context API
        # cannot accidentally be concealed by this reproduction's reconstruction.
        assert data['common'] == output.common and data['extra'] == output.extra
    elif route == 'chunk_initial':
        def begin(key):
            start = tuple(value * 16 for value in key)
            size = tuple(min(16, source.size[i] - start[i]) for i in range(3))
            values = bytearray([1]) * (size[0] * size[1] * size[2])
            for pos in occupied:
                if all(start[i] <= pos[i] < start[i] + size[i] for i in range(3)):
                    local = tuple(pos[i] - start[i] for i in range(3))
                    values[(local[1] * size[0] + local[0]) * size[2] + local[2]] = 2
            occupancy.bulk.initial = (key, (values, size))
        occupancy.bulk.begin = begin
        output = SurfacePalette(source.size)
        for key in sorted(source.blocks.chunks):
            size = tuple(min(16, source.size[i] - key[i] * 16) for i in range(3))
            for unused in prepare_chunk(occupancy, source.blocks, key, size, output):
                pass
    else:
        runtime.occupied.clear()
        for pos in source.blocks:
            occupancy.initial_visible(pos)
        occupancy.rendered = occupancy.state[:]
        runtime.occupied.update(occupied)
        for pos in occupied:
            occupancy.read(pos)
        occupancy.snapshot = occupancy.state[:]
        output = occupancy.output = SurfacePalette(source.size)
        for unused in occupancy.prepare():
            pass
    return native_cells(output), occupancy


def missing_case(source, label, keep, occupied):
    full = native_cells(source)
    before = source.blocks.copy()
    routes = []
    for route in ('visibility_callback', 'chunk_initial', 'dynamic_rebuild'):
        actual, occupancy = missing_inputs(source, [occupied], route)
        keep_payload = actual.get(keep)
        preserved = source.blocks == before and occupancy.document.blocks == before
        context_retained = occupied in actual
        remaining_exact = keep_payload == full.get(keep)
        routes.append({'route': route, 'passed': context_retained and remaining_exact and preserved,
                       'context_retained': context_retained, 'remaining_payload_exact': remaining_exact,
                       'document_preserved': preserved, 'target_still_tracked': occupied in occupancy.targets,
                       'native_cells': len(actual), 'lost_context': full.get(occupied),
                       'remaining': keep_payload,
                       'remaining_large_chest_actor_without_partner': bool(
                           keep_payload and keep_payload.get('actor') and
                           keep_payload['actor'].get('chestIsLargeChest') and not context_retained)})
    return {'category': label, 'keep': keep, 'occupied': occupied,
            'passed': all(row['passed'] for row in routes), 'routes': routes}


def audit():
    source = build(FIXTURE)
    cases = [row for row in CASES if source.get(row[1]) != AIR and source.get(row[2]) != AIR]
    editors = [editor_case(source, *row) for row in cases]
    full = [dict(category=label, **editor_context(source, keep, neighbor))
            for label, keep, neighbor in cases]
    missing = [missing_case(source, *row) for row in cases]
    # The shipped connected fixture contains no liquid layer. Keep its native
    # geometry layout and add explicit water payloads only for this sidecar.
    layered = clone(source)
    for label, keep, neighbor in cases:
        if label in ('fence', 'chest'):
            for pos in (keep, neighbor):
                value = layered.get(pos)
                layered.blocks[pos] = make_cell(foreground(value), ('minecraft:water', 0), actor_data(value))
    background_cases = [missing_case(layered, label + '_water_sidecar', keep, neighbor)
                        for label, keep, neighbor in cases if label in ('fence', 'chest')]
    failures = ['editor:' + row['category'] for row in editors if not row['passed']]
    failures += ['full_context:' + row['category'] for row in full if not row['passed']]
    failures += ['missing:' + row['category'] for row in missing + background_cases if not row['passed']]
    return {'schema': 1, 'fixture': FIXTURE, 'size': source.size, 'blocks': len(source.blocks),
            'evidence_kind': 'offline editor transactions and native palette inputs; no SDK tessellation or pixels',
            'editor_passed': all(row['passed'] for row in editors),
            'full_projection_context_passed': all(row['passed'] for row in full),
            'missing_passed': all(row['passed'] for row in missing + background_cases),
            'editor': editors, 'full_context': full, 'missing': missing,
            'background_sidecar': background_cases, 'failures': failures,
            'limitations': ['Missing filtering loses occupied native context before Combine.',
                            'A remaining sub chest can still carry large-chest actor fields with no partner palette cell.',
                            'Rails and walls retain supplied connection states; their final missing-only visual behavior needs native pixels.',
                            'Editor audit uses full display. Intentional hidden layers and depth clipping are separate cases.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'evidence': str(args.output.resolve()), 'editor_passed': report['editor_passed'],
                      'full_context_passed': report['full_projection_context_passed'],
                      'missing_passed': report['missing_passed'], 'failures': report['failures']}, indent=2))
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    sys.exit(main())
