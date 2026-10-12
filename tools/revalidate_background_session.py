"""Issue a fresh readiness receipt without changing an earlier failed launch."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import load_session, process_identity, write_json
from instances import background_guard_state
from mcdk import Client, return_value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True, type=Path)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh readiness receipt')
    data = load_session(args.session, args.owner)
    if Path(data['project']).resolve() != ROOT or not data.get('noactivation', {}).get('requested'):
        parser.error('Require an owned background session from this project')
    for name in ('mcdk', 'game'):
        if process_identity(data[name + '_pid']) != data[name + '_identity']:
            raise RuntimeError('Process identity changed: ' + name)
    guard = background_guard_state(data['game_pid'], Path(data['game_executable']).name)
    if not guard['background_safe'] or not guard['window_noactivate']:
        raise RuntimeError('Background window contract failed')
    with Client(data['mcp_url'], timeout=8, bind_session=False) as client:
        identity = return_value(client.call('execute_code', {
            'code': "import os\n_result={'pid':os.getpid(),'appdata':os.environ.get('APPDATA')}",
            'is_client': True, 'direct_return': True}))
        if identity != {'pid': data['game_pid'], 'appdata': data['appdata']}:
            raise RuntimeError('Runtime process or APPDATA differs from the launch')
        for side in (True, False):
            marker = return_value(client.call('execute_code', {
                'code': "import sys\n_result=getattr(sys,'_pyreact_mcdk_session',None)",
                'is_client': side, 'direct_return': True}))
            if marker != data['token']:
                raise RuntimeError('Runtime session marker differs from the launch')
    final = background_guard_state(data['game_pid'], Path(data['game_executable']).name)
    if not final['background_safe'] or not final['window_noactivate']:
        raise RuntimeError('Background window contract changed during revalidation')
    data.update(state='ready', ready=True, session_file=str(args.output.resolve()),
                launch_manifest=str(args.session.resolve()),
                revalidated_at=datetime.now(timezone.utc).isoformat())
    data['noactivation'].update(final)
    write_json(args.output, data)
    print({'ready': True, 'session_file': data['session_file'], 'game_pid': data['game_pid'],
           'launch_manifest_unchanged': data['launch_manifest']})


if __name__ == '__main__':
    main()
