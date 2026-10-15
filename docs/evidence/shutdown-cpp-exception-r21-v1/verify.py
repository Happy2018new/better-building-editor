"""Recompute preserved evidence without a debugger, Windows API or third party package."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET


BASE = Path(__file__).resolve().parent
EXPECTED_STACK = (
    'ucrtbase!abort+0x4e', 'ucrtbase!terminate+0x1e', 'VCRUNTIME140_1+0x186b',
    'VCRUNTIME140_1+0x21a5', 'VCRUNTIME140_1+0x21f6', 'VCRUNTIME140_1!_CxxFrameHandler4+0xa5',
    'ntdll!_chkstk+0x9f', 'ntdll!RtlWow64GetCurrentMachine+0x655', 'ntdll!RtlRaiseException+0x18d',
    'KERNELBASE!RaiseException+0x8a', 'VCRUNTIME140!CxxThrowException+0x97',
    'msvcp140!std::_Xbad_function_call+0x1f', 'Minecraft_Windows+0x17e530b',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(name):
    return json.loads((BASE / name).read_text(encoding='utf-8'))


def inventory():
    result = {}
    for path in sorted(BASE.rglob('*')):
        if path.is_file() and path != BASE / 'manifest.json':
            require(path.suffix.lower() not in ('.dll', '.exe', '.dmp', '.nupkg', '.zip', '.pdb'),
                    'Unexpected binary in text-only package: ' + str(path))
            result[path.relative_to(BASE).as_posix()] = {'size': path.stat().st_size, 'sha256': sha(path)}
    return result


def fragments(name, external):
    payload = load(name)
    result = {}
    for item in payload['fragments']:
        data = bytes.fromhex(item['hex'])
        require(item['id'] not in result, 'Duplicate fragment id')
        require(len(data) == item['size'] and hashlib.sha256(data).hexdigest() == item['sha256'],
                'Fragment byte identity mismatch')
        result[item['id']] = (item, data)
    if external:
        source = Path(payload['source']['private_path'])
        require(source.stat().st_size == payload['source']['size'] and
                sha(source) == payload['source']['sha256'], 'External original identity mismatch')
        with source.open('rb') as stream:
            for item, data in result.values():
                stream.seek(item['file_offset'])
                require(stream.read(item['size']) == data, 'External original slice differs')
    return payload, result


def modules(items):
    result = {}
    for key in items:
        if not key.startswith('module-record-'):
            continue
        leaf = key[len('module-record-'):]
        record_item, raw = items[key]
        base, size, checksum, timestamp, name_offset = struct.unpack_from('<QIIII', raw)
        name_item, name_raw = items['module-path-' + leaf]
        length = struct.unpack_from('<I', name_raw)[0]
        require(name_item['file_offset'] == name_offset and len(name_raw) == length + 4,
                'Module path binding mismatch')
        path = name_raw[4:].decode('utf-16-le')
        require(path.rsplit('\\', 1)[-1].lower() == leaf, 'Module leaf differs')
        result[leaf] = {'base': base, 'size': size, 'checksum': checksum, 'timestamp': timestamp, 'path': path}
    return result


def type_reader(items):
    dos = items['dos-header'][1]
    header_item, headers = items['pe-headers-and-section-table']
    pe_offset = struct.unpack_from('<I', dos, 0x3c)[0]
    require(header_item['file_offset'] == pe_offset and headers[:4] == b'PE\0\0', 'PE headers invalid')
    sections = struct.unpack_from('<H', headers, 6)[0]
    optional_size = struct.unpack_from('<H', headers, 20)[0]
    timestamp = struct.unpack_from('<I', headers, 8)[0]
    image_size = struct.unpack_from('<I', headers, 24 + 56)[0]
    checksum = struct.unpack_from('<I', headers, 24 + 64)[0]
    for item, data in items.values():
        if 'rva' not in item:
            continue
        rva = int(item['rva'], 16)
        matching = False
        for index in range(sections):
            offset = 24 + optional_size + index * 40
            virtual_size, address, raw_size, body = struct.unpack_from('<4I', headers, offset + 8)
            if address <= rva and rva + len(data) <= address + raw_size:
                require(item['file_offset'] == body + rva - address, 'PE slice file mapping differs')
                matching = True
                break
        require(matching, 'PE slice is outside section raw data')

    def read(rva, size):
        for item, data in items.values():
            if 'rva' in item:
                start = int(item['rva'], 16)
                if start <= rva and rva + size <= start + len(data):
                    return data[rva - start:rva - start + size]
        raise ValueError('Required RVA is not retained: 0x%x' % rva)

    return read, {'timestamp': timestamp, 'size': image_size, 'checksum': checksum}


def verify_log(pid):
    for label in ('local', 'cpp-record'):
        prefix = 'logs/dbgeng-%d-%s' % (pid, label)
        receipt = load(prefix + '.json')
        require(receipt['success'] and receipt['offline_dump_only'] and not receipt['live_attach'],
                'Debugger receipt not accepted')
        require(all(item['hresult'] == '0x00000000' for item in receipt['calls']), 'Debugger call failed')
        require(sha(BASE / (prefix + '.txt')) == receipt['output_sha256'], 'Raw debugger log differs')
        text = (BASE / (prefix + '.txt')).read_text(encoding='utf-8')
        trace = text.split('COMMAND: kpn\n', 1)[1].split('\nCOMMAND:', 1)[0]
        stack = tuple(re.findall(r'^\w{2}\s+[0-9a-f`]+\s+[0-9a-f`]+\s+(.*)$', trace, re.M))
        require(stack == EXPECTED_STACK, 'Normalized captured stack differs')
        require('Subcode: 0x7 FAST_FAIL_FATAL_APP_EXIT' in text, 'Fatal exit subcode differs')
        if label == 'cpp-record':
            require('ExceptionCode: e06d7363 (C++ EH exception)' in text, 'Original C++ record missing')


def verify_process(case):
    prefix = 'process/' + case['label'] + '/'
    session = load(prefix + 'session-selected.json')
    exact = load(prefix + 'exact-exit.json')
    require(session['id'] == exact['session'] == case['session'], 'Session binding differs')
    game = exact['processes']['game']
    require(session['game_pid'] == game['pid'] == case['pid'], 'Game PID binding differs')
    require(session['game_identity'] == game['identity'] == case['identity'], 'Creation identity differs')
    require(game['exit_code'] == 0xc0000409 and exact['processes']['mcdk']['exit_code'] == 0,
            'Exact exit code differs')
    parsed = {}
    ns = {'e': 'http://schemas.microsoft.com/win/2004/08/events/event'}
    for entry in load(prefix + 'application-events.json'):
        root = ET.fromstring(entry['xml'])
        kind = int(root.find('e:System/e:EventID', ns).text)
        fields = {node.attrib['Name']: node.text for node in root.findall('e:EventData/e:Data', ns)}
        require(fields == entry['fields'], 'Event parsed fields differ from retained XML')
        require(int(root.find('e:System/e:EventRecordID', ns).text) == entry['record'], 'Event ID differs')
        parsed[kind] = fields
    error, wer = parsed[1000], parsed[1001]
    require(int(error['ProcessId'], 16) == case['pid'], 'Windows event PID differs')
    require(str(int(error['ProcessCreationTime'], 16)) == case['identity'], 'Windows creation identity differs')
    require(error['IntegratorReportId'] == wer['ReportId'] == case['integrator_report_identifier'],
            'WER event correlation differs')
    require(error['ExceptionCode'] == 'c0000409' and int(error['FaultingOffset'], 16) == 0xa527e,
            'Windows event fault differs')
    require(wer['P9'] == '0000000000000007', 'WER fatal exit code differs')
    report_path = BASE / (prefix + 'Report.wer')
    require(sha(report_path) == case['wer_sha256'], 'Raw WER byte identity differs')
    report = report_path.read_text(encoding='utf-16')
    require('ReportIdentifier=' + case['wer_report_identifier'] in report, 'WER ReportIdentifier differs')
    require('IntegratorReportIdentifier=' + case['integrator_report_identifier'] in report,
            'WER integrator identity differs')
    require(not case['WM_CLOSE_post_exact_timestamp_recorded'], 'Unsupported window-message evidence claim')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--write-manifest', action='store_true')
    parser.add_argument('--check-original-inputs', action='store_true')
    args = parser.parse_args()
    files = inventory()
    manifest_path = BASE / 'manifest.json'
    if args.write_manifest:
        require(not manifest_path.exists(), 'Refusing to replace existing manifest')
        manifest_path.write_text(json.dumps({'schema': 1, 'files': files}, indent=2) + '\n', encoding='utf-8')
    require(load('manifest.json')['files'] == files, 'Manifest or path inventory differs')
    for entry in load('provenance.json')['copied_verbatim']:
        require(files[entry['package_path']]['sha256'] == entry['sha256'], 'Copied source identity differs')
    header = (BASE / 'inputs/DbgEng.h').read_text(encoding='utf-8-sig')
    indices = load('interface-indices.json')
    for interface in ('IDebugClient', 'IDebugControl', 'IDebugSymbols'):
        block = re.search(r'DECLARE_INTERFACE_\(\s*' + interface +
                          r'\s*,\s*IUnknown\s*\)\s*\{(.*?)\n\};', header, re.S).group(1)
        declarations = re.findall(r'STDMETHODV?(?:_\(\s*[^,]+,\s*(\w+)\s*\)|\(\s*(\w+)\s*\))', block)
        require({left or right: index for index, (left, right) in enumerate(declarations)} == indices[interface],
                'Official interface method order differs')
    require(indices['IDebugControl']['Execute'] == 66 and indices['IDebugControl']['WaitForEvent'] == 93,
            'Corrected DbgEng method offsets differ')
    network = load('microsoft-sources.json')['network_inputs']
    header_source = next(item for item in network if item['name'] == 'DbgEng.h')
    require(sha(BASE / 'inputs/DbgEng.h') == header_source['sha256'], 'Microsoft header identity differs')
    type_source, type_items = fragments('fragments/msvcp140-types.json', args.check_original_inputs)
    read_type, pe_identity = type_reader(type_items)
    original_analysis = load('analysis/cpp-inspection-v2.json')
    bindings = load('process-bindings.json')['cases']
    for binding in bindings:
        pid = binding['pid']
        verify_process(binding)
        verify_log(pid)
        source, items = fragments('fragments/dump-%d.json' % pid, args.check_original_inputs)
        accepted = next(case for case in original_analysis['cases'] if case['pid'] == pid)
        require(source['source']['sha256'] == accepted['dump_sha256'], 'Dump identity differs')
        require(source['source']['private_path'] == load('logs/dbgeng-%d-local.json' % pid)['dump'],
                'Private dump path binding differs')
        module = modules(items)
        require(all(module['msvcp140.dll'][key] == value for key, value in pe_identity.items()),
                'Runtime PE does not match dump module identity')
        context_item, context = items['exception-context-amd64']
        stream_item, stream = items['fast-fail-exception-stream']
        require(struct.unpack_from('<I', stream, 8)[0] == 0xc0000409, 'Final exception differs')
        context_size, context_offset = struct.unpack_from('<II', stream, 160)
        require(context_offset == context_item['file_offset'] and context_size == len(context),
                'Exception context source mapping differs')
        require(struct.unpack_from('<Q', context, 128)[0] == 7, 'Fault RCX differs')
        rsp = struct.unpack_from('<Q', context, 152)[0]
        record_item, record = items['original-cpp-exception-record']
        require(int(record_item['virtual_address'], 16) == struct.unpack_from('<Q', context, 232)[0],
                'Original record does not match captured R14')
        require(record.hex() == accepted['record_hex'], 'Original record bytes differ from v2 analysis')
        code, flags, nested, exception_address, count, _ = struct.unpack_from('<IIQQII', record)
        require(code == 0xe06d7363 and flags == 0x81 and count == 4, 'Original C++ exception differs')
        magic, obj, throw, image_base = struct.unpack_from('<4Q', record, 32)
        require(magic == 0x19930520 and image_base == module['msvcp140.dll']['base'], 'C++ image binding differs')
        obj_item, obj_raw = items['original-cpp-exception-object']
        require(obj == int(obj_item['virtual_address'], 16), 'Exception object pointer differs')
        require(type_source['source']['sha256'] == accepted['throw_metadata_image']['sha256'],
                'Matching runtime hash differs')
        throw_info = read_type(throw - image_base, 16)
        array_rva = struct.unpack_from('<I', throw_info, 12)[0]
        type_count = struct.unpack('<I', read_type(array_rva, 4))[0]
        types = []
        for index in range(type_count):
            catch_rva = struct.unpack('<I', read_type(array_rva + 4 + index * 4, 4))[0]
            catch = read_type(catch_rva, 28)
            descriptor = struct.unpack_from('<I', catch, 4)[0]
            types.append(read_type(descriptor + 16, 64).split(b'\0', 1)[0].decode('ascii'))
        require(types == ['.?AVbad_function_call@std@@', '.?AVexception@std@@'], 'Recomputed C++ types differ')
        require(struct.unpack('<Q', items['abort-return-slot'][1])[0] == module['ucrtbase.dll']['base'] + 0xc218e,
                'Captured abort return slot differs')
        require(struct.unpack('<Q', items['terminate-return-slot'][1])[0] == module['vcruntime140_1.dll']['base'] + 0x186b,
                'Captured terminate return slot differs')
        require(struct.unpack('<Q', items['first-game-return-slot'][1])[0] == module['minecraft.windows.exe']['base'] + 0x17e530b,
                'Captured first game return differs')
        require(not source['game_code_captured'], 'Unsupported engine code evidence claim')
    summary = load('summary.json')
    require(summary['underlying_engine_cause'] == summary['guard_causality'] == 'unknown', 'Unsupported root-cause claim')
    require(not summary['stack_corruption_established'] and not summary['game_unwind_beyond_return_accepted'],
            'Unsupported stack claim')
    print(json.dumps({'cases_verified': len(bindings), 'raw_frames_per_trace': len(EXPECTED_STACK),
                      'recomputed_cpp_type': 'std::bad_function_call', 'engine_return_rva': '0x17e530b',
                      'engine_root_cause': 'unknown', 'guard_causality': 'unknown',
                      'actual_dbgeng_reexecuted': False, 'external_originals_checked': args.check_original_inputs,
                      'files': len(files), 'bytes': sum(item['size'] for item in files.values()),
                      'manifest_sha256': sha(manifest_path)}, indent=2))


if __name__ == '__main__':
    main()
