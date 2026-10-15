"""Prepared single-lectern cardinal holdout. Never starts or activates a game."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('lectern_plain_v3', HERE / 'probe_runtime_v3.py')
WRAPPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WRAPPER)
BASE = WRAPPER.HOST
native, CLIENT = BASE.native, BASE.CLIENT
DIRECTIONS = {'south': 0, 'west': 1, 'north': 2, 'east': 3}
CASES = ('empty', 'book')
PHASES = ('full', 'missing', 'hidden')
INSTALL = BASE.INSTALL.replace("'lectern_indices':[index", "'materials':[{'material':material,'indices':list(indices)}\n"
    "    for material,indices in data.get('common',{}).items()],\n   'lectern_indices':[index")
if INSTALL == BASE.INSTALL:
    raise ValueError('The native material receipt template changed')

BUILD = BASE.SERVER + WRAPPER.WRAPPER.CLEAR + '''for x in range(3):
 for y in range(3):
  for z in range(3):clear((x,y,z))
assert info.SetBlockNew(world((1,0,1)),{'name':'minecraft:cyan_concrete','aux':0},0,dimension,True,False)
name,aux=%r
assert info.SetBlockNew(world((1,1,1)),{'name':name,'aux':aux},0,dimension,True,False)
_result=True
'''

USE_BOOK = BASE.SERVER + '''items=factory.CreateItem(saved['player'])
item_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
slot=next((index for index in range(36) if not items.GetPlayerItem(item_type,index,True)),None)
assert slot is not None
saved['book_slot']=slot
assert items.SpawnItemToPlayerInv({'itemName':'minecraft:writable_book','count':1,'auxValue':0},saved['player'],slot)
used=info.PlayerUseItemToPos(world((1,1,1)),item_type,slot,1)
assert items.SetInvItemNum(slot,0)
_result=json.dumps({'used':used,'slot':slot})
'''

WORLD_STATE = BASE.SERVER + '''position=(1,1,1)
_result=json.dumps({'position':position,'block':info.GetBlockNew(world(position),dimension),
 'states':factory.CreateBlockState(api.GetLevelId()).GetBlockStates(world(position),dimension),
 'nbt':info.GetBlockEntityData(dimension,world(position))})
'''

READ_DOCUMENT = CLIENT + '''from modern_projection.projection.model import Document
from modern_projection.projection.cell import AIR,make_cell,actor_data,foreground
from modern_projection.projection.visible_actor import compose_actor
from modern_projection.projection.entity_render import native_actor
from modern_projection.projection.nbt_spatial import rebase
from modern_projection.projection.book_render_plan import appearance
saved=sys._lectern_body_r21
origin=tuple(sys._liquid_pose_client['origin'])
row=json.loads(%r)
expected_material,expected_direction,expect_book=%r
position=(1,1,1)
assert row['block']==dict(name=expected_material[0],aux=expected_material[1]),row['block']
if expected_direction is not None:
 assert row['states']['minecraft:cardinal_direction']==expected_direction,row['states']
 assert row['states']['powered_bit'] is False,row['states']
high=tuple(origin[axis]+2 for axis in range(3))
palette=factory.CreateBlock(level).GetBlockPaletteBetweenPos(origin,high,False)
assert palette is not None
raw=palette.SerializeBlockPalette()
assert tuple(raw['volume'])==(3,3,3),raw['volume']
common=dict((index,material) for material,indices in raw['common'].items() for index in indices)
extra=dict((index,material) for material,indices in raw.get('extra',{}).items() for index in indices)
actors=dict((index,payload) for name,entries in raw.get('actor',{}).items() for index,payload in entries.items())
doc=Document((3,3,3))
for index,material in common.items():
 if material==AIR:continue
 point=(index//3%%3,index//9,index%%3)
 actor=actors.get(index)
 if point==position and expected_direction is not None:
  assert material==expected_material and actor=={},(material,actor)
  actor=compose_actor(actor,rebase(row['nbt'],tuple(-value for value in origin)))
 doc.set_cell(point,make_cell(material,extra.get(index,AIR),actor))
assert foreground(doc.get((1,0,1)))==('minecraft:cyan_concrete',0)
assert foreground(doc.get(position))==expected_material
assert sum(1 for point in doc.points() if foreground(doc.get(point))!=AIR)==2
body_input=(foreground(doc.get(position)),native_actor(foreground(doc.get(position)),actor_data(doc.get(position))))
book=appearance(foreground(doc.get(position)),actor_data(doc.get(position)),api.GetEngineVersion())
assert bool(book)==expect_book,book
if expected_direction is not None:assert body_input[1]=={},body_input
saved['document']=doc.to_data()
_result=json.dumps({'document':saved['document'],'raw_common':repr(raw['common']),
 'raw_actor':repr(raw.get('actor',{})),'native_body_input':body_input,
 'logical_book_appearance':book,'true_cardinal_direction':expected_direction,
 'target_material':expected_material,'support_position':(1,0,1),'target_position':position})
'''

REMOVE = BASE.SERVER + WRAPPER.WRAPPER.CLEAR + '''for x in range(3):
 for y in range(3):
  for z in range(3):clear((x,y,z))
_result=True
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(directions):
    return [(direction, case) for direction in directions for case in CASES] + [(None, 'cyan')]


def check_templates():
    count = 0
    for direction, case in rows(DIRECTIONS):
        material = ('minecraft:cyan_concrete', 0) if case == 'cyan' else ('minecraft:lectern', DIRECTIONS[direction])
        for name, code in (('install', INSTALL), ('build', BUILD % (material,)),
                ('use', USE_BOOK), ('state', WORLD_STATE),
                ('read', READ_DOCUMENT % (json.dumps({}), (material, direction, case == 'book'))),
                ('remove', REMOVE), ('load', BASE.LOAD_DOCUMENT % (case == 'book')),
                ('project', BASE.PROJECT % False), ('restore', BASE.RESTORE)):
            compile(code, name + '_' + str(direction) + '_' + case, 'exec')
            count += 1
    return dict(compiled_templates=count, planned_captures=40, game_calls=0,
        true_block_directions=DIRECTIONS, fixed_camera_offset=(3., 2.4, 5.),
        powered_appearance_tested=False, product_qualified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--session', type=Path)
    parser.add_argument('--owner')
    parser.add_argument('--project', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--capture-exe', type=Path)
    parser.add_argument('--direction', action='append', choices=tuple(DIRECTIONS))
    args = parser.parse_args()
    if args.check:
        print(json.dumps(check_templates()))
        return
    if any(getattr(args, key) is None for key in ('session', 'owner', 'project', 'output', 'capture_exe')):
        parser.error('Use an exact assigned session, owner, project, fresh output and verified capture helper')
    session = json.loads(args.session.read_bytes())
    if session['owner'] != args.owner or Path(session['project']).resolve() != args.project.resolve():
        parser.error('Owned session and project must match exactly')
    if args.output.exists() or sha(args.capture_exe) != BASE.SINGLE_FRAME_SHA256:
        parser.error('Use a fresh output and the verified single-frame helper')
    config = json.loads((args.project / '.mcdev.json').read_bytes())
    if any(config.get(key) is not False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                                   'auto_hot_reload_shaders', 'auto_hot_reload_materials')):
        parser.error('Keep all four hot reload settings false')
    args.output.mkdir(parents=True)
    os.environ.update(MCDEV_SESSION_FILE=str(args.session.resolve()), MCDEV_OWNER=args.owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    sources = BASE.snapshot_sources(args.project)
    cases = rows(args.direction or DIRECTIONS)
    report = dict(schema=1, stage='prepared_single_lectern_cardinal_holdout',
        created_at=datetime.now(timezone.utc).isoformat(), completed=False, restored=False,
        product_qualified=False, pixel_acceptance_claimed=False, source_sha256=sources,
        host_sha256=sha(Path(__file__)), host_chain={name: sha(HERE / name) for name in (
            'probe_runtime.py', 'probe_runtime_v2.py', 'probe_runtime_v3.py')},
        host_dependencies={name: sha(BASE.ROOT / 'tools' / name) for name in (
            'probe_liquid_pose_channel.py', 'probe_product_water.py', 'capture_native_window.py',
            'verify_debug_blueprints.py', 'context_test_environment.py', 'verify_biome_shader.py')},
        capture_exe_sha256=sha(args.capture_exe), config_sha256=sha(args.project / '.mcdev.json'),
        planned_captures=len(cases) * 4 + sum(case == 'book' for direction, case in cases),
        session={key: session[key] for key in ('id', 'owner', 'game_pid', 'game_identity')},
        captures={}, cases={}, cleanup_errors=[], limits=[
            'One fixed oblique camera per independent source; four actual cardinal block states.',
            'Native book back-facing visibility differs from the custom owner; counts are not book pixel parity.',
            'Cyan-only has two adjacent native cyan cells; hiding the top leaves the lower support.',
            'Body-only book cases disable only the existing logical book profile as a negative control.',
            'No powered appearance or packed-neighbor matrix is covered.'])

    def persist():
        native.write(args.output / 'report.json', report)

    with native.Client(timeout=40) as client:
        installed = world = saved = environment = False

        def call(code, server=False):
            return native.run(client, code, server)

        def wait(predicate, timeout=35.):
            deadline = time.monotonic() + timeout
            while True:
                state = call(BASE.STATE)
                if state['preview_error'] or state['error']:
                    raise RuntimeError('Public route failed: ' + repr(state))
                if predicate(state):
                    return state
                if time.monotonic() > deadline:
                    raise TimeoutError('Public route did not settle: ' + repr(state))
                time.sleep(.25)

        def frame(label, projected):
            camera = native.CAMERA.replace('target=(origin[0]+.5,origin[1]+.5,origin[2]+.5)',
                'target=(origin[0]+1.5,origin[1]+1.5,origin[2]+1.5)')
            camera = camera.replace('offset=(3.,3.,5.)', 'offset=(3.,2.4,5.)')
            camera_state = call(camera)
            time.sleep(.7)
            check = native.CAMERA_CHECK.replace('target=tuple(axis+.5 for axis in origin)',
                'target=(origin[0]+1.5,origin[1]+1.5,origin[2]+1.5)')
            before = call(check)
            receipt = native.capture(str(args.session), args.owner, args.output / (label + '.png'), args.capture_exe)
            after = call(check)
            if before != after or receipt.get('reliable') is not True:
                raise RuntimeError('Unreliable frame or changing camera')
            report['captures'][label] = dict(receipt=receipt, camera=camera_state, before=before,
                after=after, route_state=call(BASE.STATE) if projected else None)
            persist()

        try:
            installed = True
            report['installed'] = call(INSTALL)
            environment = True
            report['environment'] = call(native.ENVIRONMENT, True)
            world = True
            report['world'] = call(native.PREPARE % 'minecraft:cyan_concrete', True)
            origin = tuple(report['world']['origin'])
            report['near_player'] = call(native.NEAR_PLAYER, True)
            saved = True
            call(native.SAVE % (origin,))
            for direction, case in cases:
                label = (direction + '_' if direction else '') + case
                row = report['cases'][label] = {}
                material = ('minecraft:cyan_concrete', 0) if case == 'cyan' else ('minecraft:lectern', DIRECTIONS[direction])
                call(CLIENT + 'b.stop_projection()\n_result=True')
                call(BUILD % (material,), True)
                target = tuple(origin[axis] + (1, 1, 1)[axis] for axis in range(3))
                deadline = time.monotonic() + 20.
                while True:
                    replication = call(native.REPLICATION % (target,))
                    if any(item['name'] == material[0] and item['aux'] == material[1]
                           for item in replication['materials']):
                        break
                    if time.monotonic() > deadline:
                        raise TimeoutError('The independently placed target did not reach the client')
                    time.sleep(.25)
                if case == 'book':
                    row['use_book'] = call(USE_BOOK, True)
                time.sleep(1.2)
                row['world'] = call(WORLD_STATE, True)
                row['source'] = call(READ_DOCUMENT % (json.dumps(row['world']), (material, direction, case == 'book')))
                frame(label + '_world', False)
                phases = (('body_only',) if case == 'book' else ()) + PHASES
                for phase in phases:
                    call(CLIENT + 'b.stop_projection()\n_result=True')
                    call(REMOVE, True)
                    time.sleep(.7)
                    call(BASE.LOAD_DOCUMENT % (case == 'book' and phase != 'body_only'))
                    wait(lambda state: state['preview_ready'])
                    if phase == 'hidden':
                        call(CLIENT + "s.toggle_layer('hide',1)\n_result=True")
                        wait(lambda state: state['preview_ready'])
                    call(CLIENT + "sys._lectern_body_r21['receipts']=[]\n_result=True")
                    call(BASE.PROJECT % (phase == 'missing'))
                    books = int(case == 'book' and phase in ('full', 'missing'))
                    state = wait(lambda state: state['work_ready'] and not state['preparing']
                        and state['book_ready'] and state['book_models'] == books)
                    if not state['logical_source_unchanged']:
                        raise RuntimeError('Public route mutated the logical source')
                    receipts = call(CLIENT + "_result=json.dumps(sys._lectern_body_r21['receipts'])")
                    active = {part[0]: part[2] for part in state['parts']}
                    body_count = 0
                    for receipt in receipts:
                        if receipt['result'] not in active:
                            continue
                        if active[receipt['result']] and receipt['lectern_indices']:
                            raise RuntimeError('The single body leaked into a neighbor context')
                        body_count += len(receipt['lectern_indices'])
                    expected = int(case != 'cyan' and phase != 'hidden')
                    if body_count != expected:
                        raise RuntimeError('A single target did not emit exactly once: ' + repr(receipts))
                    row[phase] = dict(state=state, receipts=receipts, target_body_count=body_count,
                                      expected_target_body_count=expected)
                    frame(label + '_' + phase, True)
            report['completed'] = len(report['captures']) == report['planned_captures']
        except Exception as error:
            report['error'] = type(error).__name__ + ': ' + str(error)
            persist()
            raise
        finally:
            actions = [('projection_stop', CLIENT + 'b.stop_projection()\n_result=True', False)] if installed else []
            if world:
                actions += [('inventory_restore', BASE.CLEAN_INVENTORY, True), ('world_restore', native.CLEAN_WORLD, True)]
            if saved:
                actions.append(('camera_restore', native.CLEAN_CLIENT, False))
            if environment:
                guarded = "if hasattr(sys,'_context_environment_saved'):\n" + ''.join(
                    ' ' + line + '\n' for line in native.RESTORE_ENVIRONMENT.splitlines()) + '\n_result=True'
                actions.append(('environment_restore', 'import sys\n' + guarded, True))
            if installed:
                actions.append(('session_restore', BASE.RESTORE, False))
            for label, code, server in actions:
                try:
                    report[label] = call(code, server)
                except Exception as error:
                    report['cleanup_errors'].append(label + ': ' + str(error))
            report['source_unchanged'] = sources == BASE.snapshot_sources(args.project)
            report['restored'] = not report['cleanup_errors']
            persist()
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'source_unchanged', 'planned_captures')}))


if __name__ == '__main__':
    main()
