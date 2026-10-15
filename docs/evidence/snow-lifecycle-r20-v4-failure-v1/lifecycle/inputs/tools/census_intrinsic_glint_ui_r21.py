"""Page through every exact-version loaded item using removable native UI pairs.

The auxiliary pass covers distinct textures in the measured resolver domain,
not every possible NBT state or unmeasured auxiliary value. A pause request is
acknowledged only between restored pages; the game process keeps running.
"""
import argparse
from collections import Counter
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from analyze_intrinsic_glint_ui_r21 import analyze
from freeze_intrinsic_glint_project_r21 import fingerprint
from probe_intrinsic_glint_r21 import ROOT, VERSION
from probe_intrinsic_glint_ui_r21 import load_session, run
from read_owned_startup_handles import snapshot
from _session import _identity, _kernel

BASIC = ROOT / '.runtime/item-catalog-info-r16/catalog.json'
TEXTURES = ROOT / '.runtime/item-catalog-r16/catalog.json'
CONTROLS = [('minecraft:diamond_sword', 0, False),
            ('minecraft:golden_apple', 0, False), ('minecraft:stone', 0, False),
            ('minecraft:enchanted_golden_apple', 0, False)]
LAYOUT = {'columns': 12, 'top': 48., 'layer': 5, 'control_count': len(CONTROLS)}


class PerformanceInfo(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD)] + [(name, ctypes.c_size_t) for name in (
        'CommitTotal', 'CommitLimit', 'CommitPeak', 'PhysicalTotal',
        'PhysicalAvailable', 'SystemCache', 'KernelTotal', 'KernelPaged',
        'KernelNonpaged', 'PageSize')] + [
            ('HandleCount', wintypes.DWORD), ('ProcessCount', wintypes.DWORD),
            ('ThreadCount', wintypes.DWORD)]


