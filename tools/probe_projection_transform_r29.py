"""Read-only R29 census, explicit-source audit and owned-session state probe.

This tool never starts/stops a game, grants a render qualification, or writes
world blocks. A successful probe is diagnostic evidence, not a visual pass.
"""
import argparse
import ast
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
MODULE = 'behavior_pack/modern_projection/projection/'
sys.path.insert(0, str(SCRIPTS))


def digest(path, normalize=False):
    data = path.read_bytes()
    return hashlib.sha256(data.replace(b'\r\n', b'\n') if normalize else data).hexdigest()


def explicit_sources(path, variable):
    """Read the checked-in literal comprehension without importing probe hosts."""
    tree = ast.parse(path.read_text(encoding='utf8'))
    values = [node.value for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == variable for target in node.targets)]
    if len(values) != 1:
        raise ValueError('Expected one explicit source assignment: ' + str(path))
    value = values[0]
    if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
            and value.func.id == 'tuple' and len(value.args) == 1
            and isinstance(value.args[0], ast.GeneratorExp)):
        raise ValueError('Unsupported source declaration: ' + str(path))
    expression = value.args[0]
    if len(expression.generators) != 1:
        raise ValueError('Expected one literal source generator')
    generator = expression.generators[0]
    if generator.ifs or not isinstance(generator.target, ast.Name):
        raise ValueError('Conditional source declarations need explicit review')
    names = ast.literal_eval(generator.iter)
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                constants[node.targets[0].id] = node.value.value

    def expression_value(node, bindings):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name) and node.id in bindings:
            return bindings[node.id]
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return expression_value(node.left, bindings) + expression_value(node.right, bindings)
        raise ValueError('Unsupported source expression requires explicit review')

    result = []
    for name in names:
        if not isinstance(name, str):
            raise ValueError('Source module names must be strings')
        value = expression_value(expression.elt, dict(constants, **{generator.target.id: name}))
        if not value.startswith(MODULE) or not value.endswith('.py'):
            raise ValueError('Source declaration leaves the reviewed projection directory')
        result.append(value)
    if len(result) != len(set(result)):
        raise ValueError('Duplicate explicit source declarations')
    return tuple(result)


def source_audit(project, helpers):
    declarations = (
        ('water', 'tools/generate_liquid_product_owner_contract.py', 'SOURCES'),
        ('portal', 'tools/probe_portal_product_r16.py', 'SOURCES'),
        ('book', 'tools/probe_book_native_r16.py', 'OWNER_SOURCES'))
    scopes = {}
    for label, filename, variable in declarations:
        paths = explicit_sources(project / filename, variable)
        scopes[label] = {'declaration': filename, 'count': len(paths),
                         'declaration_sha256': digest(project / filename),
                         'source_sha256_lf': {name: digest(project / name, True) for name in paths},
                         'requested_helpers_missing': [name for name in helpers if name not in paths]}
    stored_path = project / 'tools/data/liquid_product_owner_contract_v1.json'
    stored = json.loads(stored_path.read_bytes())
    expected, actual = stored['source_sha256'], scopes['water']['source_sha256_lf']
    differences = []
    for name in sorted(set(expected) | set(actual)):
        if expected.get(name) != actual.get(name):
            differences.append({'path': name, 'stored': expected.get(name), 'current': actual.get(name)})
    return {'scopes': scopes, 'water_stored_contract_sha256': digest(stored_path),
            'water_source_differences': differences,
            'water_generator_changed': stored.get('generator_sha256') != digest(project / declarations[0][1], True),
            'all_requested_helpers_declared': all(not row['requested_helpers_missing'] for row in scopes.values()),
            'scope': 'Explicit declarations only; not a transitive dependency or GPU qualification',
            'runtime_gate_note': 'Runtime compares stored metadata constants; it does not hash Python files.'}


def commit_memory():
    from ctypes import wintypes
    class Performance(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD)] + [(key, ctypes.c_size_t) for key in
            ('CommitTotal', 'CommitLimit', 'CommitPeak', 'PhysicalTotal', 'PhysicalAvailable',
             'SystemCache', 'KernelTotal', 'KernelPaged', 'KernelNonpaged', 'PageSize')] + [
             (key, wintypes.DWORD) for key in ('HandleCount', 'ProcessCount', 'ThreadCount')]
    api = ctypes.WinDLL('psapi', use_last_error=True)
    api.GetPerformanceInfo.argtypes = (ctypes.POINTER(Performance), wintypes.DWORD)
    api.GetPerformanceInfo.restype = wintypes.BOOL
    info = Performance()
    info.cb = ctypes.sizeof(info)
    if not api.GetPerformanceInfo(ctypes.byref(info), info.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {'committed_bytes': info.CommitTotal * info.PageSize,
            'limit_bytes': info.CommitLimit * info.PageSize,
            'headroom_bytes': (info.CommitLimit - info.CommitTotal) * info.PageSize,
            'physical_available_bytes': info.PhysicalAvailable * info.PageSize}


def census():
    from _session import registry_dir, process_identity, read_json
    counts, live, errors, reused = {}, [], [], 0
    for path in registry_dir().glob('*/session.json'):
        try:
            session = read_json(path)
        except (OSError, ValueError) as error:
            errors.append({'path': str(path), 'error': str(error)})
            continue
        state = session.get('state', 'unknown')
        counts[state] = counts.get(state, 0) + 1
        for kind in ('game', 'mcdk'):
            pid = session.get(kind + '_pid')
            actual = process_identity(pid) if pid else None
            if actual and actual == session.get(kind + '_identity'):
                live.append({'session_file': str(path), 'owner': session.get('owner'),
                             'project': session.get('project'), 'state': state, 'kind': kind,
                             'pid': pid, 'identity': actual})
            elif actual:
                reused += 1
    # No command lines or session tokens are included in this report.
    command = "Get-CimInstance Win32_Process -Filter \"Name='Minecraft.Windows.exe'\" | Select-Object ProcessId,HandleCount,ThreadCount,ExecutablePath | ConvertTo-Json -Compress"
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command],
                            capture_output=True, text=True, encoding='utf8', check=True)
    processes = json.loads(result.stdout or '[]')
    if isinstance(processes, dict):
        processes = [processes]
    for process in processes:
        process['live_creation_identity'] = process_identity(process['ProcessId'])
    return {'session_records': sum(counts.values()), 'state_counts': counts,
            'exact_live_bindings': live, 'session_read_errors': errors,
            'reused_pid_matches_ignored': reused, 'minecraft_processes': processes,
            'actual_live_mc_count': sum(bool(row['live_creation_identity']) for row in processes),
            'memory': commit_memory()}


