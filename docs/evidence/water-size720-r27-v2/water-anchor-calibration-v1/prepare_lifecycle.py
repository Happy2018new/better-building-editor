"""Freeze independent diagnostic source/host bindings without starting a process."""
import ast
from datetime import datetime,timezone
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[3]
WORK=Path(__file__).resolve().parent
OLD=ROOT/'.runtime/round-20261022/water-size720-v3'
OWNER='water-r27-anchor-calibration-v1'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name,value):
    with (WORK/name).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2)
        stream.write('\n')


def main():
    diagnostic=json.loads((WORK/'diagnostic-source-v1.json').read_bytes())
    project=Path(diagnostic['private_project'])
    assert not (WORK/'launch').exists()
    binding=json.loads((OLD/'final-source-binding-v1.json').read_bytes())
    changes=[]
    names=('candidate_bootstrap.py','bootstrap_payload.py','guard_policy.py','modal_guard.py',
           'launch_r25.py','start_assert_watch.py','watch_handles.py','run_candidate_bootstrap.py',
           'retire_bootstrap_marker.py','retire_helpers.py')
    for name in names:
        before=(OLD/name).read_text('utf-8')
        after=before
        if name!='candidate_bootstrap.py':
            after=after.replace('water-r27-final41-size720-v3',OWNER)
            after=after.replace('prelaunch-host-binding-r27-direct.json','prelaunch-host-binding-v1.json')
        if name=='launch_r25.py':
            previous="PROJECT = Path('D:\\\\Happy2018newの个人文件\\\\GitHub\\\\better-building-editor\\\\.runtime\\\\projects\\\\water-r25-final41-v2')"
            assert previous in after
            after=after.replace(previous,'PROJECT = Path('+repr(str(project))+')')
            old_archive="Path('D:\\\\Happy2018newの个人文件\\\\GitHub\\\\better-building-editor\\\\.runtime\\\\round-20261021\\\\water-final41-r25-v2\\\\final-launch-source.zip')"
            assert old_archive in after
            after=after.replace(old_archive,"Path(binding['archive']['path'])")
        with (WORK/name).open('x',encoding='utf-8',newline='\n') as stream:stream.write(after)
        changes.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
                                           fromfile='size720-v3/'+name,tofile='anchor-v1/'+name))
    archive=WORK/'diagnostic-launch-source-v1.zip'
    assert not archive.exists()
    files=dict(diagnostic['source_sha256'],**diagnostic['auxiliary_sha256'])
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as stream:
        for name,expected in sorted(files.items()):
            assert sha(project/name)==expected,name
            stream.write(project/name,name)
    with zipfile.ZipFile(archive,'r') as stream:
        assert sorted(stream.namelist())==sorted(files)
        for name,expected in files.items():assert hashlib.sha256(stream.read(name)).hexdigest()==expected,name
    binding.update(owner=OWNER,project=str(project),guard_deadline_utc='2026-10-21T23:45:00+00:00',
                   bootstrap_receipt_marker='_water_r27_anchor_bootstrap_v1',
                   source_sha256=diagnostic['source_sha256'],auxiliary_sha256=diagnostic['auxiliary_sha256'],
                   source_contract_sha256=diagnostic['source_contract_sha256'],
                   archive={'path':str(archive),'sha256':sha(archive),'size_bytes':archive.stat().st_size,
                            'scope':'Independent diagnostic source and enumerated auxiliary files, not complete transitive closure'},
                   diagnostic_additions_only=True,new_source_bytes_created=True,
                   base_source_contract_sha256=diagnostic['base_source_contract_sha256'],
                   diagnostic_manifest_sha256=sha(WORK/'diagnostic-source-v1.json'),
                   previous_host_binding_sha256=sha(OLD/'prelaunch-host-binding-r27-direct.json'))
    assert sha(WORK/'candidate_bootstrap.py')==binding['bootstrap_sha256']
    write('final-source-binding-v1.json',binding)
    inputs=json.loads((OLD/'product-v2-launch-inputs.json').read_bytes())
    inputs.update(owner=OWNER,project=str(project),source_sha256=diagnostic['source_sha256'],
                  source_contract_sha256=diagnostic['source_contract_sha256'],archive=binding['archive'],
                  diagnostic_only=True,production_admission_performed=False)
    write('product-v2-launch-inputs.json',inputs)
    write('stage-r25.json',dict(schema=1,owner=OWNER,label='neutral-cube-anchor-matrix-only',
          plan_sha256=sha(WORK/'plan-v1.json'),formal_A_accepted=False,manual_closures_added=0,
          source_scope_is_not_transitive_closure=True,new_diagnostic_source_manifest_sha256=sha(WORK/'diagnostic-source-v1.json')))
    oldhosts=json.loads((OLD/'prelaunch-host-binding-r27-direct.json').read_bytes())
    external={name:sha(ROOT/name) for name in oldhosts['external_host_sha256']}
    for name in ('.runtime/round-20261022/water-size720-v3/resize_adapter.py',
                 '.runtime/round-20261022/water-size720-v3/run_size_group.py',
                 'tools/diagnose_window_dpi.py'):
        external[name]=sha(ROOT/name)
    for path in WORK.glob('*.py'):ast.parse(path.read_bytes(),filename=str(path))
    import sys
    sys.path.insert(0,str(WORK))
    from bootstrap_payload import dispatch_code
    payload=dispatch_code((WORK/'candidate_bootstrap.py').read_text('utf-8'),binding)
    with (WORK/'dispatched-bootstrap-payload.py').open('x',encoding='utf-8',newline='\n') as stream:stream.write(payload)
    result=subprocess.run(['D:/Program/Python27/python.exe','-B','-c',
        'import sys;compile(open(sys.argv[1],"rb").read(),sys.argv[1],"exec")',
        str(WORK/'dispatched-bootstrap-payload.py')],capture_output=True,text=True)
    result.check_returncode()
    write('prelaunch-host-binding-v1.json',dict(schema=1,source_binding_sha256=sha(WORK/'final-source-binding-v1.json'),
          host_sha256={path.name:sha(path) for path in WORK.glob('*.py')}|
              {name:sha(WORK/name) for name in ('product-v2-launch-inputs.json','stage-r25.json','plan-v1.json')},
          external_host_sha256=external,MC_started=False,frozen_at_utc=datetime.now(timezone.utc).isoformat()))
    with (WORK/'size720-v3-to-anchor-v1-host.patch').open('x',encoding='utf-8',newline='\n') as stream:stream.write(''.join(changes))
    write('lifecycle-preparation-review-v1.json',dict(schema=1,MC_started=False,source_files=len(diagnostic['source_sha256']),
          auxiliary_files=len(diagnostic['auxiliary_sha256']),archive=binding['archive'],
          archive_entries_verified=len(files),bootstrap_core_unchanged=True,python2_bootstrap_compile_exit=result.returncode,
          host_binding_sha256=sha(WORK/'prelaunch-host-binding-v1.json'),plan_sha256=sha(WORK/'plan-v1.json'),
          production_admission_performed=False))
    print(json.dumps({'prepared':True,'MC_started':False,'archive_size_bytes':archive.stat().st_size,
                      'archive_sha256':sha(archive),'host_binding_sha256':sha(WORK/'prelaunch-host-binding-v1.json')}))


if __name__=='__main__':main()
