"""Build a text-only audit from frozen receipts and exact original byte slices."""
import datetime
import hashlib
import json
import mmap
from pathlib import Path
import re
import shutil
import struct


BASE = Path(__file__).resolve().parents[1]
RUNTIME = BASE.parent
V1 = RUNTIME / 'shutdown-audit-r21-v1'
V2 = RUNTIME / 'shutdown-audit-r21-v2'
ROOT = RUNTIME.parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(name, value):
    path = BASE / name
    if path.exists():
        raise RuntimeError('Refusing to overwrite: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def fragment(identifier, offset, raw, address=None):
    result = {'id': identifier, 'file_offset': offset, 'size': len(raw),
              'sha256': hashlib.sha256(raw).hexdigest(), 'hex': raw.hex()}
    if address is not None:
        result['virtual_address'] = hex(address)
    return result


def dump_fragments(pid):
    receipt = load(V2 / ('dbgeng-%d-local.json' % pid))
    path = Path(receipt['dump'])
    assert sha(path) == receipt['dump_sha256']
    result = {'source': {'kind': 'minidump', 'private_path': str(path),
                         'sha256': receipt['dump_sha256'], 'size': path.stat().st_size},
              'fragments': [], 'module_ids': []}
    fragments = result['fragments']
    with path.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
        fragments.append(fragment('minidump-header', 0, data[:32]))
        count, directory = struct.unpack_from('<II', data, 8)
        fragments.append(fragment('stream-directory', directory, data[directory:directory + count * 12]))
        streams = {}
        for index in range(count):
            kind, size, offset = struct.unpack_from('<III', data, directory + index * 12)
            streams[kind] = (offset, size)
        exception, exception_size = streams[6]
        fragments.append(fragment('fast-fail-exception-stream', exception, data[exception:exception + exception_size]))
        context_size, context_offset = struct.unpack_from('<II', data, exception + 160)
        fragments.append(fragment('exception-context-amd64', context_offset,
                                  data[context_offset:context_offset + context_size]))
        modules = {}
        module_offset = streams[4][0]
        wanted = {'minecraft.windows.exe', 'ucrtbase.dll', 'msvcp140.dll', 'vcruntime140.dll',
                  'vcruntime140_1.dll', 'ntdll.dll', 'kernelbase.dll', 'native_focus_guard.dll'}
        for index in range(struct.unpack_from('<I', data, module_offset)[0]):
            offset = module_offset + 4 + index * 108
            base, size, checksum, timestamp, name_offset = struct.unpack_from('<QIIII', data, offset)
            name_size = struct.unpack_from('<I', data, name_offset)[0]
            name = data[name_offset + 4:name_offset + 4 + name_size].decode('utf-16-le')
            leaf = name.rsplit('\\', 1)[-1].lower()
            if leaf in wanted:
                modules[leaf] = {'base': base, 'size': size, 'timestamp': timestamp, 'checksum': checksum}
                fragments.append(fragment('module-record-' + leaf, offset, data[offset:offset + 108]))
                fragments.append(fragment('module-path-' + leaf, name_offset,
                                          data[name_offset:name_offset + 4 + name_size]))
                result['module_ids'].append(leaf)
        assert set(modules) == wanted
        ranges = []
        if 5 in streams:
            offset = streams[5][0]
            for index in range(struct.unpack_from('<I', data, offset)[0]):
                descriptor_offset = offset + 4 + index * 16
                address, size, body = struct.unpack_from('<QII', data, descriptor_offset)
                ranges.append((address, size, body, descriptor_offset))
        if 9 in streams:
            offset = streams[9][0]
            count, body = struct.unpack_from('<QQ', data, offset)
            for index in range(count):
                descriptor_offset = offset + 16 + index * 16
                address, size = struct.unpack_from('<QQ', data, descriptor_offset)
                ranges.append((address, size, body, descriptor_offset))
                body += size

        def capture(identifier, address, size):
            for start, length, body, descriptor_offset in ranges:
                if start <= address and address + size <= start + length:
                    offset = body + address - start
                    item = fragment(identifier, offset, data[offset:offset + size], address)
                    item['memory_range'] = {'virtual_start': hex(start), 'size': length,
                                            'data_file_offset': body, 'descriptor_file_offset': descriptor_offset,
                                            'descriptor_hex': data[descriptor_offset:descriptor_offset + 16].hex()}
                    fragments.append(item)
                    return data[offset:offset + size]
            raise ValueError('Not captured: ' + hex(address))

        rsp = struct.unpack_from('<Q', data, context_offset + 152)[0]
        record_address = struct.unpack_from('<Q', data, context_offset + 232)[0]
        record = capture('original-cpp-exception-record', record_address, 152)
        code = struct.unpack_from('<I', record)[0]
        assert code == 0xe06d7363
        obj = struct.unpack_from('<Q', record, 40)[0]
        capture('original-cpp-exception-object', obj, 32)
        capture('abort-return-slot', rsp + 0x28, 8)
        capture('terminate-return-slot', rsp + 0x58, 8)
        text = (V2 / ('dbgeng-%d-local.txt' % pid)).read_text(encoding='utf-8')
        game_frame_sp = int(re.search(r'^0c\s+([0-9a-f`]+)', text, re.M).group(1).replace('`', ''), 16)
        returned = struct.unpack('<Q', capture('first-game-return-slot', game_frame_sp - 8, 8))[0]
        assert returned == modules['minecraft.windows.exe']['base'] + 0x17e530b
        result['first_game_return_rva'] = '0x17e530b'
        result['game_code_captured'] = any(start <= returned - 16 and returned + 16 <= start + length
                                           for start, length, _, _ in ranges)
    return result


def type_fragments():
    report = load(V2 / 'cpp-inspection.json')
    inventory = next(item for item in report['binary_inventory'] if item['source'].lower().endswith('msvcp140.dll'))
    path = Path(inventory['source'])
    assert sha(path) == inventory['sha256']
    data = path.read_bytes()
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    sections = struct.unpack_from('<H', data, pe + 6)[0]
    optional_size = struct.unpack_from('<H', data, pe + 20)[0]
    section_offset = pe + 24 + optional_size
    fragments = [fragment('dos-header', 0, data[:64]),
                 fragment('pe-headers-and-section-table', pe,
                          data[pe:section_offset + sections * 40])]

    def capture(identifier, rva, size):
        for index in range(sections):
            offset = section_offset + index * 40
            virtual_size, address, raw_size, raw_address = struct.unpack_from('<4I', data, offset + 8)
            if address <= rva and rva + size <= address + raw_size:
                body = raw_address + rva - address
                item = fragment(identifier, body, data[body:body + size])
                item['rva'] = hex(rva)
                fragments.append(item)
                return data[body:body + size]
        raise ValueError('RVA not backed by file: ' + hex(rva))

    throw_rva = int(report['cases'][0]['throw_metadata_image']['throw_rva'], 16)
    throw = capture('throw-info', throw_rva, 16)
    array_rva = struct.unpack_from('<I', throw, 12)[0]
    count_bytes = None
    for index in range(sections):
        offset = section_offset + index * 40
        virtual_size, address, raw_size, raw_address = struct.unpack_from('<4I', data, offset + 8)
        if address <= array_rva < address + raw_size:
            count_bytes = data[raw_address + array_rva - address:raw_address + array_rva - address + 4]
            break
    count = struct.unpack('<I', count_bytes)[0]
    array = capture('catchable-type-array', array_rva, 4 + count * 4)
    for index in range(count):
        catch_rva = struct.unpack_from('<I', array, 4 + index * 4)[0]
        catch = capture('catchable-type-%d' % index, catch_rva, 28)
        descriptor_rva = struct.unpack_from('<I', catch, 4)[0]
        capture('type-descriptor-%d' % index, descriptor_rva, 80)
    return {'source': {'kind': 'matching_runtime_PE', 'private_path': str(path),
                       'sha256': sha(path), 'size': len(data)}, 'fragments': fragments}


def main():
    provenance = []
    v1_index = load(V1 / 'manifest.json')['files']
    v2_index = {item['path']: item for item in load(V2 / 'manifest.json')['files']}

    def copy(origin, name, destination=None):
        destination = destination or name
        source = origin / name
        expected = (v1_index if origin == V1 else v2_index)[name]
        assert sha(source) == expected['sha256']
        target = BASE / destination
        if target.exists():
            raise RuntimeError('Refusing to overwrite: ' + str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        provenance.append({'package_path': destination, 'source_path': source.relative_to(ROOT).as_posix(),
                           'sha256': sha(source), 'size': source.stat().st_size,
                           'source_manifest_sha256': sha(origin / 'manifest.json')})

    for pid in (2188, 25292):
        for label in ('local', 'cpp-record'):
            for suffix in ('txt', 'json'):
                name = 'dbgeng-%d-%s.%s' % (pid, label, suffix)
                copy(V2, name, 'logs/' + name)
        write('fragments/dump-%d.json' % pid, dump_fragments(pid))
    for name, destination in (
            ('debug_existing_dump.py', 'sources/debug_existing_dump_v2.py'),
            ('inputs/DbgEng.h', 'inputs/DbgEng.h'),
            ('interface-indices.json', 'interface-indices.json'),
            ('acquisition.json', 'sources/acquisition-v2.json'),
            ('cpp-inspection.json', 'analysis/cpp-inspection-v2.json'),
            ('binary-signatures.json', 'analysis/binary-signatures-v2.json')):
        copy(V2, name, destination)
    for label in ('portal', 'shelf'):
        for name in ('application-events.json', 'exact-exit.json', 'Report.wer',
                     'session-selected.json', 'mcdk-shutdown-lines.json'):
            copy(V1, label + '/' + name, 'process/' + label + '/' + name)
    write('fragments/msvcp140-types.json', type_fragments())
    v1 = load(V1 / 'audit.json')
    cases = [case for case in v1['cases'] if case['pid'] in (2188, 25292)]
    write('process-bindings.json', {'cases': cases, 'source_path': '.runtime/shutdown-audit-r21-v1/audit.json',
                                    'source_sha256': sha(V1 / 'audit.json')})
    acquisition = load(V2 / 'acquisition.json')
    write('microsoft-sources.json', {'network_inputs': acquisition['network_inputs'],
                                    'acquired_utc': acquisition['acquired_utc'],
                                    'nuget_version': '20260319.1511.0', 'nuget_contains_exe': False,
                                    'actual_debugger': 'Windows DbgEng 10.0.26100.1 / DbgHelp 10.0.26100.9549',
                                    'authoritative_indices': 'interface-indices.json',
                                    'initial_acquisition_index_map_is_incomplete': True,
                                    'package_binary_retained': False})
    write('summary.json', {'schema': 1, 'case_pids': [2188, 25292],
                           'cpp_exception': 'std::bad_function_call', 'cpp_exception_code': '0xe06d7363',
                           'fatal_exit': 'FAST_FAIL_FATAL_APP_EXIT=7', 'first_game_return_rva': '0x17e530b',
                           'underlying_engine_cause': 'unknown', 'guard_causality': 'unknown',
                           'stack_corruption_established': False, 'game_unwind_beyond_return_accepted': False,
                           'live_game_actions': False, 'product_guard_stop_modified': False,
                           'raw_logs_are_copied_verbatim': True, 'original_dumps_are_external': True,
                           'debugger_binaries_are_external': True, 'lightweight_replay_is_dbgeng_reexecution': False})
    write('provenance.json', {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                              'copied_verbatim': provenance, 'byte_slices': 'fragments/*.json',
                              'all_slices_extracted_programmatically': True})
    print(json.dumps({'copied_verbatim_files': len(provenance), 'destination': str(BASE)}))


if __name__ == '__main__':
    main()
