"""Separate native world coordinates from packed source positions diagnostically."""
import argparse
import json
from pathlib import Path
import sys

import verify_dripstone_world_visuals as suite
from projection.debug_dripstone_blueprints import METADATA
from projection.render_context import CONTEXT_CENTER, CONTEXT_STRIDE


def configure(source_shift, world_shift):
    native, world = suite.native, suite.world
    original = tuple(tuple(pos) for pos in suite.metadata['merged_tips'])
    delta = (source_shift[0], 0, source_shift[1])
    positions = tuple(tuple(pos[i] + delta[i] for i in range(3)) for pos in original)
    assert all(0 <= pos[i] < METADATA[3][i]
               for pos in positions for i in range(3)), positions
    injection = '''doc=s.editor.document
from modern_projection.projection.model import Document
original=%r
delta=%r
cells=dict((tuple(pos[i]+delta[i] for i in range(3)),doc.get(pos)) for pos in original)
doc=Document(doc.size,cells,name=doc.name,biome=doc.biome)
s.editor.document=doc
'''.rstrip() % (original, delta)
    assert 'doc=s.editor.document' in native.CROP_FIXTURE
    native.CROP_FIXTURE = native.CROP_FIXTURE.replace('doc=s.editor.document', injection, 1)
    native.CROP_FIXTURE = native.CROP_FIXTURE.replace(
        'sys._neighbor_qa_origin=tuple(s.origin)',
        's.origin=(s.origin[0]+%r,s.origin[1],s.origin[2]+%r)\n'
        'sys._neighbor_qa_origin=tuple(s.origin)' % tuple(world_shift), 1)
    native.VISUAL_CASES = {'merged_tips': positions}
    world.CASES = ('merged_tips',)
    return {'source_shift': source_shift, 'world_shift': world_shift,
            'source_positions': positions,
            'packed_positions': [tuple((pos[i] & 15) * CONTEXT_STRIDE + CONTEXT_CENTER for i in range(3))
                                 for pos in positions],
            'scope': 'Diagnostic coordinate controls; no fitted offsets or production renderer changes.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-shift', type=int, nargs=2, default=(0, 0), metavar=('X', 'Z'))
    parser.add_argument('--world-shift', type=int, nargs=2, default=(0, 0), metavar=('X', 'Z'))
    parser.add_argument('--capture-helper', type=Path, required=True)
    options, remaining = parser.parse_known_args()
    if not remaining or remaining[0].startswith('-'):
        parser.error('Supply the output JSON first, followed by the visual suite options')
    configuration = configure(options.source_shift, options.world_shift)
    from verify_neighbor_native_png import main as capture
    sys.argv = [sys.argv[0], '--suite', 'dripstone', '--capture-helper', str(options.capture_helper)] + remaining
    output = Path(remaining[0])
    try:
        return capture()
    finally:
        if output.is_file():
            report = json.loads(output.read_text(encoding='utf8'))
            report['coordinate_control'] = configuration
            for case in report['cases']:
                if 'source' in case:
                    origin = case['source']['origin']
                    case['coordinate_control_world_positions'] = [
                        tuple(origin[i] + pos[i] for i in range(3)) for pos in configuration['source_positions']]
            suite.world.write_json(output, report)


if __name__ == '__main__':
    raise SystemExit(main())