LIVE_STATE = '''import json
import mod.client.extraClientApi as api
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
assert owner is not None and owner.session is not None, 'Ordinary Session is not initialized'
s=owner.session
b=owner.bridge
def fields(value):
 result={}
 for key,item in value.__dict__.items():
  if ('projection' in key or 'origin' in key) and not key.startswith('_'):
   if item is None or isinstance(item,(bool,int,long,float,str,unicode)):
    result[key]=item
   elif isinstance(item,(tuple,list)) and all(isinstance(v,(bool,int,long,float,str,unicode)) for v in item):
    result[key]=item
 return result
def document_summary(doc):
 if doc is None:return None
 from modern_projection.projection.cell import foreground,background,actor_data
 return {'id':id(doc),'size':doc.size,'name':doc.name,'blocks':len(doc.blocks),
  'cells':[{'position':pos,'foreground':foreground(cell),'background':background(cell),
            'has_actor':actor_data(cell) is not None} for pos,cell in sorted(doc.blocks.items())]
          if len(doc.blocks)<=256 else None}
work=getattr(b,'projection_work',None)
occupancy=getattr(b,'projection_occupancy',None)
target=getattr(b,'projection_target',None)
_result=json.dumps({'session':fields(s),'bridge':fields(b),'busy':s.busy,
 'preview_pending':s.preview_pending,'preview_error':s.preview_error,
 'source_document':document_summary(s.editor.document),
 'work_document':document_summary(getattr(work,'document',None)),
 'occupancy_document':document_summary(getattr(occupancy,'document',None)),
 'committed_target':None if target is None else {
  'id':id(target),'operations':target.operations,'origin':target.origin,
  'size':target.size,'source_key':target.source_key,
  'hidden':sorted(target.hidden),'layer':target.layer,
  'document':document_summary(target.document)},
 'source_editor_id':id(s.editor),'work_origin':getattr(work,'origin',None),
 'water_profile':type(s.liquid_profile).__name__ if s.liquid_profile else None,
 'book_profile':type(s.book_profile).__name__ if s.book_profile else None,
 'portal_profile':type(s.portal_profile).__name__ if s.portal_profile else None})
'''


def live_state(project, session_file, owner):
    from _session import load_session
    session = load_session(session_file, owner, live=True)
    if Path(session['project']).resolve() != project:
        raise ValueError('Assigned session project does not match --project')
    if '.runtime' not in project.parts:
        raise ValueError('Use an independent .runtime test project for this probe')
    os.environ.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=owner,
                      MCDEV_MCP_URL=session['mcp_url'])
    from mcdk import Client, return_value
    response = Client(timeout=25).call('execute_code',
        {'code': LIVE_STATE, 'is_client': True, 'direct_return': True})
    if response.get('isError'):
        raise RuntimeError(response)
    value = return_value(response)
    return json.loads(value) if isinstance(value, str) else value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('census', 'source-audit', 'live-state'))
    parser.add_argument('--project', type=Path, default=ROOT)
    parser.add_argument('--helper', action='append', default=[], help='New true dependency module basename')
    parser.add_argument('--session')
    parser.add_argument('--owner')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    project = args.project.resolve(strict=True)
    if args.output and args.output.exists():
        parser.error('Choose a fresh report; previous evidence is never overwritten')
    if args.mode == 'census':
        report = census()
    elif args.mode == 'source-audit':
        report = source_audit(project, [MODULE + name + '.py' for name in args.helper])
    else:
        if not args.session or not args.owner:
            parser.error('live-state requires --session and --owner')
        report = live_state(project, args.session, args.owner)
    report.update(mode=args.mode, recorded_at=datetime.now(timezone.utc).isoformat(),
                  diagnostic_only=True, runtime_qualification=False, world_write_performed=False)
    data = json.dumps(report, sort_keys=True, ensure_ascii=True, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data, encoding='ascii')
    print(data, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
