"""Generate isolated, opt-in centered crosses from pinned native plant textures."""
import argparse
import hashlib
import json
from pathlib import Path

from generate_static_plant_proxies import (ROOT, SOURCE, TEMPLATE, behavior,
                                           centered_cross_model, validate)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def candidate(spec, name):
    validate(spec)
    plant = spec['plants'][name]
    identifier = 'modern_projection:diagnostic_centered_' + name
    key = 'modern_projection_diagnostic_centered_' + name
    definition = behavior(identifier, 'alpha')
    definition['minecraft:block']['components'].update({
        'netease:water_source': {'value': True},
        'netease:water_flow_source': {'value': True}})
    model = centered_cross_model(spec, identifier, key)
    return {
        'behavior.json': definition,
        'model.json': model,
        'registration.json': {
            'identifier': identifier,
            'appearance': {'netease_model': identifier,
                           'sound': plant['definition'].get('sound', 'grass')},
            'texture_key': key,
            'texture_entry': {'textures': plant['texture_path'].rsplit('.', 1)[0]},
            'native_material': ['minecraft:' + name, 0],
            'alpha_top_height': 1. - plant['alpha_bounds'][1] / float(plant['texture_size'][1]),
            'production_default_enabled': False,
            'opt_in_required': True,
            'position_contract': {
                'xz_translation': [0., 0.], 'unit_cross_height': 1.,
                'native_random_offset_applied': False,
                'native_mesh_authority': False,
                'position_fidelity_accepted': False,
                'geometry_fit_allowed': False,
                'hypothesis': 'Existing centered cross template, unit height; native texture alpha unchanged'},
            'source': {'manifest': SOURCE.relative_to(ROOT).as_posix(), 'manifest_sha256': sha(SOURCE),
                       'template': TEMPLATE.relative_to(ROOT).as_posix(), 'template_sha256': sha(TEMPLATE),
                       'native_texture_path': plant['texture_path'],
                       'native_texture_sha256': spec['sha256']['texture_' + name]},
        },
    }


def generate(name, output, native=None):
    spec = json.loads(SOURCE.read_bytes())
    validate(spec, native)
    files = candidate(spec, name)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Candidate output must be fresh')
    output.mkdir(parents=True)
    for filename, value in files.items():
        (output / filename).write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    manifest = {'schema': 1, 'plant': name, 'production_acceptance': False,
                'files': {filename: {'sha256': sha(output / filename),
                                     'bytes': (output / filename).stat().st_size}
                          for filename in files}}
    (output / 'index.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='ascii')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plant', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-resource-root', type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.plant, args.output, args.native_resource_root)))


if __name__ == '__main__':
    main()
