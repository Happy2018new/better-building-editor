"""Native Esc mapping and asymmetric safe-area layout on the bound client."""
import json
import time
from pathlib import Path
from verify_world_tools import game, input_step, snapshot


def main():
    report = {}
    try:
        game('''from HelloScript.pyreact import navigator, host
api._safe_review=(host.get_safe_area_size(),host.get_safe_area_insets())
owner.open_workspace()
_result=True''')
        time.sleep(1.5)
        input_step('/key', keys='esc')
        time.sleep(1.)
        report['esc_native_closed'] = game('''from HelloScript.pyreact import navigator
_result=not navigator.contains('modern_projection_workspace')''')
        if not report['esc_native_closed']:
            report['back_state']=game('''from HelloScript.pyreact import navigator
h=navigator.top._host
_result={'back_time':getattr(h,'_last_back_time',None),'top':navigator.top_ui_name,
         'dialogs':[s.pending_confirm,s.pending_rename,s.material_browser],
         'sharing':s.sharing.opened,'transition':navigator.is_transitioning}''')
        assert report['esc_native_closed'], report
        game('''from HelloScript.pyreact import host
host._SAFE_AREA_PROBE[0]._next_measure=host.time.time()+30.
host._publish_safe_area((408.,235.),host.SafeAreaInsets(13.,24.,27.,48.))
owner.open_workspace()
_result=True''')
        time.sleep(.8)
        report['asymmetric_layout'] = game('''from HelloScript.pyreact import navigator, host
h=navigator.top._host
nodes=[]
def visit(f):
 if f.native_path:
  c=h.GetBaseUIControl(f.native_path)
  if c and len(nodes)<8:
   nodes.append([f.native_path,c.GetGlobalPosition(),c.GetSize()])
 for child in f.child_fibers: visit(child)
visit(h._root_fiber)
_result={'safe':host.get_safe_area_size(),'nodes':nodes}''')
        # Screenshot is actual pixels after runtime safe-area publication;
        # this simulates insets, not a physical Android display notch.
        report['screenshot'] = snapshot('safe_asymmetric')
        assert any(abs(n[1][0]-48.)<.1 and abs(n[1][1]-13.)<.1 and
                   abs(n[2][0]-408.)<.1 and abs(n[2][1]-235.)<.1
                   for n in report['asymmetric_layout']['nodes']), report
    finally:
        game('''from HelloScript.pyreact import navigator, host
saved=getattr(api,'_safe_review',None)
if saved:
 host._publish_safe_area(saved[0],saved[1])
 host._SAFE_AREA_PROBE[0]._next_measure=0.
 del api._safe_review
if navigator.contains('modern_projection_workspace'):navigator.pop()
_result=True''')
    path=Path(__file__).resolve().parents[1]/'.runtime/safe_back_report.json'
    path.write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
