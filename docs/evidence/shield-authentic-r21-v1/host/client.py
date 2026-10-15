"""Temporary native shield controls; supplied ACTION, INPUTS, ACTORS, CONFIG."""
import copy
import json
import sys
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator

KEY = '_shield_authentic_client_r21'
factory = api.GetEngineCompFactory()
level = api.GetLevelId()
owner = api.GetSystem('ModernProjection', 'ModernProjectionClientSystem')
session, bridge = owner.session, owner.bridge
camera = factory.CreateCamera(level)
FIELDS = ('page', 'name', 'view', 'focus_view', 'section', 'solo_layer',
          'focused', 'box_anchor', 'canvas_x', 'canvas_z', 'paste_origin',
          'paste_pinned', 'camera_pose', 'camera_yaw', 'camera_pitch', 'zoom',
          'camera_pan', 'camera_pivot', 'camera_depth', 'camera_depth_pose',
          'camera_focus_request', 'camera_reset_animated', 'progress',
          'direct_mode', 'grid')


def new_control(saved, template, label, position, size, layer):
    control = saved['node'].CreateChildControl(template, label, None, True)
    assert control is not None
    saved['controls'].append(control)
    control.SetPosition(position)
    control.SetSize(size)
    control.SetLayer(layer)
    control.SetVisible(True)
    return control


def clear_controls(saved):
    while saved['controls']:
        control = saved['controls'][-1]
        control.SetVisible(False)
        assert saved['node'].RemoveChildControl(control)
        saved['controls'].pop()
    saved['dolls'] = []


def configure(saved):
    results = []
    for label, doll in saved['dolls']:
        params = {'entity_id': saved['actors'][label], 'scale': 1.4,
                  'render_depth': -50, 'init_rot_x': CONFIG.get('pitch', 0.),
                  'init_rot_y': CONFIG.get('yaw', 0.), 'init_rot_z': 0.}
        returned = doll.RenderEntity(params)
        results.append({'label': label, 'params': params, 'returned': returned})
    return results


def mount(saved, workspace):
    assert not saved['controls'] and not navigator.is_transitioning
    if workspace:
        assert navigator.contains('modern_projection_workspace')
    saved['node'] = api.GetTopUINode()
    assert saved['node'] is not None
    width, height = factory.CreateGame(level).GetScreenSize()
    if not workspace:
        background = new_control(saved, 'PyreactBase.image', 'r21_shield_background',
                                 (0., 0.), (width, height), 500)
        background.asImage().SetSprite('textures/ui/white')
        background.asImage().SetSpriteColor((.12, .12, .12))
    labels = ('plain', 'authentic', 'sword')
    layout = []
    column = (width - 16.) / 3.
    for index, label in enumerate(labels):
        x = 8. + index * column
        if not workspace:
            icon_size = min(80., column - 12., height * .30)
            item = INPUTS['items'][label]
            icon = new_control(saved, 'PyreactBase.item', 'r21_shield_item_' + label,
                               (x + (column - icon_size) / 2., 8.),
                               (icon_size, icon_size), 502 + index * 4)
            returned = icon.asItemRenderer().SetUiItem(
                item['newItemName'], item['newAuxValue'], False, item.get('userData'))
            assert returned
            layout.append({'label': label, 'native_ui': True, 'payload': item,
                           'position': icon.GetPosition(), 'size': icon.GetSize(),
                           'returned': returned})
        top = height * (.32 if not workspace else .20)
        size = (column - 6., height * (.64 if not workspace else .72))
        doll = new_control(saved, 'PyreactBase.paperDoll', 'r21_shield_doll_' + label,
                           (x, top), size, 503 + index * 4)
        renderer = doll.asNeteasePaperDoll()
        assert renderer is not None
        saved['dolls'].append((label, renderer))
        layout.append({'label': label, 'native_ui': False,
                       'position': doll.GetPosition(), 'size': doll.GetSize()})
    return {'screen': [width, height], 'controls': layout,
            'workspace_candidate_only': workspace, 'render': configure(saved)}


if ACTION == 'journal':
    assert not hasattr(sys, KEY)
    assert not session.busy and not session.projection_active
    assert session.edit_job is None and session.io_job is None
    assert api.GetTopUI() == 'hud_screen' and navigator.top is None
    assert not navigator.is_transitioning
    saved = {'controls': [], 'dolls': [], 'actors': dict(ACTORS), 'bindings': {},
             'models': {}, 'editor': session.editor,
             'fields': dict((key, getattr(session, key)) for key in FIELDS),
             'camera': {'position': camera.GetPosition(), 'rotation': camera.GetCameraRotation(),
                        'fov': camera.GetFov(), 'pitch_lock': camera.IsModCameraLockPitch(),
                        'yaw_lock': camera.IsModCameraLockYaw()},
             'workspace_opened': False, 'camera_changed': False}
    setattr(sys, KEY, saved)
    assert not saved['camera']['pitch_lock'] and not saved['camera']['yaw_lock']
    for label, entity in saved['actors'].items():
        assert factory.CreateEngineType(entity).GetEngineTypeStr() == 'modern_projection:anchor'
        model = factory.CreateModel(entity)
        identity = model.SetModel('modern_projection_item_icon_d19ff5bff710ac9e')
        assert identity >= 0
        assert model.SetModelMaterial(identity, 'entity_for_skeleton')
        saved['models'][label] = identity
    _result = json.dumps({'journaled': True, 'actors': saved['actors'],
                          'models': saved['models'], 'camera': saved['camera']})
