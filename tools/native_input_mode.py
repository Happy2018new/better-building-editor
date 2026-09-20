"""F11 developer touch switching, with native readback, in a bound instance."""
import time
import verify_ui as ui
from mcdk import Client, return_value


def state():
    with Client() as client:
        return return_value(client.call('execute_code', {'code': '''
import mod.client.extraClientApi as api
from HelloScript.projection.input_mode import current_mode, is_touch
_result = {'mode': current_mode(), 'simulated': api.IsTouchWithMouse(), 'touch': is_touch()}
''', 'is_client': True, 'direct_return': True}))


def key(name):
    # MCDK sends native scan codes; keybd_event virtual F-keys did not toggle
    # this client. A queued key is not success until state() confirms it.
    with Client() as client:
        result = client.call('mc_input', {'op': '/key', 'args': {'keys': name}})
    assert not result.get('isError') and result.get('structuredContent', {}).get('ok'), result


def set_touch(enabled):
    if state()['simulated'] == enabled:
        return
    close = next(n for n in ui.nodes('Action') if n['props'].get('glyph') == 'close')
    ui.call('click', ui.nodes('Button', close)[0]['id'])
    time.sleep(.5)
    key('f11')
    time.sleep(.3)
    assert state()['simulated'] == enabled, 'F11 did not change native touch simulation'
    key('p')
    time.sleep(.8)
    from verify_selection_scope import diagnostic
    diagnostic.identity = None
    assert state()['simulated'] == enabled


if __name__ == '__main__':
    import sys
    set_touch('--touch' in sys.argv)
    print(state())
