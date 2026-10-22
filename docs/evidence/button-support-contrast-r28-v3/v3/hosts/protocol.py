"""Bound support-color A/B/A with matched support-only controls; no launch."""
from client_diagnostic import STAGES
PAIR_PLAN = {'owner': 'r28-button-support-contrast-v3', 'identity': 'test.transforms.acceptance.t02',
    'points': [[3,3,27],[3,4,27]], 'yaw':35.0,'pitch':-80.0,'zoom':12.0,
    'native_volume':[16,16,10], 'button_index':827,'support_index':1083,
    'support_material_a':['minecraft:stone',0], 'support_material_b':['minecraft:white_concrete',0],
    'logical_translation':[0,0,0], 'stage_labels':[label for label,unused in STAGES],
    'stage_count':6,'model_count':4,'minimum_frames':6,'minimum_seconds':.25,
    'maximum_wait_seconds':2.0,'world_write_performed':False,
    'production_certificate_during_diagnostic':False,'source_unassigned':False,'launch_disabled':True}
