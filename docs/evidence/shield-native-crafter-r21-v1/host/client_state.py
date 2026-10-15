"""Journal and verify the unchanged camera; no camera mutation is performed."""
import json
import sys
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator

camera = api.GetEngineCompFactory().CreateCamera(api.GetLevelId())
current = {'position': camera.GetPosition(), 'rotation': camera.GetCameraRotation(),
           'fov': camera.GetFov(), 'top_ui': api.GetTopUI(),
           'workspace': navigator.contains('modern_projection_workspace')}
if ACTION == 'journal':
    assert not hasattr(sys, '_shield_crafter_client_r20')
    assert current['top_ui'] == 'hud_screen' and not current['workspace']
    sys._shield_crafter_client_r20 = current
    _result = json.dumps({'before': current, 'camera_mutation_planned': False})
elif ACTION == 'restore':
    before = getattr(sys, '_shield_crafter_client_r20', None)
    if before is None:
        _result = json.dumps({'present': False, 'camera_mutation_performed': False})
    else:
        assert current['top_ui'] == before['top_ui']
        assert current['workspace'] == before['workspace']
        assert current['fov'] == before['fov']
        assert max(abs(current['position'][i] - before['position'][i]) for i in range(3)) < .05
        assert max(abs(current['rotation'][i] - before['rotation'][i]) for i in range(3)) < .05
        _result = json.dumps({'before': before, 'after': current,
                              'camera_mutation_performed': False, 'camera_unchanged': True})
        del sys._shield_crafter_client_r20
else:
    raise ValueError('Unknown client action: ' + ACTION)