def commit_at_boundary():
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    psapi.GetPerformanceInfo.argtypes = [ctypes.POINTER(PerformanceInfo), wintypes.DWORD]
    psapi.GetPerformanceInfo.restype = wintypes.BOOL
    info = PerformanceInfo()
    info.cb = ctypes.sizeof(info)
    if not psapi.GetPerformanceInfo(ctypes.byref(info), info.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {'observed_at': datetime.now(timezone.utc).isoformat(),
            'commit_total_bytes': info.CommitTotal * info.PageSize,
            'commit_limit_bytes': info.CommitLimit * info.PageSize,
            'commit_available_bytes': (info.CommitLimit - info.CommitTotal) * info.PageSize,
            'physical_available_bytes': info.PhysicalAvailable * info.PageSize}


def resource_stop(handles, commit, handle_threshold, min_commit_gib):
    if handles.get('status') != 'live' or handles['handle_count'] >= handle_threshold:
        return 'owned_game_handle_budget'
    if commit['commit_available_bytes'] < min_commit_gib * 1024 ** 3:
        return 'system_commit_budget'
    return None


def requests(basic, textures, variants):
    if (not basic.get('completed') or not textures.get('completed') or
            basic.get('engine_version') != VERSION or textures.get('engine_version') != VERSION):
        raise ValueError('Complete exact-version native catalogs are required')
    loaded = sorted({row['name'] for row in basic['rows']})
    result = [(name, 0, False) for name in loaded]
    represented = set((name, aux) for name, aux, unused in result)
    if variants:
        by_texture = {}
        for row in sorted(textures['rows'], key=lambda row: (row['name'], row['aux'])):
            if row['name'] not in loaded or not row.get('texture'):
                continue
            by_texture.setdefault((row['name'], row['texture']), row['aux'])
        for (name, unused), aux in sorted(by_texture.items()):
            if (name, aux) not in represented:
                result.append((name, aux, False))
                represented.add((name, aux))
    return result


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


def pause_at_boundary(path, completed_pages):
    if path is None or not path.exists():
        return
    ack = path.with_suffix(path.suffix + '.ack.json')
    write_json(ack, {'paused_at_restored_page_boundary': True,
                     'game_process_suspended': False, 'owned_controls_present': False,
                     'completed_pages': completed_pages,
                     'acknowledged_at': datetime.now(timezone.utc).isoformat()})
    print(json.dumps({'pause_ack': str(ack), 'completed_pages': completed_pages}), flush=True)
    while path.exists():
        time.sleep(.5)
    ack.unlink()
    print(json.dumps({'resumed_after_restored_boundary': True}), flush=True)


def handles_at_boundary(session, owner):
    manifest = load_session(session, owner, live=True)
    kernel = _kernel()
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                 ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.GetProcessHandleCount.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetProcessHandleCount.restype = wintypes.BOOL
    return snapshot(kernel, _identity, manifest['game_pid'], manifest['game_identity'],
                    manifest['game_executable'])


def census(args):
    basic = json.loads(BASIC.read_text(encoding='utf8'))
    textures = json.loads(TEXTURES.read_text(encoding='utf8'))
    cases = requests(basic, textures, args.texture_variants)
    frozen_project = json.loads(args.project_manifest.read_text(encoding='ascii'))
    session = load_session(args.session, args.owner, live=True)
    project = Path(session['project'])
    if fingerprint(project) != frozen_project['files']:
        raise ValueError('The native UI project differs from its complete frozen inputs')
    pages = [cases[start:start + args.page_size] for start in range(0, len(cases), args.page_size)]
    binding = {'basic_sha256': hashlib.sha256(BASIC.read_bytes()).hexdigest(),
               'textures_sha256': hashlib.sha256(TEXTURES.read_bytes()).hexdigest(),
               'requests_sha256': hashlib.sha256(json.dumps(cases).encode('ascii')).hexdigest(),
               'project_files_sha256': frozen_project['files_sha256'],
               'sampler_sha256': hashlib.sha256(
                   Path(__file__).with_name('probe_intrinsic_glint_ui_r21.py').read_bytes()).hexdigest(),
               'layout': LAYOUT, 'controls': [list(row) for row in CONTROLS],
               'page_size': args.page_size, 'texture_variants': args.texture_variants}
    args.output.mkdir(parents=True, exist_ok=True)
    summary_path = args.output / 'census.json'
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding='ascii'))
        if summary['binding'] != binding:
            raise ValueError('Existing census uses different catalog inputs or requests')
    else:
        summary = {'schema': 1, 'engine_version': VERSION, 'binding': binding,
                   'loaded_id_count': len(basic['rows']), 'requested_pairs': len(cases),
                   'requested_pages': len(pages), 'pages': [], 'completed': False,
                   'production_qualified': False,
                   'limitations': ['Only auxiliary zero is exhaustive across loaded identifiers.',
                                   'The optional variant pass samples each measured distinct texture.',
                                   'Equal textures do not prove equal rules at unmeasured auxiliary values.',
                                   'No item target, location, clock time or other NBT state is inspected.',
                                   'Native UI classification does not qualify projection pixels.']}
    processed, newly_processed = len(summary['pages']), 0
    for page_index in range(processed, len(pages)):
        pause_at_boundary(args.pause_file, len(summary['pages']))
        handles = handles_at_boundary(args.session, args.owner)
        commit = commit_at_boundary()
        stop_reason = resource_stop(handles, commit, args.handle_threshold, args.min_commit_gib)
        if stop_reason:
            summary['stopped_at_restored_boundary'] = {
                'reason': stop_reason, 'handles': handles, 'system_memory': commit,
                'handle_threshold': args.handle_threshold, 'min_commit_gib': args.min_commit_gib,
                'completed_pages': len(summary['pages'])}
            write_json(summary_path, summary)
            print(json.dumps(summary['stopped_at_restored_boundary']), flush=True)
            break
        started = time.perf_counter()
        output = args.output / ('page-%03d' % page_index)
        if output.exists():
            raise ValueError('An incomplete page exists; review its restoration before retrying: ' + str(output))
        report = run(args.session, args.owner, output, args.wgc,
                     cases=CONTROLS + pages[page_index], layout=LAYOUT)
        analysis = analyze(output)
        control_status = [row['classification'] for row in analysis['rows'][:len(CONTROLS)]]
        if (not analysis['native_controls_passed'] or control_status !=
                ['no_intrinsic_glint_in_this_probe'] * 3 + ['intrinsic_glint_native_confirmed']):
            raise RuntimeError('Native page controls did not qualify; page remains unaccepted')
        rows = analysis['rows'][len(CONTROLS):]
        summary['pages'].append({'index': page_index, 'path': output.name,
                                 'elapsed_seconds': time.perf_counter() - started,
                                 'handles_before': handles,
                                 'handles_after': handles_at_boundary(args.session, args.owner),
                                 'system_memory_before': commit,
                                 'system_memory_after': commit_at_boundary(),
                                 'restored': report['restoration']['restored'],
                                 'report_sha256': hashlib.sha256((output / 'report.json').read_bytes()).hexdigest(),
                                 'analysis_sha256': hashlib.sha256((output / 'analysis.json').read_bytes()).hexdigest(),
                                 'classifications': dict(Counter(row['classification'] for row in rows)),
                                 'rows': rows})
        all_rows = [row for page in summary['pages'] for row in page['rows']]
        summary['completed'] = len(summary['pages']) == len(pages)
        summary['coverage'] = {'observed_pairs': len(all_rows),
                               'observed_ids': len({row['name'] for row in all_rows}),
                               'classifications': dict(Counter(row['classification'] for row in all_rows)),
                               'intrinsic_pairs': [{'name': row['name'], 'aux': row['aux']}
                                                   for row in all_rows if row['classification'] ==
                                                   'intrinsic_glint_native_confirmed']}
        write_json(summary_path, summary)
        print(json.dumps({'page_completed': page_index, 'pages': len(pages),
                          'elapsed_seconds': summary['pages'][-1]['elapsed_seconds'],
                          'handles_after': summary['pages'][-1]['handles_after'],
                          'system_memory_after': summary['pages'][-1]['system_memory_after'],
                          'coverage': summary['coverage']}), flush=True)
        newly_processed += 1
        pause_at_boundary(args.pause_file, len(summary['pages']))
        if args.limit_pages and newly_processed >= args.limit_pages:
            break
    summary['project_source_unchanged'] = fingerprint(project) == frozen_project['files']
    write_json(summary_path, summary)
    if not summary['project_source_unchanged']:
        raise RuntimeError('The private native UI source changed during census')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--wgc', type=Path, required=True)
    parser.add_argument('--project-manifest', type=Path, required=True)
    parser.add_argument('--page-size', type=int, default=32)
    parser.add_argument('--texture-variants', action='store_true')
    parser.add_argument('--pause-file', type=Path)
    parser.add_argument('--limit-pages', type=int)
    parser.add_argument('--handle-threshold', type=int, default=200000)
    parser.add_argument('--min-commit-gib', type=float, default=3.)
    args = parser.parse_args()
    if args.page_size < 1 or args.page_size > 32:
        parser.error('Page size must be between 1 and 32')
    if args.min_commit_gib < 0:
        parser.error('Minimum available system commit must be nonnegative')
    result = census(args)
    print(json.dumps({'completed': result['completed'], 'coverage': result.get('coverage')}), flush=True)
