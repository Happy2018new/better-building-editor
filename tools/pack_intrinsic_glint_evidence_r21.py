"""Archive the completed native UI census and its exact replay inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ('tools/audit_intrinsic_glint_r21.py', 'tools/probe_intrinsic_glint_r21.py',
           'tools/probe_intrinsic_glint_ui_r21.py', 'tools/analyze_intrinsic_glint_ui_r21.py',
           'tools/census_intrinsic_glint_ui_r21.py', 'tools/freeze_intrinsic_glint_project_r21.py',
           'tools/pack_intrinsic_glint_evidence_r21.py', 'tests/test_intrinsic_glint_r21.py',
           'tools/watch_intrinsic_glint_exit_r21.py',
           'tools/probe_intrinsic_glint_aux_r21.py',
           'behavior_pack/modern_projection/projection/intrinsic_item_glint.py',
           'behavior_pack/modern_projection/projection/item_sprite_plan.py')


def pack(census, project_manifest, output):
    summary = json.loads((census / 'census.json').read_text(encoding='ascii'))
    if (not summary['completed'] or not summary['project_source_unchanged'] or
            len(summary['pages']) != summary['requested_pages'] or
            any(not page['restored'] for page in summary['pages'])):
        raise ValueError('A complete, source-bound, restored census is required')
    frozen = json.loads(project_manifest.read_text(encoding='ascii'))
    if frozen['files_sha256'] != summary['binding']['project_files_sha256']:
        raise ValueError('The archived project manifest does not match the census')
    bindings = {'sampler_sha256': 'tools/probe_intrinsic_glint_ui_r21.py',
                'analyzer_sha256': 'tools/analyze_intrinsic_glint_ui_r21.py',
                'census_source_sha256': 'tools/census_intrinsic_glint_ui_r21.py',
                'basic_sha256': '.runtime/item-catalog-info-r16/catalog.json',
                'textures_sha256': '.runtime/item-catalog-r16/catalog.json'}
    for key, name in bindings.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != summary['binding'][key]:
            raise ValueError('A bound census source or input changed: ' + name)
    for page in summary['pages']:
        directory = census / page['path']
        for name in ('report', 'analysis'):
            if hashlib.sha256((directory / (name + '.json')).read_bytes()).hexdigest() != page[name + '_sha256']:
                raise ValueError('A completed page report changed')
    extra_path = census / 'supplemental-aux/summary.json'
    extra = json.loads(extra_path.read_text(encoding='ascii')) if extra_path.exists() else None
    if extra is not None:
        if (not extra['completed'] or not extra['project_source_unchanged'] or
                extra['full_census_sha256'] != hashlib.sha256((census / 'census.json').read_bytes()).hexdigest() or
                extra['source_sha256'] != hashlib.sha256(
                    (ROOT / 'tools/probe_intrinsic_glint_aux_r21.py').read_bytes()).hexdigest()):
            raise ValueError('The auxiliary supplement must remain complete and source-bound')
        for page in extra['pages']:
            if not page['restored']:
                raise ValueError('A supplemental page was not restored')
            for name in ('report', 'analysis'):
                payload = (extra_path.parent / page['path'] / (name + '.json')).read_bytes()
                if hashlib.sha256(payload).hexdigest() != page[name + '_sha256']:
                    raise ValueError('A supplemental native report changed')
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(census, output / 'census')
    shutil.copyfile(project_manifest, output / 'project-source-manifest.json')
    for name in SOURCES:
        target = output / 'sources' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    for key in ('basic_sha256', 'textures_sha256'):
        shutil.copyfile(ROOT / bindings[key], output / (key.replace('_sha256', '') + '-catalog.json'))
    for name in ('intrinsic-glint-r21-ui-v1', 'intrinsic-glint-r21-ui-layer-v3'):
        source = ROOT / '.runtime' / name
        if source.is_dir():
            shutil.copytree(source, output / 'exploratory' / name)
    semantics = ROOT / '.runtime/intrinsic-glint-r21-semantics-v1.json'
    if semantics.is_file():
        shutil.copyfile(semantics, output / 'exploratory' / semantics.name)
    public = ROOT / 'tools/data/intrinsic_glint_census_nemc_3.10.0.420447.json'
    shutil.copyfile(public, output / public.name)
    files = [{'path': path.relative_to(output).as_posix(),
              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
             for path in sorted(output.rglob('*')) if path.is_file()]
    index = {'schema': 1, 'engine_version': summary['engine_version'],
             'native_sampling_complete': True, 'all_nbt_states_qualified': False,
             'production_qualified': False, 'coverage': summary['coverage'],
             'auxiliary_supplement': extra['coverage'] if extra is not None else None,
             'limitations': summary['limitations'], 'files': files,
             'exploratory_note': 'Historical reports preserve exact submitted game code and capture receipts; '
                                 'their original external wrapper bytes were not retained. '
                                 'The final census binds the archived current sampler bytes.'}
    (output / 'index.json').write_text(json.dumps(index, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    return index


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--census', required=True, type=Path)
    parser.add_argument('--project-manifest', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = pack(args.census, args.project_manifest, args.output)
    print(json.dumps({'files': len(result['files']), 'coverage': result['coverage'],
                      'production_qualified': result['production_qualified']}))
