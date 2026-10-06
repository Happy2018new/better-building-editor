"""Native emitter failure paths and the shader's bounded transport contract."""
import math
import json
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack'))
from modern_projection.projection.native_glow import NativeGlow, aura_packet, survey_packet

ROOT = Path(__file__).resolve().parents[1]


class FakeParticleSystem:
    def __init__(self):
        self.live = {}
        self.calls = []
        self.next_id = 1
        self.fail_create = self.fail_position = self.fail_remove = 0
        self.fail_variables = set()

    def Create(self, name, position, rotation):
        assert type(name) is str and name.isascii()
        self.calls.append(('create', name, position))
        if self.fail_create:
            self.fail_create -= 1
            return 0
        eid = self.next_id
        self.next_id += 1
        self.live[eid] = {'name': name, 'position': position, 'variables': {'ready': 0.}}
        return eid

    def SetVariable(self, eid, name, value):
        assert type(name) is str and name.isascii()
        assert name.startswith('variable.')
        self.calls.append(('variable', eid, name, value))
        if name in self.fail_variables or eid not in self.live:
            return False
        self.live[eid]['variables'][name[9:]] = value
        return True

    def SetPos(self, eid, position):
        self.calls.append(('position', eid, position))
        if self.fail_position:
            self.fail_position -= 1
            return False
        if eid not in self.live:
            return False
        self.live[eid]['position'] = position
        return True

    def Remove(self, eid):
        self.calls.append(('remove', eid))
        if self.fail_remove:
            self.fail_remove -= 1
            return False
        self.live.pop(eid, None)
        return True

    def Exist(self, eid):
        self.calls.append(('exist', eid))
        return eid in self.live


def transport(variables, index, aura=False):
    """Reproduce Molang's atlas UVs and native UNORM16/UNORM8 attributes."""
    ux = variables['ux'] + (index if aura else 0)
    uy = variables['uy'] + (0 if aura else (index % 128) * 64)
    color = [variables[key] for key in ('red', 'green', 'blue', 'alpha')]
    if not aura:
        color[0] += index // 128
    assert all(0 <= value <= 255 for value in color)
    assert 0 <= ux < 8192 and 0 <= uy < 8192
    decoded = []
    for offset in (2, 6):
        decoded.append(tuple(int(round((value * 8 + offset) / 65536. * 65535.)) // 8
                             for value in (ux, uy)))
    assert decoded[0] == decoded[1]
    color = tuple(int(round(value / 255. * 255.)) for value in color)
    return decoded[0], color


def decode_survey(variables, index, strike=False):
    (u, v), (r, g, b, a) = transport(variables, index)
    compact_id = (v >> 6) + ((r & 7) << 7)
    return {'size': (1, 1, 1) if strike else ((u & 63) + 1, (u >> 6) + 1, (v & 63) + 1),
            'face': u if strike else None,
            'id': compact_id if compact_id < (149 if strike else 449)
                  else compact_id + (184 if strike else 1584),
            'theme': (r >> 3) & 1,
            'brightness': ((r >> 4) + ((g & 7) << 4)) / 84.,
            'density': ((g >> 3) + ((b & 3) << 5)) / 70.,
            'orbit': ((b >> 2) + ((a & 3) << 6)) / 85.,
            'entered': (a >> 2) / 63.}


def decode_aura(variables, index):
    (u, v), (r, g, b, a) = transport(variables, index, True)
    velocity_codes = ((v >> 11) + ((r & 15) << 2), (r >> 4) + ((g & 3) << 4), g >> 2)
    return {'seeds': ((u >> 8) + ((v & 7) << 5), (v >> 3) & 255),
            'id': (u & 255) + (128 if (u & 255) < 112 else 352),
            'velocity': tuple((code - 31) * (7. / 31.) for code in velocity_codes),
            'entered': (b & 127) / 127., 'switching': ((b >> 7) + ((a & 31) << 1)) / 63.,
            'tool': (a >> 5) & 1, 'motion': (a >> 6) & 1, 'third_person': a >> 7}


