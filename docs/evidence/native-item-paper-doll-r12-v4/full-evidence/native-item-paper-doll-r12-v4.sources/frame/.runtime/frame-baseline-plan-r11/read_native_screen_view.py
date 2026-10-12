"""One owner-bound screen metric getter; no navigation, attachment or shader mutation."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

from session_pack_stage import SessionPackStage, digest, require
from run_frame_translation import ARTIFACTS, SESSION, OWNER
from mcdk import Client, return_value


CODE = '''import json,os,sys,time
import mod.client.extraClientApi as api
game=api.GetEngineCompFactory().CreateGame(api.GetLevelId())
logical=game.GetScreenSize()
view=game.GetScreenViewInfo()
top=api.GetTopScreen()
root=None
if top is not None and hasattr(top,'_root_path'):
 control=top.GetBaseUIControl(top._root_path)
 if control is not None:root={'position':control.GetGlobalPosition(),'size':control.GetSize(),'path':control.GetPath()}
_result=json.dumps({'logical':logical,'view':view,'native_root':root,'top_present':top is not None,
 'runtime':api.GetMinecraftVersion(),'pid':os.getpid(),'token':getattr(sys,'_pyreact_mcdk_session',None),'clock':time.time()})
'''


def main():
    output = ARTIFACTS / 'native-item-paper-doll-r12.screen-view-readonly-v1.json'
    require(not output.exists(), 'Preserve prior screen observation')
    guard = SessionPackStage(ARTIFACTS, ARTIFACTS / 'native-item-screen-view-readonly.unused-stage-journal.json')
    deadline = time.monotonic() + 25.
    report = {'schema': 1, 'scope': 'One read-only native screen-view getter', 'requests': [],
              'navigation_mutation_attempted': False, 'bind_mutation_attempted': False,
              'shader_or_pack_mutation_attempted': False, 'completed': False,
              'source_sha256': digest(Path(__file__))}

    def save():
        temporary = output.with_name(output.name + '.tmp')
        with temporary.open('x', encoding='ascii') as target:
            json.dump(report, target, ensure_ascii=True, indent=2)
            target.write('\n')
        os.replace(temporary, output)

    class RecordedClient(Client):
        def _post(self, method, params=None, notification=False):
            row = {'request': {'jsonrpc': '2.0', 'method': method, 'params': params or {}},
                   'started_at': datetime.now(timezone.utc).isoformat()}
            if not notification:
                row['request']['id'] = self.counter + 1
            report['requests'].append(row)
            save()
            try:
                require(time.monotonic() < deadline, 'Read-only screen deadline exhausted')
                if method == 'tools/call':
                    row['background_before'] = guard.guard()
                self.timeout = min(10., deadline - time.monotonic())
                require(self.timeout > 0, 'Guard consumed screen-read budget')
                row['response'] = super()._post(method, params, notification)
                return row['response']
            except Exception as error:
                row['error'] = repr(error)
                raise
            finally:
                row['finished_at'] = datetime.now(timezone.utc).isoformat()
                save()

    try:
        os.environ['MCDEV_SESSION_FILE'] = str(SESSION / 'session.json')
        os.environ['MCDEV_OWNER'] = OWNER
        report['background_before'] = guard.guard()
        report['physical_window'] = guard.window
        with RecordedClient(timeout=10) as client:
            result = return_value(client.call('execute_code', {'code': CODE, 'is_client': True, 'direct_return': True}))
            report['observed'] = json.loads(result) if isinstance(result, str) else result
            require(report['observed']['pid'] == client.binding['game_pid'] and
                    report['observed']['token'] == client.binding['token'], 'Wrong native screen session')
        report['background_after'] = guard.guard()
        report['completed'] = True
    except Exception as error:
        report['error'] = repr(error)
    finally:
        save()
    print(json.dumps({'completed': report['completed'], 'observed': report.get('observed'),
                      'sha256': digest(output)}))
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
