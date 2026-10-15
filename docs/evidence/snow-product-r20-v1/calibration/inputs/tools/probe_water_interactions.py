"""Read native item-use water interactions in an owned, disposable test cell.

Unlike the all-state static probe, this never resets states after using water.
Each case has an isolated basin and records immediate and delayed readbacks.
API item use does not trigger player events; this tests engine item behavior,
not screen input or permission handling.
"""
import json
import math
import sys
import time
import traceback
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry as registry
from modern_projection.projection.block_traits import is_waterloggable
from modern_projection.server_system import WorldAdapter

NAMES = ('oak_fence', 'oak_stairs', 'oak_slab', 'rail', 'white_carpet', 'web',
         'sea_pickle', 'candle', 'white_candle', 'candle_cake', 'white_candle_cake',
         'campfire', 'soul_campfire', 'cactus', 'cocoa', 'leaf_litter', 'pink_petals',
         'snow_layer', 'wildflowers', 'hanging_roots', 'kelp', 'seagrass')
AIR = {'name': 'minecraft:air', 'aux': 0}
STONE = {'name': 'minecraft:stone', 'aux': 0}
SOURCE = {'name': 'minecraft:water', 'aux': 0}
PROFILE = getattr(sys, '_p0_water_profile_mode', 'smoke')
STABILITY_NAMES = ('cocoa', 'leaf_litter', 'pink_petals', 'snow_layer', 'wildflowers',
                   'hanging_roots', 'cactus')


