"""Read native wire edges at multiple depths without changing any blocks."""
import json
import time
import verify_ui as ui
from verify_font_share_polish import game
from verify_selection_outline import outline, same_outline


def main():
    game('''import json
from modern_projection.projection import scene
fields=('page','view','direct_mode','box_anchor','camera_yaw','camera_pitch','zoom','camera_pan',
        'camera_pivot','camera_depth','camera_depth_pose','camera_pose','grid','touch_mode')
api._depth_saved=dict((key,getattr(s,key)) for key in fields)
api._depth_selection=(s.editor.selection,s.editor.start,s.editor.end,s.editor.selection_revision)
api._depth_touch=scene.is_touch
api._depth_document=json.dumps(s.editor.document.to_data(),sort_keys=True,ensure_ascii=True)
api._depth_builds=s.tiles.builds
s.page='workspace';s.view='3d';s.direct_mode='select';s.box_anchor=None
s.editor.select_box((20,48,20),(43,79,43))
s.camera_pivot=None;s.camera_pan=(0.,0.);s.camera_depth=0.
s.camera_view(35.,20.,1.);s.emit()
_result=True''')
    try:
        for touch in (False,True):
            game('scene.is_touch=lambda:%r\ns.touch_mode=%r\n_result=True'%(touch,touch))
            previous=None
            for depth in (0., 50., 90., 0.):
                game('s.camera_depth=%r\ns.emit("camera_depth")\n_result=True'%depth)
                time.sleep(1.)
                edges=outline('cursor' if touch else 'edge')
                ui.check(('touch' if touch else 'pc')+' complete 12 edges at depth '+str(depth),all(n['visible'] for n in edges))
                if previous is not None:
                    ui.check('depth does not move or truncate selection edges',same_outline(previous,edges))
                previous=edges
            if touch:
                ui.check('touch has no duplicate blue selection',not any(n['visible'] for n in outline('edge')))
        ui.check('depth outlines never rebuild block models',game('_result=s.tiles.builds==api._depth_builds'))
    finally:
        game('''scene.is_touch=api._depth_touch
for key,value in api._depth_saved.items():setattr(s,key,value)
s.editor.selection,s.editor.start,s.editor.end,s.editor.selection_revision=api._depth_selection
s.camera_revision+=1;s.emit()
assert json.dumps(s.editor.document.to_data(),sort_keys=True,ensure_ascii=True)==api._depth_document
_result=True''')
        (ui.OUT/'stage56_depth_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
