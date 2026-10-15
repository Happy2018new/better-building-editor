"""Two near-player server actors, with retained destruction and absence evidence."""
import json
import sys
import mod.server.extraServerApi as api

KEY = '_banner_scale_server_r21'
factory = api.GetEngineCompFactory()
owner = api.GetSystem('ModernProjection', 'ModernProjectionServerSystem')
players = api.GetPlayerList()
assert len(players) == 1
player = players[0]


def observe(actors):
    return dict((label, {'entity': actor,
        'engine_type': factory.CreateEngineType(actor).GetEngineTypeStr(),
        'position': factory.CreatePos(actor).GetPos()}) for label, actor in actors.items())


if ACTION == 'journal':
    assert not hasattr(sys, KEY)
    foot = factory.CreatePos(player).GetFootPos()
    dimension = factory.CreateDimension(player).GetEntityDimensionId()
    assert foot is not None and dimension == 0
    saved = {'phase': PHASE, 'actors': {}, 'history': {}, 'requests': {},
             'foot': foot, 'dimension': dimension, 'destroy_requests': []}
    setattr(sys, KEY, saved)
    for index, label in enumerate(LABELS):
        position = (foot[0] + 16. + index * 2., foot[1] + 2., foot[2] + 4.)
        saved['requests'][label] = position
        actor = owner.CreateEngineEntityByTypeStr('modern_projection:anchor', position,
                                                (0., 0.), dimension, True, False)
        assert actor, 'Retain journal; actor creation failed'
        saved['actors'][label] = actor
        saved['history'][label] = actor
    _result = json.dumps(dict(saved, journaled=True, observations=observe(saved['history'])))
else:
    saved = getattr(sys, KEY, None)
    if saved is None:
        assert ACTION in ('inspect', 'absent', 'restore')
        rows = observe(ACTORS)
        absent = bool(rows) and all(row['engine_type'] is None and row['position'] is None
                                   for row in rows.values())
        _result = json.dumps({'journal_present': False, 'actors': rows,
                              'actors_absent': absent, 'already_restored': absent})
    else:
        assert saved['phase'] == PHASE
        if ACTION == 'restore':
            for label, actor in list(saved['actors'].items()):
                assert owner.DestroyEntity(actor), 'Retain actor journal for cleanup'
                saved['destroy_requests'].append(actor)
                del saved['actors'][label]
            _result = json.dumps({'destroy_requested': True,
                'actual_actor_absence_verified': False, 'journal_retained': True,
                'phase': PHASE, 'destroy_requests': saved['destroy_requests']})
        elif ACTION in ('inspect', 'absent'):
            rows = observe(saved['history'])
            absent = bool(rows) and all(row['engine_type'] is None and row['position'] is None
                                       for row in rows.values())
            _result = json.dumps({'journal_present_before': True, 'phase': PHASE,
                'actors': rows, 'actors_absent': absent, 'requests': saved['requests'],
                'foot_before': saved['foot'], 'foot_after': factory.CreatePos(player).GetFootPos(),
                'journal_removed': ACTION == 'absent' and absent and not saved['actors']})
            if ACTION == 'absent' and absent and not saved['actors']:
                delattr(sys, KEY)
        else:
            raise ValueError(ACTION)
