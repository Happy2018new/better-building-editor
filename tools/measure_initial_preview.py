"""Current and maximum-shell initial preview cost; no world or library writes."""
import json
import time
import verify_ui as ui
from verify_materials_paste import game


def main():
    for kind in ('max_shell','current_document'):
        payload=(ui.OUT/('stage51_'+kind+'.json')).read_text(encoding='utf8')
        started=time.monotonic()
        game('import json\nfrom HelloScript.projection.model import Document\ns.set("page","workspace")\ns._loaded(Document.from_data(json.loads('+repr(payload)+')))\ns.emit()\n_result=True')
        for unused in range(180):
            value=game('_result={"pending":s.preview_pending,"error":s.preview_error,"wall":s.performance.get("previewWall"),"controls":len(s.tiles.render_keys),"builds":s.tiles.builds,"extract_seconds":s.tiles.seconds,"blocks":len(s.editor.document.blocks),"mounting":getattr(s.tiles,"mounting",False),"waiting":sum(bool(p["pending"]) for p in s.tiles.parts.values())}')
            if not value['pending'] and not value['mounting'] and not value['waiting']:break
            time.sleep(.2)
        assert not value['pending'] and not value['error'] and not value['mounting'] and not value['waiting'],value
        value['native_settled_wall']=round(time.monotonic()-started,3)
        print(kind, json.dumps(value),flush=True)
        (ui.OUT/('stage51_initial_'+kind+'.json')).write_text(json.dumps(value),encoding='utf8')


if __name__=='__main__':main()
