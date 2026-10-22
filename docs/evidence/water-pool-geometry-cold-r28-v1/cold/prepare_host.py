"""Freeze a normal cold pool diagnostic, reusing the existing base ZIP."""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import zipfile

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
OLD = WORK.with_name('water-formal-f-editor-v2')
PROPOSAL = WORK.with_name('water-geometry-readiness-v1')
PROJECT = ROOT / '.runtime/projects/water-r28-pool-geometry-v1'
OWNER = 'water-r28-pool-geometry-v1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, value):
    with (WORK / name).open('x', encoding='ascii') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')


def once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def main():
    assert not PROJECT.exists() and not (WORK / 'final-source-binding-v1.json').exists()
    original = json.loads((OLD / 'final-source-binding-v1.json').read_bytes())
    before = dict(original['source_sha256'], **original['auxiliary_sha256'])
    changed = {}
    for name in ('liquid_product_deployment.py', 'scene.py'):
        relative = 'behavior_pack/modern_projection/projection/' + name
        raw = (PROPOSAL / ('proposed_' + name)).read_bytes()
        changed[relative] = {'before_sha256': before[relative], 'after_sha256': sha(raw)}
        assert changed[relative]['before_sha256'] != changed[relative]['after_sha256']
    overlay = WORK / 'source-overlay-v1.zip'
    with zipfile.ZipFile(overlay, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in sorted(changed):
            info = zipfile.ZipInfo(relative, date_time=(2026, 10, 23, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (PROPOSAL / ('proposed_' + Path(relative).name)).read_bytes(), compresslevel=9)
    base = original['archive']
    assert sha(Path(base['path']).read_bytes()) == base['sha256']
    PROJECT.mkdir()
    with zipfile.ZipFile(base['path']) as archive, zipfile.ZipFile(overlay) as delta:
        assert set(archive.namelist()) == set(before)
        for relative in sorted(before):
            raw = archive.read(relative)
            assert sha(raw) == before[relative], relative
            if relative in changed:
                raw = delta.read(relative)
            target = PROJECT / relative
            assert target.resolve().is_relative_to(PROJECT.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    source = dict(original['source_sha256'])
    source.update({name: values['after_sha256'] for name, values in changed.items()})
    provenance = {'kind': 'base_zip_plus_exact_overlay_v1', 'base': base,
                  'overlay': {'path': str(overlay), 'sha256': sha(overlay.read_bytes()), 'bytes': overlay.stat().st_size},
                  'changed_files': changed, 'base_source_sha256': original['source_sha256'],
                  'base_auxiliary_sha256': original['auxiliary_sha256']}
    binding = dict(original, owner=OWNER, project=str(PROJECT), base_project=original['project'],
                   prepared_at_utc=datetime.now(timezone.utc).isoformat(), source_sha256=source,
                   source_contract_sha256=sha(json.dumps(source, sort_keys=True, separators=(',', ':')).encode('ascii')),
                   source_provenance=provenance, current_shared_source_exactly_matches_frozen=False,
                   source_archive_reused_without_copy=True, new_source_bytes_created=True,
                   guard_deadline_utc='2026-10-22T23:40:00+00:00')
    binding['archive'] = dict(base, kind='base_only_requires_exact_overlay',
                             scope='Reused original base ZIP; exact overlay and full synthesis verified separately.')
    write('final-source-binding-v1.json', binding)
    write('product-v2-launch-inputs.json', {key: binding[key] for key in
          ('schema', 'project', 'owner', 'source_sha256', 'source_contract_sha256', 'archive', 'source_provenance')})
    from source_provenance import verify_source_provenance
    write('source-synthesis-v1.json', verify_source_provenance(binding))
    names = ('guard_policy.py', 'modal_guard.py', 'launch_r25.py', 'start_assert_watch.py',
             'watch_handles.py', 'retire_helpers.py', 'scene_game.py', 'scene_policy.py',
             'scene_restore.py', 'resize_adapter.py', 'resize_background.py',
             'observe_cold_default.py', 'flow_restore.py', 'run_group.py', 'world_readback.py',
             'run_frozen_editor.py')
    patch = []
    for name in names:
        original_text = (OLD / name).read_text(encoding='utf8')
        text = original_text.replace(original['owner'], OWNER).replace(Path(original['project']).name, PROJECT.name)
        if name == 'launch_r25.py':
            text = once(text, "    assert hashlib.sha256((Path(binding['archive']['path'])).read_bytes()).hexdigest()==launch_inputs['archive']['sha256']",
                        "    from source_provenance import verify_source_provenance\n    source_synthesis = verify_source_provenance(binding)\n    assert source_synthesis['passed']")
            text = once(text, "              'source_archive_sha256': launch_inputs['archive']['sha256'],",
                        "              'source_archive_sha256': launch_inputs['archive']['sha256'],\n              'source_synthesis': source_synthesis,")
        if name == 'run_frozen_editor.py':
            tree = ast.parse(text)
            cases = next(node for node in tree.body if isinstance(node, ast.Assign)
                         and any(isinstance(target, ast.Name) and target.id == 'CASES' for target in node.targets))
            text = once(text, ast.get_source_segment(text, cases), "CASES = ('pool',)")
            text = once(text, "                '--frozen', '--controls', 'all', '--visibility-controls',\n                '--opaque-side-controls', '--alpha-controls', '--measure-budgets',",
                        "                '--frozen', '--controls', 'all', '--measure-budgets',")
            text = once(text, "        geometry.append({'label': label, 'state': observed, 'verdict': verdict})",
                        "        native_layout = read_scene_controls(active_check[0], probe.blueprints.walk)\n"
                        "        geometry.append({'label': label, 'state': observed, 'verdict': verdict, 'actual_scene_controls': native_layout})")
            text = once(text, "    from scene_policy import describe_scene", "    from scene_native_layout import read_scene_controls\n    from scene_policy import describe_scene")
        with (WORK / name).open('x', encoding='utf8', newline='\n') as stream:
            stream.write(text)
        if text != original_text:
            patch.extend(difflib.unified_diff(original_text.splitlines(True), text.splitlines(True), fromfile='old/' + name, tofile='new/' + name))
    (WORK / 'host-changes-v1.patch').write_text(''.join(patch), encoding='utf8', newline='\n')
    plan = {'schema': 1, 'owner': OWNER, 'project': str(PROJECT), 'stage': 'cold_product_geometry_pool_only',
            'source_contract_sha256': binding['source_contract_sha256'], 'exact_source_changes': changed,
            'base_archive_reused': base, 'overlay_archive': provenance['overlay'],
            'source_files_compared': len(source), 'auxiliary_files_compared': len(original['auxiliary_sha256']),
            'route': 'editor', 'cases': ['pool'], 'controls': ['wet', 'dry'], 'expected_PNGs': 2,
            'actual_canvas_and_clip_readback': True, 'native_gui': 2, 'physical_client_size': [1280, 720],
            'no_unreviewed_expansion_to_F': True, 'ordinary_cold_init_required': True,
            'bootstrap_or_profile_qualification_write': False, 'explicit_candidate_profile_for_pixels': True,
            'minimum_available_commit_bytes': 6 * 1024 ** 3, 'maximum_handles': 250000, 'adjacent_growth_limit': 10000,
            'estimated_minutes': [4, 8], 'unchanged_retry_allowed': False,
            'restoration_deadline_utc': binding['guard_deadline_utc'], 'manual_closures_added': 0}
    write('plan-v1.json', plan)
    write('stage-r25.json', {'schema': 1, 'owner': OWNER, 'plan_sha256': sha((WORK / 'plan-v1.json').read_bytes()),
                           'formal_A_accepted': False, 'manual_closures_added': 0})
    for path in WORK.glob('*.py'):
        ast.parse(path.read_bytes(), filename=str(path))
    hosts = json.loads((OLD / 'prelaunch-host-binding-v1.json').read_bytes())
    write('prelaunch-host-binding-v1.json', {'schema': 1, 'source_binding_sha256': sha((WORK / 'final-source-binding-v1.json').read_bytes()),
         'host_sha256': {path.name: sha(path.read_bytes()) for path in WORK.iterdir() if path.is_file()
                        and path.suffix in ('.py', '.patch', '.json') and path.name != 'final-source-binding-v1.json'},
         'external_host_sha256': hosts['external_host_sha256'], 'startup_contract_sha256': hosts['startup_contract_sha256'],
         'MC_started': False, 'frozen_at_utc': datetime.now(timezone.utc).isoformat()})
    print(json.dumps({'prepared': True, 'MC_started': False, 'source_contract_sha256': binding['source_contract_sha256'],
                     'plan_sha256': sha((WORK / 'plan-v1.json').read_bytes()), 'overlay_bytes': overlay.stat().st_size,
                     'source_changes': len(changed)}))


if __name__ == '__main__':
    main()