else:
    saved = getattr(sys, KEY, None)
    if ACTION == 'restore' and saved is None:
        _result = json.dumps({'restored': True, 'already_absent': True})
    else:
        assert saved is not None
        if ACTION == 'mount_native':
            _result = json.dumps(mount(saved, False))
        elif ACTION == 'bind':
            assert not saved['bindings']
            component = factory.CreateItem(level)
            results = []
            for label in ('plain', 'authentic', 'sword'):
                item = copy.deepcopy(INPUTS['items'][label])
                before = copy.deepcopy(item)
                identity = component.BindItemToSkeletonModel(saved['actors'][label], item,
                    'root', False, (0., 0., 0.), (90., 0., 0.), 1. / 16.)
                assert identity >= 0
                saved['bindings'][label] = identity
                assert item == before
                results.append({'label': label, 'identity': identity, 'item': item,
                    'rotation': [90., 0., 0.], 'scale': 1. / 16., 'input_unmodified': True})
            _result = json.dumps({'bindings': results, 'render': configure(saved)})
        elif ACTION == 'pose':
            _result = json.dumps({'render': configure(saved), 'config': CONFIG})
        elif ACTION == 'world':
            clear_controls(saved)
            origin = CONFIG['origin']
            target = (origin[0] + 1., origin[1] + .5, origin[2] + .05)
            offset = (-2., .35, -3.5) if CONFIG.get('oblique') else (0., 0., -4.)
            position = tuple(target[i] + offset[i] for i in range(3))
            rotation = api.GetRotFromDir(tuple(target[i] - position[i] for i in range(3)))
            saved['camera_changed'] = True
            camera.DepartCamera()
            camera.LockModCameraPitch(True)
            camera.LockModCameraYaw(True)
            assert camera.SetCameraPos(position)
            assert camera.SetCameraRotation((rotation[0], rotation[1] + 180., 0.))
            _result = json.dumps({'target': target, 'position': camera.GetPosition(),
                'rotation': camera.GetCameraRotation(), 'frame_reference': True})
        elif ACTION == 'editor_open':
            from modern_projection.projection.model import Document
            from modern_projection.projection.debug_blueprints import material
            clear_controls(saved)
            if saved['camera_changed']:
                camera.LockModCameraPitch(False)
                camera.LockModCameraYaw(False)
                camera.ResetCameraPos()
                camera.UnDepartCamera()
                assert camera.SetCameraRotation(tuple(saved['camera']['rotation']))
                saved['camera_changed'] = False
            document = Document((3, 3, 3), name='Owned authentic native shield candidate')
            document.blocks[(1, 0, 1)] = material('stone')
            session._loaded(document)
            session.grid = False
            session.camera_view(0., 0., 2.)
            owner.open_workspace()
            saved['workspace_opened'] = True
            _result = json.dumps({'workspace_requested': True, 'scene': 'one stone only',
                'shared_depth_accepted': False})
        elif ACTION == 'mount_editor':
            _result = json.dumps(mount(saved, True))
        elif ACTION == 'restore':
            clear_controls(saved)
            for label, identity in list(saved['bindings'].items()):
                assert factory.CreateItem(level).SetBindBoneForBindItem(
                    saved['actors'][label], identity, '', False)
                del saved['bindings'][label]
            if saved['workspace_opened']:
                session.tiles.cancel()
                session.editor = saved['editor']
                for key, value in saved['fields'].items():
                    setattr(session, key, value)
                session.model_revision = None
                session.camera_reset_revision += 1
                session.refresh_preview()
                session.emit()
                if navigator.contains('modern_projection_workspace'):
                    navigator.pop()
            if saved['camera_changed']:
                camera.LockModCameraPitch(False)
                camera.LockModCameraYaw(False)
                camera.ResetCameraPos()
                camera.UnDepartCamera()
                assert camera.SetCameraRotation(tuple(saved['camera']['rotation']))
            camera.LockModCameraPitch(saved['camera']['pitch_lock'])
            camera.LockModCameraYaw(saved['camera']['yaw_lock'])
            current = {'position': camera.GetPosition(), 'rotation': camera.GetCameraRotation(),
                       'fov': camera.GetFov(), 'pitch_lock': camera.IsModCameraLockPitch(),
                       'yaw_lock': camera.IsModCameraLockYaw()}
            assert max(abs(current['position'][i] - saved['camera']['position'][i]) for i in range(3)) < .05
            assert max(abs(current['rotation'][i] - saved['camera']['rotation'][i]) for i in range(3)) < .05
            assert current['fov'] == saved['camera']['fov']
            assert session.editor is saved['editor']
            assert not navigator.contains('modern_projection_workspace')
            _result = json.dumps({'restored': True, 'camera_before': saved['camera'],
                'camera_after': current, 'bindings_removed': True, 'controls_removed': True,
                'editor_restored': True, 'workspace_restored': True})
            delattr(sys, KEY)
        else:
            raise ValueError(ACTION)
