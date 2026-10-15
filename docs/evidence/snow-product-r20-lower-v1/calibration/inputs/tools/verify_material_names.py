"""Compare both material lists with the picker in a fresh managed game instance."""
import json
import time
import verify_ui as ui
from verify_font_share_polish import game
from verify_complete_projection import snapshot


def material_rows():
    return game('_result=[(list(b),s.describe_material(b),count) for b,count in s.editor.document.materials()]')


def check_labels(kind, rows):
    labels = ui.labels(ui.nodes(kind)[0])
    ui.check(kind+' shows localized material names and counts',
             all(name in labels and str(count) in labels for value, name, count in rows))


def main():
    before = game('''_result={'page':s.page,'inspector':s.inspector,
        'browser':s.material_browser,'catalogue_ready':s.catalogue_ready,
        'document':s.editor.document.to_data()}''')
    assert not before['catalogue_ready'], 'Run in a fresh instance before opening the block picker'
    try:
        game('s.set("page","projection")\n_result=True')
        time.sleep(1)
        ui.click('辅助')
        time.sleep(1)
        rows = material_rows()
        ui.check('legacy demo names are Chinese before opening inventory', len(rows) == 6 and
                 all(any('\u4e00' <= ch <= '\u9fff' for ch in row[1]) for row in rows))
        check_labels('ProjectionSettings', rows)
        panel = ui.nodes('ProjectionSettings')[0]
        ui.call('scroll', ui.nodes('VisibleScroll', panel)[0]['id'], 10000)
        time.sleep(.3)
        snapshot('material_names_before_picker')

        game('s.set("page","workspace")\ns.set("inspector","history")\n_result=True')
        time.sleep(1)
        check_labels('History', rows)
        game('s.open_materials("material")\n_result=True')
        deadline = time.time()+30
        while game('_result=s.catalogue_loading') and time.time() < deadline:
            time.sleep(.3)
        ui.check('native catalogue loaded', game('_result=s.catalogue_ready'))
        game('s.set("material_browser",None)\n_result=True')
        time.sleep(.5)
        rows_after = material_rows()
        check_labels('History', rows_after)
        game('s.set("page","projection")\n_result=True')
        time.sleep(.7)
        check_labels('ProjectionSettings', rows_after)
        snapshot('material_names_after_picker')
        ui.check('name lookup preserves every block and aux',
                 before['document'] == game('_result=s.editor.document.to_data()'))
        (ui.OUT/'material_names_checks.json').write_text(json.dumps(
            {'checks':ui.checks,'before_picker':rows,'after_picker':rows_after},
            ensure_ascii=False, indent=2), encoding='utf8')
        print(json.dumps(rows_after, ensure_ascii=False), flush=True)
    finally:
        game('s.set("material_browser",'+repr(before['browser'])+')\n'
             's.set("page",'+repr(before['page'])+')\n'
             's.set("inspector",'+repr(before['inspector'])+')\n_result=True')


if __name__ == '__main__':
    main()
