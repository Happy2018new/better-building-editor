"""Native wet actor pixels versus public fixture projections at identical cameras.

Run through run_live_check.py in the owner's instance. Glass containment stays
in the logical context and native world while only measured cells are projected.
This is an unaccepted harness until its preserved native captures pass.
"""
import time
import json
from PIL import Image, ImageChops, ImageDraw, ImageFilter
import verify_neighbor_world_visuals as world
from verify_sign_visuals import refresh
from projection.debug_sign_blueprints import WET_VISUAL_CASE as SIGNS
from projection.debug_pot_blueprints import WET_VISUAL_CASE as POTS

native = world.native
METADATA = {'sign': SIGNS, 'pot': POTS}
CASES = dict((family + '_' + row['id'], (metadata, row))
             for family, metadata in METADATA.items() for row in metadata['cases'])
world.CASES = tuple(sorted(CASES))
native.VIEWS = ('side',)
native.VISUAL_CASES = dict((label, (row['keep'], row['actor']))
                          for label, (metadata, row) in CASES.items())

CROP = '''from modern_projection.projection.cell import AIR
keep,neighbor,opacity=%r,%r,%r
from modern_projection.projection import debug_sign_blueprints,debug_pot_blueprints
metadata=(debug_sign_blueprints if sys._blueprint_qa_identity=='test.entities.signs' else debug_pot_blueprints).WET_VISUAL_CASE
scene=next(row for row in metadata['cases'] if tuple(row['keep'])==keep and tuple(row['actor'])==neighbor)
doc=s.editor.document
selected=set(scene['cells']+scene['supports'])
for pos in tuple(doc.blocks):
 if pos not in selected:doc.blocks[pos]=AIR
sys._neighbor_qa_document=doc.blocks.copy()
sys._neighbor_qa_history=(len(s.editor.undo_stack),len(s.editor.redo_stack))
sys._neighbor_qa_editor=s.editor
sys._neighbor_qa_source=doc
sys._neighbor_qa_occupied.clear()
sys._neighbor_qa_occupied.update(scene['supports'])
foot=b.player_origin()
center=tuple((keep[i]+neighbor[i]+1.)/2. for i in range(3))
s.origin=tuple(int(foot[i]+(6,metadata['projection_height'],6)[i]-center[i]) for i in range(3))
sys._neighbor_qa_origin=tuple(s.origin)
s.opacity=opacity
s.projection_missing=True
s.projection_outline=False
b.project()
_result=json.dumps({'size':doc.size,'cells':len(doc.blocks),'scene':scene})
'''

RESERVE = '''import mod.server.extraServerApi as api
import sys,json
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import AIR,decode,foreground,background
player=api.GetPlayerList()[0]
adapter=WorldAdapter(player)
source,supports,origin=json.loads(%r),json.loads(%r),%r
source=[(tuple(pos),value) for pos,value in source]
supports=[(tuple(pos),value) for pos,value in supports]
cells=supports+source
reserved=set(tuple(pos[i]+offset[i] for i in range(3)) for pos,value in cells
             for offset in ((0,0,0),(-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1)))
assert not hasattr(sys,'_neighbor_world_saved')
for pos in reserved:assert adapter.read(pos)==AIR,(pos,adapter.read(pos))
sys._neighbor_world_saved={'player':player,'cells':cells,'reserved':reserved}
for pos,value in cells:assert adapter.write(pos,decode(value),origin),(pos,value)
actual=[]
for pos,value in cells:
 expected=decode(value)
 observed=adapter.read(pos)
 assert observed is not None and foreground(observed)==foreground(expected) and background(observed)==background(expected),(pos,expected,observed)
 actual.append((pos,foreground(observed),background(observed)))
_result=json.dumps({'verified':True,'cells':actual})
'''

