"""Inspect native item dictionary semantics in one restored private inventory slot.

This does not prove pixels or equate isEnchanted with the native glint decision.
It never starts a game, captures a window, or reads compass target data.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, return_value
from _session import load_session

VERSION = '3.10.0.420447'
CASES = (
    ('minecraft:diamond_sword', 0, False),
    ('minecraft:diamond_sword', 0, True),
    ('minecraft:apple', 0, False),
    ('minecraft:golden_apple', 0, False),
    ('minecraft:enchanted_golden_apple', 0, False),
    ('minecraft:nether_star', 0, False),
    ('minecraft:end_crystal', 0, False),
    ('minecraft:lodestone_compass', 0, False),
    ('minecraft:compass', 0, False),
    ('minecraft:recovery_compass', 0, False),
    ('minecraft:enchanted_book', 0, False),
    ('minecraft:written_book', 0, False),
    ('minecraft:experience_bottle', 0, False),
    ('minecraft:ominous_bottle', 0, False),
    ('minecraft:mojang_banner_pattern', 0, False),
    ('minecraft:potion', 0, False),
    ('minecraft:potion', 5, False),
    ('minecraft:splash_potion', 5, False),
    ('minecraft:lingering_potion', 5, False),
)

PROBE = '''import json
import mod.server.extraServerApi as intrinsic_api
assert intrinsic_api.GetMinecraftVersion() == '1.21.130.0'
intrinsic_players = intrinsic_api.GetPlayerList()
assert len(intrinsic_players) == 1, intrinsic_players
intrinsic_player = intrinsic_players[0]
intrinsic_items = intrinsic_api.GetEngineCompFactory().CreateItem(intrinsic_player)
intrinsic_kind = intrinsic_api.GetMinecraftEnum().ItemPosType.INVENTORY
intrinsic_before = [intrinsic_items.GetPlayerItem(intrinsic_kind, index, True) for index in range(36)]
intrinsic_slot = next((index for index in reversed(range(36)) if not intrinsic_before[index]), None)
assert intrinsic_slot is not None, 'A pre-existing empty inventory slot is required'
intrinsic_rows = []
intrinsic_report = {'native_version': intrinsic_api.GetMinecraftVersion(),
                    'slot': intrinsic_slot, 'rows': intrinsic_rows,
                    'inventory_before': intrinsic_before, 'restored': False}
try:
 for intrinsic_name, intrinsic_aux, intrinsic_enchant in CASES:
  assert intrinsic_items.SetInvItemNum(intrinsic_slot, 0)
  intrinsic_input = {'itemName': intrinsic_name, 'auxValue': intrinsic_aux, 'count': 1,
                     'enchantData': [], 'userData': {}}
  intrinsic_write = intrinsic_items.SpawnItemToPlayerInv(intrinsic_input, intrinsic_player, intrinsic_slot)
  intrinsic_added = None
  if intrinsic_enchant:
   intrinsic_added = intrinsic_items.AddEnchantToInvItem(intrinsic_slot, 9, 1)
  intrinsic_actual = intrinsic_items.GetPlayerItem(intrinsic_kind, intrinsic_slot, True)
  intrinsic_rows.append({'requested_name': intrinsic_name, 'requested_aux': intrinsic_aux,
                         'added_real_enchantment': intrinsic_enchant, 'input': intrinsic_input,
                         'write_return': intrinsic_write, 'enchant_return': intrinsic_added,
                         'readback': intrinsic_actual,
                         'native_enchant_data': intrinsic_items.GetInvItemEnchantData(intrinsic_slot)})
finally:
 intrinsic_report['clear_return'] = intrinsic_items.SetInvItemNum(intrinsic_slot, 0)
 intrinsic_report['inventory_after'] = [intrinsic_items.GetPlayerItem(intrinsic_kind, index, True)
                                       for index in range(36)]
 intrinsic_report['restored'] = intrinsic_before == intrinsic_report['inventory_after']
 assert intrinsic_report['restored'], intrinsic_report
_result = json.dumps(intrinsic_report)
'''


def validate_private_session(manifest):
    project = Path(manifest.get('project', manifest.get('project_path', ''))).resolve()
    private_root = (ROOT / '.runtime/projects').resolve()
    if not project.is_relative_to(private_root) or project == private_root:
        raise ValueError('Only an owned clone strictly beneath .runtime/projects is allowed')
    if Path(manifest['game_executable']).parent.name != VERSION:
        raise ValueError('The exact 3.10 target engine is required')


def run(session, owner, output):
    manifest = load_session(session, owner, live=True)
    validate_private_session(manifest)
    if output.exists():
        raise ValueError('Preserve previous probe evidence')
    os.environ.update(MCDEV_SESSION_FILE=str(session), MCDEV_OWNER=owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    report = {'schema': 1, 'engine_version': VERSION, 'session_id': manifest['id'],
              'owner': owner, 'completed': False, 'visual_qualification': False,
              'method': 'Native item dictionary readback; no pixel inference',
              'host_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'cases': CASES}
    output.parent.mkdir(parents=True, exist_ok=True)
    code = 'CASES = ' + repr(CASES) + '\n' + PROBE
    with Client(timeout=30) as client:
        reply = client.call('execute_code', {'code': code, 'is_client': False,
                                              'direct_return': True})
    report['reply_is_error'] = bool(reply.get('isError'))
    if report['reply_is_error']:
        report['error'] = reply
    else:
        result = return_value(reply)
        report['native'] = json.loads(result) if isinstance(result, str) else result
        report['completed'] = report['native'].get('restored') is True
    output.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    if not report['completed']:
        raise RuntimeError('Native probe did not complete; inspect ' + str(output))
    print(json.dumps({'output': str(output), 'completed': True,
                      'rows': len(report['native']['rows']), 'restored': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.session, args.owner, args.output)
