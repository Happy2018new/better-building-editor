"""Read-only entity visual cleanup audit with an explicitly recorded spawn.

Usage: verify_entity_visual_cleanup.py <output.json> <spawn-x> <spawn-y> <spawn-z>
Requires MCDEV_SESSION_FILE and MCDEV_OWNER for the same owned instance.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from verify_debug_blueprints import Client, CLIENT, write_json
from verify_native_entity_appearances import execute

if len(sys.argv) != 5:
    raise SystemExit(__doc__)

FLAGS = ('_neighbor_visual_options_saved', '_blueprint_qa_saved', '_native_sign_probe',
         '_p0_entity_appearances', '_p0_entity_appearance_palettes', '_p0_visual_daylight',
         '_sign_editor_diag_hud_saved', '_blueprint_visual_saved', '_pot_editor_diag_hud_saved',
         '_p0_entity_appearance_selected', '_pot_editor_diag_model_names', '_neighbor_world_saved',
         '_sign_visual_hud_saved', '_p0_entity_appearance_entities', '_p0_entity_appearance_rows',
         '_context_environment_saved', '_native_sign_probe_rows', '_native_pot_fields',
         '_cold_native_actor_saved', '_neighbor_qa_saved', '_neighbor_qa_occupied',
         '_entities_r7_bed_occupancy_player', '_entities_r7_bed_player',
         '_copper_native_probe', '_copper_native_document', '_copper_native_origin',
         '_chest_top_public_snapshot', '_entities_r7_chest_top_player',
         '_entity_visual_r8_occupied', '_entity_visual_r8_document', '_entity_visual_r8_history')
report = {'completed': False, 'restored': False, 'read_only': True}
try:
    with Client(timeout=30) as client:
        code = 'import json,sys\n_result=json.dumps(dict((key,hasattr(sys,key)) for key in %r))' % (FLAGS,)
        report['server_flags'] = execute(client, code)
        report['client_flags'] = execute(client, code, True)
        report['client_state'] = execute(client, CLIENT + '''
_result=json.dumps({'projection_active':s.projection_active,'preparing':bool(b.preparing_entity),
 'projection_actor':b.entity,'projection_actors':len(b.projection_entities),
 'projection_mesh':b.projection_mesh,'projection_work':bool(b.projection_work),
 'busy':s.busy,'edit_job':bool(s.edit_job),'io_job':bool(s.io_job),
 'workspace_open':navigator.contains('modern_projection_workspace'),
 'navigation_transition':navigator.is_transitioning,'player':b.player_position.GetFootPos(),
 'camera':b.factory.CreateCamera(b.level).GetPosition()})
''', True)
        report['server_state'] = execute(client, '''import json
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
flight=factory.CreateFly(player)
_result=json.dumps({'foot':factory.CreatePos(player).GetFootPos(),
 'can_fly':flight.IsPlayerCanFly(),'flying':flight.IsPlayerFlying(),
 'daylight_cycle':factory.CreateGame(api.GetLevelId()).GetGameRulesInfoServer()['cheat_info']['daylight_cycle']})
''')
        state = report['client_state']
        report['restored'] = (not any(report['server_flags'].values()) and
                              not any(report['client_flags'].values()) and
                              not any(state[key] for key in
                                      ('projection_active', 'preparing', 'projection_actor',
                                       'projection_actors', 'projection_mesh', 'projection_work',
                                       'busy', 'edit_job', 'io_job', 'workspace_open',
                                       'navigation_transition')) and
                              report['server_state']['foot'] == [float(value) for value in sys.argv[2:5]] and
                              report['server_state']['can_fly'] is True and
                              report['server_state']['flying'] is False and
                              report['server_state']['daylight_cycle'] is True)
        report['completed'] = True
finally:
    write_json(Path(sys.argv[1]), report)
print(json.dumps(report))
raise SystemExit(0 if report['completed'] and report['restored'] else 1)
