"""Index preserved native frame route experiments without upgrading acceptance."""
import argparse
import hashlib
import json
from pathlib import Path

from verify_debug_blueprints import write_json

ROOT = Path(__file__).resolve().parents[1]
INSTANCES = Path('C:/Users/Happy2018new/.pyreact-debug/instances')
SESSIONS = ('e1e86cf729eb4873800ee56751eaa224', '0436872602044d3780e8165da0bc24df',
            '6afcb53254cb4ed995f4a9694f73c9c8', 'd5a229031d81432a87dd90ed57f6d87d',
            '6bfab90bdc7c4085921f597c22660ece', '1ac73cb4947640b88a423327299ff627',
            '39f516430f9d4f48bb9e6fba0bce3e60', 'dfde9240ce38406d9e70f76d462a029a')


def binding(path):
    payload = path.read_bytes()
    return {'path': str(path.resolve()), 'bytes': len(payload),
            'sha256': hashlib.sha256(payload).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh evidence index')
    rows = []
    for identity in SESSIONS:
        directory = INSTANCES / identity
        session = json.loads((directory / 'session.json').read_bytes())
        assert session['owner'] == 'frame-r11-background' and session['state'] == 'stopped', identity
        artifacts = directory / 'artifacts'
        files = [path for path in artifacts.rglob('*') if path.is_file()]
        rows.append({'id': identity, 'state': session['state'], 'error': session.get('error'),
                     'game_pid': session.get('game_pid'), 'game_identity': session.get('game_identity'),
                     'mcdk_pid': session.get('mcdk_pid'), 'mcdk_identity': session.get('mcdk_identity'),
                     'session': binding(directory / 'session.json'),
                     'log': binding(directory / 'mcdk.log'),
                     'artifacts': [binding(path) for path in sorted(files)]})
    baseline = json.loads((INSTANCES / SESSIONS[1] / 'artifacts/frame-editor-r11-baseline-v2.json').read_bytes())
    scored = json.loads((INSTANCES / SESSIONS[-1] / 'artifacts/frame-sign-route-cold-v1-score.json').read_bytes())
    evidence = {'schema': 1, 'production_rendering_accepted': False,
                'source_baseline': 'f6d8e35',
                'scope': 'Preserved native route diagnostics; native entity preview depth remains unproven',
                'sessions': rows,
                'stable_editor_baseline': {'completed': baseline['completed'], 'restored': baseline['restored'],
                    'item_pixels': {key: baseline['controls'][key]['item_pixels'] for key in ('combined', 'combined_repeat')},
                    'item_only_pixels': baseline['controls']['item_only']['geometry_pixels'],
                    'shulker_control_pixels': baseline['controls']['positive']['geometry_pixels']},
                'corrected_route_markers': scored['markers'],
                'conclusions': ['The registered native transparency material produces the magenta sign body.',
                    'The same material produces no marker on frame body or combined world projection.',
                    'The green sign-specific marker did not render; the original 240 pixels were the inverse crosshair.',
                    'No successful native matrix marker decode was obtained.',
                    'Startup and post-ready IPC failures are preserved separately from rendering diagnostics.'],
                'limits': ['This does not identify the actual native frame material or a validated depth correction.',
                    'The original editor acceptance gates and all frame-item accepted flags remain false.',
                    'Per-draw matrix, alpha ownership, full/missing, facing/rotation and resource cleanup still need native acceptance.']}
    write_json(args.output, evidence)
    print(json.dumps({'sessions': len(rows), 'files': sum(len(row['artifacts']) for row in rows),
                      'production_rendering_accepted': False}))


if __name__ == '__main__':
    main()
