"""Reexecute Microsoft DbgEng against an external matching dump, never a process."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid


BASE = Path(__file__).resolve().parent
HRESULT = ctypes.c_long
ULONG = wintypes.ULONG
PVOID = ctypes.c_void_p


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(name):
    return json.loads((BASE / name).read_text(encoding='utf-8'))


def validate_inputs(args):
    receipt = load('logs/dbgeng-%d-local.json' % args.case_pid)
    if sha(args.dump) != receipt['dump_sha256']:
        raise ValueError('External dump does not match the frozen case identity')
    if sha(args.engine) != receipt['engine']['sha256']:
        raise ValueError('External DbgEng does not match the accepted engine identity')
    inventory = load('analysis/cpp-inspection-v2.json')['binary_inventory']
    tools = {'dbgeng.dll', 'dbghelp.dll', 'dbgcore.dll', 'dbgmodel.dll'}
    resolved = []
    for item in inventory:
        name = item['source'].replace('\\', '/').rsplit('/', 1)[-1]
        directories = [args.engine.parent] if name.lower() in tools else args.image_directory
        candidate = next((directory / name for directory in directories
                          if (directory / name).is_file() and sha(directory / name) == item['sha256']), None)
        if candidate is None:
            raise ValueError('Missing external matching image: ' + name)
        resolved.append({'name': name, 'path': str(candidate), 'sha256': item['sha256']})
    return {'case_pid': args.case_pid, 'dump': str(args.dump), 'dump_sha256': sha(args.dump),
            'engine': str(args.engine), 'engine_sha256': sha(args.engine),
            'matched_images': resolved, 'live_attach': False}


class GUID(ctypes.Structure):
    _fields_ = [('bytes', ctypes.c_ubyte * 16)]

    @classmethod
    def parse(cls, text):
        return cls((ctypes.c_ubyte * 16).from_buffer_copy(uuid.UUID(text).bytes_le))


def run(args, receipt):
    if os.name != 'nt':
        raise RuntimeError('Actual DbgEng reexecution requires Windows')
    if args.output.exists() or args.output.with_suffix('.json').exists():
        raise ValueError('Refusing to overwrite a previous debugger replay')
    indices = load('interface-indices.json')
    chunks = []
    calls = []

    def checked(value, name):
        calls.append({'operation': name, 'hresult': '0x%08x' % (value & 0xffffffff)})
        if value < 0:
            raise RuntimeError('%s: 0x%08x' % (name, value & 0xffffffff))

    def method(obj, kind, name, result, *parameters):
        table = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(PVOID))).contents
        return ctypes.WINFUNCTYPE(result, PVOID, *parameters)(table[indices[kind][name]])

    query_type = ctypes.WINFUNCTYPE(HRESULT, PVOID, ctypes.POINTER(GUID), ctypes.POINTER(PVOID))
    reference_type = ctypes.WINFUNCTYPE(ULONG, PVOID)
    output_type = ctypes.WINFUNCTYPE(HRESULT, PVOID, ULONG, ctypes.c_char_p)

    def query(this, guid, target):
        allowed = ('00000000-0000-0000-c000-000000000046', '4bf58045-d654-4c40-b0af-683090f356dc')
        if bytes(guid.contents.bytes) not in tuple(uuid.UUID(value).bytes_le for value in allowed):
            target[0] = None
            return -2147467262
        target[0] = this
        return 0

    def output(this, mask, text):
        chunks.append(text.decode('mbcs', errors='replace'))
        return 0

    callbacks = (query_type(query), reference_type(lambda this: 1),
                 reference_type(lambda this: 1), output_type(output))
    table = (PVOID * 4)(*(ctypes.cast(callback, PVOID).value for callback in callbacks))
    callback_obj = ctypes.pointer(ctypes.cast(table, PVOID))
    image_path = ';'.join(str(directory) for directory in args.image_directory)
    os.environ['_NT_SYMBOL_PATH'] = image_path
    os.environ['_NT_ALT_SYMBOL_PATH'] = ''
    engine = ctypes.WinDLL(str(args.engine))
    engine.DebugCreate.argtypes = [ctypes.POINTER(GUID), ctypes.POINTER(PVOID)]
    engine.DebugCreate.restype = HRESULT
    client = PVOID()
    control = symbols = None
    success = False
    error = None
    try:
        guid = GUID.parse('27fe5639-8407-4f47-8364-ee118fb08ac8')
        checked(engine.DebugCreate(ctypes.byref(guid), ctypes.byref(client)), 'DebugCreate')

        def interface(guid_text):
            target = PVOID()
            iid = GUID.parse(guid_text)
            checked(method(client, 'IDebugClient', 'QueryInterface', HRESULT,
                           ctypes.POINTER(GUID), ctypes.POINTER(PVOID))(
                               client, ctypes.byref(iid), ctypes.byref(target)), 'QueryInterface ' + guid_text)
            return target

        control = interface('5182e668-105e-416e-ad92-24ef800424ba')
        symbols = interface('8c31e98c-983a-48a5-9016-6fe5d667a950')
        checked(method(client, 'IDebugClient', 'SetOutputCallbacks', HRESULT, PVOID)(
            client, callback_obj), 'SetOutputCallbacks')
        checked(method(symbols, 'IDebugSymbols', 'SetSymbolOptions', HRESULT, ULONG)(
            symbols, 0x80000 | 0x1000 | 0x80 | 0x200 | 4 | 2), 'SetSymbolOptions')
        for name in ('SetSymbolPath', 'SetImagePath'):
            checked(method(symbols, 'IDebugSymbols', name, HRESULT, ctypes.c_char_p)(
                symbols, image_path.encode('mbcs')), name)
        checked(method(client, 'IDebugClient', 'OpenDumpFile', HRESULT, ctypes.c_char_p)(
            client, str(args.dump).encode('mbcs')), 'OpenDumpFile external matching dump')
        checked(method(control, 'IDebugControl', 'WaitForEvent', HRESULT, ULONG, ULONG)(
            control, 0, 60000), 'WaitForEvent')
        execute = method(control, 'IDebugControl', 'Execute', HRESULT, ULONG, ctypes.c_char_p, ULONG)
        for command in ('version', '.sympath', '.exepath', '.ecxr', 'kpn', '.exr -1',
                        'lmv m ucrtbase', 'lmv m VCRUNTIME140*', 'lmv m Minecraft*'):
            chunks.append('\nCOMMAND: ' + command + '\n')
            checked(execute(control, 0, command.encode('ascii'), 0), 'Execute ' + command)
        success = True
    except Exception as exc:
        error = repr(exc)
        chunks.append('\nREPLAY ERROR: ' + error + '\n')
    finally:
        if client:
            result = method(client, 'IDebugClient', 'EndSession', HRESULT, ULONG)(client, 0)
            calls.append({'operation': 'EndSession passive', 'hresult': '0x%08x' % (result & 0xffffffff)})
            if result < 0:
                success = False
        for obj in (symbols, control, client):
            if obj:
                method(obj, 'IDebugClient', 'Release', ULONG)(obj)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(''.join(chunks), encoding='utf-8')
        receipt.update({'success': success, 'error': error, 'calls': calls,
                        'output': str(args.output), 'output_sha256': sha(args.output), 'argv': sys.argv})
        args.output.with_suffix('.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return 0 if success else 1


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--case-pid', type=int, choices=(2188, 25292), required=True)
    parser.add_argument('--dump', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--image-directory', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check-inputs-only', action='store_true')
    args = parser.parse_args()
    args.dump = args.dump.resolve()
    args.engine = args.engine.resolve()
    args.image_directory = [directory.resolve() for directory in args.image_directory]
    receipt = validate_inputs(args)
    if args.check_inputs_only:
        print(json.dumps({'inputs_match': True, 'dbgeng_loaded': False, **receipt}, indent=2))
        return 0
    if args.output is None:
        parser.error('--output is required for actual debugger reexecution')
    args.output = args.output.resolve()
    if args.output.is_relative_to(BASE):
        parser.error('--output must be outside the immutable evidence package')
    return run(args, receipt)


if __name__ == '__main__':
    raise SystemExit(main())
