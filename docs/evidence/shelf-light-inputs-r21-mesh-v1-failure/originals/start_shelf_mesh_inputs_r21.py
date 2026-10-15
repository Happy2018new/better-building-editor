"""Freeze the private terrain-mesh input selector before its game window."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('shelf_frozen_start', ROOT/'.runtime/start_shelf_baked_r21.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
launcher.PROJECT = ROOT/'.runtime/projects/shelf-r21-mesh-inputs-v1'
launcher.OUTPUT = ROOT/'.runtime/shelf-mesh-inputs-r21-start-v1'
launcher.OWNER = 'root-shelf-r20-mesh-inputs-v1'

if __name__ == '__main__':
    launcher.main()
