"""Read the local client's material inheritance without redistributing its assets."""
import copy
import json
import re
from pathlib import Path


PACKS = ('resource_pack', 'extras/astral_survey_v1/resource_pack')
ENGINE_PACKS = ('vanilla_base', 'vanilla', 'vanilla_netease')


def read_jsonc(path):
    # Preserve strings (including URLs) while stripping JSON comments.
    pattern = r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/'
    text = re.sub(pattern, lambda m: m[0] if m[0].startswith('"') else '',
                  path.read_text(encoding='utf-8-sig'))
    text = re.sub(r'"(?:\\.|[^"\\])*"|,\s*([}\]])',
                  lambda m: m[0] if m[0].startswith('"') else m[1], text)
    return json.loads(text)


def list_key(field, item):
    if field == 'samplerStates':
        return item['samplerIndex']
    if field == 'variants':
        return next(iter(item))
    return item


def merge_material(base, patch):
    result = copy.deepcopy(base)
    for key, value in patch.items():
        if key[:1] not in ('+', '-'):
            result[key] = copy.deepcopy(value)
            continue
        operation, field = key[0], key[1:]
        items = result.setdefault(field, [])
        for item in value:
            identity = list_key(field, item)
            index = next((i for i, old in enumerate(items)
                          if list_key(field, old) == identity), None)
            if operation == '-':
                if index is not None:
                    items.pop(index)
            elif index is None:
                items.append(copy.deepcopy(item))
            elif field == 'variants':
                items[index][identity] = merge_material(items[index][identity], item[identity])
            elif field == 'samplerStates':
                items[index].update(copy.deepcopy(item))
    return result


class MaterialLibrary:
    def __init__(self):
        self.nodes = {}

    def add(self, path):
        for key, patch in read_jsonc(path)['materials'].items():
            if key == 'version':
                continue
            name, _, parent = key.partition(':')
            node = self.nodes.setdefault(name, {'parent': parent, 'patches': []})
            if parent:
                node['parent'] = parent
            node['patches'].append(patch)

    def resolve(self, name, chain=()):
        if name in chain:
            raise ValueError('Material inheritance cycle: ' + ' -> '.join(chain + (name,)))
        node = self.nodes[name]
        material = self.resolve(node['parent'], chain + (name,)) if node['parent'] else {}
        for patch in node['patches']:
            material = merge_material(material, patch)
        return material


def inventory(root, game):
    """Include inherited engine descendants affected by our base overrides too."""
    records, sources, engine_files = [], set(), set()
    for pack_name in PACKS:
        pack = root / pack_name
        sources.update(p.relative_to(root).as_posix()
                       for p in (pack / 'shaders/glsl').iterdir()
                       if p.suffix in ('.vertex', '.fragment'))
        library = MaterialLibrary()
        for layer in ENGINE_PACKS:
            for kind in ('entity', 'terrain'):
                path = game / 'data/resource_packs' / layer / 'materials' / (kind + '.material')
                if path.exists():
                    library.add(path)
                    engine_files.add(path)
        for path in sorted((pack / 'materials').glob('*.material')):
            library.add(path)
        for name in sorted(library.nodes):
            # Avoid resolving unrelated materials that inherit other libraries.
            def affected(candidate, chain=()):
                if candidate in chain or candidate not in library.nodes:
                    return False
                node = library.nodes[candidate]
                if any((pack / p.get('vertexShader', '__absent__')).is_file()
                       for p in node['patches']):
                    return True
                return affected(node['parent'], chain + (candidate,))

            if not affected(name):
                continue
            material = library.resolve(name)
            for variant, patch in [('default', {})] + [next(iter(v.items()))
                                                       for v in material.get('variants', [])]:
                resolved = merge_material(material, patch)
                vertex = pack / resolved['vertexShader']
                fragment = pack / resolved['fragmentShader']
                if not vertex.is_file() or not fragment.is_file():
                    raise ValueError('Mixed custom/native shader pair: ' + name)
                records.append({
                    'pack': pack_name, 'material': name, 'variant': variant,
                    'vertex': vertex.relative_to(root).as_posix(),
                    'fragment': fragment.relative_to(root).as_posix(),
                    'defines': sorted(set(resolved.get('defines', []))),
                    'render_state': {k: v for k, v in resolved.items()
                                     if k not in ('variants', 'vertexShader', 'fragmentShader',
                                                  'vrGeometryShader', 'defines')},
                    'legacy_vr_geometry': resolved.get('vrGeometryShader'),
                })
    covered = {r[s] for r in records for s in ('vertex', 'fragment')}
    if sources != covered:
        raise ValueError('Uncovered source shaders: ' + repr(sorted(sources - covered)))
    return records, sorted(sources), sorted(engine_files)
