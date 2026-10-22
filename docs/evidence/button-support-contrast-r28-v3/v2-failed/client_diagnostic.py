# -*- coding: utf-8 -*-
"""Private native pair diagnostic draft. Importing it never contacts Minecraft.

Only the owner-scoped host may install this after an independently certified
two-cell full T02 baseline. Its raw records are not production certificates.
"""
from __future__ import unicode_literals
import copy
import re
import math
import sys
import time


BUTTON = (b'minecraft:stone_button', 0)
SUPPORT = (b'minecraft:stone', 0)
WHITE = (b'minecraft:white_concrete', 0)
MODEL_LABELS = ('combined_stone', 'support_stone', 'combined_white', 'support_white')
STAGES = (
    ('a_combined_stone', ((0, 'combined_stone'),)),
    ('a_support_stone', ((0, 'support_stone'),)),
    ('b_combined_white', ((0, 'combined_white'),)),
    ('b_support_white', ((0, 'support_white'),)),
    ('a2_combined_stone', ((0, 'combined_stone'),)),
    ('a2_support_stone', ((0, 'support_stone'),)),
)


def partition_full(data):
    """Preserve volume, indices, flags and button; only support color differs."""
    assert type(data) is dict
    assert data[b'volume'] == (16, 16, 10)
    assert data[b'common'] == {BUTTON: [827], SUPPORT: [1083]}
    assert not data[b'extra'] and not data[b'actor'] and not data[b'extraStates']
    assert data[b'eliminateAir'] is True and data[b'void'] is False
    assert set(data[b'states']) == {BUTTON, SUPPORT}
    assert data[b'states'][SUPPORT] == {}
    assert data[b'states'][BUTTON] == {b'button_pressed_bit': False, b'facing_direction': 0}
    assert data[b'states'][BUTTON][b'button_pressed_bit'] is False
    result = {}
    for label, material in (('stone', SUPPORT), ('white', WHITE)):
        combined = copy.deepcopy(data)
        if material != SUPPORT:
            indices = combined[b'common'].pop(SUPPORT)
            properties = combined[b'states'].pop(SUPPORT)
            combined[b'common'][material] = indices
            combined[b'states'][material] = properties
        result['combined_' + label] = combined
        only_support = copy.deepcopy(combined)
        del only_support[b'common'][BUTTON]
        del only_support[b'states'][BUTTON]
        result['support_' + label] = only_support
    return result


def walk(fiber):
    yield fiber
    for child in fiber.child_fibers:
        for descendant in walk(child):
            yield descendant


def buffer_state(preview):
    return copy.deepcopy(dict((key, getattr(preview, key, None)) for key in
        ('front', 'names', 'poses', 'pending', 'started', 'frames', 'initialized',
         'retry_at', 'restore', 'visible', 'scene_signature', 'geometry',
         'tint_color', 'depth_hidden')))


def validate_source(saved, link, expected_native, wire, nonce, fixture):
    """Bind the actual current creation and observer, without hashing in MC."""
    for key in ('raw_sha256', 'certificate_sha256', 'actual_native_serialization_sha256'):
        assert re.match(r'^[a-f0-9]{64}$', link[key])
    assert type(link['creation_serial']) is int and link['creation_serial'] > 0
    assert link['observer_config'] == saved['config']
    assert link['owner'] == saved['config']['owner']
    assert link['fixture'] == fixture == 'test.transforms.acceptance.t02'
    assert link['nonce'] == nonce
    records = [row for row in saved['records'] if row['serial'] == link['creation_serial']]
    assert len(records) == 1
    record = records[0]
    assert record['config'] == saved['config']
    assert record['nonce'] == nonce and record['fixture'] == fixture
    assert record['name'] == record['result'] == link['native_name']
    assert record['mode'] == 0 and record['deserialize_accepted'] is True
    assert record['native_serialized'] == link['native_serialized'] == wire(expected_native)
    assert record['deserialize_input'] == link['deserialize_input']
    assert record['editor_id'] == link['editor_id'] and record['document_id'] == link['document_id']
    frame = record['frame']
    assert list(frame['key']) == link['owner_key']
    assert list(frame['origin']) == link['origin']
    assert record['signature'] == link['signature']
    return record


