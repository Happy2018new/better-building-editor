"""Audit production missing-only context palettes without claiming pixels.

The report checks the final virtual native palette emitted by
``ContextPaletteBuilder``. Ordinary targets own neighbor-context tiles;
fixed-state rail slopes own independent bodies and retain any secondary-layer
context. Occupied neighbors remain document data, not world writes.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.block_registry import canonical, states
from projection.cell import AIR, actor_data, foreground, make_cell
from projection.debug_blueprints import build
from projection.geometry_palette import prepare_palette
from projection.model import Document
from projection.nbt_spatial import rebase
from projection.render_context import prepare_document_context
from projection.render_layout import context_position, overlay_position

RAIL_NAMES = frozenset(('minecraft:rail', 'minecraft:golden_rail',
                        'minecraft:detector_rail', 'minecraft:activator_rail'))


def independent_slope(cell):
    """Independent oracle for the accepted four-family fixed-slope route."""
    return (cell is not None and cell['front'][0] in RAIL_NAMES and
            states(cell['front']).get('rail_direction') in (2, 3, 4, 5))

FIXTURE = 'test.connections.context'
CASES = (
    ('stairs', (3, 1, 23), (4, 1, 23)),
    ('rail', (3, 1, 3), (4, 1, 3)),
    ('wall', (7, 1, 17), (7, 1, 16)),
    ('fence', (17, 1, 17), (18, 1, 17)),
    ('pane', (17, 1, 20), (17, 1, 21)),
    ('iron_bars', (22, 1, 20), (22, 1, 21)),
    ('chest_sub', (27, 1, 5), (26, 1, 5)),
    ('chest_main', (26, 1, 5), (27, 1, 5)),
    ('copper_chest_sub', (27, 1, 10), (26, 1, 10)),
    ('copper_chest_main', (26, 1, 10), (27, 1, 10)),
)


def clone(source):
    document = Document(source.size, name=source.name, biome=source.biome)
    document.blocks = source.blocks.copy()
    return document


def index(position, volume):
    return (position[1] * volume[1] + position[0]) * volume[0] + position[2]


def position(value, volume):
    return (value // volume[0] % volume[1], value // (volume[0] * volume[1]),
            value % volume[0])


def palette_cells(data):
    """Map native palette slots to foreground/background and render actor."""
    result = {}
    for key, layer in (('common', 'front'), ('extra', 'back')):
        for value, entries in data.get(key, {}).items():
            for slot in entries:
                result.setdefault(slot, {'front': AIR, 'back': AIR, 'actor': None})[layer] = value
    for name, entries in data.get('actor', {}).items():
        for slot, actor in entries.items():
            result.setdefault(slot, {'front': AIR, 'back': AIR, 'actor': None})['actor'] = actor
    return result


def logical_cells(source):
    prepared = prepare_palette(source.palette_data())
    cells = palette_cells(prepared)
    result = {}
    volume = source.palette_data()['volume']
    for slot, cell in cells.items():
        if slot < volume[0] * volume[1] * volume[2]:
            result[position(slot, volume)] = cell
    canonical_cells = {}
    for pos, cell in result.items():
        front = canonical(cell['front'])
        back = canonical(cell['back'])
        canonical_cells[pos] = dict(cell, front=front, back=back)
    return canonical_cells, prepared


def target_data(source, target):
    return source.palette_data(lambda pos: pos == target)


def expected_cell(cells, pos):
    value = cells.get(pos)
    if value is None:
        return None
    actor = value.get('actor')
    return {'front': value['front'], 'back': value['back'], 'actor': actor}


def actual_cell(data, slot):
    return palette_cells(data).get(slot)


def compare_target(source, target):
    before = source.blocks.copy()
    source_cells, unused_prepared = logical_cells(source)
    actual = prepare_document_context(source, target_data(source, target))
    volume = actual['volume']
    expected_positions = []
    failures = []
    for layer in ('common', 'extra', 'actor'):
        seen = set()
        for value, entries in actual.get(layer, {}).items():
            for slot in entries:
                if slot in seen:
                    failures.append({'reason': 'duplicate_layer_slot', 'layer': layer, 'slot': slot})
                seen.add(slot)
    target_cell = source_cells.get(target)
    target_slope = independent_slope(target_cell)
    requires_context = not (target_slope and target_cell['back'] == AIR)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                pos = (target[0] + dx, target[1] + dy, target[2] + dz)
                source_value = source.blocks.get(pos, AIR)
                if source_value == AIR:
                    continue
                if not requires_context:
                    continue
                want = expected_cell(source_cells, pos)
                if independent_slope(want):
                    # The adjacent slope owns its whole mesh in its own draw;
                    # its secondary layer still supplies neighbor context.
                    want = dict(want, front=AIR, actor=None)
                if want['front'] == AIR and want['back'] == AIR and want['actor'] is None:
                    slot = index(context_position(target, (dx, dy, dz)), volume)
                    if actual_cell(actual, slot) is not None:
                        failures.append({'position': pos, 'reason': 'unowned_slope_context',
                                         'slot': slot, 'actual': actual_cell(actual, slot)})
                    continue
                expected_positions.append(pos)
                slot = index(context_position(target, (dx, dy, dz)), volume)
                got = actual_cell(actual, slot)
                if got is None:
                    failures.append({'position': pos, 'reason': 'missing_context_slot', 'slot': slot})
                    continue
                if got['front'] != want['front'] or got['back'] != want['back']:
                    failures.append({'position': pos, 'reason': 'layer_mismatch',
                                     'expected': want, 'actual': got, 'slot': slot})
                if want['actor'] is not None:
                    expected_actor = rebase(want['actor'],
                                            tuple(context_position(target, (dx, dy, dz))[i] - pos[i]
                                                  for i in range(3)))
                    if got.get('actor') != expected_actor:
                        failures.append({'position': pos, 'reason': 'actor_rebase_mismatch',
                                         'expected': expected_actor, 'actual': got.get('actor'),
                                         'slot': slot})
    allowed = set(index(context_position(target, (dx, dy, dz)), volume)
                   for dy in (-1, 0, 1) for dx in (-1, 0, 1) for dz in (-1, 0, 1))
    if not requires_context:
        allowed.clear()
    if target_slope:
        body_slot = index(overlay_position(target), volume)
        allowed.add(body_slot)
        want = dict(target_cell, back=AIR, actor=None)
        got = actual_cell(actual, body_slot)
        if got != want:
            failures.append({'position': target, 'reason': 'independent_slope_body_mismatch',
                             'slot': body_slot, 'expected': want, 'actual': got})
    extra_slots = sorted(set(slot for layer in ('common', 'extra')
                             for entries in actual[layer].values() for slot in entries) - allowed)
    if extra_slots:
        failures.append({'reason': 'independent_or_outside_tile_slots', 'slots': extra_slots[:16]})
    actor_slots = set(slot for entries in actual.get('actor', {}).values() for slot in entries)
    if actor_slots - allowed:
        failures.append({'reason': 'actor_slots_outside_tile',
                         'slots': sorted(actor_slots - allowed)[:16]})
    expected_state_slots = set(slot for layer in ('common', 'extra')
                               for entries in actual[layer].values() for slot in entries)
    state_failures = []
    for value, record in actual.get('states', {}).items():
        if value not in actual['common'] or states(value) != record:
            state_failures.append(value)
    if state_failures:
        failures.append({'reason': 'state_record_mismatch', 'values': state_failures})
    if source.blocks != before:
        failures.append({'reason': 'source_document_mutated'})
    return {
        'target': target, 'volume': volume, 'expected_neighbor_cells': len(expected_positions),
        'actual_context_slots': len(expected_state_slots), 'passed': not failures,
        'route': 'independent_slope' if target_slope else 'context_tile',
        'failures': failures, 'scope': 'CPU palette layers, state records, actor rebasing; no native pixels',
    }


def sidecar(source, cases):
    layered = clone(source)
    for label, keep, neighbor in cases:
        if label not in ('fence', 'chest_sub', 'chest_main'):
            continue
        for pos in (keep, neighbor):
            value = layered.get(pos)
            layered.blocks[pos] = make_cell(foreground(value), ('minecraft:water', 0), actor_data(value))
    return layered


def audit():
    source = build(FIXTURE)
    cases = [(label, keep, neighbor) for label, keep, neighbor in CASES
             if source.blocks.get(keep, AIR) != AIR and source.blocks.get(neighbor, AIR) != AIR]
    rows = []
    for label, keep, neighbor in cases:
        for target in (keep, neighbor):
            rows.append({'category': label, 'route': 'context_builder',
                         'target': compare_target(source, target)})
    layered = sidecar(source, cases)
    sidecar_rows = []
    for label, keep, neighbor in cases:
        if label.startswith(('fence', 'chest')):
            for target in (keep, neighbor):
                sidecar_rows.append({'category': label + '_water_sidecar', 'route': 'context_builder',
                                     'target': compare_target(layered, target)})
    all_rows = rows + sidecar_rows
    failures = [row['category'] + ':' + str(row['target']['target'])
                for row in all_rows if not row['target']['passed']]
    return {
        'schema': 2, 'fixture': FIXTURE, 'size': source.size, 'blocks': len(source.blocks),
        'evidence_kind': 'production ContextPaletteBuilder CPU palette audit; no SDK tessellation or pixels',
        'context_cpu_passed': not failures, 'editor_passed': None,
        'missing_palette_passed': not failures, 'rows': all_rows,
        'background_sidecar': sidecar_rows, 'failures': failures,
        'limitations': ['This verifies the final virtual native palette only.',
                        'Native Combine, shader clipping, PaperDoll centering, and world pixels require live acceptance.',
                        'Editor transaction behavior is intentionally outside this helper.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    summary = {'evidence': str(args.output.resolve()), 'context_cpu_passed': report['context_cpu_passed'],
               'missing_palette_passed': report['missing_palette_passed'], 'failures': report['failures']}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    sys.exit(main())
