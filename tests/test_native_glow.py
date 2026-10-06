"""Native emitter failure paths and the shader's bounded transport contract."""
import math
import json
import sys
import types
import unittest
import struct
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
    ux = variables['ux'] + (index if aura else ((index // 256) % 2) * 8192)
    uy = variables['uy'] + (0 if aura else (index % 256) * 64)
    color = [variables[key] for key in ('red', 'green', 'blue', 'alpha')]
    if not aura:
        color[0] += (index // 512) * 128
    assert all(0 <= value <= 255 for value in color)
    assert 0 <= ux < 16384 and 0 <= uy < 16384
    decoded = []
    for offset in (.5, 3):
        decoded.append(tuple(int(round((value * 4 + offset) / 65535. * 65535.)) // 4
                             for value in (ux, uy)))
    assert decoded[0] == decoded[1]
    color = tuple(int(round(value / 255. * 255.)) for value in color)
    return decoded[0], color


def decode_survey(variables, index, strike=False):
    return survey_attributes(*transport(variables, index), strike=strike)


def survey_attributes(data, color, strike=False):
    u, v = data
    r, g, b, a = color
    metadata = math.floor((r + .5) / 64.)
    compact_id = (v >> 6) + (u >> 13) * 256 + (metadata // 2) * 512
    u %= 8192
    return {'size': (1, 1, 1) if strike else ((u & 63) + 1, (u >> 6) + 1, (v & 63) + 1),
            'face': u if strike else None,
            'id': compact_id if compact_id < (149 if strike else 449)
                  else compact_id + (184 if strike else 1584),
            'theme': metadata % 2,
            'brightness': g / 170.,
            'density': .3 + (r - metadata * 64) / 40.,
            'orbit': b / 85.,
            'entered': (a - 1) / 254.}


def decode_aura(variables, index):
    return aura_attributes(*transport(variables, index, True))


def aura_attributes(data, color):
    u, v = data
    r, g, b, a = color
    metadata = tuple(math.floor((value + .5) / 64.) for value in (r, g, b))
    velocity_codes = tuple(value - bits * 64 for value, bits in zip((r, g, b), metadata))
    birth = sum(bits * multiplier for bits, multiplier in zip(metadata, (1, 4, 16))) / 63.
    phase = (a - 1) / 254.
    modes = v >> 10
    return {'seeds': ((u >> 8) + ((v & 3) << 6), (v >> 2) & 255),
            'id': (u & 255) + (128 if (u & 255) < 112 else 352),
            'velocity': tuple((code - 31) * (7. / 31.) for code in velocity_codes),
            'entered': min(1., birth + phase * (.7 / .65)), 'switching': phase,
            'birth': birth,
            'tool': modes & 1, 'motion': (modes >> 1) & 1, 'third_person': modes >> 2}


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
        self.assertEqual(0., self.particles.live[self.glow.eid]['variables']['ready'])
        self.callbacks.pop()()
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
        self.assertEqual([], self.callbacks)
        self.particles.fail_variables.clear()
        self.particles.calls.clear()
        self.assertTrue(self.glow.update(self.position, self.packet))
        self.assertEqual([('variable', eid, 'variable.blue', float(self.packet['blue']))], self.particles.calls)
        self.assertEqual(0., self.particles.live[eid]['variables']['ready'])
        self.callbacks.pop()()
        self.assertEqual(1., self.particles.live[eid]['variables']['ready'])
        self.assertEqual(1, len(self.particles.live))

    def test_create_position_and_ready_failures_retry_without_leaking_emitters(self):
        self.particles.fail_create = 1
        self.assertFalse(self.glow.update(self.position, self.packet))
        self.assertIsNone(self.glow.eid)
        self.particles.fail_variables.add('variable.ready')
        self.assertTrue(self.glow.update(self.position, self.packet))
        self.callbacks.pop()()
        eid = self.glow.eid
        self.assertEqual(0., self.particles.live[eid]['variables']['ready'])
        self.particles.fail_variables.clear()
        self.particles.fail_position = 1
        moved = (5., 65., -3.)
        self.assertFalse(self.glow.update(moved, self.packet))
        self.assertEqual(self.position, self.glow.position)
        self.assertEqual(0., self.particles.live[eid]['variables']['ready'])
        self.assertTrue(self.glow.update(moved, self.packet))
        self.callbacks.pop()()
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
        self.callbacks.pop()()
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

    def test_clearing_or_replacing_cancels_old_activation(self):
        self.glow.update(self.position, self.packet)
        old_eid, old_activate = self.glow.eid, self.callbacks.pop()
        self.glow.clear()
        old_activate()
        self.assertFalse(self.particles.live)
        self.glow.update(self.position, self.packet)
        new_eid = self.glow.eid
        old_activate()
        self.assertNotEqual(old_eid, new_eid)
        self.assertEqual(0., self.particles.live[new_eid]['variables']['ready'])
        activate = self.callbacks.pop()
        activate()
        self.particles.calls.clear()
        activate()
        self.assertEqual([], self.particles.calls)

    def test_failed_upload_invalidates_pending_activation_until_complete_again(self):
        self.glow.update(self.position, self.packet)
        old_activate = self.callbacks.pop()
        changed = dict(self.packet, green=200)
        self.particles.fail_variables.add('variable.green')
        self.assertFalse(self.glow.update(self.position, changed))
        self.particles.fail_variables.clear()
        self.assertTrue(self.glow.update(self.position, changed))
        old_activate()
        self.assertEqual(0., self.particles.live[self.glow.eid]['variables']['ready'])
        self.callbacks.pop()()
        self.assertEqual(1., self.particles.live[self.glow.eid]['variables']['ready'])

    def test_static_rebuild_waits_for_failed_removal_and_ignores_old_activation(self):
        self.glow.update(self.position, self.packet)
        old_eid, old_activate = self.glow.eid, self.callbacks.pop()
        changed = dict(self.packet, red=self.packet['red'] + 64)
        self.particles.fail_remove = 1
        self.assertFalse(self.glow.update(self.position, changed))
        old_activate()
        self.assertEqual({old_eid}, set(self.particles.live))
        self.assertEqual(0., self.particles.live[old_eid]['variables']['ready'])
        self.callbacks.pop()()
        self.assertTrue(self.glow.update(self.position, changed))
        new_eid = self.glow.eid
        self.assertNotEqual(old_eid, new_eid)
        old_activate()
        self.assertEqual(0., self.particles.live[new_eid]['variables']['ready'])
        self.callbacks.pop()()
        self.assertEqual(1., self.particles.live[new_eid]['variables']['ready'])

    def test_only_static_metadata_rebuilds_aura_not_velocity_or_phase(self):
        glow = NativeGlow(self.bridge, 'aura')
        first = aura_packet((1., 1., 1.), (0., 0., 0.), (77, 77, 0., 1.), 0.)[0]
        moving = aura_packet((1., 1., 1.), (7., -7., 7.), (77, 77, .5, 1.), 0.)[0]
        glow.update(self.position, first)
        eid = glow.eid
        glow.update(self.position, moving)
        self.assertEqual(eid, glow.eid)
        for flags, seeds, birth in (((0., 1., 1.), (77, 255), .4),
                                    ((0., 1., 0.), (77, 255), .4),
                                    ((0., 0., 0.), (77, 255), .4)):
            changed = aura_packet(flags, (1., 2., 3.), seeds + (.7, 1.), birth)[0]
            glow.update(self.position, changed)
            self.assertNotEqual(eid, glow.eid)
            eid = glow.eid
            self.assertEqual(1, len(self.particles.live))


class NativePacketTests(unittest.TestCase):
    def test_four_code_uv_cells_survive_atlas_inset_and_float32_unorm16(self):
        def f32(value):
            return struct.unpack('f', struct.pack('f', value))[0]
        for inset in (0., .125, .25, .375, .5):
            for quantize in (round, math.floor):
                for separate_size in (False, True):
                    for cell in range(16384):
                        for corner in (0, 1):
                            start, width = cell * 4 + .5 + inset, 2.5 - inset * 2
                            uv = (f32(f32(start / 65535.) + f32(width / 65535.) * corner)
                                  if separate_size else f32((start + width * corner) / 65535.))
                            self.assertTrue(0. <= uv <= 1.)
                            code = quantize(f32(uv * 65535.))
                            code = f32(f32(code / 65535.) * 65535.)
                            self.assertEqual((cell, corner), (int(code // 4), int(code % 4 >= 2)))

    def test_click_progress_interpolation_never_changes_orbit_theme_or_id(self):
        for theme in (0, 1):
            for entered in range(254):
                before = survey_packet((64, 128, 64), None, (entered / 254., 1., theme + .1, 1.), 1.)[0]
                after = survey_packet((64, 128, 64), None, ((entered + 1) / 254., 1., theme + .1, 1.), 1.)[0]
                data, old_color = transport(before, 971)
                new_data, new_color = transport(after, 971)
                self.assertEqual(data, new_data)
                for fraction in (.1, .25, .5, .75, .9):
                    color = tuple(a + (b - a) * fraction for a, b in zip(old_color, new_color))
                    decoded = survey_attributes(data, color)
                    self.assertEqual((2555, theme, 1., 1., 1.),
                                     (decoded['id'], decoded['theme'], decoded['orbit'],
                                      decoded['brightness'], decoded['density']))
                    self.assertAlmostEqual((entered + fraction) / 254., decoded['entered'])

    def test_aura_velocity_interpolation_keeps_seeds_flags_birth_and_other_axes_fixed(self):
        for birth in (0., .4, 1.):
            for axis in range(3):
                for code in range(62):
                    old_velocity = [0., 0., 0.]
                    new_velocity = [0., 0., 0.]
                    old_velocity[axis] = (code - 31) * 7. / 31.
                    new_velocity[axis] = (code - 30) * 7. / 31.
                    old = aura_packet((1., 1., 0.), old_velocity, (77, 255, .3, 1.), birth)[0]
                    new = aura_packet((1., 1., 0.), new_velocity, (77, 255, .3, 1.), birth)[0]
                    data, old_color = transport(old, 175, True)
                    new_data, new_color = transport(new, 175, True)
                    self.assertEqual(data, new_data)
                    expected = aura_attributes(data, old_color)
                    for fraction in (.1, .25, .5, .75, .9):
                        color = tuple(a + (b - a) * fraction for a, b in zip(old_color, new_color))
                        decoded = aura_attributes(data, color)
                        for key in ('id', 'seeds', 'tool', 'motion', 'third_person', 'birth', 'switching'):
                            self.assertEqual(expected[key], decoded[key])
                        for a, b, actual in zip(old_velocity, new_velocity, decoded['velocity']):
                            self.assertAlmostEqual(a + (b - a) * fraction, actual)

    def test_generated_uv_and_colors_preserve_hidden_sentinel_metadata(self):
        molang_math = types.SimpleNamespace(mod=lambda x,y:x % y, floor=math.floor)
        for kind, index in (('survey', 971), ('strike', 328), ('aura', 176)):
            components = json.loads((ROOT / ('resource_pack/particles/modern_projection_' + kind + '_glow.json')).read_text(encoding='utf8'))['particle_effect']['components']
            packet = (aura_packet((1., 1., 1.), (-7., 7., -7.), (255, 255, .5, 1.), 1.)[0]
                      if kind == 'aura' else survey_packet((64, 128, 64), 5 if kind == 'strike' else None, (1., 1.5, 1.1, 3.), 1.8)[0])
            values = types.SimpleNamespace(particle_lifetime=1048576 + index, ready=0, **packet)
            scope = {'v': values, 'math': molang_math}
            appearance = components['minecraft:particle_appearance_billboard']
            uv = [eval(expr, {'__builtins__': {}}, scope) for expr in appearance['uv']['uv']]
            expected_data, expected_color = transport(packet, index, kind == 'aura')
            self.assertEqual(expected_data, tuple(int(v // 4) for v in uv))
            self.assertEqual([2.5, 2.5], appearance['uv']['uv_size'])
            self.assertEqual(65535, appearance['uv']['texture_width'])
            self.assertEqual(65535, appearance['uv']['texture_height'])
            colors = components['minecraft:particle_appearance_tinting']['color']
            actual_rgb = [eval(expr, {'__builtins__': {}}, scope) * 255. for expr in colors[:3]]
            for actual, expected in zip(actual_rgb, expected_color):
                self.assertAlmostEqual(actual, expected)
            self.assertEqual('v.ready?v.alpha/255:0', colors[3])

    def test_only_last_carrier_expands_bounds_at_minimum_and_maximum_selection(self):
        molang_math = types.SimpleNamespace(mod=lambda x,y:x % y, pow=pow,
                                           floor=math.floor, sqrt=math.sqrt)
        for kind, visible in (('survey', 971), ('strike', 328), ('aura', 176)):
            path = ROOT / ('resource_pack/particles/modern_projection_' + kind + '_glow.json')
            components = json.loads(path.read_text(encoding='utf8'))['particle_effect']['components']
            self.assertEqual(visible + 1, components['minecraft:emitter_rate_instant']['num_particles'])
            for size in ((1, 1, 1), (4, 4, 4), (64, 128, 64)):
                packet = (aura_packet((1., 1., 1.), (0., 0., 0.), (255, 255, 1., 1.), 0.)[0]
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
        packet = aura_packet((1., 1., 1.), (-7., 7., -7.), (255, 255, 1., 1.), 1.)[0]
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
                    self.assertLessEqual(abs(decoded['entered'] - .527), .5 / 254.)
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
                        flags, velocity, seeds + (.731, 1.), .2)
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
