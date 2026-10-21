"""Explicit two-phase normal workspace cleanup; final readback is read-only."""
import time
import scene_game as game


def restore_scene(client, run, blueprints):
    result = {'restored': False, 'restore_unknown': True, 'actions': []}
    def call(code):
        return run(client, game.PREFIX + code)
    result['before'] = call(game.RESTORED)
    deadline = time.monotonic() + 15.
    while result['before']['navigator_transitioning']:
        if time.monotonic() >= deadline:
            raise RuntimeError('Workspace transition did not settle before restoration')
        time.sleep(.1)
        result['before'] = call(game.RESTORED)
    result['actions'].append({'close': call(game.CLOSE)})
    while True:
        closed = call(game.CLOSED)
        if closed['closed']:
            break
        if time.monotonic() >= deadline:
            raise RuntimeError('Ordinary workspace close did not settle')
        time.sleep(.1)
    if result['before']['blueprint_marker']:
        result['actions'].append({'blueprint_restore': call(blueprints.RESTORE)})
    if result['before']['own_marker']:
        result['actions'].append({'own_restore': call(game.RESTORE_OWN)})
    result['after'] = call(game.RESTORED)
    after = result['after']
    result['restored'] = bool(after['restored'] and not any(after[key] for key in
        ('busy', 'edit_job', 'io_job', 'projection_active', 'world_actors', 'preparing_entity')))
    result['restore_unknown'] = False
    assert result['restored'], after
    return result
