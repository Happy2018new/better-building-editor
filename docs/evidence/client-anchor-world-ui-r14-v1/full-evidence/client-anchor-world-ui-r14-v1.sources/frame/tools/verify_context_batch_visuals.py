"""Check isolated connected families, including a chunk boundary, above terrain."""
import verify_missing_neighbor_visuals as native
from context_test_environment import run, SETUP, RESTORE
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.debug_blueprints import VISUAL_CASES
METADATA = VISUAL_CASES['neighbor_context']
native.VISUAL_CASES.update(METADATA['cells'])
native.VISUAL_CASES.update(dict((family + '_cross_chunk', cells)
                               for family, cells in METADATA['cross_chunk_cells'].items()))
SOURCES = dict((cells, METADATA['cells'][family][0])
               for family, cells in METADATA['cross_chunk_cells'].items())
native.CELL_ROIS = native.CELL_ROIS.replace('(.03,.97)', '(0.,1.)')
# Look slightly up so a moving mob on the distant ground cannot contribute
# to the shown-minus-hidden signal. Keep both complete cell hulls observable.
_view_offset = native.view_offset
_roi_masks = native.roi_masks


def calibrated_roi_masks(projection, size, keep, occupied, calibration=None):
    guard = 0
    if calibration is not None and projection['projection_method'] != 'native':
        guard = max(abs(row['fit']['bounds'][i] - row['fit']['predicted_bounds'][i])
                    for row in calibration['views'] for i in range(4))
    return _roi_masks(projection, size, keep, occupied, calibration, boundary_guard=guard)


def sky_view_offset(keep, occupied, view, override=None):
    offset = _view_offset(keep, occupied, view, override)
    if view == 'side' and override is None:
        return offset[0], -abs(offset[1]), offset[2]
    return offset


native.view_offset = sky_view_offset
native.roi_masks = calibrated_roi_masks
native.CROP_FIXTURE = native.CROP_FIXTURE.replace(
    'assert doc.get(keep)!=AIR and doc.get(neighbor)!=AIR',
    '''from modern_projection.projection.cell import foreground
sources=%r
source=sources.get((keep,neighbor))
if source is not None:
 from modern_projection.projection.model import Document
 selected=foreground(doc.get(source))[0]
 delta=tuple(keep[i]-source[i] for i in range(3))
 values=dict((tuple(pos[i]+delta[i] for i in range(3)),value) for pos,value in doc.blocks.items()
             if foreground(value)[0]==selected and
             all(0<=pos[i]+delta[i]<doc.size[i] for i in range(3)))
 doc=Document(doc.size,values,biome=doc.biome)
 s.editor.document=doc
assert doc.get(keep)!=AIR and doc.get(neighbor)!=AIR''' % SOURCES).replace(
    'sys._neighbor_qa_document=doc.blocks.copy()',
    '''selected=foreground(doc.get(keep))[0]
for pos in tuple(doc.blocks):
 if foreground(doc.get(pos))[0]!=selected:doc.blocks[pos]=AIR
sys._neighbor_qa_document=doc.blocks.copy()''').replace(
    'foot[i]+(6,8,6)[i]', 'foot[i]+(6,%d,6)[i]' % METADATA['projection_height'])


if __name__ == '__main__':
    with native.Client(timeout=30) as client:
        run(client, SETUP)
        try:
            raise SystemExit(native.main())
        finally:
            run(client, RESTORE)
