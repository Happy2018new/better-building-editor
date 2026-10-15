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
           'tools/reanalyze_intrinsic_glint_r21.py',
           'tools/verify_intrinsic_glint_evidence_r21.py',
           'behavior_pack/modern_projection/projection/intrinsic_item_glint.py',
           'behavior_pack/modern_projection/projection/item_sprite_plan.py')


def pack(census, project_manifest, strict_analysis, exit_observation, output):
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
    strict_path = strict_analysis / 'summary.json'
    strict = json.loads(strict_path.read_text(encoding='ascii'))
    if (not strict['completed'] or strict['production_qualified'] or
            strict['full_census_sha256'] != hashlib.sha256((census / 'census.json').read_bytes()).hexdigest() or
            strict['original_analyzer_sha256'] != summary['binding']['analyzer_sha256'] or
            strict['strict_analyzer_source_sha256'] != hashlib.sha256(
                (ROOT / 'tools/reanalyze_intrinsic_glint_r21.py').read_bytes()).hexdigest() or
            len(strict['pages']) != len(summary['pages']) or
            len(strict['supplemental_pages']) != (len(extra['pages']) if extra else 0)):
        raise ValueError('A complete distinct source-bound stricter analysis is required')
    if extra and strict.get('supplemental_summary_sha256') != hashlib.sha256(extra_path.read_bytes()).hexdigest():
        raise ValueError('The stricter analysis supplement changed')
    for pages, original in ((strict['pages'], summary['pages']),
                            (strict['supplemental_pages'], extra['pages'] if extra else [])):
        for page, acquired in zip(pages, original):
            if (page['report_sha256'] != acquired['report_sha256'] or
                    page['original_analysis_sha256'] != acquired['analysis_sha256'] or
                    not page['native_controls_passed']):
                raise ValueError('A stricter page does not bind its original acquisition')
            for name, filename in (('analysis', 'analysis.json'), ('review', 'paired-review.png')):
                if hashlib.sha256((strict_analysis / page['path'] / filename).read_bytes()).hexdigest() != page[name + '_sha256']:
                    raise ValueError('A derived native analysis changed')
    exited = json.loads(exit_observation.read_text(encoding='ascii'))
    identity = summary['pages'][-1]['handles_after']
    if (not exited['completed'] or
            any(row['state'] != 'exited' for row in exited['processes'].values()) or
            exited['processes']['game']['pid'] != identity['pid'] or
            exited['processes']['game']['identity'] != identity['identity']):
        raise ValueError('Exact held-handle exit observations for the acquired game are required')
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(census, output / 'census')
    shutil.copytree(strict_analysis, output / 'strict-analysis')
    shutil.copyfile(project_manifest, output / 'project-source-manifest.json')
    shutil.copyfile(exit_observation, output / 'exact-process-exit.json')
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
    shutil.copyfile(ROOT / 'tools/verify_intrinsic_glint_evidence_r21.py', output / 'verify_package.py')
    (output / 'README.md').write_text(
        '# Native Intrinsic Item Glint, R21\n\n'
        'Engine: NEMC 3.10.0.420447, Minecraft 1.21.130.0.\n\n'
        'The original 89-page census covers 1,907 loaded identifiers at auxiliary zero, '
        'representatives of each measured name/texture pair, and every measured auxiliary '
        'value 0 through 15 for the seven initial positive families and normal golden apple. '
        'The separate restored supplement adds debug_stick auxiliary values 1 through 15. '
        'Together these contain 2,835 false/true native UI pairs.\n\n'
        'The authoritative classification is strict-analysis/summary.json: 128 positive '
        'pairs, 1,605 negative-in-this-probe pairs and 1,102 unresolved pairs. Eight '
        'families are positive at every measured auxiliary value 0 through 15: '
        'debug_stick, enchanted_book, enchanted_golden_apple, end_crystal, experience_bottle, '
        'lodestone_compass, nether_star and written_book. Unknown auxiliary values remain '
        'unconfirmed.\n\n'
        'The original acquisition reports and bound sampler/analyzer source remain intact. '
        'The original residual-only classifier falsely accepted the weak blue animation '
        'of double_stone_block_slab2:2. The distinct stricter analyzer recomputes all '
        'screenshots, also requires both aggregate R/B and G/B ratios to be within 0.025 '
        'of the native glint control, and retains that prismarine alias as unresolved. '
        'This is the only changed classification.\n\n'
        'The tests use paired SetUiItem false/true controls at a low UI layer. Three '
        'same-phase screenshots, actual UI readbacks, exact submitted code, restoration '
        'records, capture hashes, catalog bytes and project source manifests are retained. '
        'High-layer exploratory captures cannot prove 3D-block negatives.\n\n'
        'Native UI behavior does not qualify editor or world rendering. Unresolved items, '
        'arbitrary NBT states and unmeasured auxiliary values have not been proven negative. '
        'Actual enchantment flags remain separate from intrinsic render glint. Indicator '
        'target, location and clock metadata are not read. Metadata-rich authored books '
        'still require separate support qualification.\n\n'
        'All owned controls were restored and all frozen project bytes remained unchanged. '
        'The exact held-process watcher records game exit 0xC0000409 and MCDK exit 0. '
        'The game exit was abnormal; this package does not claim a clean shutdown or '
        'establish its cause. See exact-process-exit.json.\n\n'
        'Verification: python -X utf8 verify_package.py\n', encoding='ascii')
    files = [{'path': path.relative_to(output).as_posix(),
              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
             for path in sorted(output.rglob('*')) if path.is_file()]
    index = {'schema': 2, 'engine_version': summary['engine_version'],
             'native_sampling_complete': True, 'all_nbt_states_qualified': False,
             'production_qualified': False, 'coverage': strict['coverage'],
             'original_acquisition_coverage': summary['coverage'],
             'classification_changes': strict['classification_changes'],
             'authoritative_classification': 'strict-analysis/summary.json',
             'exact_process_exit': exited['processes'],
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
    parser.add_argument('--strict-analysis', required=True, type=Path)
    parser.add_argument('--exit-observation', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = pack(args.census, args.project_manifest, args.strict_analysis, args.exit_observation, args.output)
    print(json.dumps({'files': len(result['files']), 'coverage': result['coverage'],
                      'production_qualified': result['production_qualified']}))
