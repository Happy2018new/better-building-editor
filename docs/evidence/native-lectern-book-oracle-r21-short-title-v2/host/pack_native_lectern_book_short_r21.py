"""Seal the actual short-title native data pass and absent-book pixel result."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from PIL import Image, ImageChops

from pack_native_lectern_book_failed_r21 import credential_keys, load, save, sha

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / '.runtime/lectern-body-candidate-r21'
PROJECT = ROOT / '.runtime/projects/book-r20-native-oracle-short-v2'
RUNTIME = HERE / 'runtime-native-oracle-short-v2'
LIFECYCLE = HERE / 'native-oracle-short-v2-launch'
HOST_SHA256 = 'd701942a46dbb18dcc0438e985e5aeb152605f83716bd3b80300f37151851a72'
BASE_HOST_SHA256 = '7fdcb301e1f90e4b0e0b84e35e3521e61b7ba3b953a9a31e6a0cb150df7c5c6c'
MANIFEST_SHA256 = '4cf802c70f38ec55a67a5ccb5a5de928432de0cb436f9b50d49ace2c4cefd691'
LOOT = 'behavior_pack/loot_tables/modern_projection/r21_signed_book.json'
NBT = 'behavior_pack/modern_projection/projection/nbt_spatial.py'
FRAMES = ('native_empty_0','native_empty_1','native_authored_0','native_authored_1','native_authored_2')


def replay(package, output):
    report = load(package / 'raw/report.json')
    helpers = ast.parse((package / 'sources' / NBT).read_bytes())
    functions = [node for node in helpers.body if isinstance(node,ast.FunctionDef) and
                 node.name in ('field_key','scalar')]
    assert len(functions) == 2
    namespace = {}
    exec(compile(ast.Module(body=functions,type_ignores=[]),'<archived-nbt-helpers>','exec'),namespace)
    scalar = namespace['scalar']
    request = load(package / 'sources' / LOOT)['pools'][0]['entries'][0]['functions'][0]
    assert request == {'function':'set_book_contents','title':'R21 Book A','author':'R21 Native Loot',
                       'pages':['First authored control.','Second authored control.']}
    inserted = report['insert']
    expected = inserted['native_loot_items'][0]['userData']
    assert inserted['submitted_native_item']['userData'] == expected
    assert inserted['actual_inventory_item']['userData'] == expected
    assert scalar(expected,'title') == request['title']
    assert scalar(expected,'author') == request['author']
    assert [scalar(page,'text') for page in scalar(expected,'pages')] == request['pages']
    assert inserted['native_use_return'] is True and inserted['actual_enchantments'] == []
    assert inserted['item_data_manufactured'] is False and inserted['nbt_setter_used'] is False
    archived = ast.parse((package / 'host/probe_native_book_oracle.py').read_bytes())
    functions = [node for node in archived.body if isinstance(node,ast.FunctionDef) and
                 node.name in ('compound','value','book_signature','authored_data_preserved')]
    assert len(functions) == 4
    exec(compile(ast.Module(body=functions,type_ignores=[]),'<archived-data-gates>','exec'),namespace)
    replication = report['replication']
    assert len(replication) == 1 and replication[0]['book_signature_equal'] is True
    server,client = replication[0]['server'],replication[0]['client']
    assert namespace['book_signature'](server['nbt']) == namespace['book_signature'](client['nbt'])
    assert all(namespace['authored_data_preserved'](row['nbt'],inserted['actual_inventory_item'])
               for row in (server,client))
    assert server['states'] == report['empty_server']['states'] == {
        'powered_bit':False,'minecraft:cardinal_direction':'east'}
    assert client['raw_actor'] == report['empty_client']['raw_actor'] == "{'minecraft:lectern': {0: {}}}"
    calls = []
    for row in report['operations']:
        calls.extend(node.func.attr for node in ast.walk(ast.parse(row['code']))
                     if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute))
    assert 'SetBlockEntityData' not in calls and calls.count('PlayerUseItemToPos') == 1
    acquire = next(row['code'] for row in report['operations'] if row['label'] ==
                   'native authored A and real inventory insertion')
    acquire_ast = ast.parse(acquire)
    assert sum(isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and
               node.func.attr == 'SpawnItemToPlayerInv' for node in ast.walk(acquire_ast)) == 1
    output.mkdir(parents=True)
    crops,rows = [],[]
    first = None
    for name in FRAMES:
        path = package / 'raw' / (name+'.png')
        receipt = load(package / 'raw' / (name+'.capture.json'))
        with Image.open(path) as original:
            assert original.size == (receipt['width'],receipt['height']) == (1994,1105)
            rgb = original.convert('RGB')
            box = (rgb.width//2-240,rgb.height//2-180,rgb.width//2+240,rgb.height//2+280)
            crop = rgb.crop(box)
            crop.save(output / (name+'.crop.png'))
            crops.append(crop)
            if first is None:
                first = crop.copy()
            difference = ImageChops.difference(first,crop)
            maximum = ImageChops.lighter(ImageChops.lighter(*difference.split()[:2]),difference.split()[2])
            histogram = maximum.histogram()
            rows.append({'label':name,'raw_sha256':sha(path),'crop_box':list(box),
                         'raw_pixels_sha256':hashlib.sha256(rgb.tobytes()).hexdigest(),
                         'crop_pixels_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),
                         'pixels_different_from_empty_0':sum(histogram[1:]),
                         'pixels_different_by_more_than_12':sum(histogram[13:])})
    sheet = Image.new('RGB',(480*len(crops),460))
    for index,crop in enumerate(crops):
        sheet.paste(crop,(480*index,0))
    sheet.save(output / 'native-empty-and-authored.png')
    result = {'schema':1,'request':request,'native_title_author_and_two_pages_exact':True,
        'inventory_userdata_equals_native_loot':True,'complete_client_server_authored_book_equal':True,
        'nbt_setter_in_recorded_operations':False,'acquisition_completed':True,
        'native_book_pixel_oracle_qualified':False,'production_qualified':False,
        'visual_observation':'All five originals opened: complete lectern and cyan support; authored frames show no visible book.',
        'independent_root_visual_review':'Root independently opened native_empty_0 and native_authored_2 and confirmed the empty top.',
        'no_visual_cause_identified':True,'causal_isolation_claimed':False,
        'data_gate_readbacks_occur_before_authored_frames':True,
        'no_alignment_resize_recolor_mask_or_pixel_fitting':True,'captures':rows}
    save(output / 'analysis.json',result)
    return result


def verify(package):
    manifest = load(package / 'manifest.json')
    for name,row in manifest['files'].items():
        path = package / name
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'],name
    actual = {path.relative_to(package).as_posix() for path in package.rglob('*') if path.is_file()}
    assert actual == set(manifest['files']) | {'manifest.json'}
    assert all(credential_keys(load(path)) == 0 for path in package.rglob('*.json'))
    report = load(package / 'raw/report.json')
    assert all(report[key] is True for key in ('completed','restored','source_unchanged',
                'native_authored_data_and_client_replication_validated'))
    assert report['cleanup_errors'] == [] and 'error' not in report
    assert report['native_book_pixel_oracle_qualified'] is False and report['production_qualified'] is False
    assert [row['label'] for row in report['captures']] == list(FRAMES)
    assert report['inventory_restore']['restored'] is True
    assert report['inventory_restore']['before'] == report['inventory_restore']['after']
    assert len(report['inventory_restore']['before']) == 36
    assert report['world_restore']['restored'] is True
    assert report['camera_restore'] is True and report['environment_restore'] is True
    assert report['elapsed_seconds'] < 120.
    assert all(row['memory']['commit_available_bytes'] >= 6*1024**3 and
               row['handles']['status']=='live' and row['handles']['handle_count']<200000
               for row in report['resource_boundaries'])
    assert sha(package / 'host/probe_native_book_oracle_short_v2.py') == HOST_SHA256
    assert sha(package / 'host/probe_native_book_oracle.py') == BASE_HOST_SHA256
    assert report['binding']['host_sha256'] == HOST_SHA256
    frozen = load(package / 'frozen/source-manifest.json')
    assert sha(package / 'frozen/source-manifest.json') == MANIFEST_SHA256
    assert hashlib.sha256(json.dumps(frozen['files'],ensure_ascii=True).encode('ascii')).hexdigest() == frozen['files_sha256']
    assert report['binding']['source_digest'] == frozen['files_sha256']
    source_files = {row['path']:row for row in frozen['files']}
    for path in (package / 'sources').rglob('*'):
        if path.is_file():
            assert sha(path) == source_files[path.relative_to(package / 'sources').as_posix()]['sha256']
    for name,expected in report['binding']['dependencies'].items():
        assert sha(package / 'host/dependencies' / name) == expected
    for name in FRAMES:
        receipt = load(package / 'raw' / (name+'.capture.json'))
        assert receipt['reliable'] and receipt['native_resolution'] and not receipt['agent_activation_allowed']
        assert sha(package / 'raw' / (name+'.png')) == receipt['sha256']
        assert receipt['game_identity'] == report['session']['game_identity']
    exits = load(package / 'lifecycle/exact-exit.json')
    assert exits['completed'] is True
    assert exits['processes']['game']['exit_code_hex'] == '0xC0000409'
    assert exits['processes']['mcdk']['exit_code_hex'] == '0x00000000'
    lifecycle = load(package / 'lifecycle/summary.json')
    assert lifecycle['normal_stop_returncode'] == 1 and lifecycle['force_used'] is False
    assert lifecycle['finalize_returncode'] == 0 and lifecycle['finalize_state'] == 'stopped'
    with tempfile.TemporaryDirectory(prefix='native-book-short-replay-') as directory:
        replay(package,Path(directory)/'review')
        for path in (Path(directory)/'review').iterdir():
            assert sha(path) == sha(package / 'review' / path.name),path.name
    return {'files':len(manifest['files']),'captures':5,'authored_captures':3,
        'native_authored_data_gate_replayed':True,'credential_json_keys':0,
        'native_book_pixel_oracle_qualified':False,'production_qualified':False,
        'manifest_sha256':sha(package / 'manifest.json'),'raw_report_sha256':sha(package / 'raw/report.json')}


def pack(output):
    assert not output.exists()
    source_manifest = HERE / 'native-oracle-short-v2/source-manifest.json'
    assert sha(source_manifest) == MANIFEST_SHA256
    frozen = load(source_manifest)
    for row in frozen['files']:
        assert sha(PROJECT / row['path']) == row['sha256'],row['path']
    report = load(RUNTIME / 'report.json')
    start = load(LIFECYCLE / 'start.stdout.json')
    finalize = load(LIFECYCLE / 'finalize.stdout.json')
    assert finalize['state'] == 'stopped' and finalize['ready'] is False
    assert all(start[key] == value for key,value in report['session'].items())
    paths = {'host/'+Path(__file__).name:Path(__file__),
        'host/pack_native_lectern_book_failed_r21.py':ROOT/'tools/pack_native_lectern_book_failed_r21.py',
        'host/probe_native_book_oracle.py':HERE/'probe_native_book_oracle.py',
        'host/probe_native_book_oracle_short_v2.py':HERE/'probe_native_book_oracle_short_v2.py',
        'host/prepare_native_book_short_v2.py':HERE/'prepare_native_book_short_v2.py',
        'host/launch_native_book_short_v2.py':HERE/'launch_native_book_short_v2.py',
        'frozen/source-manifest.json':source_manifest,
        'frozen/prepare.json':HERE/'native-oracle-short-v2/prepare.json',
        'frozen/verify.json':HERE/'native-oracle-short-v2/verify.json',
        'frozen/prelaunch.json':LIFECYCLE/'prelaunch.json',
        'lifecycle/exact-exit.json':LIFECYCLE/'exact-exit.json',
        'lifecycle/normal-stop.stderr.txt':LIFECYCLE/'stop.stderr.txt'}
    for name in ('.mcdev.json',LOOT,NBT):
        paths['sources/'+name] = PROJECT/name
    for name in report['binding']['dependencies']:
        paths['host/dependencies/'+name] = ROOT/'tools'/name
    for source in RUNTIME.iterdir():
        if source.is_file():
            paths['raw/'+source.name] = source
    for relative,source in paths.items():
        target = output/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
    launch = {key:start[key] for key in ('id','owner','project','created_at','game_pid',
                                       'game_identity','mcdk_pid','mcdk_identity')}
    launch['noactivation'] = {key:start['noactivation'][key] for key in
        ('requested','dll','mcdk','user_foreground_allowed','agent_activation_allowed')}
    save(output/'lifecycle/launch.json',launch)
    save(output/'lifecycle/summary.json',{'normal_stop_returncode':1,'force_used':False,
        'finalize_returncode':0,'finalize_state':'stopped','exact_observer_completed':True,
        'original_game_identity_absent_at_finalize':True,'original_mcdk_identity_absent_at_finalize':True,
        'normal_game_shutdown_qualified':False,'exit_cause_classified':False})
    (output/'.gitattributes').write_text('* -text -diff whitespace=cr-at-eol\n',encoding='ascii')
    replay(output,output/'review')
    (output/'README.md').write_text('''# Short-Title Native Book: Data Pass, Pixels Unqualified

This preserves the actual five-image native attempt. Request title R21 Book A,
author R21 Native Loot and both original nonempty pages survive native loot,
actual inventory and complete server/client lectern book NBT unchanged. Native
PlayerUseItemToPos returned true, hasBook is 1 and totalPages is 2. Recorded
commands contain no NBT setter. Empty and authored states both have east and
powered_bit false; neither native state exposes a has_book property. Client
palette actor remains an empty object in both phases.

All five full-resolution images were actually opened. Both empty images and
all three authored images show a complete lectern and cyan support, with no
visible authored book. Root independently opened empty_0 and authored_2 and
confirmed the empty top. Acquisition completed; a native book pixel oracle
did not. This is not product projection parity, a production qualification or
a proven renderer-cache cause. Complete data readbacks occur before authored
frames; per-frame data readbacks are not claimed. Camera checks bracket each
image. Raw reports, PNGs, receipts, original frozen hosts and sources remain
unchanged. No missing book is fitted, drawn, aligned or manufactured.

The attempt plus finally took 25.438315 seconds. All 36 inventory slots match;
world air, camera and environment restoration passed without cleanup errors.
Every resource boundary passed canonical 6 GiB commit and 200000-handle gates.
All 3033 source files were verified unchanged when packing. The full source
manifest is included, with only config, request loot and exact NBT helpers
bundled. This is portable offline evidence, not a runnable game project.

Ordinary stop returned 1. Retained exact process handles then observed game
0xC0000409 and MCDK 0. Both original process identities were absent before
ordinary finalize returned 0/state stopped/ready false. No force was used;
ordinary game shutdown is unqualified and the exit cause is unclassified.
Only allowlisted launch/finalize metadata is included. Credential-bearing
session stdout is excluded and all packaged JSON credential keys are checked.

Replay with Python 3 and Pillow, without Windows APIs, original paths or game:

python -B -X utf8 host/pack_native_lectern_book_short_r21.py --verify PACKAGE

Replay verifies every payload hash, native request/item/NBT equality using
archived parser and data-gate functions, source and capture bindings, lifecycle
and resource/restoration checks. It recreates unscaled 480x460 crops and the
five-frame sheet. Analysis and PNG bytes must match. Difference counts are
descriptive and do not assert book visibility. Successful replay retains the
unqualified pixel result.
''',encoding='ascii')
    manifest = {'schema':1,'created_at':datetime.now(timezone.utc).isoformat(),
        'captures':5,'native_authored_data_gate_passed':True,
        'native_book_pixel_oracle_qualified':False,'production_qualified':False,
        'normal_game_shutdown_qualified':False,'full_game_project_bundled':False,
        'source_digest':frozen['files_sha256'],'files':{}}
    for path in sorted(output.rglob('*')):
        if path.is_file():
            manifest['files'][path.relative_to(output).as_posix()] = {'bytes':path.stat().st_size,'sha256':sha(path)}
    save(output/'manifest.json',manifest)
    return verify(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output',type=Path)
    group.add_argument('--verify',type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.verify.resolve()) if args.verify else pack(args.output.resolve())))
