"""Read finite player and reserved-cell state before any liquid world fixture."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import load_session
from mcdk import Client
from probe_liquid_pose_channel import run

CLIENT = '''import json
import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory()
player=api.GetLocalPlayerId()
_result=json.dumps({'foot':factory.CreatePos(player).GetFootPos(),'player':player})
'''
ACTUAL_WORLD_CLIENT = CLIENT.replace("_result=json.dumps({'foot':factory.CreatePos(player).GetFootPos(),'player':player})", '''owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
session=getattr(owner,'session',None) if owner is not None else None
bridge=getattr(owner,'bridge',None) if owner is not None else None
business={'owner_present':owner is not None,'session_present':session is not None,
 'bridge_present':bridge is not None,'session_ready':getattr(session,'ready',False) is True,
 'bridge_session_matches':bridge is not None and session is not None and getattr(bridge,'session',None) is session,
 'hud_present':owner is not None and getattr(owner,'hud',None) is not None}
_result=json.dumps({'foot':factory.CreatePos(player).GetFootPos(),'player':player,'business':business})''')
SERVER = '''import json,math
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
players=api.GetPlayerList()
row={'players':players,'foot':None,'dimension':None,'reserve':None,'front':None,'back':None,'reserve_cells':None}
if players:
 player=players[0]
 foot=factory.CreatePos(player).GetFootPos()
 dimension=factory.CreateDimension(player).GetEntityDimensionId()
 row.update(foot=foot,dimension=dimension)
 if foot and all(isinstance(value,(int,long,float)) and not isinstance(value,bool) and not math.isnan(value) and not math.isinf(value) for value in foot) and -64<=foot[1]<320:
  reserve=(int(math.floor(foot[0]))+6,int(math.floor(foot[1]))+24,int(math.floor(foot[2]))+6)
  region=[(reserve[0]+x,reserve[1]+y,reserve[2]+z) for x in range(-2,4) for y in range(-2,4) for z in range(-2,4)]
  row['reserve']=reserve
  if all(-64<=pos[1]<320 for pos in region):
   info=factory.CreateBlockInfo(player)
   cells=[{'pos':pos,'front':info.GetBlockNew(pos,dimension),'back':info.GetLiquidBlock(pos,dimension)} for pos in region]
   center=next(cell for cell in cells if tuple(cell['pos'])==reserve)
   row.update(reserve_cells=cells,front=center['front'],back=center['back'])
_result=json.dumps(row)
'''
FEET_SERVER = SERVER.split(' if foot and all(')[0] + '\n_result=json.dumps(row)\n'


def valid_feet(client, server):
    if not isinstance(client, dict) or not isinstance(server, dict):
        return False
    feet = [client.get('foot'), server.get('foot')]
    if any(not isinstance(foot, (list, tuple)) or len(foot) != 3 or any(
            isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            for value in foot) or not -64 <= foot[1] < 320 or abs(foot[0]) > 1000000
            or abs(foot[2]) > 1000000 for foot in feet):
        return False
    if max(abs(a - b) for a, b in zip(*feet)) > 2. or server.get('dimension') != 0:
        return False
    return True


def valid_snapshot(client, server):
    if not valid_feet(client, server):
        return False
    feet = [client.get('foot'), server.get('foot')]
    reserve = server.get('reserve')
    expected = [math.floor(feet[1][0]) + 6, math.floor(feet[1][1]) + 24, math.floor(feet[1][2]) + 6]
    region = [[expected[0] + x, expected[1] + y, expected[2] + z]
              for x in range(-2, 4) for y in range(-2, 4) for z in range(-2, 4)]
    cells = server.get('reserve_cells')
    if (reserve != expected or any(not -64 <= pos[1] < 320 for pos in region)
            or not isinstance(cells, list) or len(cells) != len(region)):
        return False
    for cell, pos in zip(cells, region):
        if not isinstance(cell, dict) or cell.get('pos') != pos:
            return False
        front, back = cell.get('front'), cell.get('back')
        if (not isinstance(front, dict) or front.get('name') != 'minecraft:air'
                or back is not None and (not isinstance(back, dict) or back.get('name') != 'minecraft:air')):
            return False
    center = cells[region.index(expected)]
    return server.get('front') == center['front'] and server.get('back') == center['back']


def actual_world_valid(client, server):
    business = client.get('business', {}) if isinstance(client, dict) else {}
    required = ('owner_present', 'session_present', 'bridge_present', 'session_ready',
                'bridge_session_matches', 'hud_present')
    players = server.get('players') if isinstance(server, dict) else None
    return (valid_feet(client, server) and all(business.get(key) is True for key in required)
            and isinstance(players, list) and len(players) == 1 and client.get('player') == players[0])


def stable_world(previous, current):
    return (all(math.floor(a) == math.floor(b) for a, b in
                zip(previous['server']['foot'], current['server']['foot']))
            and previous['server']['dimension'] == current['server']['dimension']
            and previous['client']['player'] == current['client']['player']
            and all(max(abs(a - b) for a, b in zip(previous[side]['foot'], current[side]['foot'])) <= .05
                    for side in ('client', 'server')))


class JournalResponse:
    def __init__(self, response, row, deadline, save):
        self.response, self.row, self.deadline, self.save = response, row, deadline, save
        self.headers = response.headers

    def __enter__(self):
        self.response.__enter__()
        return self

    def __exit__(self, *args):
        return self.response.__exit__(*args)

    def read(self):
        try:
            raw = self.response.read()
            self.row['response_utf8'] = raw.decode('utf-8', errors='replace')
            self.row['response_sha256'] = hashlib.sha256(raw).hexdigest()
            self.row['finished_at'] = time.time()
            if time.monotonic() >= self.deadline:
                raise TimeoutError('RPC response arrived after the physical readiness deadline')
            return raw
        except (RuntimeError, TimeoutError, ValueError, OSError) as error:
            self.row['error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            self.save()


class JournalOpener:
    """Keep the existing RPC client, with one deadline covering its handshake too."""
    def __init__(self, opener, deadline, journal, save, maximum_rpc_seconds=None):
        self.opener, self.deadline, self.journal, self.save = opener, deadline, journal, save
        self.maximum_rpc_seconds = maximum_rpc_seconds

    def open(self, request, timeout):
        row = {'http_method': request.get_method(), 'started_at': time.time(),
               'request_utf8': request.data.decode('utf-8') if request.data else None}
        self.journal.append(row)
        self.save()
        remaining = self.deadline - time.monotonic()
        row['timeout_seconds'] = min(timeout, max(0., remaining),
                                     self.maximum_rpc_seconds if self.maximum_rpc_seconds is not None else timeout)
        try:
            if remaining <= 0:
                raise TimeoutError('Physical readiness deadline elapsed before RPC dispatch')
            response = self.opener.open(request, timeout=row['timeout_seconds'])
            if time.monotonic() >= self.deadline:
                response.close()
                raise TimeoutError('RPC headers arrived after the physical readiness deadline')
            return JournalResponse(response, row, self.deadline, self.save)
        except (RuntimeError, TimeoutError, ValueError, OSError) as error:
            row.update(error='%s: %s' % (type(error).__name__, error), finished_at=time.time())
            self.save()
            raise


def collect(report, deadline, save):
    actual_world = report.get('actual_world_ready', False)
    client = Client(timeout=min(3. if actual_world else 10., max(.1, report['budget_seconds'])))
    client.opener = JournalOpener(client.opener, deadline, report['rpc_journal'], save,
                                 maximum_rpc_seconds=3. if actual_world else None)
    stable = []
    with client:
        while time.monotonic() < deadline:
            values = [run(client, code, server) for code, server in
                      ((ACTUAL_WORLD_CLIENT if actual_world else CLIENT, False),
                       (FEET_SERVER if actual_world else SERVER, True))]
            row = {'client': values[0], 'server': values[1], 'observed_at': time.time(),
                   'valid': valid_snapshot(*values)}
            accepted = row['valid']
            if actual_world:
                row['actual_world_valid'] = actual_world_valid(*values)
                if not row['actual_world_valid']:
                    stable = []
                elif stable and not stable_world(stable[-1], row):
                    stable = [row]
                else:
                    stable.append(row)
                row['stable_samples'] = len(stable)
                row['stable_elapsed_seconds'] = row['observed_at'] - stable[0]['observed_at'] if stable else 0.
                accepted = len(stable) >= 3 and row['stable_elapsed_seconds'] >= 1.
                if accepted:
                    full = {'server': run(client, SERVER, True),
                            'client': run(client, ACTUAL_WORLD_CLIENT, False), 'observed_at': time.time()}
                    row['reservation_check'] = full
                    accepted = actual_world_valid(full['client'], full['server']) and valid_snapshot(
                        full['client'], full['server']) and stable_world(row, full)
                    row['reservation_check_passed'] = accepted
                    if not accepted:
                        stable = []
            report['snapshots'].append(row)
            save()
            if actual_world and row.get('reservation_check_passed') is False:
                report['error'] = 'Actual world failed its one full reserved-area snapshot after stable UiInit/feet'
                return
            if accepted and time.monotonic() < deadline:
                report['passed'] = True
                report['actual_world_ready_at_unix'] = row['reservation_check']['observed_at'] if actual_world else None
                return
            if report.get('single_snapshot'):
                report['error'] = 'Session failed its one physical readiness snapshot'
                return
            time.sleep(min(.5, max(0., deadline - time.monotonic())))
        report['error'] = 'Physical player/level readiness did not pass within the fixed startup deadline'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--wait', type=float, default=60.)
    parser.add_argument('--retained-session', action='store_true',
                        help='One snapshot with a new sixty-second read-only deadline for an exact retained session')
    parser.add_argument('--single-snapshot', action='store_true', help='Reject a terminal snapshot without polling')
    parser.add_argument('--actual-world-ready', action='store_true',
                        help='Read-only actual UiInit and three stable physical snapshots within exact creation+180')
    args = parser.parse_args()
    if (args.output.exists() or not 0 < args.wait <= (180 if args.actual_world_ready else 60)
            or args.actual_world_ready and (args.retained_session or args.single_snapshot)):
        parser.error('Choose a fresh receipt and finite wait; actual-world-ready cannot use a single or retained snapshot')
    session = load_session(os.environ['MCDEV_SESSION_FILE'], os.environ['MCDEV_OWNER'], live=True)
    game_created = int(session['game_identity']) / 10000000. - 11644473600.
    remaining = game_created + 180. - time.time()
    budget = args.wait if args.retained_session else min(args.wait, max(0., remaining))
    deadline = time.monotonic() + budget
    report = {'schema': 1, 'passed': False, 'completed': False, 'read_only': True,
              'world_write_attempted': False, 'position_write_attempted': False,
              'session_binding': {key: session[key] for key in ('id', 'owner', 'session_file', 'game_pid', 'game_identity')},
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'startup_deadline_unix': game_created + 180., 'budget_seconds': budget,
              'single_snapshot': args.retained_session or args.single_snapshot,
              'actual_world_ready': args.actual_world_ready,
              'stability_requirement': {'samples': 3, 'minimum_elapsed_seconds': 1., 'maximum_foot_delta': .05}
                  if args.actual_world_ready else None,
              'deadline_basis': 'retained-session dispatch' if args.retained_session else 'exact game creation+180',
              'read_only_deadline_unix': time.time() + budget,
              'snapshots': [], 'rpc_journal': []}
    save = lambda: args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save()
    if budget <= 0:
        report.update(completed=True, error='Exact game startup deadline already elapsed')
        save()
        return 1
    try:
        collect(report, deadline, save)
    except (RuntimeError, TimeoutError, ValueError, OSError) as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
    finally:
        report['completed'] = True
        save()
    print(json.dumps({'passed': report['passed'], 'snapshots': len(report['snapshots']), 'budget_seconds': budget}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
