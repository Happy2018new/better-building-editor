"""Read every measured snow-coverable plant across native snow heights 1..8."""
import json
import math
import sys
import traceback
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry as registry
from modern_projection.projection.block_traits_data import SNOW_COVERABLE_BLOCKS
from modern_projection.projection.cell import AIR, background, foreground
from modern_projection.server_system import WorldAdapter


class SnowStateProbe(object):
    def __init__(self):
        previous = getattr(sys, '_p0_snow_states', None)
        if previous and previous['running']:
            raise ValueError('A snow-state probe is already running')
        self.factory = api.GetEngineCompFactory()
        self.player = api.GetPlayerList()[0]
        self.adapter = WorldAdapter(self.player)
        self.info = self.factory.CreateBlockInfo(self.player)
        self.game = self.factory.CreateGame(api.GetLevelId())
        self.dimension = self.adapter.dimension
        foot = self.factory.CreatePos(self.player).GetFootPos()
        self.target = (int(math.floor(foot[0])) + 12,
                       max(16, int(math.floor(foot[1])) + 8), int(math.floor(foot[2])) + 4)
        self.support = (self.target[0], self.target[1] - 1, self.target[2])
        self.biome = self.factory.CreateBiome(self.player)
        self.previous_biome = self.biome.GetBiomeName(self.target)
        if not self.previous_biome:
            raise ValueError('Snow fixture biome could not be read before mutation')
        for pos in (self.target, self.support):
            if self.adapter.read(pos) != AIR:
                raise ValueError('Snow state fixture requires empty protected cells')
        self.queue = iter(((name, aux), height)
                          for name in sorted(SNOW_COVERABLE_BLOCKS)
                          for aux in registry.aux_values(name) for height in range(1, 9))
        self.state = {'schema': 1, 'game_version': registry.source_version(),
                      'palette_sha256': registry.fingerprint(),
                      'method': 'supported native dry palette in verified cold biome then SetSnowBlock heights 1..8; v4',
                      'biome_before': self.previous_biome, 'biome_fixture': 'minecraft:ice_plains',
                      'supports': {'minecraft:brown_mushroom': 'minecraft:podzol',
                                   'minecraft:red_mushroom': 'minecraft:podzol',
                                   'default': 'minecraft:dirt'},
                      'delayed_seconds': .25, 'target': self.target,
                      'names': sorted(SNOW_COVERABLE_BLOCKS), 'rows': [],
                      'running': True, 'done': False, 'failure': None, 'active': None}
        sys._p0_snow_states = self.state
        if not self.biome.SetBiomeByPos(self.target, 'minecraft:ice_plains', self.dimension):
            self.finish(ValueError('Could not set cold snow fixture biome'))
            return
        self.state['biome_measured'] = self.biome.GetBiomeName(self.target)
        if self.state['biome_measured'] != 'ice_plains':
            self.finish(ValueError('Cold snow fixture biome did not apply'))
            return
        self.adapter.write(self.support, ('minecraft:dirt', registry.DEFAULT_AUX['minecraft:dirt']))
        self.next_case()

    def read(self):
        value = self.adapter.read(self.target)
        if value is None:
            raise ValueError('Snow state fixture palette is not loaded')
        front, back = foreground(value), background(value)
        return {'front': list(front), 'states': registry.states(front),
                'back': list(back), 'back_states': registry.states(back)}

    def next_case(self):
        try:
            case = next(self.queue, None)
            if case is None:
                self.finish()
                return
            value, height = case
            self.state['active'] = {'name': value[0], 'aux': value[1], 'height': height}
            self.adapter.write(self.target, AIR)
            # Podzol permits mushrooms in daylight. Otherwise the survival
            # tick destroys the dry fixture instead of testing snow layers.
            support = self.state['supports'].get(value[0], self.state['supports']['default'])
            self.adapter.write(self.support, (support, registry.DEFAULT_AUX[support]))
            self.adapter.write(self.target, value)
            dry = self.read()
            if dry['front'] != list(value) or dry['states'] != registry.states(value):
                raise ValueError('Invalid dry snow seed: %r' % (value,))
            result = self.info.SetSnowBlock(self.target, self.dimension, height)
            self.active = {'name': value[0], 'aux': value[1], 'height': height,
                           'dry': dry, 'set_snow': result, 'immediate': self.read()}
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
            self.game.AddTimer(.01, self.next_case)
        except Exception as error:
            traceback.print_exc()
            self.finish(error)

    def finish(self, error=None):
        self.state.update(running=False, done=False, failure=None if error is None else repr(error))
        try:
            for pos in (self.target, self.support):
                self.adapter.write(pos, AIR)
            if not self.biome.SetBiomeByPos(self.target, self.previous_biome, self.dimension):
                raise ValueError('Could not restore snow fixture biome')
            self.game.AddTimer(.5, self.cleaned)
        except Exception as cleanup_error:
            traceback.print_exc()
            self.state.update(done=True, restored=False, cleanup_failure=repr(cleanup_error))

    def cleaned(self):
        try:
            residue = []
            for pos in (self.target, self.support):
                if self.adapter.read(pos) != AIR:
                    residue.append(list(pos))
            biome_after = self.biome.GetBiomeName(self.target)
            self.state.update(done=True, restored=not residue and biome_after == self.previous_biome,
                              cleanup_residue=residue, biome_after=biome_after)
        except Exception as error:
            traceback.print_exc()
            self.state.update(done=True, restored=False, cleanup_failure=repr(error))


_probe = SnowStateProbe()
_result = json.dumps({'started': True, 'target': _probe.target})
