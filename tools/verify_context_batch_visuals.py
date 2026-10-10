"""Check isolated connected families, including a chunk boundary, above terrain."""
import verify_missing_neighbor_visuals as native
from context_test_environment import run, SETUP, RESTORE

native.VISUAL_CASES['fence_cross_chunk'] = ((15, 1, 17), (16, 1, 17))
native.CELL_ROIS = native.CELL_ROIS.replace('(.03,.97)', '(0.,1.)')
native.CROP_FIXTURE = native.CROP_FIXTURE.replace(
    'assert doc.get(keep)!=AIR and doc.get(neighbor)!=AIR',
    '''from modern_projection.projection.cell import foreground
if keep==(15,1,17):
 from modern_projection.projection.model import Document
 selected=foreground(doc.get((17,1,17)))[0]
 values=dict(((pos[0]-2,pos[1],pos[2]),value) for pos,value in doc.blocks.items()
             if foreground(value)[0]==selected)
 doc=Document(doc.size,values,biome=doc.biome)
 s.editor.document=doc
assert doc.get(keep)!=AIR and doc.get(neighbor)!=AIR''').replace(
    'sys._neighbor_qa_document=doc.blocks.copy()',
    '''selected=foreground(doc.get(keep))[0]
for pos in tuple(doc.blocks):
 if foreground(doc.get(pos))[0]!=selected:doc.blocks[pos]=AIR
sys._neighbor_qa_document=doc.blocks.copy()''').replace('foot[i]+(6,8,6)[i]', 'foot[i]+(6,24,6)[i]')


if __name__ == '__main__':
    with native.Client(timeout=30) as client:
        run(client, SETUP)
        try:
            raise SystemExit(native.main())
        finally:
            run(client, RESTORE)
