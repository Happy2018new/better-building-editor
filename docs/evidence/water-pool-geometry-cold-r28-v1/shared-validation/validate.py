"""Exact shared source checks with real Python 3 and Python 2 interpreters."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
SOURCE = 'behavior_pack/modern_projection/projection/'
FILES = (SOURCE + 'liquid_product_deployment.py', SOURCE + 'scene.py',
         'tests/test_liquid_product_geometry.py', 'tests/test_liquid_product_gui.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = WORK / 'validation-v1.json'
    assert not output.exists()
    before = {name: sha(ROOT / name) for name in FILES}
    commands = {
        'python3-targeted': [sys.executable, '-B', '-X', 'utf8', '-m', 'unittest',
                            'tests.test_liquid_product_geometry', 'tests.test_liquid_product_gui',
                            'tests.test_book_gui_anchor', 'tests.test_liquid_viewport',
                            'tests.test_liquid_product_profile'],
        'python2-actual-geometry-and-scene': ['D:/Program/Python27/python.exe', '-B',
                                            'tests/test_liquid_product_geometry.py'],
        'python2-production-compile': ['D:/Program/Python27/python.exe', '-B', '-c',
                                     'import sys; [compile(open(p,"rb").read(),p,"exec") for p in sys.argv[1:]]',
                                     *FILES[:2]],
    }
    rows = {}
    for name, command in commands.items():
        result = subprocess.run(command, cwd=ROOT, capture_output=True)
        (WORK / (name + '.stdout.txt')).write_bytes(result.stdout)
        (WORK / (name + '.stderr.txt')).write_bytes(result.stderr)
        rows[name] = {'command': command, 'exit_code': result.returncode,
                      'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
                      'stderr_sha256': hashlib.sha256(result.stderr).hexdigest()}
        assert result.returncode == 0, name
    scene = (ROOT / (SOURCE + 'scene.py')).read_text('utf8')
    previous = subprocess.check_output(['git', 'show', 'HEAD:' + SOURCE + 'scene.py'], cwd=ROOT).decode('utf8')
    water_addition = ("                gui_geometry = getattr(liquid_profile, 'ui_geometry_for_gui', None)\n"
                      "                if gui_geometry is not None:\n"
                      "                    position, size = gui_geometry(view.position, view.size, Theme.native_gui_scale)\n"
                      "                    return view._replace(position=position, size=size)\n")
    assert scene.count(water_addition) == 1
    assert scene.replace(water_addition, '') == previous.replace('\r\n', '\n')
    # The private cold candidate's ProductWater source is byte-identical. Its
    # Scene differs from shared by the already committed book-only GUI hook.
    proposal = WORK.with_name('water-geometry-readiness-v1') / 'proposed_liquid_product_deployment.py'
    assert (ROOT / FILES[0]).read_text('utf8') == proposal.read_text('utf8')
    after = {name: sha(ROOT / name) for name in FILES}
    assert before == after
    result = {'schema': 1, 'passed': True, 'commands': rows, 'source_sha256': after,
              'python3_targeted_tests': 57, 'python2_actual_geometry_and_scene_tests': 5,
              'book_branch_and_all_other_scene_bytes_preserved': True,
              'product_water_source_matches_private_cold_candidate': True,
              'qualification_or_owner_data_modified': False,
              'MC_started': False, 'RPC_dispatched': False}
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='ascii')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
