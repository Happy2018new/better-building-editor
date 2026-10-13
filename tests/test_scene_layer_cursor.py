"""Run the production hover fragment without loading the native UI runtime."""
import ast
import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.cell import AIR, actor_data, make_cell
from projection.model import Document, Editor
from projection.session import Session
from test_session import Bridge


SCENE = Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection/projection/scene.py'
FENCE = ('minecraft:oak_fence', 0)
WATER = ('minecraft:water', 0)
STONE = ('minecraft:stone', 0)


def cursor_fragments():
    # Preserve the real cache branch and effect inputs, replacing only engine I/O.
    module = ast.parse(SCENE.read_text(encoding='utf8'), filename=str(SCENE))
    scene = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == 'Scene')
    tick = next(node for node in scene.body if isinstance(node, ast.FunctionDef) and node.name == 'tick')
    hover = next(node for node in tick.body if isinstance(node, ast.If) and any(
        isinstance(child, ast.Attribute) and child.attr == 'GetMousePosition'
        for child in ast.walk(node)))
    reset = next(node for node in scene.body if isinstance(node, ast.FunctionDef) and node.name == 'reset_cursor')
    effect = next(node for node in scene.body if isinstance(node, ast.Expr) and
                  isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and
                  node.value.func.id == 'use_effect' and node.value.args and
                  isinstance(node.value.args[0], ast.Name) and node.value.args[0].id == 'reset_cursor')
    result = []
    for nodes in ([hover], [reset, effect]):
        isolated = ast.fix_missing_locations(ast.Module(body=copy.deepcopy(nodes), type_ignores=[]))
        result.append(compile(isolated, str(SCENE), 'exec'))
    return result


class SceneLayerCursorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hover_code, cls.reset_code = cursor_fragments()

    def scope(self, cell=FENCE):
        session = Session(Bridge())
        session.editor = Editor(Document((8, 8, 8), {(2, 2, 2): cell}))
        session.choose_mode('place')
        session.editor.material = WATER
        hits = []

        def hit_at(x, y):
            hits.append((x, y))
            return (2, 2, 2), (1, 0, 0)

        scope = dict(session=session, e=session.editor, signature='fixed-camera',
                     drag=SimpleNamespace(current=None),
                     mouse=SimpleNamespace(GetMousePosition=lambda: (20, 30)),
                     screen_hit=lambda point: True,
                     pointer=SimpleNamespace(current=SimpleNamespace(GetGlobalPosition=lambda: (0, 0))),
                     placed_pointer=SimpleNamespace(current=None),
                     hover_preview=SimpleNamespace(current=None),
                     hit_at=hit_at, preview_cell=None, preview_error=None, active=True)
        return session, scope, hits

    def frame(self, scope):
        exec(self.hover_code, scope)
        return scope['preview_cell'], scope['preview_error']

    def test_stationary_pointer_recomputes_foreground_background_and_auto_targets(self):
        session, scope, hits = self.scope()
        for mode, target in ((0, (3, 2, 2)), (1, (2, 2, 2)), (2, (2, 2, 2)), (0, (3, 2, 2))):
            with self.subTest(mode=mode):
                session.set_editor('edit_layer', mode)
                self.assertEqual((target, None), self.frame(scope))
                prior_hits = len(hits)
                self.assertEqual((target, None), self.frame(scope))
                self.assertEqual(prior_hits, len(hits))
        self.assertEqual(4, len(hits))

    def test_placement_action_matches_recomputed_layer_target_and_undo(self):
        for mode, target in ((0, (3, 2, 2)), (1, (2, 2, 2)), (2, (2, 2, 2))):
            with self.subTest(mode=mode):
                session, scope, unused_hits = self.scope()
                session.set_editor('edit_layer', mode)
                self.assertEqual((target, None), self.frame(scope))
                self.assertEqual(1, session.point_action((2, 2, 2), (1, 0, 0)))
                self.assertEqual(target, session.focused)
                self.assertEqual({target}, set(session.editor.selection))
                if mode == 0:
                    self.assertEqual(WATER, session.editor.document.get(target))
                    self.assertEqual(FENCE, session.editor.document.get((2, 2, 2)))
                else:
                    self.assertEqual(make_cell(FENCE, WATER), session.editor.document.get(target))
                session.editor.undo()
                self.assertEqual({(2, 2, 2): FENCE}, dict(session.editor.document.blocks.items()))

    def test_layer_switch_recomputes_mask_error_without_mouse_motion(self):
        session, scope, unused_hits = self.scope()
        session.choose_mode('erase')
        session.editor.mask = 'air'
        session.set_editor('edit_layer', 0)
        target, error = self.frame(scope)
        self.assertEqual((2, 2, 2), target)
        self.assertIsNotNone(error)
        session.set_editor('edit_layer', 1)
        self.assertEqual(((2, 2, 2), None), self.frame(scope))
        session.set_editor('edit_layer', 2)
        self.assertIsNotNone(self.frame(scope)[1])

    def test_layer_switch_releases_just_placed_cursor_but_document_edit_does_not(self):
        session, scope, unused_hits = self.scope()
        dependencies = [None]

        def use_effect(callback, values):
            if dependencies[0] != values:
                dependencies[0] = list(values)
                callback()

        scope['use_effect'] = use_effect
        session.set_editor('edit_layer', 0)
        exec(self.reset_code, scope)
        self.assertEqual(((3, 2, 2), None), self.frame(scope))
        session.point_action((2, 2, 2), (1, 0, 0))
        scope['placed_pointer'].current = (20, 30)
        exec(self.reset_code, scope)
        self.assertEqual(((3, 2, 2), None), self.frame(scope))
        self.assertEqual((20, 30), scope['placed_pointer'].current)
        session.set_editor('edit_layer', 1)
        exec(self.reset_code, scope)
        self.assertIsNone(scope['placed_pointer'].current)
        self.assertEqual(((2, 2, 2), None), self.frame(scope))

    def test_erase_action_keeps_unselected_layer_and_actor_or_promotes_auto_background(self):
        position = (2, 2, 2)
        actor = {'id': 'Chest', 'Items': [{'Count': 7, 'tag': {'keep': (b'\x00\xff', 1 << 40)}}]}
        before = make_cell(STONE, WATER, actor)
        expected = {0: make_cell(AIR, WATER), 1: make_cell(STONE, AIR, actor), 2: WATER}
        for mode in (0, 1, 2):
            with self.subTest(mode=mode):
                session, scope, unused_hits = self.scope(before)
                session.choose_mode('erase')
                session.erase_scope = 'single'
                session.set_editor('edit_layer', mode)
                self.assertEqual((position, None), self.frame(scope))
                self.assertEqual(1, session.point_action(position))
                self.assertEqual(expected[mode], session.editor.document.get(position))
                self.assertEqual(actor if mode == 1 else None,
                                 actor_data(session.editor.document.get(position)))
                session.editor.undo()
                self.assertEqual(before, session.editor.document.get(position))
                session.editor.redo()
                self.assertEqual(expected[mode], session.editor.document.get(position))


if __name__ == '__main__':
    unittest.main()
