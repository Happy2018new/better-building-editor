"""Probe native water overlays in bounded, isolated subchunk palettes."""
import json
import math
import sys
import time
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry

TICK_SECONDS = .006
TICK_DELAY = .001
LOAD_TIMEOUT_SECONDS = 30.0
STATES_PER_SUBCHUNK = 32
LEVELS_PER_COLUMN = 13
COLUMNS_PER_SIDE = 7
AIR = {'name': 'minecraft:air', 'aux': 0}
WATER = {'name': 'minecraft:water', 'aux': 0}
PROBE_METHOD = ('Dry-verified SetBlockNew+SetBlockStates over water, '
                'isLegacy=True, updateNeighbors=False; v2')


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
        self.blockstate = factory.CreateBlockState(api.GetLevelId())
        self.chunks = factory.CreateChunkSource(api.GetLevelId())
        if self.dimension != 0:
            raise ValueError('Distributed fluid export requires the overworld height range')
        foot = factory.CreatePos(player).GetFootPos()
        self.origin = (int(math.floor(foot[0] / 16.0)) * 16 + 40,
                       int(math.floor(foot[2] / 16.0)) * 16 + 40)
        self.target = self.support = None
        self.cell_index = None
        self.cell_ready = False
        self.waiting_since = None
        self.area_key = 'modern_projection_p0_water_%d' % int(time.time() * 1000)
        self.area_created = False
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
            'target': self.target, 'support': self.support, 'readback_states': {},
            'verified_states': 0, 'state_mismatches': [],
            'states_per_subchunk': STATES_PER_SUBCHUNK,
            'method': PROBE_METHOD,
            'tick_budget_seconds': TICK_SECONDS}
        self.state['blocks'] = self.state['results']
        sys._p0_native_probe = self.state
        try:
            capacity = (COLUMNS_PER_SIDE ** 2 * LEVELS_PER_COLUMN * STATES_PER_SUBCHUNK)
            if self.state['total_states'] > capacity:
                raise ValueError('Native palette exceeds the distributed probe capacity')
            extent = (COLUMNS_PER_SIDE - 1) * 16
            minimum = (self.origin[0] - 80, 0, self.origin[1] - 80)
            maximum = (self.origin[0] + extent + 80, 319, self.origin[1] + extent + 80)
            if not self.chunks.SetAddArea(self.area_key, self.dimension, minimum, maximum):
                raise ValueError('Could not load the distributed native probe area')
            self.area_created = True
            self.state.update(area_key=self.area_key, min_pos=minimum, max_pos=maximum)
            self.game.AddTimer(TICK_DELAY, self.step)
        except Exception as error:
            self.finish(error)
            raise

    def finish(self, error=None):
        self.state.update(running=False, done=True,
                          failure=None if error is None else str(error),
                          elapsed_seconds=time.time() - self.state['start'])
        try:
            self.clear_cell()
        except Exception as cleanup_error:
            self.state['cleanup_failure'] = str(cleanup_error)
        finally:
            if self.area_created:
                try:
                    if not self.chunks.DeleteArea(self.area_key):
                        self.state['cleanup_failure'] = 'Could not release the native probe area'
                except Exception as cleanup_error:
                    self.state['cleanup_failure'] = str(cleanup_error)
                self.area_created = False

    def clear_cell(self):
        if self.cell_ready:
            self.info.SetLiquidBlock(self.target, AIR, self.dimension)
            self.info.SetBlockNew(self.target, AIR, 0, self.dimension, True, False)
            self.info.SetBlockNew(self.support, AIR, 0, self.dimension, True, False)
            self.cell_ready = False

    def select_cell(self):
        index = self.state['tested_states'] // STATES_PER_SUBCHUNK
        if index != self.cell_index:
            self.clear_cell()
            column, level = divmod(index, LEVELS_PER_COLUMN)
            self.target = (self.origin[0] + (column % COLUMNS_PER_SIDE) * 16,
                           113 + level * 16,
                           self.origin[1] + (column // COLUMNS_PER_SIDE) * 16)
            self.support = (self.target[0], self.target[1] - 1, self.target[2])
            self.cell_index = index
            self.waiting_since = time.time()
            self.state.update(target=self.target, support=self.support, subchunk_index=index)
        if self.cell_ready:
            return True
        if not self.chunks.CheckChunkState(self.dimension, self.target):
            if time.time() - self.waiting_since > LOAD_TIMEOUT_SECONDS:
                raise ValueError('Distributed native probe area did not finish loading')
            return False
        for pos in (self.target, self.support):
            block = self.info.GetBlockNew(pos, self.dimension)
            if not block or block.get('name') != 'minecraft:air':
                raise ValueError('Fluid capability export requires empty disposable cells')
        self.cell_ready = True
        if self.info.SetBlockNew(self.support, {'name': 'minecraft:stone', 'aux': 0},
                                 0, self.dimension, True, False) is False:
            raise ValueError('Could not place the disposable native probe support')
        return True

    def step(self):
        if not self.state['running'] or getattr(sys, '_p0_native_probe', None) is not self.state:
            return
        deadline = time.time() + TICK_SECONDS
        try:
            while time.time() < deadline:
                if self.cursor >= len(self.values):
                    if self.name is not None:
                        result = (True if self.values and len(self.accepted) == len(self.values) else
                                  self.accepted if self.accepted else False)
                        self.state['results'][self.name] = result
                        self.state['completed_blocks'] += 1
                    row = next(self.rows, None)
                    if row is None:
                        self.state['progress'] = 1.0
                        error = (ValueError('Native block state readback mismatch: %d states' %
                                            len(self.state['state_mismatches']))
                                 if self.state['state_mismatches'] else None)
                        self.finish(error)
                        return
                    self.name, self.values = row
                    self.cursor, self.accepted = 0, []
                    if not self.values:
                        continue
                aux = self.values[self.cursor]
                self.state.update(current_name=self.name, current_aux=aux)
                if not self.select_cell():
                    self.game.AddTimer(TICK_DELAY, self.step)
                    return
                expected = block_registry.states((self.name, aux))
                native_aux = self.blockstate.GetBlockAuxValueFromStates(self.name.encode('utf8'), expected)
                if native_aux is None or native_aux < 0:
                    raise ValueError('Could not resolve native aux: %s [%d]' % (self.name, aux))
                self.info.SetLiquidBlock(self.target, AIR, self.dimension)
                self.info.SetBlockNew(self.target, AIR, 0, self.dimension, True, False)
                native = {'name': self.name.encode('utf8'), 'aux': native_aux}
                self.info.SetBlockNew(self.target, native, 0, self.dimension, True, False)
                if expected:
                    self.blockstate.SetBlockStates(self.target, expected, self.dimension)
                dry_front = self.info.GetBlockNew(self.target, self.dimension)
                dry_states = self.blockstate.GetBlockStates(self.target, self.dimension)
                if self.name == 'minecraft:air' and dry_states is None:
                    dry_states = {}
                dry_matched = bool(dry_front and dry_front.get('name') == self.name and
                                   dry_states == expected)
                if dry_matched:
                    self.state['verified_states'] += 1
                else:
                    self.state['state_mismatches'].append({
                        'name': self.name, 'aux': aux, 'native_aux': native_aux,
                        'expected': expected, 'actual': dry_states, 'front': dry_front})
                self.info.SetLiquidBlock(self.target, AIR, self.dimension)
                self.info.SetBlockNew(self.target, AIR, 0, self.dimension, True, False)
                self.info.SetBlockNew(self.target, WATER, 0, self.dimension, True, False)
                self.info.SetBlockNew(self.target, native, 0, self.dimension, True, False)
                placed = self.info.GetBlockNew(self.target, self.dimension)
                if expected and placed and placed.get('name') == self.name:
                    self.blockstate.SetBlockStates(self.target, expected, self.dimension)
                front = self.info.GetBlockNew(self.target, self.dimension)
                liquid = self.info.GetLiquidBlock(self.target, self.dimension)
                actual = self.blockstate.GetBlockStates(self.target, self.dimension)
                self.state['readback_states'].setdefault(self.name, {})[str(aux)] = {
                    'native_aux': native_aux, 'dry': {'front': dry_front, 'states': dry_states},
                    'wet': {'front': front, 'states': actual}, 'liquid': liquid}
                matched = bool(front and front.get('name') == self.name and actual == expected)
                if (dry_matched and matched and liquid and
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