class WaterInteractionProbe(object):
    def __init__(self):
        previous = getattr(sys, '_p0_water_interactions', None)
        if previous and previous['running']:
            raise ValueError('A water interaction probe is already running')
        self.factory = api.GetEngineCompFactory()
        self.player = api.GetPlayerList()[0]
        self.dimension = self.factory.CreateDimension(self.player).GetEntityDimensionId()
        self.info = self.factory.CreateBlockInfo(self.player)
        self.blockstate = self.factory.CreateBlockState(api.GetLevelId())
        self.game = self.factory.CreateGame(api.GetLevelId())
        self.adapter = WorldAdapter(self.player)
        foot = self.factory.CreatePos(self.player).GetFootPos()
        self.target = (int(math.floor(foot[0])) + 12,
                       int(math.floor(foot[1])) + 8, int(math.floor(foot[2])) + 4)
        self.support = (self.target[0], self.target[1] - 1, self.target[2])
        self.cells = tuple((self.target[0] + x, self.target[1] + y, self.target[2] + z)
                           for x in range(-2, 3) for y in range(-1, 3)
                           for z in range(-2, 3))
        for pos in self.cells:
            front = self.info.GetBlockNew(pos, self.dimension)
            if not front or front['name'] != 'minecraft:air':
                raise ValueError('Water interaction fixture requires an empty test basin')
        self.queue = iter(self.cases())
        self.active = None
        self.state = {'schema': 1, 'game_version': registry.source_version(),
                      'palette_sha256': registry.fingerprint(),
                      'method': 'UseItemToPos on basin support; no post-use SetBlockStates; v2',
                      'source_scope': 'engine item use, not player events',
                      'delayed_seconds': 2. if PROFILE == 'flow_spread' else .6,
                      'profile': PROFILE, 'target': self.target,
                      'running': True, 'done': False, 'failure': None, 'rows': [], 'active': None}
        sys._p0_water_interactions = self.state
        self.next_case()

    def cases(self):
        if PROFILE == 'source_stability_states':
            for short in STABILITY_NAMES:
                name = 'minecraft:' + short
                for aux in registry.aux_values(name):
                    yield (name, aux), 'add_source'
            return
        if PROFILE == 'extinguish_states':
            for name in sorted(registry.BLOCKS):
                if not name.startswith('minecraft:'):
                    continue
                for aux in registry.aux_values(name):
                    value = (name, aux)
                    properties = registry.states(value)
                    if ('lit' in properties or 'extinguished' in properties) and is_waterloggable(value):
                        yield value, 'add_source'
            return
        for short in NAMES:
            name = 'minecraft:' + short
            if name not in registry.DEFAULT_AUX:
                continue
            default = (name, registry.DEFAULT_AUX[name])
            if PROFILE == 'flow_spread':
                yield default, 'flow_spread'
                continue
            properties = registry.states(default)
            variants = [default]
            if 'lit' in properties:
                properties['lit'] = True
                variants.append(registry.from_states(name, properties))
            elif 'extinguished' in properties:
                properties['extinguished'] = False
                variants = [registry.from_states(name, properties)]
            for value in variants:
                yield value, 'add_source'
            yield default, 'place_in_source'
            yield default, 'place_in_flowing'

    def set_block(self, pos, value):
        name, aux = value
        properties = registry.states(value)
        native_aux = self.blockstate.GetBlockAuxValueFromStates(name.encode('utf8'), properties)
        if native_aux is None or native_aux < 0:
            raise ValueError('No native seed for ' + name)
        self.info.SetBlockNew(pos, {'name': name.encode('utf8'), 'aux': native_aux},
                              0, self.dimension, True, False)
        if properties and not self.blockstate.SetBlockStates(pos, properties, self.dimension):
            raise ValueError('Could not seed semantic states for ' + name)

    def read(self):
        return {'front': self.info.GetBlockNew(self.target, self.dimension),
                'states': self.blockstate.GetBlockStates(self.target, self.dimension),
                'liquid': self.info.GetLiquidBlock(self.target, self.dimension)}

    def clear(self):
        for pos in self.cells:
            front = self.info.GetBlockNew(pos, self.dimension)
            liquid = self.info.GetLiquidBlock(pos, self.dimension)
            if (front and front['name'] == 'minecraft:air' and
                    (not liquid or liquid.get('name') == 'minecraft:air')):
                continue
            self.adapter.write(pos, ('minecraft:air', 0))

    def basin(self, value):
        for pos in self.cells:
            x, y, z = tuple(pos[i] - self.target[i] for i in range(3))
            if y == -1 or (abs(x) == 2 or abs(z) == 2):
                self.info.SetBlockNew(pos, STONE, 0, self.dimension, True, False)
        support = 'sand' if value[0] == 'minecraft:cactus' else 'dirt'
        self.set_block(self.support, ('minecraft:' + support, registry.DEFAULT_AUX['minecraft:' + support]))
        if value[0] == 'minecraft:cocoa':
            # Give every horizontal state its required jungle-log support.
            # A single west support invalidated other directions before water.
            for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                self.set_block((self.target[0] + dx, self.target[1], self.target[2] + dz),
                               ('minecraft:jungle_log', registry.DEFAULT_AUX['minecraft:jungle_log']))
        if value[0] == 'minecraft:hanging_roots':
            self.info.SetBlockNew((self.target[0], self.target[1] + 1, self.target[2]),
                                  STONE, 0, self.dimension, True, False)

    def next_case(self):
        try:
            case = next(self.queue, None)
            if case is None:
                self.finish()
                return
            value, action = case
            self.state['active'] = {'name': value[0], 'aux': value[1], 'action': action,
                                    'phase': 'prepare'}
            self.clear()
            self.basin(value)
            if action in ('add_source', 'flow_spread'):
                self.set_block(self.target, value)
            else:
                liquid = dict(SOURCE, aux=0 if action == 'place_in_source' else 3)
                self.info.SetBlockNew(self.target, liquid, 0, self.dimension, True, False)
            before = self.read()
            dry_valid = before['front']['name'] == value[0] and before['states'] == registry.states(value)
            item = 'minecraft:water_bucket' if action in ('add_source', 'flow_spread') else value[0]
            self.state['active']['phase'] = 'item_use'
            clicked = self.support
            if action == 'flow_spread':
                clicked = (self.target[0] + 1, self.target[1] - 1, self.target[2])
            result = self.game.UseItemToPos({'newItemName': item.encode('utf8'),
                                            'newAuxValue': 0, 'count': 1},
                                           self.dimension, clicked, api.GetMinecraftEnum().Facing.Up)
            self.active = {'name': value[0], 'aux': value[1], 'action': action,
                           'expected_seed': registry.states(value), 'dry_valid': dry_valid,
                           'item': item, 'item_result': result, 'before': before,
                           'immediate': self.read()}
            self.state['active']['phase'] = 'delay'
            self.game.AddTimer(self.state['delayed_seconds'], self.delayed)
        except Exception as error:
            traceback.print_exc()
            self.finish(error)

    def delayed(self):
        try:
            self.active['delayed'] = self.read()
            self.state['rows'].append(self.active)
            self.active = None
            self.state['active'] = None
            self.game.AddTimer(.1, self.next_case)
        except Exception as error:
            traceback.print_exc()
            self.finish(error)

    def finish(self, error=None):
        self.state.update(running=False, done=False,
                          failure=None if error is None else repr(error))
        try:
            self.clear()
            self.game.AddTimer(1., self.cleaned)
        except Exception as cleanup_error:
            traceback.print_exc()
            self.state.update(done=True, restored=False,
                              cleanup_failure=repr(cleanup_error))

    def cleaned(self):
        try:
            self.clear()
            residue = []
            for pos in self.cells:
                front = self.info.GetBlockNew(pos, self.dimension)
                liquid = self.info.GetLiquidBlock(pos, self.dimension)
                if (not front or front['name'] != 'minecraft:air' or
                        liquid and liquid.get('name') != 'minecraft:air'):
                    residue.append({'pos': pos, 'front': front, 'liquid': liquid})
            self.state.update(done=True, restored=not residue, cleanup_residue=residue)
        except Exception as error:
            traceback.print_exc()
            self.state.update(done=True, restored=False, cleanup_failure=repr(error))


_probe = WaterInteractionProbe()
_result = json.dumps({'started': True, 'target': _probe.target})
