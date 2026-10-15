"""Run the isolated candidate and existing shared-route regression tests."""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CLONE = ROOT / '.runtime/projects/book-r20'
sys.path.insert(0, str(CLONE / 'behavior_pack/modern_projection'))
import projection
from projection import lectern_body, render_context

MODULES = ('test_lectern_body_candidate', 'test_lectern_world_candidate', 'test_render_context', 'test_context_batches',
           'test_context_cached_writes', 'test_native_actor_context', 'test_native_render_profile',
           'test_static_table_render', 'test_book_render_plan', 'test_book_owner',
           'test_book_qualification', 'test_book_resources')


def main():
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / 'tests'))
    assert Path(render_context.__file__).resolve().is_relative_to(CLONE)
    assert lectern_body.CANDIDATE_ENABLED is False
    lectern_body.CANDIDATE_ENABLED = True
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in MODULES)
    stream = io.StringIO()
    start = time.perf_counter()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report = {
        'schema': 1,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'stage': 'offline_isolated_candidate',
        'product_qualified': False,
        'native_pixels_qualified': False,
        'candidate_enabled_only_in_test_process': True,
        'clone': str(CLONE),
        'modules': MODULES,
        'tests_run': result.testsRun,
        'errors': len(result.errors),
        'failures': len(result.failures),
        'skipped': len(result.skipped),
        'successful': result.wasSuccessful(),
        'elapsed_seconds': time.perf_counter() - start,
        'loaded_render_context': str(Path(render_context.__file__).resolve()),
        'candidate_sources': {
            str(Path(value).relative_to(ROOT)): hashlib.sha256(Path(value).read_bytes()).hexdigest()
            for value in (render_context.__file__, lectern_body.__file__, __file__,
                          HERE / 'test_lectern_body_candidate.py', HERE / 'test_lectern_world_candidate.py')},
        'unchanged_main_render_context_sha256': hashlib.sha256(
            (ROOT / 'behavior_pack/modern_projection/projection/render_context.py').read_bytes()).hexdigest(),
        'log': 'offline-tests.log',
    }
    (HERE / 'offline-tests.log').write_text(stream.getvalue(), encoding='utf-8')
    (HERE / 'offline-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    if not result.wasSuccessful():
        print(stream.getvalue())
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
