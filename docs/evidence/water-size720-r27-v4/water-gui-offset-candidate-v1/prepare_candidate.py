"""Prepare a separate GUI-offset water candidate; retain all original contracts."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
BASE = ROOT / '.runtime/projects/water-r27-anchor-diagnostic-v1'
MANIFEST = WORK.with_name('water-anchor-calibration-v1') / 'diagnostic-source-v1.json'
PREFIX = 'behavior_pack/modern_projection/projection/'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def main():
    target = WORK / 'candidate'
    assert not target.exists(), 'Never overwrite a prepared candidate'
    manifest = json.loads(MANIFEST.read_bytes())
    assert sha(MANIFEST.read_bytes()) == '3226cd8e8790e0a571e97fa5aa0e3b3761528532c227904d30a24fc9b66fed07'
    changes = {}
    old_raws = {}
    for name in ('widgets.py', 'liquid_product_deployment.py', 'scene.py'):
        relative = PREFIX + name
        raw = (BASE / relative).read_bytes()
        assert sha(raw) == manifest['source_sha256'][relative]
        old_raws[relative] = raw
        text = raw.decode('utf-8').replace('\r\n', '\n')
        if name == 'widgets.py':
            text = replace_once(text, '    input_font_scale = 1.\n',
                                '    input_font_scale = 1.\n    native_gui_scale = None\n')
            text = replace_once(text,
                '        # Keep the original bitmap glyphs at whole screen magnifications. A\n',
                '        # Refresh the native GUI cache even when the font/theme is unchanged.\n'
                '        cls.native_gui_scale = gui\n'
                '        # Keep the original bitmap glyphs at whole screen magnifications. A\n')
        elif name == 'liquid_product_deployment.py':
            text = replace_once(text,
                'from .liquid_render_target_data import TARGET_ENGINE_VERSION\n',
                'from .liquid_render_target_data import TARGET_ENGINE_VERSION\n'
                'from .storage import integer_types\n')
            text = replace_once(text, '\n\ndef candidate_profile(frozen=False):\n',
                '\n\ndef ui_offset_for_gui(size, gui):\n'
                '    """Place only the explicit product-water candidate at the native GUI anchor."""\n'
                '    if (isinstance(gui, bool) or not isinstance(gui, integer_types + (float,))\n'
                "            or not 1. <= gui < float('inf') or gui != round(gui)):\n"
                "        raise ValueError('Product water needs a positive integer native GUI scale')\n"
                '    return 0., min(size) / float(gui)\n'
                '\n\ndef candidate_profile(frozen=False):\n')
            text = replace_once(text,
                '    return ProductLiquidProfile(selected, ui_pose, ui_offset)\n',
                '    profile = ProductLiquidProfile(selected, ui_pose, ui_offset)\n'
                '    profile.ui_offset_for_gui = ui_offset_for_gui\n'
                '    return profile\n')
        else:
            text = replace_once(text,
                '                offset = liquid_profile.ui_offset(view.size)\n',
                "                gui_offset = getattr(liquid_profile, 'ui_offset_for_gui', None)\n"
                '                offset = (gui_offset(view.size, Theme.native_gui_scale) if gui_offset is not None\n'
                '                          else liquid_profile.ui_offset(view.size))\n')
        output = text.encode('utf-8')
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(output)
        changes[relative] = {'base_sha256': sha(raw), 'candidate_sha256': sha(output),
                             'shared_at_prepare_sha256': sha((ROOT / relative).read_bytes())}
        patch = ''.join(difflib.unified_diff(raw.decode('utf-8').splitlines(True), text.splitlines(True),
                        fromfile='base/' + relative, tofile='candidate/' + relative))
        (WORK / (name + '.patch')).write_bytes(patch.encode('utf-8'))
    report = {'schema': 1, 'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
              'base_manifest_sha256': sha(MANIFEST.read_bytes()), 'base_project': str(BASE),
              'base_source_contract_sha256': manifest['source_contract_sha256'],
              'candidate_scope': 'Three private files only; SDK cache + explicit Product water callback + water Scene branch',
              'changed_files': changes, 'MC_started': False,
              'original_contracts_modified': False, 'production_admission_performed': False,
              'formal_A_accepted': False, 'manual_closures_added': 0,
              'unmodified_pivot': '+1.5 entityY retained; shader/resource bytes unchanged',
              'original_failures_retained': ['all-image neutral masks with debug text',
                  'GUI2 front WVP factor signed24 bound ratio 1.190508', 'formal A incomplete temporal capture']}
    (WORK / 'candidate-v1.json').write_bytes((json.dumps(report, indent=2) + '\n').encode('utf-8'))
    assert all((BASE / name).read_bytes() == raw for name, raw in old_raws.items())
    print(json.dumps({'prepared': True, 'changed_files': changes, 'MC_started': False}, indent=2))


if __name__ == '__main__':
    main()
