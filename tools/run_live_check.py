"""Run an owner-bound regression, locking the desktop when the suite needs it."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import desktop_lock, load_session, process_identity

# These suites were checked to use SDK calls only, including their cleanup.
SDK_BACKGROUND_SCRIPTS = frozenset(('verify_dripstone_native_boxes.py',))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--sdk-background', action='store_true',
                        help='Run a reviewed SDK-only suite without the desktop input lock')
    parser.add_argument('script', help='Python regression filename within tools/')
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != ROOT:
        parser.error('The session belongs to a different project')
    path = (ROOT / 'tools' / args.script).resolve(strict=True)
    if path.parent != ROOT / 'tools' or path.suffix != '.py' or path == Path(__file__).resolve():
        parser.error('Choose a project regression directly within tools/')
    if args.sdk_background and path.name not in SDK_BACKGROUND_SCRIPTS:
        parser.error('This suite has not been reviewed for SDK-only background execution')
    env = os.environ.copy()
    env.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=args.owner,
               MCDEV_MCP_URL=session['mcp_url'], MCDEV_GAME_PID=str(session['game_pid']))
    command = [sys.executable, '-X', 'utf8', str(path)] + args.args
    if args.sdk_background:
        env.pop('PYREACT_DESKTOP_LOCK_PID', None)
        env.pop('PYREACT_DESKTOP_LOCK_IDENTITY', None)
        return subprocess.call(command, env=env)
    # Child resize/input tools inherit ownership of this live parent's lock.
    with desktop_lock(timeout=30):
        env['PYREACT_DESKTOP_LOCK_PID'] = str(os.getpid())
        env['PYREACT_DESKTOP_LOCK_IDENTITY'] = process_identity(os.getpid())
        return subprocess.call(command, env=env)


if __name__ == '__main__':
    sys.exit(main())
