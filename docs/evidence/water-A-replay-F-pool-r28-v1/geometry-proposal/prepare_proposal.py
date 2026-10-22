"""Write reviewable source proposals without editing the shared or frozen tree."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
PROJECT = ROOT / '.runtime/projects/water-r27-merged-flow-editor-v1'


def main():
    assert not (WORK / 'source-proposal-v1.json').exists()
    names = ('liquid_product_deployment.py', 'scene.py')
    originals = {name: (PROJECT / 'behavior_pack/modern_projection/projection' / name).read_text(encoding='utf8') for name in names}
    candidate = (WORK / 'candidate_geometry.py').read_text(encoding='utf8')
    function = ast.get_source_segment(candidate, ast.parse(candidate).body[-1])
    function = function.replace('(int, float)', 'integer_types + (float,)')
    product = originals[names[0]].replace('from . import liquid_product_qualification_data', 'import math\n\nfrom . import liquid_product_qualification_data', 1)
    product = product.replace('\ndef candidate_profile(', '\n' + function + '\n\n\ndef candidate_profile(', 1)
    product = product.replace('    profile.ui_offset_for_gui = ui_offset_for_gui', '    profile.ui_offset_for_gui = ui_offset_for_gui\n    profile.ui_geometry_for_gui = ui_geometry_for_gui', 1)
    old = """                gui_offset = getattr(liquid_profile, 'ui_offset_for_gui', None)
                offset = (gui_offset(view.size, Theme.native_gui_scale) if gui_offset is not None
                          else liquid_profile.ui_offset(view.size))
                return view._replace(position=tuple(view.position[axis] + offset[axis] for axis in range(2)))"""
    new = """                gui_geometry = getattr(liquid_profile, 'ui_geometry_for_gui', None)
                if gui_geometry is not None:
                    position, size = gui_geometry(view.position, view.size, Theme.native_gui_scale)
                    return view._replace(position=position, size=size)
""" + old
    assert originals[names[1]].count(old) == 1
    proposals = {names[0]: product, names[1]: originals[names[1]].replace(old, new, 1)}
    patch = []
    records = {}
    for name, text in proposals.items():
        ast.parse(text)
        path = WORK / ('proposed_' + name)
        path.write_text(text, encoding='utf8', newline='\n')
        records[name] = {'original_sha256': hashlib.sha256(originals[name].encode('utf8')).hexdigest(),
                         'proposal_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        patch.extend(difflib.unified_diff(originals[name].splitlines(True), text.splitlines(True),
                         fromfile='a/behavior_pack/modern_projection/projection/' + name,
                         tofile='b/behavior_pack/modern_projection/projection/' + name))
    (WORK / 'source-proposal-v1.patch').write_text(''.join(patch), encoding='utf8', newline='\n')
    (WORK / 'source-proposal-v1.json').write_text(json.dumps({'schema': 1, 'files': records,
           'source_mutated': False, 'native_tested': False, 'scope': 'Product water only; optional Scene geometry callback; legacy callback fallback retained.'}, indent=2) + '\n', encoding='ascii')
    print(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
