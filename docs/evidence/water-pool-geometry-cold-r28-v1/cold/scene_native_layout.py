"""Read actual ordinary Scene canvas and clipping controls through existing APIs."""


def read_scene_controls(check, walk):
    tree = check.command('dump_tree')['tree']
    scenes = [node for node in walk(tree) if node.get('type') == 'Scene']
    assert len(scenes) == 1
    roots = scenes[0]['children']
    assert len(roots) == 1 and roots[0]['type'] == 'Panel'
    canvas = roots[0]
    candidates = [node for node in canvas['children'] if node.get('type') == 'Panel'
                  and any(child.get('type') == 'LiquidModels' and child.get('key') is None for child in node['children'])]
    assert len(candidates) == 1, 'Ordinary Scene clipping panel is ambiguous'
    clip = candidates[0]
    result = {}
    for label, node in (('canvas', canvas), ('clip', clip)):
        value = check.command('native_control', node['id'])['result']
        result[label] = {'id': node['id'], 'type': node['type'], 'native': value, 'declared_layout': node.get('layout')}
    assert all(row['native']['visible'] is True for row in result.values())
    return result
