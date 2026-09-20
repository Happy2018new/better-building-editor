"""Run a project regression in one validated MCDK instance with desktop ownership."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import desktop_lock, load_session, process_identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('script', help='Python regression filename within tools/')
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != ROOT:
        parser.error('The session belongs to a different project')
    path = (ROOT / 'tools' / args.script).resolve(strict=True)
    if path.parent != ROOT / 'tools' or path.suffix != '.py' or path == Path(__file__).resolve():
        parser.error('Choose a project regression directly within tools/')
    env = os.environ.copy()
    env.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=args.owner,
               MCDEV_MCP_URL=session['mcp_url'], MCDEV_GAME_PID=str(session['game_pid']))
    # Child resize/input tools inherit ownership of this live parent's lock.
    with desktop_lock(timeout=30):
        env['PYREACT_DESKTOP_LOCK_PID'] = str(os.getpid())
        env['PYREACT_DESKTOP_LOCK_IDENTITY'] = process_identity(os.getpid())
        return subprocess.call([sys.executable, '-X', 'utf8', str(path)] + args.args, env=env)


if __name__ == '__main__':
    sys.exit(main())
