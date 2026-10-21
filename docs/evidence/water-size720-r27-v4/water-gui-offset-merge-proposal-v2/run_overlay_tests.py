"""Run the proposed unittest file against isolated source overrides, without writes."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
PREFIX = Path('behavior_pack/modern_projection/projection')
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = WORK / 'overlay-tests-v1.json'
    assert not output.exists()
    names = ['widgets.py', 'liquid_product_deployment.py', 'scene.py',
             'liquid_product_owner_data.py', 'liquid_product_qualification_data.py']
    before = {name: sha(ROOT / PREFIX / name) for name in names}
    spec = importlib.util.spec_from_file_location(
        'projection._gui_merge_candidate', WORK / 'candidate' / PREFIX / 'liquid_product_deployment.py')
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    test_path = WORK / 'candidate/tests/test_liquid_product_gui.py'
    spec = importlib.util.spec_from_file_location('_gui_merge_tests', test_path)
    tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tests)
    tests.ROOT = WORK / 'candidate'
    tests.deployment = candidate
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(tests.ProductWaterGuiTests)
    buffer = io.StringIO()
    result = unittest.TextTestRunner(stream=buffer, verbosity=2).run(suite)
    assert all(sha(ROOT / PREFIX / name) == value for name, value in before.items())
    report = {
        'schema': 1, 'passed': result.wasSuccessful(), 'tests_run': result.testsRun,
        'failures': len(result.failures), 'errors': len(result.errors),
        'scope': 'Proposed actual unittest module with explicit test globals ROOT/source-deployment overrides; shared LiquidControls and renderer fixtures imported unchanged',
        'unittest_output': buffer.getvalue(),
        'shared_source_before_and_after_sha256': before,
        'candidate_sha256': {name: sha(WORK / 'candidate' / PREFIX / name) for name in names[:3]},
        'test_sha256': sha(test_path), 'proposal_patch_sha256': sha(WORK / 'proposal.patch'),
        'MC_started': False, 'shared_source_written': False,
        'production_admission_performed': False, 'formal_A_accepted': False,
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(buffer.getvalue())
    print(json.dumps({'passed': report['passed'], 'tests_run': result.testsRun,
                      'report_sha256': sha(output), 'shared_source_written': False}))
    assert result.wasSuccessful()


if __name__ == '__main__':
    main()
