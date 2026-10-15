"""Read exactly one of two frozen existing dumps through Microsoft DbgEng."""
import argparse
import ctypes
from ctypes import wintypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback
import uuid


BASE = Path(__file__).resolve().parent
INTERFACES = json.loads((BASE / 'interface-indices.json').read_text(encoding='utf-8'))
CASES = {
    2188: 'd63ff129f7ed32227c0b8596386b1ab7b9514521b303ea2a5490c27d1b4ecd94',
    25292: '2cef55c51df3263a30465e73b8260392e27dd77e098223f088179e69cfeb68c2',
}
GAME = Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447')
HRESULT = ctypes.c_long
ULONG = wintypes.ULONG
PVOID = ctypes.c_void_p


class GUID(ctypes.Structure):
    _fields_ = [('bytes', ctypes.c_ubyte * 16)]

    @classmethod
    def parse(cls, text):
        return cls((ctypes.c_ubyte * 16).from_buffer_copy(uuid.UUID(text).bytes_le))


def method(interface, kind, name, result, *arguments):
    index = INTERFACES[kind][name]
    table = ctypes.cast(interface, ctypes.POINTER(ctypes.POINTER(PVOID))).contents
    return ctypes.WINFUNCTYPE(result, PVOID, *arguments)(table[index])


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def debug_dump(args):
    dump = Path('C:/Users/Happy2018new/AppData/Local/CrashDumps/'
                'Minecraft.Windows.exe.%d.dmp' % args.pid)
    if digest(dump) != CASES[args.pid]:
        raise RuntimeError('Input dump hash differs from frozen v1 identity')
    destination = BASE / ('dbgeng-%d-%s' % (args.pid, args.label))
    for suffix in ('.txt', '.json'):
        if destination.with_suffix(suffix).exists():
            raise RuntimeError('Refusing to replace prior output: ' + str(destination))
    receipt = {'pid': args.pid, 'dump': str(dump), 'dump_sha256': CASES[args.pid],
               'offline_dump_only': True, 'live_attach': False,
               'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'argv': sys.argv, 'calls': [], 'success': False}
    chunks = []

    def checked(value, operation):
        receipt['calls'].append({'operation': operation, 'hresult': '0x%08x' % (value & 0xffffffff)})
        if value < 0:
            raise RuntimeError('%s failed: 0x%08x' % (operation, value & 0xffffffff))

    def query_interface(interface, guid_text):
        guid = GUID.parse(guid_text)
        target = PVOID()
        checked(method(interface, 'IDebugClient', 'QueryInterface', HRESULT,
                       ctypes.POINTER(GUID), ctypes.POINTER(PVOID))(
                           interface, ctypes.byref(guid), ctypes.byref(target)), 'QueryInterface ' + guid_text)
        return target

    query_type = ctypes.WINFUNCTYPE(HRESULT, PVOID, ctypes.POINTER(GUID), ctypes.POINTER(PVOID))
    reference_type = ctypes.WINFUNCTYPE(ULONG, PVOID)
    output_type = ctypes.WINFUNCTYPE(HRESULT, PVOID, ULONG, ctypes.c_char_p)

    def query(this, guid, target):
        if bytes(guid.contents.bytes) not in (
                uuid.UUID('00000000-0000-0000-c000-000000000046').bytes_le,
                uuid.UUID('4bf58045-d654-4c40-b0af-683090f356dc').bytes_le):
            target[0] = None
            return -2147467262
        target[0] = this
        return 0

    def output(this, mask, value):
        chunks.append(value.decode('utf-8', errors='replace'))
        return 0

    callbacks = (query_type(query), reference_type(lambda this: 1),
                 reference_type(lambda this: 1), output_type(output))
    vtable = (PVOID * 4)(*(ctypes.cast(callback, PVOID).value for callback in callbacks))
    callback_object = ctypes.pointer(ctypes.cast(vtable, PVOID))
    symbol_path = args.symbol_path
    os.environ['_NT_SYMBOL_PATH'] = symbol_path
    os.environ['_NT_ALT_SYMBOL_PATH'] = ''
    engine_path = Path(args.engine).resolve()
    receipt['engine'] = {'path': str(engine_path), 'sha256': digest(engine_path)}
    receipt['symbol_path'] = symbol_path
    client = control = symbols = None
    try:
        engine = ctypes.WinDLL(str(engine_path))
        engine.DebugCreate.argtypes = [ctypes.POINTER(GUID), ctypes.POINTER(PVOID)]
        engine.DebugCreate.restype = HRESULT
        client_guid = GUID.parse('27fe5639-8407-4f47-8364-ee118fb08ac8')
        client = PVOID()
        checked(engine.DebugCreate(ctypes.byref(client_guid), ctypes.byref(client)), 'DebugCreate')
        control = query_interface(client, '5182e668-105e-416e-ad92-24ef800424ba')
        symbols = query_interface(client, '8c31e98c-983a-48a5-9016-6fe5d667a950')
        checked(method(client, 'IDebugClient', 'SetOutputCallbacks', HRESULT, PVOID)(
            client, callback_object), 'SetOutputCallbacks')
        # Ignore embedded absolute PDB paths; permit only the explicit symbol path.
        checked(method(symbols, 'IDebugSymbols', 'SetSymbolOptions', HRESULT, ULONG)(
            symbols, 0x80000 | 0x1000 | 0x80 | 0x200 | 4 | 2), 'SetSymbolOptions')
        checked(method(symbols, 'IDebugSymbols', 'SetSymbolPath', HRESULT, ctypes.c_char_p)(
            symbols, symbol_path.encode('mbcs')), 'SetSymbolPath')
        checked(method(symbols, 'IDebugSymbols', 'SetImagePath', HRESULT, ctypes.c_char_p)(
            symbols, (str(GAME) + ';C:\\Windows\\System32').encode('mbcs')), 'SetImagePath')
        checked(method(client, 'IDebugClient', 'OpenDumpFile', HRESULT, ctypes.c_char_p)(
            client, str(dump).encode('ascii')), 'OpenDumpFile existing dump')
        checked(method(control, 'IDebugControl', 'WaitForEvent', HRESULT, ULONG, ULONG)(
            control, 0, 60000), 'WaitForEvent')
        execute = method(control, 'IDebugControl', 'Execute', HRESULT, ULONG, ctypes.c_char_p, ULONG)
        commands = ['version', '.sympath', '.exepath', '.ecxr', 'kpn', '.exr -1',
                    'lmv m ucrtbase', 'lmv m VCRUNTIME140*', 'lmv m Minecraft*',
                    'lmv m native_focus_guard']
        if args.command:
            commands.extend(args.command)
        receipt['commands'] = commands
        for command in commands:
            chunks.append('\nCOMMAND: ' + command + '\n')
            checked(execute(control, 0, command.encode('ascii'), 0), 'Execute ' + command)
        receipt['success'] = True
    except Exception:
        receipt['error'] = traceback.format_exc()
        chunks.append('\nWRAPPER ERROR:\n' + receipt['error'])
    finally:
        if client:
            checked(method(client, 'IDebugClient', 'EndSession', HRESULT, ULONG)(client, 0),
                    'EndSession passive')
        for interface in (symbols, control, client):
            if interface:
                method(interface, 'IDebugClient', 'Release', ULONG)(interface)
        receipt['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        destination.with_suffix('.txt').write_text(''.join(chunks), encoding='utf-8')
        receipt['output_sha256'] = digest(destination.with_suffix('.txt'))
        destination.with_suffix('.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps({'success': receipt['success'], 'output': str(destination.with_suffix('.txt')),
                      'error': receipt.get('error')}, indent=2))
    return 0 if receipt['success'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--pid', type=int, choices=sorted(CASES), required=True)
    parser.add_argument('--label', default='local')
    parser.add_argument('--engine', default='C:/Windows/System32/dbgeng.dll')
    parser.add_argument('--symbol-path', default='C:\\Windows\\System32')
    parser.add_argument('--command', action='append')
    raise SystemExit(debug_dump(parser.parse_args()))
