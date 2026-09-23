"""Native PC/F11 regression for retained options, callback updates and captions."""
import json
import time
import verify_ui as ui
from verify_font_share_polish import game
from verify_biome_controls import native_click
from verify_large_editor import snapshot
from native_input_mode import set_touch, state


def main():
    touch = state()['simulated']
    saved = game('_result=(s.page,s.inspector,s.tool,s.direct_mode,s.group)')
    try:
        for mode in (False, True):
            set_touch(mode)
            game('s.set("page","workspace")\ns.set("inspector","params")\ns.choose_tool("fill")\n_result=True')
            time.sleep(.6)
            for identity in ('select','place','erase','browse'):
                root = ui.nodes('ViewportModes')[0]
                option = next(n for n in ui.nodes('SegmentChoice',root) if n['props']['identity']==identity)
                native_click(option)
                ui.check(('F11' if mode else 'PC')+' mode '+identity,game('_result=s.direct_mode')==identity)
            # Repeatedly shrink/grow the channel list, then click the retained
            # secondary choice: this must use its newest callback and position.
            game('s.choose_group("pattern")\ns.choose_tool("checker")\n_result=True')
            time.sleep(.5)
            pool = [n['id'] for n in ui.nodes('SegmentChoice',ui.nodes('MaterialPicker')[0])]
            for tool in ('fill','checker','fill','checker'):
                game('s.choose_tool('+repr(tool)+')\n_result=True');time.sleep(.2)
            ui.check('channel controls survive repeated tool switches',pool==[n['id'] for n in ui.nodes('SegmentChoice',ui.nodes('MaterialPicker')[0])])
            picker = ui.nodes('MaterialPicker')[0]
            option = next(n for n in ui.nodes('SegmentChoice',picker) if n['props']['identity']=='secondary')
            scroll = ui.nodes('VisibleScroll',ui.nodes('Parameters')[0])[0]
            ui.call('scroll',scroll['id'],0)
            time.sleep(.2)
            option_box=ui.call('native_control',ui.nodes('Button',option)[0]['id'])['result']
            viewport=ui.call('native_control',scroll['id'])['result']
            ui.call('scroll',scroll['id'],max(0,option_box['global'][1]-viewport['global'][1]-viewport['size'][1]*.3))
            time.sleep(.25)
            native_click(option)
            picker = ui.nodes('MaterialPicker')[0]
            ui.check('retained channel invokes current handler',ui.nodes('MaterialSummary',picker)[0]['props']['channel']=='secondary')
            snapshot('perf67_options_'+('touch' if mode else 'pc'))
        ui.check('static caption cache is bounded and respects size/scale',game('''from HelloScript.projection import widgets as w
a=w.text(u'\u5de5\u5177',12)
b=w.text(u'\u5de5\u5177',12)
c=w.text(u'\u5de5\u5177',14)
_result=a is b and a is not c and len(w._TEXT_ELEMENTS)<=w._TEXT_ELEMENT_LIMIT'''))
        (ui.OUT/'perf67_ui_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')
    finally:
        game('s.page,s.inspector,s.tool,s.direct_mode,s.group='+repr(tuple(saved))+'\ns.emit()\n_result=True')
        set_touch(touch)


if __name__=='__main__':main()