PALETTE_PROBE = '''import json,sys
from modern_projection.projection.cell import AIR,decode,foreground,background,actor_data,freeze
from modern_projection.projection.world_capture import native_palette_layers,native_palette_actors
cells,empty=json.loads(%r),%r
lo=tuple(min(pos[i] for pos,value in cells) for i in range(3))
hi=tuple(max(pos[i] for pos,value in cells) for i in range(3))
size=tuple(hi[i]-lo[i]+1 for i in range(3))
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(lo,hi,False)
result={'matches':False,'layers_match':False,'actors_match':False,'cells':[],'actor_mismatches':[],'raw_palette':None}
if palette is not None:
 source=palette.SerializeBlockPalette()
 sys._wet_actor_qa_palette=source
 result['raw_palette']=freeze(source)
 fronts,backs=native_palette_layers(source,size)
 layers_match=tuple(source.get('volume',()))==(size[2],size[0],size[1])
 actors_match=True
 actors={}
 for name,entries in source.get('actor',{}).items():
  name=name.decode('utf8') if isinstance(name,bytes) else name
  for index in entries:
   front=fronts.get(index,AIR)
   if front[0]!=name:
    result['actor_mismatches'].append({'index':index,'actor_name':name,'foreground':front})
 try:
  actors=dict((index,name) for index,name,payload in native_palette_actors(source,fronts,backs,size[0]*size[1]*size[2]))
 except ValueError as error:
  actors_match=False
  result['normalization_error']=str(error)
 for pos,value in cells:
  local=tuple(pos[i]-lo[i] for i in range(3))
  index=(local[1]*size[0]+local[0])*size[2]+local[2]
  front,back=fronts.get(index,AIR),backs.get(index,AIR)
  expected=decode(value)
  matched=(front==AIR and back==AIR) if empty else (front==foreground(expected) and back==background(expected))
  layers_match=layers_match and matched
  if empty and index in actors:actors_match=False
  if not empty and actor_data(expected) is not None and actors.get(index)!=foreground(expected)[0]:actors_match=False
  result['cells'].append({'pos':pos,'foreground':front,'background':back,'matched':matched,'actor_name':actors.get(index)})
 result.update(layers_match=layers_match,actors_match=actors_match,matches=layers_match and actors_match)
_result=json.dumps(result)
'''

REPLICATION = '''import json
from modern_projection.projection.cell import decode,foreground,background,actor_data
from modern_projection.projection.model import Document
from modern_projection.projection.world_capture import merge_palette
from modern_projection.projection.entity_render import native_actor
cells,empty=json.loads(%r),%r
lo=tuple(min(pos[i] for pos,value in cells) for i in range(3))
hi=tuple(max(pos[i] for pos,value in cells) for i in range(3))
size=tuple(hi[i]-lo[i]+1 for i in range(3))
matches=False
observations=[]
if hasattr(sys,'_wet_actor_qa_palette'):
 doc=Document(size)
 merge_palette(doc,sys._wet_actor_qa_palette,(0,0,0),size,lo)
 matches=True
 for pos,value in cells:
  actual=doc.get(tuple(pos[i]-lo[i] for i in range(3)))
  expected=decode(value)
  matched=(foreground(actual)[0]=='minecraft:air' and background(actual)[0]=='minecraft:air') if empty else (foreground(actual)==foreground(expected) and background(actual)==background(expected))
  if not empty and actor_data(expected) is not None:
   wanted=native_actor(foreground(expected),actor_data(expected))
   observed=native_actor(foreground(actual),actor_data(actual))
   matched=matched and observed is not None and all(observed.get(key)==item for key,item in wanted.items())
  matches=matches and matched
  observations.append({'pos':pos,'foreground':foreground(actual),'background':background(actual),'matched':matched})
_result=json.dumps({'matches':matches,'cells':observations})
'''


def wire_json(value):
    # JSON creates Unicode tree tags in Python 2; Python 3 repr does not.
    return json.dumps(value, ensure_ascii=True, separators=(',', ':'))


def reserve_code(cells, supports, origin):
    return RESERVE % (wire_json(cells), wire_json(supports), origin)


def replication_code(cells, empty=False):
    return REPLICATION % (wire_json(cells), empty)


