"""Behavioral regressions for per-target concrete support-copy ownership."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# This file can be copied into the repository tests/ without runtime fixtures.
ROOT = next(path for path in Path(__file__).resolve().parents
            if (path / 'behavior_pack/modern_projection/projection').is_dir())
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import render_context as context
from projection.block_registry import canonical
from projection.cell import make_cell
from projection.debug_blueprints import material
from projection.model import Document
from projection.nbt_spatial import rebase
from projection.render_layout import context_position, local_context_position

LEVER = ('minecraft:lever', 5)
WATER = material('water')
STONE = material('stone')


class WaterOwner(object):
    supported_names = frozenset(('minecraft:water', 'minecraft:flowing_water'))


def _normalized(value):
    if isinstance(value, dict):
        return tuple(sorted((repr(key), _normalized(child)) for key, child in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_normalized(child) for child in value)
    return value


def _tile(packed, target):
    if '_context_batches' in packed:
        origin = tuple(axis & ~15 for axis in target)
        matches = [data for corner, is_context, data in packed['_context_batches']
                   if corner == origin and is_context]
        if not matches:
            return []
        assert len(matches) == 1
        packed, center = matches[0], local_context_position(target)
    else:
        center = context_position(target)
    volume = packed['volume']
    shift = tuple(center[i] - target[i] for i in range(3))

    def relative(index):
        position = (index // volume[0] % volume[1], index // (volume[0] * volume[1]), index % volume[0])
        delta = tuple(position[i] - center[i] for i in range(3))
        return delta if max(abs(axis) for axis in delta) <= 1 else None

    rows = []
    for layer in ('common', 'extra'):
        for value, indices in packed[layer].items():
            for index in indices:
                delta = relative(index)
                if delta is not None:
                    rows.append((layer, value, delta))
    for name, actors in packed['actor'].items():
        for index, payload in actors.items():
            delta = relative(index)
            if delta is not None:
                rows.append(('actor', name, delta, _normalized(rebase(payload, tuple(-v for v in shift)))))
    return sorted(rows, key=repr)


def _entries(document, profile=None):
    source = document.palette_data()
    prepared = context.prepare_palette
    # The legacy reference API predates liquid_profile. Inject only its normal
    # preparation call so all three paths exercise the same real water owner.
    def with_owner(*args, **kwargs):
        kwargs['liquid_profile'] = profile
        return prepared(*args, **kwargs)
    with patch.object(context, 'prepare_palette', side_effect=with_owner):
        reference = context.prepare_context_palette(source, source)
    builder = context.ContextPaletteBuilder(document, source, liquid_profile=profile)
    for unused in builder.prepare():
        pass
    batches = context.prepare_context_batches(document, source, liquid_profile=profile)
    outputs = (reference, builder.data, batches)
    for position in document.blocks:
        rows = [_tile(output, position) for output in outputs]
        assert rows[0] == rows[1] == rows[2], (position, rows)
    return outputs


class ConcreteFloorContextTests(unittest.TestCase):
    def assert_support(self, outputs, target, expected, copied):
        row = ('common', expected, (0, -1, 0))
        for output in outputs:
            rows = _tile(output, target)
            self.assertEqual(copied, row in rows, (target, expected, rows))

    def test_all_archived_colors_keep_lever_wires_and_own_support_targets(self):
        for aux in range(16):
            legacy = ('minecraft:concrete', aux)
            concrete = canonical(legacy)
            for target, size in (((3, 2, 3), (8, 8, 8)), ((15, 16, 15), (32, 32, 32))):
                with self.subTest(alias=legacy, target=target):
                    below = (target[0], target[1] - 1, target[2])
                    wires = tuple((target[0] + dx, target[1], target[2] + dz)
                                  for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                    cells = {below: legacy, target: LEVER}
                    cells.update((position, material('redstone_wire')) for position in wires)
                    document = Document(size, cells)
                    before = copy.deepcopy(document.to_data())
                    outputs = _entries(document)
                    self.assert_support(outputs, target, concrete, False)
                    for output in outputs:
                        self.assertIn(('common', LEVER, (0, 0, 0)), _tile(output, target))
                        self.assertIn(('common', concrete, (0, 0, 0)), _tile(output, below))
                        for position in wires:
                            delta = tuple(below[i] - position[i] for i in range(3))
                            self.assertIn(('common', concrete, delta), _tile(output, position))
                    self.assertEqual(before, document.to_data())

    def test_wet_reversed_and_two_solid_cells_never_gain_dry_admission(self):
        for aux in range(16):
            legacy = ('minecraft:concrete', aux)
            concrete = canonical(legacy)
            for kind in ('wet_lever', 'wet_support', 'reverse_lever', 'reverse_support',
                         'two_solid_lever', 'two_solid_support', 'other_lever'):
                for profile in (None, WaterOwner()):
                    with self.subTest(alias=legacy, kind=kind, owner=profile is not None):
                        below, target = (1, 0, 1), (1, 1, 1)
                        lever, support = LEVER, legacy
                        if kind == 'wet_lever':
                            lever = make_cell(LEVER, WATER)
                        elif kind == 'wet_support':
                            support = make_cell(legacy, WATER)
                        elif kind == 'reverse_lever':
                            lever = make_cell(WATER, LEVER)
                        elif kind == 'reverse_support':
                            support = make_cell(WATER, legacy)
                        elif kind == 'two_solid_lever':
                            lever = make_cell(LEVER, STONE)
                        elif kind == 'two_solid_support':
                            support = make_cell(legacy, STONE)
                        else:
                            lever = ('minecraft:lever', 6)
                        document = Document((4, 4, 4), {below: support, target: lever})
                        before = copy.deepcopy(document.to_data())
                        outputs = _entries(document, profile)
                        if kind == 'reverse_support':
                            for output in outputs:
                                self.assertTrue(any(row[:3] in (
                                    ('common', concrete, (0, -1, 0)),
                                    ('extra', concrete, (0, -1, 0))) for row in _tile(output, target)))
                        else:
                            self.assert_support(outputs, target, concrete, True)
                        self.assertEqual(before, document.to_data())

    def test_actor_payload_is_removed_only_with_copied_support_body(self):
        below, target = (1, 0, 1), (1, 1, 1)
        support = ('minecraft:concrete', 14)
        concrete = canonical(support)
        payload = {'x': 1, 'y': 0, 'z': 1, 'review': {'keep': [1, 2, 3]}}
        document = Document((4, 4, 4), {
            below: make_cell(support, nbt=payload),
            target: make_cell(LEVER, nbt={'x': 1, 'y': 1, 'z': 1, 'lever_note': 17})})
        before = copy.deepcopy(document.to_data())
        outputs = _entries(document)
        self.assert_support(outputs, target, concrete, False)
        for output in outputs:
            self.assertFalse(any(row[0] == 'actor' and row[2] == (0, -1, 0)
                                 for row in _tile(output, target)))
            self.assertTrue(any(row[0] == 'actor' and row[2] == (0, 0, 0)
                                for row in _tile(output, below)))
            self.assertTrue(any(row[0] == 'actor' and row[2] == (0, 0, 0)
                                for row in _tile(output, target)))
        self.assertEqual(before, document.to_data())

    def test_cache_keeps_dry_and_suppressed_wet_cells_distinct(self):
        legacy, concrete = ('minecraft:concrete', 0), canonical(('minecraft:concrete', 0))
        cells = {}
        specs = (((2, 1, 2), LEVER, legacy, False),
                 ((6, 1, 2), make_cell(LEVER, WATER), legacy, True),
                 ((10, 1, 2), LEVER, make_cell(legacy, WATER), True),
                 ((14, 1, 2), make_cell(LEVER, WATER), make_cell(legacy, WATER), True))
        for target, lever, support, unused in specs:
            cells[target] = lever
            cells[(target[0], target[1] - 1, target[2])] = support
        document = Document((16, 4, 4), cells)
        before = copy.deepcopy(document.to_data())
        outputs = _entries(document, WaterOwner())
        for target, unused, unused_support, copied in specs:
            self.assert_support(outputs, target, concrete, copied)
        # One dry support is reused as both its own visible target and a copied
        # neighbor. Its cached writer plan must honor both ownership decisions.
        for output in outputs:
            self.assertIn(('common', concrete, (0, 0, 0)), _tile(output, (2, 0, 2)))
        self.assertEqual(before, document.to_data())

    def test_registry_resolved_logical_front_must_match_prepared_common(self):
        legacy = ('minecraft:concrete', 0)
        white, red = canonical(legacy), material('red_concrete')
        document = Document((4, 4, 4), {(1, 0, 1): legacy, (1, 1, 1): LEVER})
        prepare = context.prepare_palette

        def altered(*args, **kwargs):
            result = prepare(*args, **kwargs)
            if white in result['common']:
                result['common'][red] = result['common'].pop(white)
            return result

        with patch.object(context, 'prepare_palette', side_effect=altered):
            outputs = _entries(document)
        self.assert_support(outputs, (1, 1, 1), red, True)


if __name__ == '__main__':
    unittest.main()
