"""Compare fixed public gate and chorus cells with native world controls."""
import verify_neighbor_world_visuals as world
from projection.debug_connection_blueprints import VISUAL_CASE

native = world.native
rows = dict((row['id'], row) for row in VISUAL_CASE['cases'])
native.FIXTURE = VISUAL_CASE['fixture']
native.VIEWS = ('side',)
native.VISUAL_CASES = dict((identity, (row['keep'], row['occupied'])) for identity, row in rows.items())
world.CASES = tuple(rows)
world.CELL_HEIGHT = VISUAL_CASE['cell_hull_height']
native.CELL_ROIS = native.CELL_ROIS.replace('(0.,1.6)', '(0.,1.)')
native.CROP_FIXTURE = '''from modern_projection.projection.cell import AIR
keep=%r
neighbor=%r
cases=%r
row=next(value for value in cases if value['keep']==keep and value['occupied']==neighbor)
doc=s.editor.document
allowed=set(row['cells'])
for pos in tuple(doc.blocks):
 if pos not in allowed:doc.blocks[pos]=AIR
sys._neighbor_qa_document=doc.blocks.copy()
sys._neighbor_qa_history=(len(s.editor.undo_stack),len(s.editor.redo_stack))
sys._neighbor_qa_editor=s.editor
sys._neighbor_qa_source=doc
sys._neighbor_qa_occupied.clear()
foot=b.player_origin()
center=tuple((keep[i]+neighbor[i]+1.)/2. for i in range(3))
s.origin=tuple(int(foot[i]+(6,24,6)[i]-center[i]) for i in range(3))
sys._neighbor_qa_origin=tuple(s.origin)
s.opacity=%r
s.projection_missing=True
s.projection_outline=False
b.project()
_result=json.dumps({'size':doc.size,'cells':len(doc.blocks),'source':'public fixed static connection case'})
'''.replace('cases=%r', 'cases=' + repr(VISUAL_CASE['cases']))


def offset(keep, occupied, view, override=None):
    if override is not None:
        return tuple(override)
    row = next(row for row in rows.values() if row['keep'] == keep and row['occupied'] == occupied)
    assert row['camera']['view'] == view, row
    return row['camera']['offset']


def supports(cells):
    lowest = min(pos[1] for pos, value in cells)
    return [((pos[0], pos[1] - 1, pos[2]),
             ('minecraft:end_stone' if value[0] == 'minecraft:chorus_plant' else 'minecraft:stone', 0))
            for pos, value in cells if pos[1] == lowest]


native.view_offset = offset
world.native_supports = supports


if __name__ == '__main__':
    raise SystemExit(world.main())
