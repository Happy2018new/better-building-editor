"""Configure the local game target independently of the retained block registry."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path('tools/data/runtime_target_manifest.json')


def validate(data, registry):
    if type(data.get('schema_version')) is not int or data['schema_version'] != 1:
        raise ValueError('Unsupported development runtime manifest schema')
    for key in ('engine_version', 'minecraft_version'):
        if not isinstance(data.get(key), str) or re.fullmatch(r'[0-9]+(?:\.[0-9]+){3}', data[key]) is None:
            raise ValueError('Missing explicit four-component ' + key)
    if data.get('resource_version') != 'NEMC ' + data['engine_version']:
        raise ValueError('Resource source must match the development engine')
    if (data.get('registry_version') != registry.get('game_version') or
            data.get('registry_sha256') != registry.get('source_sha256', '').lower()):
        raise ValueError('Retained block registry differs from the development manifest')
    if (data.get('block_registry_update_deferred') is not True or
            data.get('transforms_update_deferred') is not True):
        raise ValueError('Registry and transform migration remain explicitly deferred')
    for key in ('game_executable_sha256', 'registry_sha256'):
        if not isinstance(data.get(key), str) or re.fullmatch(r'[0-9a-f]{64}', data[key]) is None:
            raise ValueError('Missing explicit SHA-256: ' + key)
    executable = data.get('game_executable_path')
    if not isinstance(executable, str) or not executable or Path(executable).name != 'Minecraft.Windows.exe':
        raise ValueError('Development target must name a Minecraft executable')
    rendering = data.get('rendering')
    if not isinstance(rendering, dict) or rendering != {
            'native_nbt': 'prefer_supported_appearance', 'native_fire': 'accepted',
            'world_water': 'custom', 'world_lava': 'native', 'cauldron_contents': 'custom'}:
        raise ValueError('Native water or cauldron cannot replace the custom fluid policy')
    return data


def load_target(root=ROOT):
    data = json.loads((root / MANIFEST).read_bytes())
    relative = data.get('block_registry_manifest')
    if not isinstance(relative, str) or relative != 'tools/data/block_registry_manifest.json':
        raise ValueError('Unexpected retained registry manifest path')
    registry = json.loads((root / relative).read_bytes())
    return validate(data, registry)


def configure(config, target, executable=None):
    if not isinstance(config, dict):
        raise ValueError('Local development config must be an object')
    result = dict(config)
    result['game_executable_path'] = str(executable or target['game_executable_path']).replace('\\', '/')
    result.setdefault('included_mod_dirs', ['./'])
    for key in ('mods', 'ui', 'materials', 'shaders'):
        result.setdefault('auto_hot_reload_' + key, False)
    return result


def verify_binary(path, target):
    path = Path(path)
    if not path.is_file():
        raise ValueError('Development game executable is missing: ' + str(path))
    with path.open('rb') as source:
        actual = hashlib.file_digest(source, 'sha256').hexdigest()
    if actual != target['game_executable_sha256']:
        raise ValueError('Development game bytes differ; record and review the new build before testing')
    return actual


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / '.mcdev.json')
    parser.add_argument('--game-exe', type=Path, help='Alternate installation of the same pinned binary')
    parser.add_argument('--apply', action='store_true', help='Update the local ignored MCDK config')
    parser.add_argument('--check-config', action='store_true', help='Require a configured local game target')
    parser.add_argument('--check-installed', action='store_true', help='Verify installed executable bytes')
    args = parser.parse_args(argv)
    target = load_target()
    config = json.loads(args.config.read_bytes()) if args.config.exists() else {}
    updated = configure(config, target, args.game_exe)
    if args.check_installed or args.apply:
        verify_binary(updated['game_executable_path'], target)
    if args.apply:
        args.config.parent.mkdir(parents=True, exist_ok=True)
        args.config.write_text(json.dumps(updated, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    elif args.check_config and config != updated:
        raise ValueError('Local runtime config is stale; run this command with --apply')
    print(json.dumps({'engine_version': target['engine_version'],
                      'resource_version': target['resource_version'],
                      'registry_version': target['registry_version'],
                      'registry_update_deferred': True, 'config_applied': args.apply,
                      'game_executable_path': updated['game_executable_path']}, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
