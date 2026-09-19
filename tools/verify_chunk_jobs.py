"""Maximum draft transaction feedback/cancellation, without library or world writes."""
import json
import time
import verify_ui as ui
from verify_selection_scope import diagnostic, wait_preview
from verify_interaction import category
from verify_large_editor import snapshot


def main():
    ui.click('工作台'); ui.click('浏览')
    diagnostic({'fixture':'solid'}); wait_preview()
    category('grid'); ui.click('随机混合')
    before = diagnostic()
    ui.click('执行 · 随机混合')
    progress = ui.nodes('PreviewProgress')[0]
    ui.check('large procedural edit exposes visible progress',
             ui.nodes('Panel',progress)[0]['style'].get('visible') is True and
             any('正在修改方块' in label for label in ui.labels(progress)))
    snapshot('chunk_job_progress')
    ui.click('取消编辑')
    time.sleep(.3)
    ui.check('cancellation preserves all original blocks and material data',
             diagnostic()['blocks']==before['blocks'] and diagnostic()['previewBuilds']==before['previewBuilds'] and
             any('操作已取消' in label for label in ui.labels()))
    category('brush'); ui.click('清空选区')
    started=time.perf_counter(); ui.click('执行 · 清空选区'); wait_preview()
    erased=time.perf_counter()-started
    ui.check('whole region erases atomically',diagnostic()['blocks']==0)
    ui.click('历史')
    started=time.perf_counter(); ui.click('撤销'); wait_preview()
    undone=time.perf_counter()-started
    ui.check('whole-region undo restores all 524288 cells',diagnostic()['blocks']==524288)
    ui.click('重做'); wait_preview()
    ui.check('whole-region redo clears the draft again',diagnostic()['blocks']==0)
    ui.click('撤销'); wait_preview(); ui.click('参数')
    (ui.OUT/'chunk_job_checks.json').write_text(json.dumps({'checks':ui.checks,
        'eraseSecondsIncludingUI':erased,'undoSecondsIncludingUI':undone},ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__': main()