class NativePairDiagnostic(object):
    """Uses the existing tile's two Dolls and never writes their layout/tint.

    Construction performs preflight reads only. freeze() is the first mutation;
    the caller must preserve this object and invoke restore() in its finally.
    """
    def __init__(self, session, navigator, bridge, token, source_link,
                 expected_native, type_name, wire, strict_saved):
        # A persistent host-owned object exists before this constructor starts.
        # These fields make finally safe even when a later preflight read fails.
        self.frozen, self.restoration = False, None
        self.models, self.creation_records, self.stage_records = {}, [], []
        assert re.match(r'^[a-f0-9]{32}$', token)
        assert strict_saved is sys._strict_cache_r27
        validate_source(strict_saved, source_link, expected_native, wire,
                        sys._blueprint_qa_nonce, sys._blueprint_qa_identity)
        self.strict_saved = strict_saved
        self.session, self.navigator, self.bridge = session, navigator, bridge
        self.token, self.source_link, self.wire = token, dict(source_link), wire
        self.native_inputs = partition_full(expected_native)
        self.editor, self.document = session.editor, session.editor.document
        assert not session.solo_layer
        assert len(self.document.blocks) == 2
        assert set(self.document.blocks) == {(3, 3, 27), (3, 4, 27)}
        assert session.camera_depth == 0. and session.camera_depth_pose == 0.
        assert tuple(session.camera_pose) == (35., -80., 12.)
        self.host = navigator.top._host
        scenes = [fiber for fiber in walk(self.host._root_fiber)
                  if type_name(fiber) == 'Scene' and fiber.props.get('session') is session]
        assert len(scenes) == 1
        self.scene = scenes[0]
        tiles = [fiber for fiber in walk(self.scene) if type_name(fiber) == 'PreviewTile'
                 and fiber.props['identity'] in session.tiles.region_owners
                 and tuple(fiber.props['identity']) == tuple(source_link['owner_key'])]
        assert len(tiles) == 1
        self.tile = tiles[0]
        self.key, self.registry = self.tile.props['identity'], self.tile.props['registry']
        self.entry = self.registry[self.key]
        self.dolls, self.surfaces, self.preview = self.entry
        self.part = session.tiles.parts[self.key]
        assert list(self.key) == source_link['owner_key']
        assert list(self.part['origin']) == source_link['origin']
        assert self.part['name'] == source_link['native_name']
        assert id(self.editor) == source_link['editor_id'] and id(self.document) == source_link['document_id']
        assert self.preview.ready(self.part['name']) and not self.part['pending']
        assert not getattr(self.preview, 'depth_hidden', False) and not getattr(self.preview, 'suspended', False)
        assert self.preview.initialized and not self.preview.restore
        assert all(ref.current is not None for ref in self.dolls + self.surfaces)
        assert all(ref.current.GetVisible() for ref in self.dolls)
        self.native_dolls = tuple(ref.current.asNeteasePaperDoll() for ref in self.dolls)
        assert all(self.native_dolls)
        self.original_buffer = buffer_state(self.preview)
        self.original_surface_visibility = tuple(ref.current.GetVisible() for ref in self.surfaces)
        assert self.original_surface_visibility[self.preview.front]
        assert not self.original_surface_visibility[1 - self.preview.front]
        self.pose = tuple(self.preview.poses[self.preview.front])
        self.layout = self.read_layout()
        assert self.layout[0] == self.layout[1]
        hooks = [slot for slot in self.scene.hooks if slot.get('type') == 'animation_frame']
        assert len(hooks) == 1
        self.hook = hooks[0]
        self.original_callback = self.hook['callback']
        assert self.hook['active'] and self.hook.get('_registration_id') == id(self.hook)
        assert self.host._animation_frames[id(self.hook)] is self.hook
        self.registration_id = self.hook['_registration_id']
        self.camera = self.read_camera()
        self.frames = 0
        self.frozen_callback = lambda now: self.count_frame(now)
        self.original_calibration = self.read_calibration()

    def read_layout(self):
        return tuple((tuple(ref.current.GetPosition()), tuple(ref.current.GetGlobalPosition()),
                      tuple(ref.current.GetSize())) for ref in self.dolls)

    def read_camera(self):
        s = self.session
        return (s.camera_pose, s.camera_pivot, s.camera_pan, s.camera_depth,
                s.camera_depth_pose, s.scene_origin, s.scene_size)

    def read_calibration(self):
        # Read the existing mounted tick closure; never invoke/recreate its camera.
        callback = self.original_callback
        code = getattr(callback, 'func_code', getattr(callback, '__code__', None))
        cells = getattr(callback, 'func_closure', getattr(callback, '__closure__', None))
        values = dict(zip(code.co_freevars, [cell.cell_contents for cell in cells]))
        required = ('canvas', 'clipping', 'clip_geometry', 'camera', 'unit', 'width', 'height')
        assert all(key in values for key in required)
        def rectangle(ref):
            control = ref.current
            assert control is not None
            return {'position': tuple(control.GetPosition()),
                    'global': tuple(control.GetGlobalPosition()),
                    'size': tuple(control.GetSize()), 'visible': control.GetVisible()}
        camera, unit = values['camera'], values['unit']()
        from modern_projection.projection.widgets import Theme
        game = self.strict_saved['factory'].CreateGame(self.bridge.level)
        logical_screen = tuple(game.GetScreenSize())
        physical_screen_info = game.GetScreenViewInfo()
        assert type(physical_screen_info) is tuple and len(physical_screen_info) == 4
        assert len(logical_screen) == 2 and min(logical_screen) > 0
        assert all(isinstance(value, (int, float)) and not math.isnan(value) and not math.isinf(value)
                   for value in logical_screen + physical_screen_info)
        assert min(physical_screen_info[:2]) > 0
        # Exact formula from frozen widgets.Theme.configure; old Theme has no cache.
        native_gui_scale = max(1., round(float(physical_screen_info[0]) / logical_screen[0]))
        canvas, clipping = rectangle(values['canvas']), rectangle(values['clipping'])
        assert canvas['visible'] and clipping['visible']
        assert unit > 0 and self.session.scene_scale > 0
        assert abs(self.pose[0] - unit*self.session.scene_scale/10.) < 1e-8
        projection_key = camera._projection_key
        expected_key = (camera.render_angles(), camera.pan, camera.pivot, self.session.scene_size,
                        values['width']*Theme.scale, values['height']*Theme.scale, unit)
        assert projection_key == expected_key
        return {'logical_screen': logical_screen, 'physical_screen_info': physical_screen_info,
                'scene_props': (values['width'], values['height']), 'theme_scale': Theme.scale,
                'native_gui_scale': native_gui_scale,
                'native_gui_scale_source': 'frozen_Theme_configure_formula_from_actual_Game_tuples',
                'Theme_has_native_gui_scale': hasattr(Theme, 'native_gui_scale'), 'cell_unit': unit,
                'scene_scale': self.session.scene_scale, 'native_pose': self.pose,
                'canvas': canvas, 'clipping': clipping,
                'clip_geometry': tuple(values['clip_geometry'].current),
                'source_configures_clips_children': True, 'GPU_scissor_readback': False,
                'surface_layout': tuple(dict((key, value) for key, value in rectangle(ref).items()
                                             if key != 'visible') for ref in self.surfaces),
                'doll_layout': self.read_layout(),
                'camera_projection_key': projection_key,
                'camera_projection': camera._projection_value,
                'camera_basis': camera._basis_value,
                'projection_scope': 'Actual mounted Camera cached affine coefficients; not native GPU matrix.'}

    def count_frame(self, unused_now):
        self.frames += 1

    def guard(self):
        assert sys._strict_cache_r27 is self.strict_saved
        validate_source(self.strict_saved, self.source_link, self.native_inputs['combined'], self.wire,
                        sys._blueprint_qa_nonce, sys._blueprint_qa_identity)
        assert self.frozen and self.hook['callback'] is self.frozen_callback
        assert self.hook.get('_registration_id') == self.registration_id
        assert self.host._animation_frames.get(self.registration_id) is self.hook
        assert self.hook['active'] and self.scene._mounted and self.tile._mounted
        assert self.navigator.top._host is self.host
        assert self.session.editor is self.editor and self.editor.document is self.document
        assert id(self.editor) == self.source_link['editor_id'] and id(self.document) == self.source_link['document_id']
        assert self.registry.get(self.key) is self.entry
        assert self.session.tiles.parts.get(self.key) is self.part
        assert self.part['name'] == self.source_link['native_name']
        assert self.read_camera() == self.camera and self.read_layout() == self.layout
        assert buffer_state(self.preview) == self.original_buffer
        assert self.read_calibration() == self.original_calibration

    def freeze(self):
        assert not self.frozen and self.hook['callback'] is self.original_callback
        self.hook['callback'] = self.frozen_callback
        self.frozen = True
        self.guard()

    def prepare_models(self, native_factory, level):
        self.guard()
        assert native_factory is self.strict_saved['factory']
        assert not self.models and not self.creation_records
        for label in MODEL_LABELS:
            data = copy.deepcopy(self.native_inputs[label])
            palette = native_factory.CreateBlock(level).GetBlankBlockPalette()
            assert palette is not None
            assert palette.DeserializeBlockPalette(data) is True
            actual = palette.SerializeBlockPalette()
            assert actual == data
            name = ('r28_button_support_contrast_%s_%s' % (self.token, label)).encode('ascii')
            record = {'label': label, 'name': name.decode('ascii'), 'unsupported_mode': 0,
                      'deserialize_input': self.wire(data), 'native_serialized': self.wire(actual)}
            self.creation_records.append(record)
            result = native_factory.CreateBlockGeometry(level).CombineBlockPaletteToGeometry(palette, name, 0)
            record['result'] = result
            assert result == name
            self.models[label] = result
            self.guard()

    def params(self, name, pose=None):
        scale, pitch, yaw = self.pose if pose is None else pose
        return {'block_geometry_model_name': name, 'scale': scale,
                'init_rot_x': pitch, 'init_rot_y': 0., 'init_rot_z': yaw}

    def submit_next(self):
        self.guard()
        assert set(self.models) == set(MODEL_LABELS)
        index = len(self.stage_records)
        assert index < len(STAGES)
        label, drawings = STAGES[index]
        row = {'label': label, 'start_frame': self.frames, 'started': time.time(),
               'drawings': [], 'pixels_qualified': False, 'production_certificate': False}
        self.stage_records.append(row)
        visible = set(slot for slot, unused_label in drawings)
        for slot, surface in enumerate(self.surfaces):
            surface.current.SetVisible(slot in visible, False)
        for slot, model_label in drawings:
            params = self.params(self.models[model_label])
            request = {'slot': slot, 'model_label': model_label, 'params': dict(params)}
            row['drawings'].append(request)
            request['result'] = self.native_dolls[slot].RenderBlockGeometryModel(params)
            assert request['result'] is True
        row['requested_surface_visibility'] = tuple(slot in visible for slot in range(2))
        self.guard()
        return label

    def state(self):
        self.guard()
        assert self.stage_records
        row = self.stage_records[-1]
        frames = self.frames - row['start_frame']
        age = time.time() - row['started']
        return {'token': self.token, 'source_link': self.source_link, 'stage': row,
                'frame_opportunities': frames, 'age': age, 'settled_gate': frames >= 6 and age >= .25,
                'native_layout': self.read_layout(), 'camera': self.read_camera(),
                'calibration': self.read_calibration(),
                'surface_visibility': tuple(ref.current.GetVisible() for ref in self.surfaces),
                'doll_visibility': tuple(ref.current.GetVisible() for ref in self.dolls),
                'document': self.document.to_data(), 'document_id': id(self.document), 'editor_id': id(self.editor),
                'shared_tint_control_id': id(self.preview.tint.current),
                'source_tint_setter_value': self.preview.tint_color,
                'native_tint_uniform_readback': False, 'native_mesh_vertices_readback': False,
                'pixels_qualified': False, 'production_certificate': False}

    def restore(self):
        if self.restoration is not None:
            return self.restoration
        errors, draws = [], []
        callback_owned = (getattr(self, 'hook', {}).get('callback') is
                          getattr(self, 'frozen_callback', object()))
        try:
            if self.frozen:
                assert self.scene._mounted and self.tile._mounted
                assert self.registry.get(self.key) is self.entry
                for slot, surface in enumerate(self.surfaces):
                    try:
                        surface.current.SetVisible(False, False)
                        name, pose = self.original_buffer['names'][slot], self.original_buffer['poses'][slot]
                        if name and pose is not None:
                            result = self.native_dolls[slot].RenderBlockGeometryModel(self.params(name, pose))
                            draws.append({'slot': slot, 'name': name, 'pose': pose, 'result': result})
                            assert result is True
                    except Exception as error:
                        errors.append('slot %d original draw: %r' % (slot, error))
                for slot, surface in enumerate(self.surfaces):
                    try:
                        surface.current.SetVisible(self.original_surface_visibility[slot], False)
                    except Exception as error:
                        errors.append('slot %d visibility: %r' % (slot, error))
        except Exception as error:
            errors.append(repr(error))
        finally:
            if callback_owned:
                self.hook['callback'] = self.original_callback
            elif self.frozen:
                errors.append('Diagnostic callback ownership changed; foreign callback was not overwritten')
            self.frozen = False
        self.restoration = {'token': getattr(self, 'token', None), 'callback_was_owned': callback_owned,
                            'original_native_submissions': draws, 'errors': errors,
                            'restored': not errors, 'needs_independent_source_snapshot': True,
                            'normal_shutdown_qualified': False, 'manual_issues_closed': 0}
        return self.restoration
