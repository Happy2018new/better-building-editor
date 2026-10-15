"""Explicit one-use launch entry; preflight alone never starts a game."""
import argparse
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location('water_alpha_host',
    Path(__file__).with_name('water-r21-alpha-host.py'))
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'start'))
    args = parser.parse_args()
    if args.action == 'preflight':
        print(json.dumps(host.preflight(launch=True)))
    else:
        raise SystemExit(host.start_once())