class NativeGlowTests(unittest.TestCase):
    def setUp(self):
        self.particles = FakeParticleSystem()
        self.callbacks = []
        self.components = []
        def component(entity):
            self.components.append(entity)
            return self.particles
        self.bridge = types.SimpleNamespace(
            factory=types.SimpleNamespace(CreateParticleSystem=component),
            later=lambda delay, callback: self.callbacks.append(callback))
        self.glow = NativeGlow(self.bridge, 'survey')
        self.position = (4., 65., -3.)
        self.packet = survey_packet((8, 16, 32), None, (1., 1., .1, 1.), 1.)[0]

    def test_steady_updates_reuse_emitter_and_component_without_native_uploads(self):
        self.assertTrue(self.glow.update(self.position, self.packet))
        self.assertEqual(1., self.particles.live[self.glow.eid]['variables']['ready'])
        self.assertEqual(('variable', self.glow.eid, 'variable.ready', 1.), self.particles.calls[-1])
        self.particles.calls.clear()
        for unused in range(30):
            self.assertTrue(self.glow.update(self.position, dict(self.packet)))
        self.assertEqual([None], self.components)
        self.assertEqual([], self.particles.calls)
        self.assertEqual(1, len(self.particles.live))

    def test_initial_failure_stays_hidden_then_retries_only_unaccepted_variables(self):
        self.particles.fail_variables.add('variable.blue')
        self.assertFalse(self.glow.update(self.position, self.packet))
        eid = self.glow.eid
        self.assertEqual(0., self.particles.live[eid]['variables']['ready'])
        self.assertNotIn('blue', self.glow.variables)
        self.particles.fail_variables.clear()
        self.particles.calls.clear()
        self.assertTrue(self.glow.update(self.position, self.packet))
        self.assertEqual([('variable', eid, 'variable.blue', float(self.packet['blue'])),
                          ('variable', eid, 'variable.ready', 1.)], self.particles.calls)
        self.assertEqual(1, len(self.particles.live))

    def test_create_position_and_ready_failures_retry_without_leaking_emitters(self):
        self.particles.fail_create = 1
        self.assertFalse(self.glow.update(self.position, self.packet))
        self.assertIsNone(self.glow.eid)
        self.particles.fail_variables.add('variable.ready')
        self.assertFalse(self.glow.update(self.position, self.packet))
        eid = self.glow.eid
        self.particles.fail_variables.clear()
        self.particles.fail_position = 1
        moved = (5., 65., -3.)
        self.assertFalse(self.glow.update(moved, self.packet))
        self.assertEqual(self.position, self.glow.position)
        self.assertEqual(0., self.particles.live[eid]['variables']['ready'])
        self.assertTrue(self.glow.update(moved, self.packet))
        self.assertEqual(moved, self.particles.live[eid]['position'])
        self.assertEqual(eid, self.glow.eid)
        self.assertEqual(1, len(self.particles.live))

    def test_clear_cancels_incomplete_registration_and_is_idempotent(self):
        self.particles.fail_variables.add('variable.blue')
        self.glow.update(self.position, self.packet)
        self.assertTrue(self.glow.clear())
        self.assertTrue(self.glow.clear())
        self.assertFalse(self.particles.live)
        self.assertEqual({}, self.glow.variables)
        self.assertEqual(1, len([call for call in self.particles.calls if call[0] == 'remove']))

    def test_failed_removal_hides_and_retries_after_owner_release_without_resurrection(self):
        self.glow.update(self.position, self.packet)
        eid = self.glow.eid
        self.particles.fail_remove = 1
        self.assertFalse(self.glow.clear())
        self.assertEqual(0., self.particles.live[eid]['variables']['ready'])
        self.assertFalse(self.glow.update(self.position, self.packet))
        self.assertEqual(1, len(self.particles.live))
        retry = self.callbacks.pop()
        retry()
        self.assertFalse(self.particles.live)
        self.assertTrue(self.glow.update(self.position, self.packet))
        new_eid = self.glow.eid
        retry()
        self.assertEqual({new_eid}, set(self.particles.live))

    def test_disappeared_emitter_is_recreated_only_after_a_failed_update(self):
        self.glow.update(self.position, self.packet)
        eid = self.glow.eid
        self.particles.live.clear()
        changed = dict(self.packet, alpha=0)
        self.assertFalse(self.glow.update(self.position, changed))
        self.assertIsNone(self.glow.eid)
        self.assertTrue(self.glow.update(self.position, changed))
        self.assertNotEqual(eid, self.glow.eid)
        self.assertEqual(1, len(self.particles.live))


