"""Exercise the real P/F6/F7 handlers without sending keys to another application."""
import json
import time
import verify_ui as ui
import capture_screen as capture


def key(hwnd, code):
    capture.user32.PostMessageW(hwnd, 0x100, code, 1)
    time.sleep(.1)
    capture.user32.PostMessageW(hwnd, 0x101, code, 0xC0000001)
    time.sleep(.4)


def main():
    if not capture.IS_WINDOWS:
        raise RuntimeError('This entry check requires the Windows development game.')
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and not window['minimized'], 'An open game window is required'
    ui.click('工作台')
    ui.call('navigator', value={'action': 'close'})
    time.sleep(.5)
    for code in (117, 118, 80):
        key(window['hwnd'], code)
    current = ui.labels()
    ui.check('P reopens workspace', '场景视图' in current)
    ui.check('F7 marks the second corner', any(s.startswith('已标记终点：') for s in current))
    ui.click('读取选区')
    ui.click('确认继续')
    for unused in range(20):
        current = ui.labels()
        if any(s.startswith('已读取世界选区') for s in current):
            break
        time.sleep(.3)
    ui.check('F6 and F7 define a readable world selection', any(s.startswith('已读取世界选区') for s in current))
    ui.save('ui_entry_verified')
    (ui.OUT / 'entry_checks.json').write_text(json.dumps(ui.checks, indent=2), encoding='utf8')
    ui.click('入门指南')
    ui.click('载入庭院示例')
    ui.click('确认继续')
    ui.click('工作台')


if __name__ == '__main__':
    main()
