"""Run neighbor visual suites with a preserved, hash-recorded native PNG helper."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=('dripstone', 'static'), required=True)
    parser.add_argument('--capture-helper', type=Path, required=True,
                        help='Checkpointed verify_sign_visuals.py exporting SignCheck')
    options, remaining = parser.parse_known_args()
    if not remaining or remaining[0].startswith('-'):
        parser.error('Supply the output JSON first, followed by the visual suite options')
    helper = options.capture_helper.resolve(strict=True)
    payload = helper.read_bytes()
    spec = importlib.util.spec_from_file_location('neighbor_png_capture_helper', helper)
    module = importlib.util.module_from_spec(spec)
    exec(compile(payload, str(helper), 'exec'), module.__dict__)
    if options.suite == 'dripstone':
        import verify_dripstone_world_visuals as suite
    else:
        import verify_static_neighbor_world_visuals as suite
    from verify_debug_blueprints import INSTALL_PROBE, write_json
    world = suite.world

    class NativePngNeighborCheck(module.SignCheck):
        def __init__(self, client, output, timeout):
            module.SignCheck.__init__(self, client, output, timeout, native_resolution=True)

        def run(self, code):
            result = module.SignCheck.run(self, code)
            if code == INSTALL_PROBE:
                self.refresh()
            return result

    world.BlueprintCheck = NativePngNeighborCheck
    import sys
    sys.argv = [sys.argv[0]] + remaining
    output = Path(remaining[0])
    helper_snapshot = output.with_name(output.stem + '_capture_helper.py')
    helper_snapshot.parent.mkdir(parents=True, exist_ok=True)
    helper_snapshot.write_bytes(payload)
    try:
        return world.main()
    finally:
        if output.is_file():
            report = json.loads(output.read_text(encoding='utf8'))
            report['native_png_capture_helper'] = {
                'path': str(helper), 'sha256': hashlib.sha256(payload).hexdigest(),
                'snapshot': str(helper_snapshot.resolve()),
                'class': 'SignCheck', 'native_resolution': True,
                'desktop_ownership': 'Caller must hold run_live_check.py desktop lock.'}
            write_json(output, report)


if __name__ == '__main__':
    raise SystemExit(main())
