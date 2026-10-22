"""Close workspace first, then recover original probe markers if needed."""
import scene_game
import scene_restore


PROFILE = '''if hasattr(sys,'_product_water_saved_profile'):
 s.liquid_profile,s.grid=sys._product_water_saved_profile
 del sys._product_water_saved_profile
_result=True
'''

TIMING = '''if hasattr(sys,'_product_water_timing'):
 for cls,name,original in sys._product_water_timing['saved']:
  setattr(cls,name,original)
 del sys._product_water_timing
_result=True
'''

READ = '''_result=json.dumps({'remaining_markers':[name for name in
 ('_product_water_saved_profile','_product_water_timing','_blueprint_qa_saved',
 '_blueprint_visual_saved','_sign_visual_hud_saved','_neighbor_visual_options_saved')
 if hasattr(sys,name)],'navigator_open':navigator.top is not None,
 'navigator_transitioning':navigator.is_transitioning,
 'busy':s.busy,'edit_job':s.edit_job is not None,'io_job':s.io_job is not None,
 'projection_active':s.projection_active,
 'world_actors':len(b.projection_entities)+int(bool(b.entity)),
 'preparing_entity':bool(b.preparing_entity)})
'''


def restore_scene(client, run, blueprints):
    result = scene_restore.restore_scene(client, run, blueprints)
    for label, code in (('profile', PROFILE), ('timing', TIMING)):
        result['actions'].append({label: run(client, scene_game.PREFIX + code)})
    result['final_markers'] = run(client, scene_game.PREFIX + READ)
    state = result['final_markers']
    result['restored'] = result['restored'] and not state['remaining_markers'] and not any(
        state[key] for key in ('navigator_open', 'navigator_transitioning', 'busy', 'edit_job',
                              'io_job', 'projection_active', 'world_actors', 'preparing_entity'))
    assert result['restored'], state
    return result
