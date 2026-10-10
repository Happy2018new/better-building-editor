"""Start a tick-budgeted native water overlay probe in one disposable cell."""
import json
import math
import sys
import time
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry

TICK_SECONDS = .006
TICK_DELAY = .001
AIR = {'name': 'minecraft:air', 'aux': 0}
WATER = {'name': 'minecraft:water', 'aux': 0}


class WaterOverlayProbe(object):
    def __init__(self):
        previous = getattr(sys, '_p0_native_probe', None)
        if previous is not None and previous.get('running'):
            raise ValueError('A native capability probe is already running')
        factory = api.GetEngineCompFactory()
        player = api.GetPlayerList()[0]
        self.dimension = factory.CreateDimension(player).GetEntityDimensionId()
        self.info = factory.CreateBlockInfo(player)
        self.game = factory.CreateGame(api.GetLevelId())
        foot = factory.CreatePos(player).GetFootPos()
        self.target = (int(math.floor(foot[0])) + 24, int(math.floor(foot[1])) + 10,
                       int(math.floor(foot[2])) - 5)
        self.support = (self.target[0], self.target[1] - 1, self.target[2])
        for pos in (self.target, self.support):
            block = self.info.GetBlockNew(pos, self.dimension)
            if not block or block.get('name') != 'minecraft:air':
                raise ValueError('Fluid capability export requires an empty loaded area')
        names = sorted(name for name in block_registry.BLOCKS if name.startswith('minecraft:'))
        self.rows = iter((name, block_registry.aux_values(name)) for name in names)
        self.name = None
        self.values = ()
        self.cursor = 0
        self.accepted = []
        self.state = {
            'schema': 1, 'game_version': block_registry.source_version(),
            'palette_sha256': block_registry.fingerprint(), 'blocks': {},
            'start': time.time(), 'progress': 0.0, 'results': {}, 'failure': None,
            'running': True, 'done': False, 'tested_states': 0,
            'total_states': sum(len(block_registry.aux_values(name)) for name in names),
            'completed_blocks': 0, 'total_blocks': len(names),
            'target': self.target, 'support': self.support,
            'method': 'SetBlockNew over water, isLegacy=True, updateNeighbors=False',
            'tick_budget_seconds': TICK_SECONDS}
        self.state['blocks'] = self.state['results']
        sys._p0_native_probe = self.state
        try:
            self.info.SetBlockNew(self.support, {'name': 'minecraft:stone', 'aux': 0},
                                  0, self.dimension, True, False)
            self.game.AddTimer(TICK_DELAY, self.step)
        except Exception as error:
            self.finish(error)
            raise

    def finish(self, error=None):
        self.state.update(running=False, done=True,
                          failure=None if error is None else str(error),
                          elapsed_seconds=time.time() - self.state['start'])
        try:
            self.info.SetLiquidBlock(self.target, AIR, self.dimension)
            self.info.SetBlockNew(self.target, AIR, 0, self.dimension, True, False)
            self.info.SetBlockNew(self.support, AIR, 0, self.dimension, True, False)
        except Exception as cleanup_error:
            self.state['cleanup_failure'] = str(cleanup_error)

    def step(self):
        if not self.state['running'] or getattr(sys, '_p0_native_probe', None) is not self.state:
            return
        deadline = time.time() + TICK_SECONDS
        try:
            while time.time() < deadline:
                if self.cursor >= len(self.values):
                    if self.name is not None:
                        result = (True if len(self.accepted) == len(self.values) else
                                  self.accepted if self.accepted else False)
                        self.state['results'][self.name] = result
                        self.state['completed_blocks'] += 1
                    row = next(self.rows, None)
                    if row is None:
                        self.state['progress'] = 1.0
                        self.finish()
                        return
                    self.name, self.values = row
                    self.cursor, self.accepted = 0, []
                aux = self.values[self.cursor]
                self.state.update(current_name=self.name, current_aux=aux)
                self.info.SetLiquidBlock(self.target, AIR, self.dimension)
                self.info.SetBlockNew(self.target, AIR, 0, self.dimension, True, False)
                self.info.SetBlockNew(self.target, WATER, 0, self.dimension, True, False)
                self.info.SetBlockNew(self.target, {'name': self.name.encode('utf8'), 'aux': aux},
                                      0, self.dimension, True, False)
                front = self.info.GetBlockNew(self.target, self.dimension)
                liquid = self.info.GetLiquidBlock(self.target, self.dimension)
                if (front and front.get('name') == self.name and liquid and
                        liquid.get('name') == 'minecraft:water' and
                        self.name not in ('minecraft:water', 'minecraft:flowing_water', 'minecraft:air')):
                    self.accepted.append(aux)
                self.cursor += 1
                self.state['tested_states'] += 1
                self.state['progress'] = (float(self.state['tested_states']) /
                                          max(1, self.state['total_states']))
            self.state['elapsed_seconds'] = time.time() - self.state['start']
            self.game.AddTimer(TICK_DELAY, self.step)
        except Exception as error:
            self.finish(error)


_probe = WaterOverlayProbe()
_result = json.dumps({'started': True, 'total_states': _probe.state['total_states'],
                      'target': _probe.target, 'support': _probe.support})