def replication(check, cells, empty=False, diagnostics=None):
    def read():
        probe = check.run(PALETTE_PROBE % (wire_json(cells), empty))
        if diagnostics is not None:
            diagnostics.clear()
            diagnostics.update(probe)
        if not probe['matches']:
            return {'matches': False, 'layers_match': probe['layers_match'],
                    'actors_match': probe['actors_match'], 'cells': probe['cells'],
                    'actor_mismatches': probe['actor_mismatches']}
        return check.run(replication_code(cells, empty))
    return check.wait('complete wet actor palette replication', lambda row: row['matches'],
                      read)


def component_checks(baseline, actual, masks, native_path, threshold, min_pixels):
    union = ImageChops.lighter(*masks)
    presence = ImageChops.multiply(native.binary(native.maximum(baseline), threshold), union)
    with Image.open(native_path).convert('RGB') as frame:
        pixels = list(frame.getdata())
    result = {}
    for name, predicate in (
            ('water', lambda r, g, b: b > r * 1.2 and b > g * .95),
            ('actor', lambda r, g, b: r > b * 1.1 and r > g * .9)):
        mask = Image.new('L', baseline.size)
        mask.putdata([255 if predicate(*pixel) else 0 for pixel in pixels])
        mask = ImageChops.multiply(mask, presence)
        result[name] = native.compare_complete(baseline, actual,
                                              (mask, Image.new('L', baseline.size)),
                                              threshold, min_pixels)
    return result


def wet_case(check, label, args, row):
    metadata, scene = CASES[label]
    if not hasattr(check, '_wet_actor_refreshed'):
        refresh(check)
        check._wet_actor_refreshed = True
    native.FIXTURE = metadata['fixture']
    native.CROP_FIXTURE = CROP
    native.view_offset = lambda keep, occupied, view, override=None: tuple(override or metadata['camera_offset'])
    keep, occupied = scene['keep'], scene['actor']
    before = native.prepare_case(check, keep, occupied, args.opacity)
    source = check.run('from modern_projection.projection.cell import encode\n'
                       '_result=json.dumps({"origin":s.origin,"cells":'
                       '[(pos,encode(value)) for pos,value in s.editor.document.blocks.items()]})')
    selected = set(scene['cells'])
    measured = [(tuple(pos), value) for pos, value in source['cells'] if tuple(pos) in selected]
    cells = [(tuple(source['origin'][i] + pos[i] for i in range(3)), value) for pos, value in measured]
    supports = [(tuple(source['origin'][i] + pos[i] for i in range(3)), value)
                for pos, value in source['cells'] if tuple(pos) not in selected]
    row.update(keep=keep, occupied=occupied, source={'origin': source['origin'], 'cells': measured},
               fixture=before, fixture_id=metadata['fixture'], cell_height=world.CELL_HEIGHT,
               native_supports=supports, views={})
    check.run('b.stop_projection()\n_result=True')
    row['world_setup'] = world.run(check.client, reserve_code(cells, supports, tuple(source['origin'])))
    row['near_player'] = world.run(check.client, world.NEAR_PLAYER % (cells,))
    row['near_player']['client'] = world.player_ready(check, row['near_player']['after'])
    row['world_replication_diagnostics'] = {}
    row['world_replication'] = replication(check, cells, diagnostics=row['world_replication_diagnostics'])
    row['support_replication_diagnostics'] = {}
    row['support_replication'] = replication(check, supports, diagnostics=row['support_replication_diagnostics'])
    baselines, masks = {}, {}
    for view in args.view:
        pose, shown = world.camera_capture(check, label + '_' + view + '_world', keep, occupied, view)
        row['views'][view] = {'camera': pose, 'world': shown}
    world.run(check.client, world.CLEAR_SOURCE % (cells,))
    row['world_cleared_diagnostics'] = {}
    row['world_cleared'] = replication(check, cells, True, row['world_cleared_diagnostics'])
    for view, frames in row['views'].items():
        pose, empty = world.camera_capture(check, label + '_' + view + '_empty', keep, occupied, view)
        baseline = native.signal(frames['world']['path'], empty['path'])
        projection = check.run(native.CELL_ROIS)
        projection['cells'] = [item for item in projection['cells'] if tuple(item['pos']) in selected]
        first, second, record = native.roi_masks(projection, baseline.size, keep, occupied, args.calibration)
        baselines[view], masks[view] = baseline, (first, second)
        frames.update(empty=empty, roi=record)
    check.run('b.project()\n_result=True')
    initial = native.projection_ready(check, occupied)
    assert initial['state'] == 1, initial
    row['context_all_air'] = initial
    for view, frames in row['views'].items():
        native.select_view(check, keep, occupied, view, None)
        signal, capture = native.capture_signal(check, label + '_' + view + '_context', occupied)
        frames['context'] = capture
        frames['context_matches_world'] = native.compare_complete(baselines[view], signal, masks[view], args.threshold, args.min_pixels)
        frames['components'] = component_checks(baselines[view], signal, masks[view], frames['world']['path'], args.threshold, args.min_pixels)
    check.run('sys._neighbor_qa_occupied.add(%r)\nb.projection_occupancy.read(%r)\n_result=True' % (occupied, occupied))
    for stage in ('dynamic', 'initial'):
        if stage == 'initial':
            check.run('b.project()\n_result=True')
        state = native.projection_ready(check, occupied, initial['commits'] + 1 if stage == 'dynamic' else None)
        assert state['state'] == 2, state
        row[stage] = {'projection': state, 'views': {}}
        for view in row['views']:
            native.select_view(check, keep, occupied, view, None)
            signal, capture = native.capture_signal(check, label + '_' + view + '_' + stage, occupied)
            prefix = args.output.with_name(args.output.stem + '_' + label + '_' + view + '_' + stage)
            row[stage]['views'][view] = {'capture': capture, 'pixels': native.compare_pixels(
                baselines[view], signal, masks[view], prefix, args.min_pixels, args.threshold)}
    row['passed'] = (all(frames['context_matches_world']['passed'] and
                         all(item['passed'] for item in frames['components'].values())
                         for frames in row['views'].values()) and
                     all(item['pixels']['passed'] for stage in ('dynamic', 'initial')
                         for item in row[stage]['views'].values()))
    row['completed'] = True
    return row


