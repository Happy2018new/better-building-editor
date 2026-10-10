"""Keep the orientation widget's UI helper independent of block cell layers."""
import ast
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
PROJECTION = ROOT / 'behavior_pack/modern_projection/projection'
spec = importlib.util.spec_from_file_location('_ui_layers_test', PROJECTION / 'ui_layers.py')
layers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layers)


class UiLayerTests(unittest.TestCase):
    def test_gizmo_layer_import_resolves(self):
        tree = ast.parse((PROJECTION / 'gizmo.py').read_text(encoding='utf8'))
        imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
                   and any(alias.name == 'apply_layers' for alias in node.names)]
        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0].module, 'ui_layers')
        self.assertTrue(callable(layers.apply_layers))

    def test_last_request_wins_and_only_final_control_refreshes(self):
        first, second = Mock(), Mock()
        layers.apply_layers([(first, 1), (second, 2), (first, 3)])
        first.SetLayer.assert_called_once_with(3, False, False)
        second.SetLayer.assert_called_once_with(2, False, True)

    def test_empty_batch_does_not_refresh(self):
        layers.apply_layers([])


if __name__ == '__main__':
    unittest.main()