class NativePacketTests(unittest.TestCase):
    def test_only_last_carrier_expands_bounds_at_minimum_and_maximum_selection(self):
        molang_math = types.SimpleNamespace(mod=lambda x,y:x % y, pow=pow,
                                           floor=math.floor, sqrt=math.sqrt)
        for kind, visible in (('survey', 971), ('strike', 328), ('aura', 176)):
            path = ROOT / ('resource_pack/particles/modern_projection_' + kind + '_glow.json')
            components = json.loads(path.read_text(encoding='utf8'))['particle_effect']['components']
            self.assertEqual(visible + 1, components['minecraft:emitter_rate_instant']['num_particles'])
            for size in ((1, 1, 1), (4, 4, 4), (64, 128, 64)):
                packet = (aura_packet((1., 1., 1., 1.), (0., 0., 0.), (255, 255, 1., 1.))[0]
                          if kind == 'aura' else
                          survey_packet(size, 5 if kind == 'strike' else None, (1., 1., .1, 1.), 1.)[0])
                expected_bound = (3. if kind == 'aura' else 4. if kind == 'strike'
                                  else math.sqrt(sum(v * v for v in size)) * .5 + 18.)
                for expression in components['minecraft:particle_appearance_billboard']['size']:
                    # Evaluate the actual generated single Molang conditional;
                    # no test-side size expression can conceal a bad threshold.
                    condition, choices = expression.split('?', 1)
                    when_true, when_false = choices.split(':', 1)
                    radii = []
                    for index in range(visible + 1):
                        values = types.SimpleNamespace(particle_lifetime=1048576 + index, **packet)
                        scope = {'v': values, 'math': molang_math}
                        branch = when_true if eval(condition, {'__builtins__': {}}, scope) else when_false
                        radii.append(eval(branch, {'__builtins__': {}}, scope))
                    self.assertEqual([.000001] * visible, radii[:-1])
                    self.assertAlmostEqual(expected_bound, radii[-1])

    def test_sentinels_follow_last_visible_id_without_packet_overflow(self):
        packet = survey_packet((64, 128, 64), None, (1., 1.5, 1.1, 3.), 1.8)[0]
        self.assertEqual(2554, decode_survey(packet, 970)['id'])
        self.assertEqual(2555, decode_survey(packet, 971)['id'])
        packet = survey_packet((1, 1, 1), 5, (.8, 1.5, .1, 3.), 1.8)[0]
        self.assertEqual(511, decode_survey(packet, 327, True)['id'])
        self.assertEqual(512, decode_survey(packet, 328, True)['id'])
        packet = aura_packet((1., 1., 1., 1.), (-7., 7., -7.), (255, 255, 1., 1.))[0]
        self.assertEqual(527, decode_aura(packet, 175)['id'])
        self.assertEqual(528, decode_aura(packet, 176)['id'])

    def test_maximum_selection_and_gold_starry_strike_packets_survive_native_attributes(self):
        for theme, face in ((0, None), (1, None), (0, 5)):
            with self.subTest(theme=theme, face=face):
                variables, appearance, density = survey_packet(
                    (64, 128, 64), face, (.527, 1.5, theme + .1, 3.), 1.8)
                for index in (0, 127, 128, 327) if face is not None else (0, 448, 449, 970):
                    decoded = decode_survey(variables, index, face is not None)
                    self.assertEqual((1, 1, 1) if face is not None else (64, 128, 64), decoded['size'])
                    self.assertEqual(face, decoded['face'])
                    self.assertEqual(theme, decoded['theme'])
                    self.assertEqual(1.5, decoded['brightness'])
                    self.assertEqual(1.8, decoded['density'])
                    self.assertEqual(3., decoded['orbit'])
                    self.assertEqual(appearance[0], decoded['entered'])
                    self.assertLessEqual(abs(decoded['entered'] - .527), .5 / 63.)
                    self.assertEqual(density, decoded['density'])
                self.assertEqual(511 if face is not None else 2554, decoded['id'])

    def test_every_clicked_face_and_reduced_motion_survives_packet(self):
        for face in range(6):
            variables, appearance, unused = survey_packet((1, 1, 1), face, (0., .35, .1, 0.), .3)
            decoded = decode_survey(variables, 149, True)
            self.assertEqual(face, decoded['face'])
            self.assertEqual(333, decoded['id'])
            self.assertEqual(0., decoded['entered'])
            self.assertEqual(0., decoded['orbit'])
            self.assertEqual(appearance[1], decoded['brightness'])

    def test_aura_seed_extremes_signed_motion_and_flags_match_actor_parameters(self):
        for seeds in ((0, 255), (255, 0), (255, 255)):
            for velocity in ((-7., 0., 7.), (-1.234, 2.718, -.01), (0., 0., 0.)):
                for flags in ((0., 0., 0.), (1., 1., 1.), (0., 1., 0.)):
                    variables, appearance, motion, layout = aura_packet(
                        (.527,) + flags, velocity, seeds + (.731, 1.))
                    for index in (0, 111, 112, 175):
                        decoded = decode_aura(variables, index)
                        self.assertEqual(seeds, decoded['seeds'])
                        self.assertEqual(motion[:3], decoded['velocity'])
                        self.assertEqual(appearance[0], decoded['entered'])
                        self.assertEqual(layout[2], decoded['switching'])
                        self.assertEqual(flags, (decoded['tool'], decoded['motion'], decoded['third_person']))
                        self.assertEqual(index + (128 if index < 112 else 352), decoded['id'])
                    self.assertAlmostEqual(math.sqrt(sum(v * v for v in motion[:3])), motion[3])
                    for raw, rendered in zip(velocity, motion):
                        self.assertLessEqual(abs(raw - rendered), 7. / 62.)


if __name__ == '__main__':
    unittest.main()