world.world_case = wet_case
_save = world.write_json


def write_report(path, report):
    report['fixture'] = [metadata['fixture'] for metadata in METADATA.values()]
    report['scope'] = 'Contained public wet actors: native/projection full silhouette, fixed native water/actor masks, and dynamic/initial occupancy'
    report['limits'] = 'Unaccepted until native execution; component color masks require observable native pixels; no threshold reductions'
    report['passed'] = report['passed'] and report.get('restored', True)
    _save(path, report)


_replay = world.replay


def replay(args):
    _replay(args)
    report = json.loads(args.output.read_text(encoding='utf8'))
    for row in report['cases']:
        for frames in row['views'].values():
            baseline = native.signal(frames['world']['path'], frames['empty']['path'])
            actual = native.signal(frames['context']['shown']['path'], frames['context']['actor_hidden']['path'])
            masks = []
            for name in ('keep', 'occupied'):
                mask = Image.new('L', baseline.size)
                ImageDraw.Draw(mask).polygon([tuple(point) for point in frames['roi'][name]], fill=255)
                masks.append(mask)
            guard = frames['roi']['neighbor_boundary_guard_pixels']
            first, second = masks
            if guard:
                masks = (ImageChops.subtract(first, second.filter(ImageFilter.MaxFilter(guard * 2 + 1))),
                         ImageChops.subtract(second, first.filter(ImageFilter.MaxFilter(guard * 2 + 1))))
            frames['components'] = component_checks(baseline, actual, masks, frames['world']['path'], args.threshold, args.min_pixels)
            row['passed'] = row['passed'] and all(item['passed'] for item in frames['components'].values())
    report['passed'] = all(row['passed'] for row in report['cases'])
    write_report(args.output, report)
    print(json.dumps({'wet_components_replayed': True, 'passed': report['passed']}))
    return 0 if report['passed'] else 1


world.write_json = write_report
world.replay = replay
if __name__ == '__main__':
    raise SystemExit(world.main())
