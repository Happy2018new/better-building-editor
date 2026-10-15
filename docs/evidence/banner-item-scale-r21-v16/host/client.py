"""Bounded native banner item views using only the proven v11 host."""
import copy
import json
import sys
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator

KEY = '_banner_scale_client_r21'
factory = api.GetEngineCompFactory()
level = api.GetLevelId()
assert PHASE == 'banner'


def control(saved, template, label, position, size, layer):
    result = saved['node'].CreateChildControl(template, label, None, True)
    assert result is not None
    saved['controls'].append(result)
    result.SetPosition(position)
    result.SetSize(size)
    result.SetLayer(layer)
    result.SetVisible(True)
    return result


def render(saved):
    results = []
    pose = POSES[CONFIG['pose']]
    for label, doll in saved['dolls']:
        params = {'entity_id': saved['actors'][label], 'scale': 1.4, 'render_depth': -50,
                  'init_rot_x': pose['pitch'], 'init_rot_y': pose['yaw'], 'init_rot_z': 0.}
        returned = doll.RenderEntity(params)
        assert returned
        results.append({'label': label, 'params': params, 'returned': returned,
                        'model_id_immediate_not_settled': doll.GetModelId()})
    saved['pose'] = CONFIG['pose']
    return results


if ACTION == 'setup':
    assert not hasattr(sys, KEY)
    owner = api.GetSystem('ModernProjection', 'ModernProjectionClientSystem')
    assert not owner.session.busy and not owner.session.projection_active
    assert owner.session.edit_job is None and owner.session.io_job is None
    assert api.GetTopUI() == 'hud_screen' and navigator.top is None
    assert not navigator.is_transitioning
    saved = {'phase': PHASE, 'actors': dict(ACTORS), 'rows': [], 'models': {},
             'bindings': {}, 'bind_attempted': False, 'scale_attempted': False, 'controls': [], 'dolls': [], 'pose': None}
    setattr(sys, KEY, saved)
    for label in LABELS:
        actor = saved['actors'][label]
        name = MODELS['known']
        row = {'label': label, 'actor': actor, 'model_name': name,
            'engine_type': factory.CreateEngineType(actor).GetEngineTypeStr(),
            'position': factory.CreatePos(actor).GetPos(),
            'client_current_dimension': factory.CreateGame(level).GetCurrentDimension(),
            'client_dimension_source': 'GameComponentClient.GetCurrentDimension'}
        saved['rows'].append(row)
        assert row['engine_type'] == 'modern_projection:anchor'
        assert row['position'] is not None and row['client_current_dimension'] == 0
        component = factory.CreateModel(actor)
        identity = component.SetModel(name)
        row['set_model_result'], row['created'] = identity, identity >= 0
        if identity >= 0:
            saved['models'][label] = identity
        assert identity >= 0, 'Known host failed; preserve journal, no retry'
        row['native_material_result'] = component.SetModelMaterial(identity, 'entity_for_skeleton')
        assert row['native_material_result']
    _result = json.dumps({'phase': PHASE, 'rows': saved['rows'], 'setup_once': True,
                          'api_result_is_not_render_proof': True})
