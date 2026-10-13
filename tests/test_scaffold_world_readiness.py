"""Native IPC, loading placeholders, and fresh PNGs cannot admit a fixture."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import scaffold_diagnostic_world as world


class ScaffoldWorldReadinessTests(unittest.TestCase):
    def observation(self):
        client = {'runtime': world.RUNTIME, 'player': 'player', 'foot': [.5, -60., .5],
                  'ui_initialized': True, 'render_ticks': 2}
        server = {'runtime': world.RUNTIME, 'player': 'player', 'foot': [.5, -60., .5], 'dimension': 0,
                  'ground': {'front': {'name': 'minecraft:grass_block', 'aux': 0}, 'states': {}},
                  'reserve': [{'offset': offset, 'front': {'name': 'minecraft:air', 'aux': 0},
                               'states': {}, 'liquid': None} for offset in world.OFFSETS]}
        return client, server

    def test_loading_height_sentinel_and_ipc_only_state_are_rejected(self):
        client, server = self.observation()
        self.assertTrue(world.ready(client, server))
        for mutation in ('loading_height', 'no_ui', 'one_tick', 'unloaded_ground', 'another_player', 'version',
                         'wet_reserve', 'missing_native_states', 'unequal_feet', 'bool_ground_aux', 'bool_air_aux'):
            changed_client, changed_server = copy.deepcopy(client), copy.deepcopy(server)
            if mutation == 'loading_height':
                changed_client['foot'][1] = changed_server['foot'][1] = 32769.62109375
            elif mutation == 'no_ui':
                changed_client['ui_initialized'] = False
            elif mutation == 'one_tick':
                changed_client['render_ticks'] = 1
            elif mutation == 'unloaded_ground':
                changed_server['ground']['states'] = None
            elif mutation == 'another_player':
                changed_server['player'] = 'another'
            elif mutation == 'version':
                changed_server['runtime'] = 'next'
            elif mutation == 'wet_reserve':
                changed_server['reserve'][0]['liquid'] = {'name': 'minecraft:water', 'aux': 0}
            elif mutation == 'missing_native_states':
                changed_server['reserve'][0]['states'] = None
            elif mutation == 'unequal_feet':
                changed_client['foot'][1] += 1
            elif mutation == 'bool_ground_aux':
                changed_server['ground']['front']['aux'] = False
            else:
                changed_server['reserve'][0]['front']['aux'] = False
            with self.subTest(mutation=mutation):
                self.assertFalse(world.ready(changed_client, changed_server))

    def test_ui_listener_requires_actual_event_and_cleans_up_both_listeners(self):
        listeners, removed = [], []
        class ClientSystem:
            def __init__(self, namespace, systemName):
                pass
            def ListenForEvent(self, *args):
                listeners.append(args)
            def UnListenForEvent(self, *args):
                removed.append(args)
        api = types.ModuleType('mod.client.extraClientApi')
        api.GetClientSystemCls = lambda: ClientSystem
        api.GetEngineNamespace = lambda: 'Minecraft'
        api.GetEngineSystemName = lambda: 'Engine'
        mod, client = types.ModuleType('mod'), types.ModuleType('mod.client')
        mod.client, client.extraClientApi = client, api
        with patch.dict(sys.modules, {'mod': mod, 'mod.client': client, 'mod.client.extraClientApi': api}):
            scope = {}
            exec(compile(world.CLIENT_SYSTEM, 'diagnostic-client', 'exec'), scope)
            system = scope['ScaffoldDiagnosticClientSystem']('ScaffoldLifecycleDiagnostic', 'Client')
            system.render_tick({})
            self.assertFalse(system.ui_initialized)
            self.assertEqual(0, system.render_ticks)
            system.ui_init({})
            system.render_tick({})
            system.render_tick({})
            self.assertTrue(system.ui_initialized)
            self.assertEqual(2, system.render_ticks)
            system.Destroy()
        self.assertEqual(['UiInitFinished', 'GameRenderTickEvent'], [row[2] for row in listeners])
        self.assertEqual(listeners, removed)

    def test_background_air_aux_keeps_integer_type_and_missing_aux_compatibility(self):
        client, server = self.observation()
        cell = server['reserve'][0]
        for aux in (False, True, 0.0):
            cell['liquid'] = {'name': 'minecraft:air', 'aux': aux}
            with self.subTest(aux=aux):
                self.assertFalse(world.ready(client, server))
        cell['liquid'] = {'name': 'minecraft:air', 'aux': 0}
        self.assertTrue(world.ready(client, server))
        cell['liquid'] = {'name': 'minecraft:air'}
        self.assertTrue(world.ready(client, server))

    def test_malformed_native_ground_is_pending_instead_of_raising(self):
        client, server = self.observation()
        for value in (None, False, [], 'unavailable'):
            changed = copy.deepcopy(server)
            changed['ground'] = value
            with self.subTest(ground=value):
                self.assertFalse(world.ready(client, changed))
            changed['ground'] = {'front': value, 'states': {}}
            with self.subTest(front=value):
                self.assertFalse(world.ready(client, changed))

    def test_minimal_pack_keeps_exact_registry_and_own_manifest_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'pack'
            world.build_pack(ROOT, target)
            package = target / 'behavior_pack/modern_projection'
            for name in ('block_registry.py', 'block_registry_data.py'):
                self.assertEqual((ROOT / 'behavior_pack/modern_projection/projection' / name).read_bytes(),
                                 (package / 'projection' / name).read_bytes())
            self.assertEqual(world.CLIENT_SYSTEM, (package / 'client_system.py').read_text(encoding='ascii'))
            manifest = json.loads((target / 'behavior_pack/manifest.json').read_bytes())
            production = json.loads((ROOT / 'behavior_pack/manifest.json').read_bytes())
            self.assertNotEqual(production['header']['uuid'], manifest['header']['uuid'])
            self.assertNotEqual(manifest['header']['uuid'], manifest['modules'][0]['uuid'])
            with self.assertRaises(FileExistsError):
                world.build_pack(ROOT, target)

    def test_loading_with_no_player_is_pending_without_creating_components(self):
        def unexpected_factory():
            raise AssertionError('No player means no world components')
        api = types.ModuleType('mod.server.extraServerApi')
        api.GetPlayerList = lambda: []
        api.GetMinecraftVersion = lambda: world.RUNTIME
        api.GetEngineCompFactory = unexpected_factory
        api.GetLocalPlayerId = lambda: None
        api.GetSystem = lambda namespace, system: None
        mod = types.ModuleType('mod')
        server, client = types.ModuleType('mod.server'), types.ModuleType('mod.client')
        mod.server, mod.client = server, client
        server.extraServerApi, client.extraClientApi = api, api
        with patch.dict(sys.modules, {'mod': mod, 'mod.server': server, 'mod.server.extraServerApi': api,
                                     'mod.client': client, 'mod.client.extraClientApi': api}):
            scope = {}
            exec(compile(world.CLIENT, 'world-client', 'exec'), scope)
            observed_client = scope['_result']
            exec(compile(world.SERVER, 'world-server', 'exec'), scope)
            self.assertFalse(world.ready(observed_client, scope['_result']))
            self.assertIsNone(observed_client['foot'])
            self.assertIsNone(scope['_result']['ground'])

    def test_game_side_payloads_compile_under_python2(self):
        pypy = Path('C:/Users/Happy2018new/Desktop/PyPy/pypy2.exe')
        if not pypy.is_file():
            self.skipTest('Game-compatible Python2 unavailable')
        for source in (world.MOD_MAIN, world.CLIENT_SYSTEM, world.CLIENT, world.SERVER):
            result = subprocess.run([str(pypy), '-c', 'compile(%r,"scaffold-world","exec")' % source],
                                    capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
