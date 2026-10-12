"""NBT adapters follow coordinate geometry and leave unrelated payloads intact."""
import copy
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.cell import actor_data, make_cell, transform
from projection.nbt_spatial import rebase, root_payload, scalar, transform_pair
from projection.visible_actor import compose_actor, entity_nbt, render_actor


FACES = ((0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0))
OPERATIONS = ('rotate_y90', 'rotate_y180', 'rotate_y270', 'mirror_x', 'mirror_y', 'mirror_z')


def vector(value, operation):
    x, y, z = value
    if operation.startswith('rotate_y'):
        for unused in range(int(operation[8:]) // 90):
            x, z = -z, x
    elif operation == 'mirror_x':
        x = -x
    elif operation == 'mirror_y':
        y = -y
    elif operation == 'mirror_z':
        z = -z
    return (x, y, z)


def tagged(value, kind):
    return {'__type__': kind, '__value__': value}


class NbtDirectionTests(unittest.TestCase):
    def test_client_fields_are_opaque_in_tagged_native_nbt(self):
        payload = {'id': tagged('FutureEntity', 8),
                   'facingDirection': tagged(2, 3),
                   'signStandingRotation': tagged(1, 3),
                   'chestIsLargeChest': True, 'chestMainSubChest': True,
                   'chestModelOffset': 0.0}
        byte_payload = {key.encode('ascii'): value for key, value in payload.items()}
        for source in (payload, byte_payload, tagged(payload, 10)):
            before = copy.deepcopy(source)
            for operation in OPERATIONS:
                self.assertEqual(before, transform_pair(source, (3, 2, 8), operation))
            self.assertEqual(before, source)

    def test_envelope_limits_client_rules_to_render_data_even_for_tagged_fields(self):
        render = {'facingDirection': tagged(2, 3), 'signStandingRotation': tagged(1, 3),
                  'chestIsLargeChest': tagged(True, 1),
                  'chestMainSubChest': tagged(True, 1), 'chestModelOffset': tagged(0.0, 5)}
        nbt = {'id': 'FutureEntity', 'facingDirection': 2, 'signStandingRotation': 1,
               'chestIsLargeChest': True, 'chestMainSubChest': True, 'chestModelOffset': 0.0}
        actor = compose_actor(render, nbt)
        before = copy.deepcopy(actor)
        normal = FACES[2]
        sign_normal = (-math.sin(math.pi / 8), 0, math.cos(math.pi / 8))
        for operation in OPERATIONS:
            changed = transform_pair(actor, (0, 0, 0), operation)
            client = render_actor(changed)
            self.assertEqual(FACES.index(vector(normal, operation)), scalar(client, 'facingDirection'))
            x, unused, z = vector(sign_normal, operation)
            expected_sign = int(round(math.atan2(-x, z) * 8 / math.pi)) % 16
            self.assertEqual(expected_sign, scalar(client, 'signStandingRotation'))
            mirrored = operation in ('mirror_x', 'mirror_z')
            self.assertEqual(not mirrored, scalar(client, 'chestMainSubChest'))
            self.assertEqual(-0.5 if mirrored else 0.0, scalar(client, 'chestModelOffset'))
            self.assertEqual(nbt, entity_nbt(changed))
        self.assertEqual(before, actor)

    def test_native_direction_adapter_preserves_similarly_named_client_fields(self):
        payload = {'id': tagged('ShulkerBox', 8), 'facing': tagged(2, 1),
                   'facingDirection': tagged(2, 3), 'signStandingRotation': tagged(1, 3)}
        for operation in OPERATIONS:
            changed = transform_pair(payload, (0, 0, 0), operation)
            self.assertEqual(FACES.index(vector(FACES[2], operation)), scalar(changed, 'facing'))
            self.assertEqual(payload['facingDirection'], changed['facingDirection'])
            self.assertEqual(payload['signStandingRotation'], changed['signStandingRotation'])

    def test_material_specific_client_fields_are_opaque_in_native_payloads_without_id(self):
        fixtures = (
            (('minecraft:skeleton_skull', 1),
             {'skullType': tagged(255, 3), 'rotation': tagged(22.5, 5)}),
            (('minecraft:bed', 0), {'direction': tagged(0, 3)}),
            (('minecraft:decorated_pot', 0),
             dict({'decoratedPotShredNamesSize': tagged(4, 3)},
                  **{'decoratedPotShredNames' + str(index): tagged('side' + str(index), 8)
                     for index in range(4)})),
        )
        for material, payload in fixtures:
            for source in (tagged(payload, 10), compose_actor(None, payload)):
                before = copy.deepcopy(source)
                for operation in OPERATIONS:
                    self.assertEqual(before, transform_pair(source, (0, 0, 0), operation, material))
                self.assertEqual(before, source)

    def test_editor_transforms_rebase_sign_root_coordinates_without_rewriting_nbt_client_names(self):
        from projection.model import Document, Editor
        from projection.sharing_codec import encode_steps, decode_steps
        source, center = (1, 0, 1), (2, 1, 2)
        nbt = {'id': tagged('Sign', 8), 'facingDirection': tagged(2, 3),
               'signStandingRotation': tagged(9, 3),
               'FrontText': {'Text': tagged('Front', 8)},
               'BackText': {'Text': tagged('Back', 8)},
               'Items': [{'tag': {'x': 80, 'facingDirection': 2}}]}
        nbt.update({axis: tagged(source[index], 3) for index, axis in enumerate(('x', 'y', 'z'))})
        original = make_cell(('minecraft:standing_sign', 1),
                             nbt=compose_actor({'signStandingRotation': 1}, nbt))
        offset = tuple(source[index] - center[index] for index in range(3))
        for operation in OPERATIONS:
            editor = Editor(Document((5, 3, 5), {source: original}))
            editor.select_box((1, 0, 1), (3, 2, 3))
            editor.run(operation)
            moved = vector(offset, operation)
            target = tuple(center[index] + moved[index] for index in range(3))
            payload = actor_data(editor.document.get(target))
            changed_nbt = entity_nbt(payload)
            self.assertEqual(target, tuple(scalar(changed_nbt, axis) for axis in ('x', 'y', 'z')))
            for field in ('facingDirection', 'signStandingRotation', 'FrontText', 'BackText', 'Items'):
                self.assertEqual(nbt[field], changed_nbt[field])
            shared = list(encode_steps(editor.document))[-1]['text']
            restored = list(decode_steps(shared))[-1]['document']
            self.assertEqual(payload, actor_data(restored.get(target)))
            editor.undo()
            self.assertEqual(original, editor.document.get(source))

    def test_all_six_shulker_faces_follow_coordinate_geometry_and_keep_byte_tags(self):
        for face, normal in enumerate(FACES):
            original = tagged({'id': tagged('ShulkerBox', 8), 'facing': tagged(face, 1)}, 10)
            for operation in OPERATIONS:
                changed = transform_pair(original, (0, 0, 0), operation)
                self.assertEqual(FACES.index(vector(normal, operation)), scalar(root_payload(changed), 'facing'))
                self.assertEqual(1, root_payload(changed)['facing']['__type__'])
            self.assertEqual(face, scalar(root_payload(original), 'facing'))

    def test_shulker_envelope_tracks_render_and_nbt_and_preserves_unknown_metadata(self):
        nbt = {'id': tagged('ShulkerBox', 8), 'facing': tagged(5, 1),
               'x': tagged(4, 3), 'y': tagged(2, 3), 'z': tagged(8, 3),
               'Items': tagged([{'tag': {'facing': 5, 'x': 400, 'y': 200, 'z': 800}}], 9)}
        actor = compose_actor({'facingDirection': 5}, nbt)
        actor['future_metadata'] = {'x': 80, 'facing': 5}
        original = copy.deepcopy(actor)
        changed = transform_pair(actor, (4, 2, 8), 'rotate_y90')
        self.assertEqual(3, scalar(entity_nbt(changed), 'facing'))
        self.assertEqual(3, render_actor(changed)['facingDirection'])
        self.assertEqual(actor['future_metadata'], changed['future_metadata'])
        self.assertEqual(nbt['Items'], entity_nbt(changed)['Items'])
        moved = rebase(changed, (3, -2, 5))
        self.assertEqual((7, 0, 13), tuple(scalar(entity_nbt(moved), axis) for axis in ('x', 'y', 'z')))
        self.assertEqual(actor['future_metadata'], moved['future_metadata'])
        self.assertEqual(original, actor)

    def test_byte_keys_and_byte_ids_are_preserved(self):
        actor = {b'id': {b'__type__': 8, b'__value__': b'ShulkerBox'},
                 b'facing': {b'__type__': 1, b'__value__': 1}}
        changed = transform_pair(actor, (0, 0, 0), 'mirror_y')
        self.assertEqual(0, changed[b'facing'][b'__value__'])
        self.assertEqual(actor[b'id'], changed[b'id'])
        self.assertEqual(set(actor), set(changed))

    def test_missing_unknown_or_invalid_fields_are_not_invented_or_coerced(self):
        for actor in ({'id': 'Unknown', 'facing': 5}, {'facing': 5},
                      {'id': 'ShulkerBox'}, {'id': 'ShulkerBox', 'facing': True},
                      {'id': 'ShulkerBox', 'facing': 6}, {'id': 'ShulkerBox', 'facing': 5.0}):
            self.assertEqual(actor, transform_pair(actor, (0, 0, 0), 'rotate_y90'))
        with_nested = {'id': 'ShulkerBox', 'facing': 4,
                       'Items': [{'tag': {'id': 'ShulkerBox', 'facing': 4, 'pairx': 5}}],
                       'Command': 'setblock 4 5 6 minecraft:chest',
                       'custom': {'x': 44, 'facing': 4, 'pairlead': 1}}
        changed = transform_pair(with_nested, (0, 0, 0), 'mirror_x')
        self.assertEqual(5, changed['facing'])
        for key in ('Items', 'Command', 'custom'):
            self.assertEqual(with_nested[key], changed[key])

    def test_shulker_native_cell_direction_survives_complete_serialization(self):
        from projection.model import Document
        from projection.sharing_codec import encode_steps, decode_steps
        actor = compose_actor({}, {'id': tagged('ShulkerBox', 8), 'facing': tagged(1, 1)})
        value = make_cell(('minecraft:purple_shulker_box', 0), nbt=actor)
        mirrored = transform(value, 'mirror_y', (0, 0, 0))
        self.assertEqual(0, scalar(entity_nbt(actor_data(mirrored)), 'facing'))
        self.assertEqual({}, render_actor(actor_data(mirrored)))
        doc = Document((1, 1, 1), {(0, 0, 0): mirrored})
        shared = list(encode_steps(doc))[-1]['text']
        restored = list(decode_steps(shared))[-1]['document']
        self.assertEqual(mirrored, restored.get((0, 0, 0)))

    def test_native_and_render_directions_obey_inverse_and_four_turn_closure(self):
        for face in range(6):
            actor = compose_actor({'facingDirection': face},
                                  {'id': 'ShulkerBox', 'facing': face})
            changed = actor
            for unused in range(4):
                changed = transform_pair(changed, (0, 0, 0), 'rotate_y90')
            self.assertEqual(actor, changed)
            for operation in OPERATIONS:
                inverse = {'rotate_y90': 'rotate_y270', 'rotate_y270': 'rotate_y90'}.get(operation, operation)
                changed = transform_pair(actor, (0, 0, 0), operation)
                self.assertEqual(actor, transform_pair(changed, (0, 0, 0), inverse))

    def test_native_double_chest_mirrors_roles_and_offsets_together(self):
        origin = (10, 3, -8)
        for offset in ((1, 0, 0), (0, 0, -1)):
            for lead in (False, True, 0, 1):
                nbt = {'id': tagged('Chest', 8), 'pairlead': tagged(lead, 1),
                       'renderlead': tagged(not lead if type(lead) is bool else 1 - lead, 1),
                       'pairx': tagged(origin[0] + offset[0], 3),
                       'pairz': tagged(origin[2] + offset[2], 3),
                       'Items': tagged([{'Slot': 0, 'tag': {'pairlead': lead}}], 9)}
                render = {'chestIsLargeChest': True, 'chestMainSubChest': bool(lead),
                          'chestModelOffset': 0.0 if lead else -0.5}
                actor = compose_actor(render, nbt)
                for operation in OPERATIONS:
                    mirrored = operation in ('mirror_x', 'mirror_z')
                    changed = transform_pair(actor, origin, operation)
                    changed_nbt = entity_nbt(changed)
                    expected_offset = vector(offset, operation)
                    self.assertEqual(origin[0] + expected_offset[0], scalar(changed_nbt, 'pairx'))
                    self.assertEqual(origin[2] + expected_offset[2], scalar(changed_nbt, 'pairz'))
                    self.assertEqual(bool(lead) != mirrored, bool(scalar(changed_nbt, 'pairlead')))
                    self.assertIs(type(scalar(changed_nbt, 'pairlead')), type(lead))
                    self.assertEqual(1, changed_nbt['pairlead']['__type__'])
                    self.assertEqual(bool(lead) == mirrored, bool(scalar(changed_nbt, 'renderlead')))
                    self.assertIs(type(scalar(changed_nbt, 'renderlead')), type(lead))
                    self.assertEqual(1, changed_nbt['renderlead']['__type__'])
                    self.assertEqual(bool(lead) != mirrored, render_actor(changed)['chestMainSubChest'])
                    self.assertEqual(nbt['Items'], changed_nbt['Items'])
                    inverse = {'rotate_y90': 'rotate_y270', 'rotate_y270': 'rotate_y90'}.get(operation, operation)
                    self.assertEqual(actor, transform_pair(changed, origin, inverse))

    def test_pairlead_without_valid_native_pair_is_preserved(self):
        for actor in ({'id': 'Chest', 'pairlead': True},
                      {'id': 'Custom', 'pairx': 1, 'pairz': 0, 'pairlead': True},
                      {'id': 'Chest', 'pairx': 1, 'pairz': 0, 'pairlead': 3}):
            changed = transform_pair(actor, (0, 0, 0), 'mirror_x')
            self.assertEqual(actor['pairlead'], changed['pairlead'])

    def test_renderlead_missing_invalid_or_unpaired_fields_are_not_invented(self):
        for actor in ({'id': 'Chest', 'renderlead': True},
                      {'id': 'Unknown', 'pairx': 1, 'pairz': 0, 'renderlead': 1},
                      {'id': 'Chest', 'pairx': True, 'pairz': 0, 'renderlead': False},
                      {'id': 'Chest', 'pairx': 1, 'pairz': 0, 'renderlead': 3},
                      {'id': 'Chest', 'pairx': 1, 'pairz': 0, 'renderlead': 0.0},
                      {'id': 'Chest', 'pairx': 1, 'pairz': 0, 'pairlead': 1}):
            changed = transform_pair(actor, (0, 0, 0), 'mirror_x')
            self.assertEqual(actor.get('renderlead'), changed.get('renderlead'))
            self.assertEqual('renderlead' in actor, 'renderlead' in changed)

    def test_native_double_chest_preserves_lead_complement_after_mirrors(self):
        origin = (10, 3, -8)
        for pairlead in (0, 1):
            actor = {b'id': tagged(b'Chest', 8),
                     b'pairlead': tagged(pairlead, 1),
                     b'renderlead': tagged(1 - pairlead, 1),
                     b'pairx': tagged(11, 3), b'pairz': tagged(-8, 3)}
            for operation in ('mirror_x', 'mirror_z'):
                changed = transform_pair(actor, origin, operation)
                self.assertEqual(1 - pairlead, scalar(changed, 'pairlead'))
                self.assertEqual(pairlead, scalar(changed, 'renderlead'))
                self.assertEqual(1, scalar(changed, 'pairlead') + scalar(changed, 'renderlead'))
                self.assertEqual(actor, transform_pair(changed, origin, operation))


if __name__ == '__main__':
    unittest.main()
