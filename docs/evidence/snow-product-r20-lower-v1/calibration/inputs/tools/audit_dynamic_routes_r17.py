"""Plan and acquire bounded public dynamic-block evidence on an assigned game.

The plan distinguishes native observations from product qualification. The run
action never launches games, changes desktop focus, or claims pixel acceptance.
It reuses the ordinary editor/full/missing entry points and keeps slow flipbook
sampling separate from static-body controls.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = 'tools/data/render_compatibility_nemc_3.10.0.420447.json'
FLIPBOOKS = 'docs/reference/native_animations/nemc_3.10.0.420447/textures/flipbook_textures.json'
ROUTES = ('editor', 'full', 'missing')
SPECIALIZED = frozenset(('water', 'flowing_water', 'bubble_column', 'cauldron',
                         'end_portal', 'end_gateway', 'enchanting_table',
                         'lectern', 'mob_spawner', 'trial_spawner'))
HEADS = ('creeper_head', 'dragon_head', 'piglin_head', 'player_head',
         'skeleton_skull', 'wither_skeleton_skull', 'zombie_head')
PISTONS = ('piston', 'sticky_piston', 'piston_arm_collision',
           'sticky_piston_arm_collision')
SOURCE_FILES = (INVENTORY, FLIPBOOKS,
                'behavior_pack/modern_projection/projection/debug_compatibility_blueprints.py')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_cases():
    sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
    from projection.debug_compatibility_blueprints import CASES
    return CASES


def make_plan():
    import json5
    inventory = json.loads((ROOT / INVENTORY).read_bytes())
    flipbooks = json5.loads((ROOT / FLIPBOOKS).read_text(encoding='utf8'),
                           allow_duplicate_keys=False)
    periods = {}
    for entry in flipbooks:
        periods.setdefault(entry['atlas_tile'], []).append(entry.get('ticks_per_frame', 1))
    linked = {row['name']: row for row in inventory['flipbook_inventory']['rows']}
    ordinary = set(inventory['ordinary_flipbook_names']) - {'minecraft:chemical_heat'}
    nbt = set(inventory['nbt_flipbook_names'])
    rows = []
    catalogue = {}
    for fixture, cases in public_cases().items():
        for case in cases:
            catalogue.setdefault(case['name'], []).append((fixture, case))
        if not fixture.startswith('test.dynamic.'):
            continue
        for case in cases:
            name = case['name']
            short = name.split(':', 1)[1]
            if short in SPECIALIZED:
                continue
            associated = linked.get(name, {}).get('associations', ())
            ticks = sorted({period for association in associated
                            for period in periods.get(association['tile'], ())})
            # 300 ticks/frame prismarine requires a genuinely different phase.
            delay = max(ticks or [0]) / 20. + .15 if ticks else 0.
            rows.append({'fixture': fixture, 'case': case['id'], 'name': name,
                         'material': case['material'], 'variant': case['variant'],
                         'routes': ROUTES, 'ordinary_flipbook': name in ordinary,
                         'nbt_flipbook': name in nbt, 'ticks_per_frame': ticks,
                         'sample_interval_seconds': max(.35, delay),
                         'native_observation': native_observation(short),
                         'product_qualification': 'pending',
                         'source_condition': ('state_may_disable_animation' if case['variant'] == 'state'
                                              else 'default_may_disable_animation')})
    gaps = []
    for name in HEADS + PISTONS:
        captures = catalogue.get('minecraft:' + name, ())
        gaps.append({'name': 'minecraft:' + name,
                     'public_default_cases': [{'fixture': f, 'case': c['id']} for f, c in captures],
                     'product_qualification': 'pending',
                     'required_fixture': ('authentic_client_actor_with_valid_head_type_and_static_or_powered_pose'
                                          if name in HEADS else
                                          'extended_body_plus_matching_arm_cell_with_orientation'),
                     'negative_evidence_valid': False})
    return {'schema_version': 1, 'engine': '3.10.0.420447',
            'registry_migration': False, 'particles_required': False,
            'source_sha256': {name: digest(ROOT / name) for name in SOURCE_FILES},
            'rows': rows, 'fixture_gaps': gaps,
            'native_only_references': {
                'fire': 'docs/evidence/r15-solo-runtime/fire-v2/report.json',
                'lantern': 'docs/evidence/r15-solo-runtime/lantern-v3/report.json',
                'heads': 'docs/evidence/native-render-profile-r15/90-head-item-setup/report.json'},
            'required_controls': ('public_case_source_unchanged', 'support_visible',
                                  'target_hidden_support_retained', 'same_camera_timed_frames',
                                  'editor_full_missing_distinct', 'snapshot_state_checked'),
            'pixel_acceptance_claimed': False}


def native_observation(short):
    if short in ('fire', 'soul_fire'):
        return 'body_and_temporal_change_seen_on_clean_combine'
    if 'lantern' in short:
        return 'body_seen_temporal_product_qualification_pending'
    if short.startswith('prismarine') or short in ('sculk', 'sculk_vein', 'sculk_sensor',
                                                  'calibrated_sculk_sensor', 'sculk_catalyst',
                                                  'sculk_shrieker'):
        return 'limited_body_observation_temporal_qualification_pending'
    return 'no_effective_product_qualification'


def document(row, visible=True):
    from projection.debug_compatibility_blueprints import source_document, FOCUS
    from projection.cell import AIR
    doc = source_document(row['fixture'], row['case'])
    if not visible:
        for position in tuple(doc.blocks):
            if position[1] >= FOCUS[1]:
                doc.set_cell(position, AIR)
    return json.loads(json.dumps(doc.to_data()))


def runtime_sources(project):
    roots = ('behavior_pack/modern_projection', 'resource_pack/shaders',
             'resource_pack/materials')
    result = {}
    for root in roots:
        for path in sorted((project / root).rglob('*')):
            if path.is_file() and path.suffix in ('.py', '.vertex', '.fragment', '.material'):
                result[path.relative_to(project).as_posix()] = digest(path)
    for name in ('resource_pack/blocks.json', 'resource_pack/textures/terrain_texture.json'):
        result[name] = digest(project / name)
    return result


def acquire(args, selected):
    from _session import load_session
    from audit_native_visual_r15 import save
    from audit_native_coordinates_r15 import LOAD, PROJECT
    from probe_banner_product_r16 import BannerAudit
    from probe_portal_product_r16 import PortalAudit
    from verify_debug_blueprints import CLIENT
    project = args.project.resolve(strict=True)
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != project:
        raise ValueError('Project does not own this instance')
    if args.output.exists():
        raise ValueError('Choose a fresh output directory')
    args.output.mkdir(parents=True)
    os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '1'
    audit = BannerAudit(args)
    report = {'schema_version': 1, 'engine': '3.10.0.420447', 'completed': False,
              'restored': False, 'source_sha256': runtime_sources(project),
              'rows': {}, 'captures': {}, 'cleanup_errors': [],
              'pixel_acceptance_claimed': False, 'plan': selected,
              'session': {key: session[key] for key in ('id', 'owner', 'game_pid', 'game_identity')}}
    installed = False
    started = time.monotonic()

    def checkpoint():
        save(args.output / 'report.json', report)

    def load(row, visible):
        data = document(row, visible)
        result = audit.execute('load', LOAD % ('production', (), json.dumps(data)))
        audit.settle()
        actual = audit.execute('saved_source', CLIENT + '_result=json.dumps(s.editor.document.to_data())')
        if actual != data:
            raise ValueError('Loading changed the public case payload')
        return {'loaded': result, 'saved_document': data}

    try:
        report['admission'] = audit.execute('admission', CLIENT + '''assert api.GetEngineVersion()=='3.10.0.420447'
assert not s.projection_active and not b.preparing_entity
assert not s.busy and s.edit_job is None and s.io_job is None
assert navigator.top is None or navigator.top.key=='modern_projection_workspace'
assert not hasattr(sys,'_dynamic_r17_saved')
fields=('view','page','grid','opacity','origin','projection_missing','projection_outline',
 'camera_pose','camera_yaw','camera_pitch','zoom','camera_pan','camera_depth','camera_depth_pose',
 'name','focused','box_anchor','camera_reset_animated','camera_focus_request')
sys._dynamic_r17_saved={'editor':s.editor,'fields':dict((key,getattr(s,key)) for key in fields),
 'factory':b.factory,'native_factory':getattr(sys,'_native_r15_factory',None),
 'native_geometry':getattr(sys,'_native_r15_geometry',None),
 'workspace':navigator.top is not None}
_result=json.dumps({'engine':api.GetEngineVersion(),'foot':b.player_position.GetFootPos()})
''')
        installed = True
        for row in selected:
            if time.monotonic() - started >= args.max_seconds:
                raise TimeoutError('Bounded batch deadline reached')
            key = row['fixture'] + '/' + row['case']
            report['rows'][key] = load(row, True)
            for route in args.route or ROUTES:
                if route == 'editor':
                    audit.execute('open', CLIENT + 'owner.open_workspace()\n_result=True')
                    audit.view(35., 3.)
                else:
                    code = (PROJECT % (route == 'missing')).replace('s.origin=(0,-57,0)',
                        'foot=b.player_position.GetFootPos()\ns.origin=(int(foot[0]),int(foot[1])+3,int(foot[2]))')
                    audit.execute('project', code)
                    audit.settle(True)
                    PortalAudit.camera(audit)
                prefix = route + '_' + row['case']
                for sample in range(3):
                    if time.monotonic() - started + row['sample_interval_seconds'] >= args.max_seconds:
                        raise TimeoutError('Bounded batch cannot finish the next temporal sample')
                    if sample:
                        time.sleep(row['sample_interval_seconds'])
                    label = prefix + '_motion%d' % sample
                    report['captures'][label] = audit.frame(label)
                    checkpoint()
                if route != 'editor':
                    audit.execute('stop', CLIENT + 'b.stop_projection()\n_result=True')
            load(row, False)
            audit.view(35., 3.)
            label = 'editor_' + row['case'] + '_target_hidden'
            report['captures'][label] = audit.frame(label)
            checkpoint()
        report['completed'] = True
    finally:
        if installed:
            try:
                report['restoration'] = audit.execute('restore', CLIENT + '''b.stop_projection()
saved=sys._dynamic_r17_saved
s.tiles.cancel();b.factory=saved['factory'];s.editor=saved['editor']
for key,value in saved['fields'].items():setattr(s,key,value)
for key,saved_key in (('_native_r15_factory','native_factory'),('_native_r15_geometry','native_geometry')):
 if saved[saved_key] is None:
  if hasattr(sys,key):delattr(sys,key)
 else:setattr(sys,key,saved[saved_key])
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos();cam.UnDepartCamera();cam.LockModCameraPitch(False);cam.LockModCameraYaw(False)
if navigator.top is not None:navigator.pop()
if saved['workspace']:owner.open_workspace()
s.model_revision=None;s.camera_reset_revision+=1;s.refresh_preview();s.emit()
del sys._dynamic_r17_saved
_result=True
''')
                report['restored'] = True
            except Exception as error:
                report['cleanup_errors'].append('%s: %s' % (type(error).__name__, error))
        report['source_unchanged'] = runtime_sources(project) == report['source_sha256']
        report['elapsed_seconds'] = time.monotonic() - started
        checkpoint()
    return {'completed': report['completed'], 'restored': report['restored'],
            'source_unchanged': report['source_unchanged'], 'captures': len(report['captures']),
            'pixel_acceptance_claimed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'run'))
    parser.add_argument('--fixture')
    parser.add_argument('--case', action='append')
    parser.add_argument('--route', action='append', choices=ROUTES)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--session')
    parser.add_argument('--owner')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--max-seconds', type=float, default=300.)
    args = parser.parse_args()
    plan = make_plan()
    selected = [row for row in plan['rows'] if (not args.fixture or row['fixture'] == args.fixture)
                and (not args.case or row['case'] in args.case)]
    if args.action == 'plan':
        plan['rows'] = selected
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(plan, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
        print(json.dumps(plan, ensure_ascii=True, indent=2))
        return
    if not all((args.project, args.session, args.owner, args.output)):
        parser.error('Run requires project, session, owner and fresh output')
    if not args.case or not selected or len(selected) > 5:
        parser.error('Select between one and five explicit cases per bounded run')
    if set(args.case) != {row['case'] for row in selected}:
        parser.error('One or more cases do not exist in the selected public fixture')
    if not 30. <= args.max_seconds <= 600.:
        parser.error('Batch bound must be between 30 and 600 seconds')
    print(json.dumps(acquire(args, selected), ensure_ascii=True))


if __name__ == '__main__':
    main()
