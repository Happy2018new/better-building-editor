"""Bounded read-only world/player load gate for the protected single-door probe."""
import math
import time

RUNTIME = '1.21.120.0'
DIMENSION = 0
MIN_Y, MAX_Y = -64, 320
HORIZONTAL_SCOPE = 128
LOAD_SECONDS = 30
POLL_SECONDS = .25
FOOT_TOLERANCE = .01

SERVER_READ = '''import json,sys
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
players=api.GetPlayerList()
raw={'runtime':api.GetMinecraftVersion(),'level':level,'players':players,
 'marker_present':hasattr(sys,%r),'player':None,'dimension':None,'foot':None}
if len(players)==1:
 player=players[0]
 raw.update(player=player,dimension=factory.CreateDimension(player).GetEntityDimensionId(),
  foot=factory.CreatePos(player).GetFootPos())
'''

READ_ANCHOR = SERVER_READ + "_result=json.dumps(raw)\n"

READ_CHUNKS = SERVER_READ + '''import math
expected=%r
reserved=%r
raw['chunks']=[]
raw['same_anchor']=False
foot=raw['foot']
if (raw['runtime']==expected['runtime'] and raw['level']==expected['level'] and
 raw['players']==[expected['player']] and type(raw['dimension']) is int and
 raw['dimension']==0 and not raw['marker_present'] and
 isinstance(foot,(tuple,list)) and len(foot)==3 and
 all(type(v) in (int,float) and not math.isnan(v) and not math.isinf(v) for v in foot) and
 all(abs(foot[i]-expected['foot'][i])<.01 for i in range(3)) and
 tuple(int(math.floor(foot[i]))+(4,12,4)[i] for i in range(3))==tuple(expected['origin']) and
 all(-128<=foot[i]<128 for i in (0,2)) and -64<=foot[1]<320 and
 all(-64<=pos[1]<320 and all(-128<=pos[i]<128 for i in (0,2)) for pos in reserved)):
 raw['same_anchor']=True
 chunk=factory.CreateChunkSource(level)
 positions={}
 for pos in reserved:
  key=(pos[0]>>4,pos[2]>>4)
  if key not in positions:positions[key]=tuple(pos)
 for key in sorted(positions):
  pos=positions[key]
  raw['chunks'].append({'chunk':key,'pos':pos,'loaded':chunk.CheckChunkState(0,pos)})
 raw['foot_after_chunks']=factory.CreatePos(expected['player']).GetFootPos()
_result=json.dumps(raw)
'''


class LoadPreflightError(RuntimeError):
    pass


def anchor_status(raw, fixture):
    """Keep raw readings intact and derive fixture positions only after bounds checks."""
    if raw.get('marker_present') is not False:
        return 'prior_fixture_unresolved', None
    if raw.get('runtime') != RUNTIME:
        return 'unsupported_runtime', None
    if raw.get('level') is None:
        return 'world_not_loaded', None
    players = raw.get('players')
    if not isinstance(players, (list, tuple)) or not players:
        return 'player_not_loaded', None
    if len(players) != 1 or raw.get('player') != players[0]:
        return 'single_player_binding_invalid', None
    if raw.get('dimension') is None:
        return 'dimension_not_loaded', None
    if type(raw['dimension']) is not int or raw['dimension'] != DIMENSION:
        return 'unsupported_dimension', None
    foot = raw.get('foot')
    if not isinstance(foot, (list, tuple)) or len(foot) != 3 or any(
            type(value) not in (int, float) or not math.isfinite(value) for value in foot):
        return 'foot_unavailable_or_nonfinite', None
    if not MIN_Y <= foot[1] < MAX_Y or any(not -HORIZONTAL_SCOPE <= foot[i] < HORIZONTAL_SCOPE
                                           for i in (0, 2)):
        return 'foot_outside_fixed_scope', None
    origin = tuple(math.floor(foot[i]) + (4, 12, 4)[i] for i in range(3))
    rows, support, reserved = fixture(origin)
    if any(not MIN_Y <= pos[1] < MAX_Y or any(not -HORIZONTAL_SCOPE <= pos[i] < HORIZONTAL_SCOPE
                                              for i in (0, 2)) for pos in reserved):
        return 'fixture_outside_fixed_scope', None
    anchor = {key: raw[key] for key in ('runtime', 'level', 'player', 'dimension', 'foot')}
    anchor.update(origin=origin, rows=rows, support=support, reserved=reserved)
    return 'in_bounds', anchor