else:
    saved = getattr(sys, KEY, None)
    if saved is None:
        assert ACTION in ('inspect', 'restore')
        _result = json.dumps({'journal_present': False, 'already_restored': True})
    else:
        assert saved['phase'] == PHASE
        if ACTION == 'restore':
            while saved['controls']:
                current = saved['controls'][-1]
                current.SetVisible(False)
                assert saved['node'].RemoveChildControl(current)
                saved['controls'].pop()
            saved['dolls'] = []
            for label, identity in list(saved['bindings'].items()):
                assert factory.CreateItem(level).SetBindBoneForBindItem(saved['actors'][label], identity, '', False)
                del saved['bindings'][label]
            for label in list(saved['models']):
                assert factory.CreateModel(saved['actors'][label]).ResetModel()
                del saved['models'][label]
            _result = json.dumps({'restored': True, 'phase': PHASE, 'controls': 0,
                'bindings': 0, 'models_reset': True, 'camera_untouched': True,
                'inventory_blocks_scene_untouched': True, 'rows': saved['rows']})
            delattr(sys, KEY)
        elif ACTION == 'inspect':
            _result = json.dumps({'journal_present': True, 'phase': PHASE,
                'rows': saved['rows'], 'models': saved['models'], 'pose': saved['pose'],
                'bind_attempted': saved['bind_attempted'], 'bindings': saved['bindings'],
                'scale_attempted': saved['scale_attempted'], 'scale_result': saved.get('scale_result'),
                'controls': len(saved['controls']),
                'ui_ids': dict((label, doll.GetModelId()) for label, doll in saved['dolls']),
                'banner_shape_accepted': False, 'thickness_accepted': False,
                'shared_scene_depth_accepted': False})
        else:
            if ACTION == 'mount':
                assert not saved['controls'] and CONFIG['pose'] == 'yaw90'
                assert not navigator.is_transitioning
                saved['node'] = api.GetTopUINode()
                assert saved['node'] is not None
                width, height = factory.CreateGame(level).GetScreenSize()
                background = control(saved, 'PyreactBase.image', 'banner_pose_background',
                                     (0., 0.), (width, height), 500)
                background.asImage().SetSprite('textures/ui/white')
                background.asImage().SetSpriteColor((.12, .12, .12))
                layout = []
                column = (width - 16.) / 2.
                for index, label in enumerate(LABELS):
                    x = 8. + index * column
                    size = min(80., column - 12., height * .30)
                    item = INPUTS['items'][label]
                    icon = control(saved, 'PyreactBase.item', 'banner_pose_icon_' + label,
                        (x + (column - size) / 2., 8.), (size, size), 502 + index * 4)
                    assert icon.asItemRenderer().SetUiItem(item['newItemName'], item['newAuxValue'],
                                                         False, item.get('userData'))
                    doll = control(saved, 'PyreactBase.paperDoll', 'banner_pose_doll_' + label,
                        (x, height * .32), (column - 6., height * .64), 503 + index * 4)
                    renderer = doll.asNeteasePaperDoll()
                    assert renderer is not None
                    saved['dolls'].append((label, renderer))
                    layout.append({'label': label, 'position': doll.GetPosition(), 'size': doll.GetSize()})
                _result = json.dumps({'screen': [width, height], 'layout': layout, 'render': render(saved)})
            elif ACTION == 'bind':
                assert saved['dolls'] and not saved['bind_attempted']
                assert saved['pose'] == 'yaw90' and CONFIG['pose'] == 'yaw90'
                saved['bind_attempted'] = True
                results = []
                for label in LABELS:
                    item = copy.deepcopy(INPUTS['items'][label])
                    before = copy.deepcopy(item)
                    identity = factory.CreateItem(level).BindItemToSkeletonModel(saved['actors'][label],
                        item, 'root', False, (0., 0., 0.), (0., 0., 0.), 1. / 16.)
                    assert identity >= 0, 'Preserve partial bindings; no blind replay'
                    saved['bindings'][label] = identity
                    assert item == before
                    results.append({'label': label, 'identity': identity, 'item': item,
                        'rotation': [0., 0., 0.], 'scale': 1. / 16., 'input_unmodified': True})
                _result = json.dumps({'bindings': results, 'render': render(saved)})
            elif ACTION == 'scale':
                assert saved['dolls'] and saved['pose'] == 'yaw90'
                assert LABELS == ['patterned'] and len(saved['bindings']) == 1
                assert not saved['scale_attempted'], 'Never replay scale mutation'
                saved['scale_attempted'] = True
                actor, identity = saved['actors']['patterned'], saved['bindings']['patterned']
                accepted = factory.CreateItem(level).SetBindItemScale(actor, identity, 1., False)
                saved['scale_result'] = accepted
                assert accepted is True, 'Retain binding for cleanup; no retry'
                _result = json.dumps({'scale': 1., 'old_scale': 1. / 16.,
                    'actor': actor, 'identity': identity, 'returned': accepted,
                    'rebound': False, 'render': render(saved)})
            elif ACTION == 'pose':
                assert len(saved['bindings']) == 2 and saved['dolls']
                assert CONFIG['pose'] != saved['pose'], 'Do not replay unchanged pose'
                _result = json.dumps({'render': render(saved), 'pose': CONFIG['pose']})
            else:
                raise ValueError(ACTION)
