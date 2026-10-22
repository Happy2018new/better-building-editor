"""Reconstruct the disposable D source and generate only its owner metadata."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zipfile

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
BRG = WORK.with_name('water-final-brg-v3')
FA = WORK.with_name('water-final-matrix-v1')
PROJECT = ROOT / '.runtime/projects/water-r28-default-v1'
OWNER = PROJECT.name
METADATA = ('tools/data/liquid_product_owner_contract_v1.json',
            'behavior_pack/modern_projection/projection/liquid_product_owner_data.py',
            'behavior_pack/modern_projection/projection/liquid_product_qualification_data.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    with (WORK/name).open('x',encoding='ascii') as stream:
        json.dump(value,stream,indent=2,sort_keys=True)
        stream.write('\n')


def main():
    assert not PROJECT.exists()
    baseline = json.loads((BRG/'final-source-binding-v1.json').read_bytes())
    release = json.loads((BRG/'precise-release-audit-v1.json').read_bytes())
    assert release['all_exact_identities_absent'] and release['independent_restored']
    expected = dict(baseline['source_sha256'],**baseline['auxiliary_sha256'])
    provenance = baseline['source_provenance']
    changes = set(provenance['added_files']) | set(provenance['changed_files'])
    base, overlay = (Path(provenance[key]['path']) for key in ('base','overlay'))
    assert sha(base)==provenance['base']['sha256']
    assert sha(overlay)==provenance['overlay']['sha256']
    shared_metadata_before={name:sha(ROOT/name) for name in METADATA}
    PROJECT.mkdir()
    with zipfile.ZipFile(base) as original,zipfile.ZipFile(overlay) as delta:
        for name,value in sorted(expected.items()):
            raw=delta.read(name) if name in changes else original.read(name)
            assert hashlib.sha256(raw).hexdigest()==value,name
            target=PROJECT/name
            assert target.resolve().is_relative_to(PROJECT.resolve())
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(raw)
    assert all(sha(PROJECT/name)==value for name,value in expected.items())
    generation=[]
    for tail in ([],['--check']):
        command=[sys.executable,'-B','-X','utf8',str(PROJECT/'tools/generate_liquid_product_owner_contract.py')]+tail
        result=subprocess.run(command,cwd=PROJECT,capture_output=True,text=True,encoding='utf8',timeout=60)
        generation.append({'argv':command,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
        assert result.returncode==0,generation[-1]
    actual={name:sha(PROJECT/name) for name in expected}
    differences={name:{'before':expected[name],'after':actual[name]} for name in expected if actual[name]!=expected[name]}
    assert set(differences)==set(METADATA[:2]),differences
    assert all(sha(ROOT/name)==value for name,value in shared_metadata_before.items())
    sys.path.insert(0,str(ROOT/'tools'))
    import generate_liquid_product_owner_contract as generator
    import qualify_water_product_r16 as qualifier
    assert generator.ROOT==qualifier.ROOT==ROOT
    assert Path(generator.__file__).resolve()==ROOT/'tools/generate_liquid_product_owner_contract.py'
    assert Path(qualifier.__file__).resolve()==ROOT/'tools/qualify_water_product_r16.py'
    owner,module=generator.generated()
    assert (PROJECT/METADATA[0]).read_bytes()==owner
    assert (PROJECT/METADATA[1]).read_bytes()==module
    contract=json.loads((PROJECT/qualifier.RESOURCE).read_bytes())
    reports={'F-editor':FA/'product-v2-f-editor-v1.json','F-full':FA/'product-v2-f-full-v2.json',
             'F-missing':FA/'product-v2-f-missing-v2.json','A':FA/'product-v2-a-v1.json',
             'B':BRG/'product-v2-b-v1.json','R':BRG/'product-v2-r-v1.json','G':BRG/'product-v2-g-v1.json'}
    for path in reports.values():
        qualifier.source_closure(PROJECT,json.loads(path.read_bytes()),contract)
    write('disposable-preparation-v1.json',{'schema':1,'prepared_at_utc':datetime.now(timezone.utc).isoformat(),
          'owner':OWNER,'project':str(PROJECT),'baseline_binding':str(BRG/'final-source-binding-v1.json'),
          'baseline_binding_sha256':sha(BRG/'final-source-binding-v1.json'),
          'baseline_source_contract_sha256':baseline['source_contract_sha256'],
          'source_files':len(baseline['source_sha256']),'auxiliary_files':len(baseline['auxiliary_sha256']),
          'all_reconstructed_files':len(expected),'base':provenance['base'],'overlay':provenance['overlay'],
          'hardlinks_used':False,'all_baseline_bytes_verified_before_generation':True,
          'owner_generation':generation,'actual_changes_before_provisional':differences,
          'only_additional_change_expected_during_provisional':METADATA[2],
          'all_39_shared_production_sources_match_disposable':all(
              (ROOT/name).read_bytes().replace(b'\r\n',b'\n')==(PROJECT/name).read_bytes().replace(b'\r\n',b'\n')
              for name in generator.SOURCES),
          'source_closure_passed_all_reports':{name:sha(path) for name,path in reports.items()},
          'shared_metadata_unchanged':shared_metadata_before,
          'shared_generator_path':str(Path(generator.__file__)),'shared_generator_sha256':sha(Path(generator.__file__)),
          'shared_qualifier_path':str(Path(qualifier.__file__)),'shared_qualifier_sha256':sha(Path(qualifier.__file__)),
          'qualified_or_default_gate_set':False,'provisional_executed':False,'MC_started':False,
          'host_sha256':sha(Path(__file__))})
    generic=json.loads((BRG/'analysis-BRG-v1/summary.json').read_bytes())
    write('root-scope-review-draft-v1.json',{'schema':1,'status':'draft_waiting_root_confirmation',
          'reviewer':'/root','root_confirmation_required':True,'provisional_execution_authorized':False,
          'root_decision_reference':'Root task: accepts original BRG scope; F exact geometry/alpha/transparency; R opposite-angle same cells/shapes and visibility; G complete public-gallery load and aggregate visibility.',
          'accepted_scope':{'F':'exact geometry, independent alpha and transparency under the existing frozen protocol',
                            'A':'visible animation and physical flow direction under the existing animated protocol',
                            'B':'biome controls and exact occupancy/remove-one/restore-four',
                            'R':'three routes and five opposite-angle cases, unchanged cells/shapes and independent visibility',
                            'G':'complete 81-cell public gallery loaded in editor and aggregate water visibility'},
          'preserved_generic_geometry_failures':{name:generic['reports'][name]['failed_geometry'] for name in ('R','G')},
          'R_or_G_exact_per_case_geometry_accepted':False,'old_failed_reports_regraded':False,
          'source_contract_sha256':baseline['source_contract_sha256'],
          'reports':{name:{'path':str(path),'sha256':sha(path)} for name,path in reports.items()},
          'required_shared_qualifier_sha256':sha(Path(qualifier.__file__)),
          'required_shared_generator_sha256':sha(Path(generator.__file__)),
          'original_brg_gates_sha256':sha(BRG/'original-brg-gates-v1.json'),
          'BRG_release_sha256':sha(BRG/'precise-release-audit-v1.json'),
          'manual_closures_added':0,'production_qualified':False,'MC_started':False})
    print(json.dumps({'prepared':True,'source_files':len(baseline['source_sha256']),
                      'auxiliary_files':len(baseline['auxiliary_sha256']),
                      'actual_changes_before_provisional':differences,
                      'preparation_sha256':sha(WORK/'disposable-preparation-v1.json'),
                      'root_scope_draft_sha256':sha(WORK/'root-scope-review-draft-v1.json'),
                      'MC_started':False,'provisional_executed':False},indent=2))


if __name__=='__main__':
    main()
