"""Float-exact payload boundaries and the explicit shape/appearance contract."""
from collections import namedtuple
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.liquid_transport import (
    MAX_HEIGHT_ERROR, MAX_DEPTH_ERROR, PAYLOAD_TAG, PREVIEW_TAG_BYTE, UNSPECIFIED_OPACITY,
    RenderGroup, appearance_uniform, pack_group, preview_tag, validate_uniforms, with_preview_distance)

Surface = namedtuple('Surface', 'position layer heights faces texture_key flow_uv')


def surface(position=(0, 0, 0), heights=(0., 1., 1. / 255., 254. / 255.),
            faces=63, texture='still_water_grey', uv=None, layer=0):
    return Surface(position, layer, heights, faces, texture, uv)


class LiquidTransportTests(unittest.TestCase):
    def test_float32_preserves_four_independent_addresses_masks_rotations_and_heights(self):
        positions = ((0, 0, 0), (1, 0, 1), (2, 2, 2), (3, 3, 3))
        faces, rotations = (1, 2, 32, 63), (0, 1, 127, 255)
        corners = ((0, 255, 1, 254), (15, 16, 63, 64), (127, 128, 254, 255), (1, 254, 16, 15))
        inputs = tuple(surface(pos, tuple(value / 255. for value in heights), mask,
                               'flowing_water_grey', ('native_flow_v1', angle))
                       for pos, heights, mask, angle in zip(positions, corners, faces, rotations))
        payload = pack_group((0, 0, 0), inputs, (18, 52, 86), None, .4)
        validate_uniforms(payload)
        decoded = [struct.unpack('4f', struct.pack('4f', *group)) for group in payload]
        pairs = decoded[1] + decoded[2]
        for slot, (pos, heights, mask, angle) in enumerate(zip(positions, corners, faces, rotations)):
            address = int(decoded[0][slot]) & 63
            self.assertEqual(pos, (address % 4, address // 16, address // 4 % 4))
            self.assertEqual(mask, int(decoded[0][slot]) // 64 % 64)
            self.assertEqual(angle, int(decoded[0][slot]) // 4096)
            first, second = map(int, pairs[slot * 2:slot * 2 + 2])
            self.assertEqual(heights, (first % 256, first // 256, second % 256, second // 256))
        self.assertEqual((PAYLOAD_TAG, UNSPECIFIED_OPACITY, float(0x123456)), decoded[3][:3])

    def test_all_height_codes_and_intermediate_values_stay_within_declared_error(self):
        for step in range(2041):
            height = step / 2040.
            payload = pack_group((0, 0, 0), (surface(heights=(height,) * 4),), (255, 255, 255), .65, 1.)
            code = int(payload[1][0]) % 256
            self.assertLessEqual(abs(code / 255. - height), MAX_HEIGHT_ERROR + 1.e-15)

    def test_unused_slots_have_no_faces_and_no_heights(self):
        payload = pack_group((4, 8, 12), (surface((7, 11, 15), faces=32),), (255, 255, 255), .5, 1.)
        self.assertEqual((63. + 32. * 64., 0., 0., 0.), payload[0])
        self.assertEqual((0., 0.), payload[1][2:])
        self.assertEqual((0.,) * 4, payload[2])

    def test_unspecified_and_explicit_alpha_are_distinct_from_projection_opacity(self):
        self.assertEqual((PAYLOAD_TAG, -1., 0., .25), appearance_uniform((0, 0, 0), None, .25))
        self.assertEqual((PAYLOAD_TAG, .65, 16777215., .25), appearance_uniform((255, 255, 255), .65, .25))

    def test_invalid_or_unrepresentable_shape_is_rejected_before_transport(self):
        invalid = (
            surface(heights=(float('nan'),) * 4), surface(heights=(-.01,) * 4),
            surface(heights=(1.01,) * 4), surface(faces=64), surface(layer=True),
            surface(texture='minecraft:water'), surface(uv=('native_flow_v1', 256)),
            surface((4, 0, 0)), surface(heights=(.5,) * 3))
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                pack_group((0, 0, 0), (value,), (1, 2, 3), None, .5)
        for values in ((surface(),) * 2,
                       (surface(), surface((1, 0, 0), texture='still_lava')),
                       (surface(), surface((1, 0, 0), uv=('other_template', 0)))):
            with self.assertRaises(ValueError):
                pack_group((0, 0, 0), values, (1, 2, 3), None, .5)

    def test_float_payload_range_tag_and_opacity_are_validated(self):
        valid = pack_group((0, 0, 0), (surface(),), (1, 2, 3), None, 1.)
        for index, value in ((0, (1048576., 0., 0., 0.)), (1, (65536., 0., 0., 0.)),
                             (3, (0., -1., 0., 1.)), (3, (PAYLOAD_TAG, -.5, 0., 1.)),
                             (3, (PAYLOAD_TAG, -1., .5, 1.))):
            changed = list(valid)
            changed[index] = value
            with self.assertRaises(ValueError):
                validate_uniforms(tuple(changed))

    def test_signed16_preview_depth_and_tag_are_exact_in_float32(self):
        for code in range(65536):
            distance = (code - 32768) / 64.
            tag = preview_tag(distance)
            encoded = struct.unpack('f', struct.pack('f', tag))[0]
            self.assertEqual(tag, encoded)
            self.assertEqual(PREVIEW_TAG_BYTE, int(encoded) % 256)
            self.assertEqual(distance, (int(encoded) // 256 - 32768) / 64.)
        for distance in (-511.993, -1.001, -.001, .001, 1.001, 511.977):
            encoded = preview_tag(distance)
            self.assertLessEqual(abs((int(encoded) // 256 - 32768) / 64. - distance), MAX_DEPTH_ERROR)

    def test_preview_distance_helper_preserves_shape_appearance_and_identity(self):
        payload = pack_group((0, 0, 0), (surface(),), (18, 52, 86), None, .4)
        group = RenderGroup(('stable', 0), 'native_liquid_model', (0, 0, 0), payload)
        changed = with_preview_distance(group, -4.)
        self.assertEqual(group[:3], changed[:3])
        self.assertEqual(payload[:3], changed.uniforms[:3])
        self.assertEqual(payload[3][1:], changed.uniforms[3][1:])
        self.assertEqual(preview_tag(-4.), changed.uniforms[3][0])
        self.assertEqual(changed.uniforms, validate_uniforms(changed.uniforms))
        self.assertIs(changed, with_preview_distance(changed, -4.))
        self.assertEqual(group, with_preview_distance(changed, None))

    def test_invalid_preview_depth_and_noninteger_packet_are_rejected(self):
        for value in (True, float('nan'), float('inf'), -512.01, 512., '4'):
            with self.assertRaises(ValueError):
                preview_tag(value)
        valid = pack_group((0, 0, 0), (surface(),), (1, 2, 3), None, 1., preview_distance=0.)
        for tag in (valid[3][0] + .5, valid[3][0] + 1., -122.):
            changed = valid[:3] + ((tag,) + valid[3][1:],)
            with self.assertRaises(ValueError):
                validate_uniforms(changed)


if __name__ == '__main__':
    unittest.main()
