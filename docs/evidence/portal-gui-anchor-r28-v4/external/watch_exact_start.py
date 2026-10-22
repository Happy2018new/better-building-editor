"""Read-only exact exit observation for one explicitly assigned cold snapshot."""
import argparse
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root/'tools'), str(root/'.agents/skills/pyreact-debugging/scripts')]
from _session import load_session, process_identity
import watch_intrinsic_glint_exit_r21 as observer

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--session', required=True, type=Path)
parser.add_argument('--owner', required=True)
parser.add_argument('--project', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
assert args.project.resolve().parent == (root/'.runtime/projects').resolve()

def owned_starting(path, expected_owner, live=False):
    assert Path(path).resolve() == args.session.resolve() and expected_owner == args.owner
    data = load_session(path, expected_owner, live=False)
    assert data['state'] in ('starting', 'ready')
    assert Path(data['project']).resolve() == args.project.resolve()
    for kind in ('game', 'mcdk'):
        assert data[kind+'_identity'] == process_identity(data[kind+'_pid'])
    return data

observer.load_session = owned_starting
observer.watch(args.session, args.owner, args.output)
