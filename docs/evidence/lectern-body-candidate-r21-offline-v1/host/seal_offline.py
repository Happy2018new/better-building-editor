"""Freeze explicit offline inputs and results without touching main business code."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CLONE = ROOT / '.runtime/projects/book-r20'
DESTINATION = HERE / 'offline-snapshot-v1'
BUSINESS = 'behavior_pack/modern_projection/projection/'
SHARED = ('resource_pack/shaders/glsl/modern_projection_biome_blocks.vertex',
          'resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment',
          'resource_pack/materials/terrain.material', BUSINESS+'occupancy_shader.py',
          BUSINESS+'book_render_plan.py', BUSINESS+'book_preview.py', BUSINESS+'book_projection.py',
          BUSINESS+'geometry_palette.py', BUSINESS+'entity_render.py', BUSINESS+'visible_actor.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if DESTINATION.exists():
        raise ValueError('The offline snapshot must be fresh')
    report = json.loads((HERE / 'offline-report.json').read_bytes())
    shader = json.loads((HERE / 'overlay-shader-report.json').read_bytes())
    if not report['successful'] or not shader['successful']:
        raise ValueError('Only complete offline controls can be sealed')
    for name, expected in report['candidate_sources'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('Offline-tested source changed: '+name)
    for name, expected in shader['sources'].items():
        if sha(Path(name)) != expected:
            raise ValueError('Raster-tested source changed: '+name)
    for name in SHARED:
        if sha(ROOT / name) != sha(CLONE / name):
            raise ValueError('The candidate modified a shared or book source: '+name)
    sources = {Path('baseline') / (BUSINESS+'render_context.py'):
               ROOT / BUSINESS / 'render_context.py'}
    sources.update({Path('candidate') / name: CLONE / name for name in (
        BUSINESS+'render_context.py', BUSINESS+'lectern_body.py', '.mcdev.json')})
    sources.update({Path('shared') / name: CLONE / name for name in SHARED})
    sources.update({Path('host') / name: HERE / name for name in (
        'README.md', 'run_offline.py', 'test_lectern_body_candidate.py',
        'test_lectern_world_candidate.py', 'prove_overlay_shader.py', 'probe_runtime.py',
        'offline-report.json', 'offline-tests.log', 'overlay-shader-report.json',
        'offline-first-harness-failure.json', 'offline-first-harness-failure.log',
        'seal_offline.py')})
    manifest = dict(schema=1, created_at=datetime.now(timezone.utc).isoformat(),
        stage='sealed_offline_candidate', product_qualified=False,
        native_runtime_experiment_executed=False,
        offline_tests=report['tests_run'], shader_programs=shader['programs'], shader_checks=shader['checks'],
        shared_and_book_sources_unchanged=True, files={})
    for relative, source in sorted(sources.items()):
        target = DESTINATION / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        manifest['files'][relative.as_posix()] = dict(sha256=sha(target), bytes=target.stat().st_size)
    (DESTINATION / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='ascii')
    print(json.dumps(dict(destination=str(DESTINATION), files=len(sources),
                         manifest_sha256=sha(DESTINATION / 'manifest.json'))))


if __name__ == '__main__':
    main()
