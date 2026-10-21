"""Small exact-PNG single-cell package; original raw files remain immutable."""
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

WORK=Path(__file__).resolve().parent
ROOT=WORK.parents[2]
CELL=WORK.with_name('water-merged-fullA-v1')
ANALYSIS=WORK.with_name('water-merged-fullA-camera-failure-analysis-v1')
OUT=WORK.with_name('water-merged-fullA-camera-failure-package-v1')
LIMIT=240000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    assert not OUT.exists(),'Use a new package version; never overwrite evidence'
    redactor_path=WORK.with_name('water-evidence-redaction-v4')/'package_v4_optimized.py'
    scanner_path=WORK.parent/'root_review_wire_bundle_v3.py'
    scanner=load('reviewed_original_scanner',scanner_path)
    assert sha(scanner_path.read_bytes())=='6c5bbd86dcf5fdcbf36ab709806beff4cb0230cbc0dad1d505b8fc172f95429e'
    redactor=load('reviewed_v4_recursive_redactor',redactor_path)
    index_v4=ROOT/'docs/evidence/water-size720-r27-v4/index.json'
    assert sha(index_v4.read_bytes())=='1cb4a95ef9a57ed659471ec243d34e0dc848ba40ad4f1700d146ef8a3c458deb'
    names=('product-v2-camera-native-v1.json', 'product-v2-camera-native-v1-host.json', 'product-v2-camera-native-v1-handles.json', 'group-execution-v1.json', 'final-source-binding-v1.json', 'prelaunch-host-binding-v1.json', 'plan-v1.json', 'root-grant-v1.json', 'cold-default-observation-v1.json', 'resize-background-v1.json', 'world-baseline-v1.json', 'independent-restore-v1.json', 'continuous-handle-guard-v1.json', 'helper-retirement-v1.json', 'launch/launch.json', 'launch/exact-exit.json', 'camera.stdout.txt', 'camera.stderr.txt', 'run_flow.py', 'run_group.py', 'run_camera.py', 'world_readback.py', 'observe_cold_default.py', 'flow_restore.py', 'scene_game.py', 'scene_restore.py', 'scene_policy.py', 'launch_r25.py', 'resize_adapter.py', 'resize_background.py', 'verify_prelaunch.py', 'host-changes-v1.patch', 'product-v2-camera-native-v1_front_shown.png', 'product-v2-camera-native-v1_front_hidden.png', 'product-v2-camera-native-v1_front_signal.png', 'product-v2-camera-native-v1_front_signal_outline_comparison.png', 'product-v2-camera-native-v1_right_shown.png', 'product-v2-camera-native-v1_right_hidden.png', 'product-v2-camera-native-v1_right_signal.png', 'product-v2-camera-native-v1_right_signal_outline_comparison.png', 'product-v2-camera-native-v1_tilted_shown.png', 'product-v2-camera-native-v1_tilted_hidden.png', 'product-v2-camera-native-v1_tilted_signal.png', 'product-v2-camera-native-v1_tilted_signal_outline_comparison.png')
    inputs={'failed-camera/'+name:CELL/name for name in names}
    for path in ANALYSIS.iterdir():
        if path.is_file():inputs['failure-analysis/'+path.name]=path
    candidate=WORK.with_name('water-camera-extractor-seam-candidate-v1')
    for name in ('candidate_extractor.py','run_controls.py','replay_controls.py','extractor-changes-v1.patch','controls-v1/report.json'):
        inputs['candidate/'+name]=candidate/name
    startup=ROOT/'.runtime/round-20261021/water-startup-protocol-v2/host-contract-v1.json'
    inputs['sampling/startup-host-contract-v1.json']=startup
    inputs['packaging/package.py']=Path(__file__)
    inputs['packaging/reviewed_recursive_redactor.py']=redactor_path
    inputs['packaging/original_independent_scanner.py']=scanner_path
    original={label:path.read_bytes() for label,path in inputs.items()}
    for label,raw in original.items():
        if inputs[label].suffix=='.json':
            redactor.discover(json.loads(raw))
    # Discover exact current local credentials without exporting their values.
    for path in (Path.home()/'.pyreact-debug/instances').glob('*/session.json'):
        redactor.discover(json.loads(path.read_bytes()))
    redactor.SECRET_PATTERN=redactor.compile_secret_pattern(redactor.secrets)
    # Reuse independently reviewed recursive JSON/base64/unescape checks.
    fixtures=[
        json.dumps({'stdout':json.dumps({'token':'synthetic-singlecell-token'})}).encode(),
        json.dumps({'payload':base64.b64encode(json.dumps({'mcp_url':'http://localhost/private'}).encode()).decode()}).encode(),
        ('"'+''.join('\\u%04x'%ord(c) for c in 'sk-'+'X'*32)+'"').encode()]
    for raw in fixtures:
        assert scanner.credentials(raw)
        clean,unused=redactor.sanitize_raw(raw)
        assert not redactor.combined_credentials(scanner,clean)
    negative=b'{"sha256":"'+b'a'*64+b'","record_count":44}'
    assert redactor.sanitize_raw(negative)[0]==negative
    prepared={}
    for label,raw in original.items():
        if inputs[label].suffix=='.png':
            prepared[label]=(raw,[])
        else:
            clean,locations=redactor.sanitize_raw(raw)
            assert not redactor.combined_credentials(scanner,clean),label
            prepared[label]=(clean,locations)
    OUT.mkdir()
    entries=[]
    for label,path in sorted(inputs.items()):
        raw=original[label]
        clean,locations=prepared[label]
        encoding='png' if path.suffix=='.png' else ('gzip' if len(clean)>100000 else 'utf8')
        encoded=gzip.compress(clean,mtime=0) if encoding=='gzip' else clean
        entry={'logical_name':label,'original_raw_path':str(path.resolve()),
            'original_raw_sha256':sha(raw),'original_raw_bytes':len(raw),
            'decoded_sanitized_sha256':sha(clean),'decoded_sanitized_bytes':len(clean),
            'original_bytes_reconstructable':clean==raw,'encoding':encoding,
            'redacted_fields':locations,'redaction_occurrences':len(locations),'derived_parts':[]}
        stem=label+('.gz' if encoding=='gzip' else '')
        pieces=[encoded[offset:offset+LIMIT] for offset in range(0,len(encoded),LIMIT)] or [b'']
        for index,piece in enumerate(pieces,1):
            name=stem+('.%03d'%index if len(pieces)>1 else '')
            target=OUT/name
            target.parent.mkdir(exist_ok=True,parents=True)
            with target.open('xb') as stream:stream.write(piece)
            entry['derived_parts'].append({'path':name,'bytes':len(piece),'sha256':sha(piece)})
        entries.append(entry)
    index={'schema':3,'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Current shared source, same-session camera failed before A cell 1; read-only one-pixel seam explanation and separate candidate controls',
        'supplement_to':{'path':str(index_v4),'sha256':sha(index_v4.read_bytes())},
        'entry_count':len(entries),'entries':entries,'single_file_limit_bytes':LIMIT,
        'source_contract_sha256':'027f11186bb5e50b4d9a0dc80a5ba4d06342104e1be4c2cc6de51a9f206bcf1a',
        'selected_original_PNGs':12,'full_burst_PNGs_included':False,'source_archive_included':False,
        'lossy_visual_references':0,'original_raws_modified':False,
        'redaction_policy':'Reviewed v4 recursive JSON/base64/unescape and exact credential removal; standard [REDACTED]; original/new SHA separate',
        'redactor_sha256':sha(redactor_path.read_bytes()),'independent_scanner_sha256':sha(scanner_path.read_bytes()),
        'credential_findings':0,'redaction_control_count':4,
        'formal_A_accepted':False,'world_A_accepted':False,'production_admission_performed':False,
        'default_path_evidence':False,'source_release_qualification_granted':False,'A_cells_attempted':0,'manual_closures_added':0}
    raw=(json.dumps(index,indent=2)+'\n').encode('ascii')
    assert len(raw)<LIMIT
    with (OUT/'index.json').open('xb') as stream:stream.write(raw)
    expected={'index.json'}
    exact=redactions=0
    for entry in entries:
        encoded=b''
        for part in entry['derived_parts']:
            raw=(OUT/part['path']).read_bytes()
            assert len(raw)==part['bytes']<300000 and sha(raw)==part['sha256']
            expected.add(part['path']);encoded+=raw
        clean=gzip.decompress(encoded) if entry['encoding']=='gzip' else encoded
        assert sha(clean)==entry['decoded_sanitized_sha256'] and len(clean)==entry['decoded_sanitized_bytes']
        if entry['encoding']!='png':assert not redactor.combined_credentials(scanner,clean),entry['logical_name']
        if entry['original_bytes_reconstructable']:
            assert clean==original[entry['logical_name']]
            exact+=1
        redactions+=entry['redaction_occurrences']
    assert all(path.read_bytes()==original[label] for label,path in inputs.items())
    assert sha(index_v4.read_bytes())=='1cb4a95ef9a57ed659471ec243d34e0dc848ba40ad4f1700d146ef8a3c458deb'
    actual={path.relative_to(OUT).as_posix() for path in OUT.rglob('*') if path.is_file()}
    assert actual==expected
    assert not redactor.combined_credentials(scanner,(OUT/'index.json').read_bytes())
    report={'schema':1,'passed':True,'package_path':str(OUT),'index_sha256':sha((OUT/'index.json').read_bytes()),
        'entries':len(entries),'stored_files':len(actual),'stored_bytes':sum((OUT/name).stat().st_size for name in actual),
        'maximum_file_bytes':max((OUT/name).stat().st_size for name in actual),
        'originals_reconstructed':exact,'selected_original_PNGs':12,'redaction_occurrences':redactions,
        'credential_findings':0,'original_inputs_unchanged':True,'prior_v4_index_unchanged':True,
        'formal_A_accepted':False,'manual_closures_added':0}
    with (WORK/'package-review-v1.json').open('x',encoding='ascii') as stream:json.dump(report,stream,indent=2)
    print(json.dumps(report))


if __name__=='__main__':
    main()
