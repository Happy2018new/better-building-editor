"""Read-only restored chest fixture audit before stopping the owned instance."""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import time

from verify_chest_occupied_frozen_holdout import BASELINE, restoration_matches
from verify_debug_blueprints import Client, write_json
from verify_native_entity_appearances import execute
from verify_sign_visuals import SignCheck

CLIENT_STATE = '''flags=("_blueprint_qa_saved","_blueprint_visual_saved","_copper_native_document",
 "_copper_native_origin","_chest_top_public_snapshot","_entity_visual_r8_document",
 "_entity_visual_r8_history","_neighbor_visual_options_saved","_sign_visual_hud_saved")
_result=json.dumps({'temporary_flags':[name for name in flags if hasattr(sys,name)],
 'projection_active':s.projection_active,'preparing':bool(b.preparing_entity),
 'entity':b.entity,'entities':list(b.projection_entities.values()),
 'workspace_open':navigator.contains('modern_projection_workspace'),
 'transition':navigator.is_transitioning})
'''

SERVER_FLAGS = '''import json,sys
flags=("_copper_native_probe","_entity_visual_r8_occupied","_entities_r7_chest_top_player","_p0_visual_daylight")
_result=json.dumps({'temporary_flags':[name for name in flags if hasattr(sys,name)]})
'''


def process_snapshot(pid):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessHandleCount.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel.GetProcessHandleCount.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        count = wintypes.DWORD()
        if not kernel.GetProcessHandleCount(handle, ctypes.byref(count)):
            raise ctypes.WinError(ctypes.get_last_error())
        return {'pid': pid, 'handles': count.value, 'recorded_at': time.time()}
    finally:
        kernel.CloseHandle(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh audit path')
    report = {'schema': 1, 'completed': False, 'restored': False, 'read_only': True,
              'session_file': os.environ['MCDEV_SESSION_FILE'],
              'process': process_snapshot(int(os.environ['MCDEV_GAME_PID']))}
    try:
        original = json.loads((args.run/'report.json').read_text(encoding='utf8'))
        with Client(timeout=30) as client:
            check = SignCheck(client, args.output, 30)
            report['client'] = check.run(CLIENT_STATE)
            report['server'] = execute(client, SERVER_FLAGS)
            report['player'] = execute(client, BASELINE)
        state = report['client']
        report['restored'] = (not state['temporary_flags'] and not report['server']['temporary_flags'] and
            not state['projection_active'] and not state['preparing'] and not state['entity'] and
            not state['entities'] and not state['workspace_open'] and not state['transition'] and
            restoration_matches(original['grounded_baseline'], report['player']))
        report['completed'] = True
    finally:
        report['process_after'] = process_snapshot(int(os.environ['MCDEV_GAME_PID']))
        write_json(args.output, report)
    print(json.dumps(report))
    return 0 if report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
