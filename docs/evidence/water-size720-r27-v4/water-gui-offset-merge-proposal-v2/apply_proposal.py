"""Check or apply three exact byte replacements, preserving the production EOL."""
import argparse
import hashlib
import json
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
PREFIX = Path('behavior_pack/modern_projection/projection')
BASE = {
    'widgets.py': '23b5e306840b660ad89af45268cbfbf322a465f42d1b5d06fb6152b0b6520dbe',
    'liquid_product_deployment.py': '50ea7fa56d084300601c25f83b2f5b9c1009e2f01fc0f4df403c866318dc43f5',
    'scene.py': '60e6362ec4cf445b33e09b1693feb76d5a6e6242428143cb50fe2fd7f8af8eda',
}
REPLACEMENTS = {
    'widgets.py': [
        ('    input_font_scale = 1.\n', '    input_font_scale = 1.\n    native_gui_scale = None\n'),
        ('        # Keep the original bitmap glyphs at whole screen magnifications. A\n',
         '        # Refresh the native GUI cache even when the font/theme is unchanged.\n'
         '        cls.native_gui_scale = gui\n'
         '        # Keep the original bitmap glyphs at whole screen magnifications. A\n'),
    ],
    'liquid_product_deployment.py': [
        ('from .liquid_render_target_data import TARGET_ENGINE_VERSION\n',
         'from .liquid_render_target_data import TARGET_ENGINE_VERSION\nfrom .storage import integer_types\n'),
        ('\n\ndef candidate_profile(frozen=False):\n',
         '\n\ndef ui_offset_for_gui(size, gui):\n'
         '    """Place only the explicit product-water candidate at the native GUI anchor."""\n'
         '    if (isinstance(gui, bool) or not isinstance(gui, integer_types + (float,))\n'
         "            or not 1. <= gui < float('inf') or gui != round(gui)):\n"
         "        raise ValueError('Product water needs a positive integer native GUI scale')\n"
         '    return 0., min(size) / float(gui)\n'
         '\n\ndef candidate_profile(frozen=False):\n'),
        ('    return ProductLiquidProfile(selected, ui_pose, ui_offset)\n',
         '    profile = ProductLiquidProfile(selected, ui_pose, ui_offset)\n'
         '    profile.ui_offset_for_gui = ui_offset_for_gui\n'
         '    return profile\n'),
    ],
    'scene.py': [
        ('                offset = liquid_profile.ui_offset(view.size)\n',
         "                gui_offset = getattr(liquid_profile, 'ui_offset_for_gui', None)\n"
         '                offset = (gui_offset(view.size, Theme.native_gui_scale) if gui_offset is not None\n'
         '                          else liquid_profile.ui_offset(view.size))\n'),
    ],
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def revised(name, raw):
    assert sha(raw) == BASE[name], 'Production baseline changed: ' + name
    eol = b'\r\n' if b'\r\n' in raw else b'\n'
    if eol == b'\r\n':
        assert b'\n' not in raw.replace(eol, b''), 'Mixed baseline EOL: ' + name
    result = raw
    for old, new in REPLACEMENTS[name]:
        old, new = (text.encode('utf-8').replace(b'\n', eol) for text in (old, new))
        assert result.count(old) == 1, 'Replacement is not unique: ' + name
        result = result.replace(old, new)
    if eol == b'\r\n':
        assert b'\n' not in result.replace(eol, b''), 'Changed EOL: ' + name
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Default is a read-only check')
    args = parser.parse_args()
    proposals, rows = {}, []
    # Validate every baseline before writing any production file.
    for name in BASE:
        path = ROOT / PREFIX / name
        before = path.read_bytes()
        after = revised(name, before)
        assert after == (WORK / 'candidate' / PREFIX / name).read_bytes()
        proposals[path] = after
        rows.append({'path': (PREFIX / name).as_posix(), 'before_sha256': sha(before),
                     'after_sha256': sha(after), 'before_CRLF': before.count(b'\r\n'),
                     'after_CRLF': after.count(b'\r\n'),
                     'after_bare_LF': after.replace(b'\r\n', b'').count(b'\n')})
    if args.apply:
        for path, after in proposals.items():
            assert sha(path.read_bytes()) == BASE[path.name]
            path.write_bytes(after)
    print(json.dumps({'checked': True, 'applied': args.apply, 'files': rows,
                      'owner_or_qualification_written': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