def same_anchor(first, second):
    return all(first[key] == second[key] for key in ('runtime', 'level', 'player', 'dimension', 'origin')) and all(
        abs(first['foot'][i] - second['foot'][i]) < FOOT_TOLERANCE for i in range(3))


def chunks_status(raw, anchor):
    if raw.get('same_anchor') is not True:
        return 'anchor_changed_before_chunk_read'
    foot = raw.get('foot_after_chunks')
    if not isinstance(foot, (tuple, list)) or len(foot) != 3 or any(
            type(value) not in (int, float) or not math.isfinite(value) or
            abs(value - anchor['foot'][index]) >= FOOT_TOLERANCE for index, value in enumerate(foot)):
        return 'anchor_changed_during_chunk_read'
    if tuple(math.floor(foot[i]) + (4, 12, 4)[i] for i in range(3)) != anchor['origin']:
        return 'anchor_changed_during_chunk_read'
    expected = {(pos[0] >> 4, pos[2] >> 4) for pos in anchor['reserved']}
    chunks = raw.get('chunks')
    if not isinstance(chunks, list) or len(chunks) != len(expected) or any(
            not isinstance(row, dict) or tuple(row.get('chunk', ())) not in expected or
            tuple(row.get('pos', ())) not in anchor['reserved'] or 'loaded' not in row for row in chunks) or {
                tuple(row['chunk']) for row in chunks} != expected:
        return 'chunk_read_incomplete'
    return 'chunks_loaded' if all(row['loaded'] is True for row in chunks) else 'chunks_not_loaded'


def wait_for_load(read, fixture, marker, receipt, deadline, progress=None):
    """read(code, deadline) must bind every network operation to the supplied deadline."""
    receipt.update(ready=False, classification='world_player_not_loaded', attempts=[],
                   dimension=DIMENSION, y_bounds=[MIN_Y, MAX_Y],
                   horizontal_fixture_scope=[-HORIZONTAL_SCOPE, HORIZONTAL_SCOPE],
                   required_stable_samples=2, mutation_attempted=False)
    previous = None
    player = None
    world = None
    started = time.monotonic()
    try:
        while time.monotonic() < deadline:
            attempt = {'started_seconds': time.monotonic() - started}
            receipt['attempts'].append(attempt)
            raw = read(READ_ANCHOR % marker, deadline)
            attempt['raw_anchor'] = raw
            status, anchor = anchor_status(raw, fixture)
            attempt['status'] = status
            if progress is not None:
                progress()
            if time.monotonic() >= deadline:
                break
            if status in ('prior_fixture_unresolved', 'unsupported_runtime',
                          'single_player_binding_invalid', 'unsupported_dimension'):
                receipt['classification'] = status
                raise LoadPreflightError(status)
            if raw.get('player') is not None:
                if player is not None and raw['player'] != player:
                    receipt['classification'] = 'player_binding_changed'
                    raise LoadPreflightError('player_binding_changed')
                player = raw['player']
            if raw.get('level') is not None:
                if world is not None and raw['level'] != world:
                    receipt['classification'] = 'world_binding_changed'
                    raise LoadPreflightError('world_binding_changed')
                world = raw['level']
            if anchor is not None:
                attempt['raw_chunks'] = read(READ_CHUNKS % (marker, anchor, anchor['reserved']), deadline)
                attempt['status'] = chunks_status(attempt['raw_chunks'], anchor)
                if progress is not None:
                    progress()
                if time.monotonic() >= deadline:
                    break
                if attempt['status'] == 'chunks_loaded':
                    if previous is not None and same_anchor(previous, anchor):
                        receipt.update(ready=True, classification='loaded_stable_anchor', anchor=anchor)
                        return anchor
                    previous = anchor
                else:
                    previous = None
            else:
                previous = None
            time.sleep(min(POLL_SECONDS, max(0, deadline - time.monotonic())))
        raise LoadPreflightError('world_player_not_loaded_before_deadline')
    except Exception as error:
        receipt['error'] = '%s: %s' % (type(error).__name__, error)
        native_error = getattr(error, 'error', None)
        if isinstance(native_error, dict):
            receipt['native_error'] = native_error
        raise
    finally:
        receipt['elapsed_seconds'] = time.monotonic() - started
        if progress is not None:
            progress()
