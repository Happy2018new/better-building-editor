"""Locate layout invalidations during option changes in an owned game instance."""
import json
import time
import verify_ui as ui
from verify_font_share_polish import game


def main():
    game('''from modern_projection.pyreact import reconciler as r
from modern_projection.pyreact.style import style_layout_changed
h=api.GetTopScreen()
h._audit_layout=[]
r._audit_saved_update=r._update_primitive
def update(fiber,host):
    prev=fiber.last_props or {}
    props=fiber.props or {}
    changed=[key for key in set(prev)|set(props) if prev.get(key)!=props.get(key)]
    causes=[]
    if changed and fiber.comp_type.props_affect_layout(prev,props,fiber.style):causes.append('props')
    if style_layout_changed(fiber.last_style,fiber.style):causes.append('style')
    if causes:
        ancestors=[]
        parent=fiber.parent_fiber
        while parent is not None:
            if parent.is_component:ancestors.append(parent.comp_type.__name__)
            parent=parent.parent_fiber
        h._audit_layout.append([type(fiber.comp_type).__name__,causes,changed,ancestors[:6]])
    return r._audit_saved_update(fiber,host)
r._update_primitive=update
_result=True''')
    rows = []
    try:
        for action in ('s.choose_mode("select")', 's.choose_mode("place")',
                       's.choose_tool("fill")', 's.choose_tool("replace")',
                       's.choose_tool("shell")', 's.set("page","library")',
                       's.set("page","workspace")'):
            game('h._audit_layout=[]\n'+action+'\n_result=True')
            time.sleep(.8)
            rows.append([action, game('_result=h._audit_layout')])
    finally:
        game('r._update_primitive=r._audit_saved_update\ndel r._audit_saved_update\ns.choose_tool("fill")\n_result=True')
    (ui.OUT/'ui_invalidation.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf8')
    for action, entries in rows:
        print(action)
        for entry in entries[:24]:print(entry)


if __name__=='__main__':main()
