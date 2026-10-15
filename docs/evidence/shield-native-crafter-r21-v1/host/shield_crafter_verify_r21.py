"""Offline replay of native crafter item/schema evidence; never connects to MC."""
import argparse
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_bytes())


def scalar(root, key):
    value = root[key]
    return value['__value__'] if isinstance(value, dict) and '__type__' in value else value


def entries(root):
    value = root['Items']
    return value['__value__'] if isinstance(value, dict) else value


def patterns(root):
    value = root['Patterns']
    value = value['__value__'] if isinstance(value, dict) else value
    return [(scalar(row, 'Color'), scalar(row, 'Pattern')) for row in value]


def verify(folder):
    records = folder / 'records' if (folder / 'records').exists() else folder
    raw = read(records / 'authentic-shield.json')
    target = read(records / 'target-output.json')
    item = raw['item']
    assert raw['native_crafting_output_acquired'] and raw['user_data_requested']
    assert not raw['native_nbt_injection'] and not raw['production_qualified']
    assert item['newItemName'] == 'minecraft:shield' and item['newAuxValue'] == 0
    assert item['count'] == 1 and item['durability'] == 336
    assert item == target['chest'][0] and not any(target['chest'][1:])
    assert not any(target['hopper']) and not entries(target['blocks']['crafter']['nbt'])
    assert target['inventory_unchanged']
    container = raw['container_nbt']
    assert container == target['blocks']['chest']['nbt']
    rows = entries(container)
    assert len(rows) == 1
    assert scalar(rows[0], 'Name') == 'minecraft:shield'
    assert scalar(rows[0], 'Count') == 1 and scalar(rows[0], 'Slot') == 0
    assert scalar(rows[0], 'Damage') == 0
    assert rows[0]['tag'] == item['userData']
    data = item['userData']
    assert data['Base'] == {'__type__': 3, '__value__': 4}
    assert data['Damage'] == {'__type__': 3, '__value__': 0}
    assert patterns(data) == [(1, 'bo'), (14, 'cr'), (11, 'mc')]
    before = read(records / '12-server-pulse_on.json')['result']['before']
    loaded = entries(before['blocks']['crafter']['nbt'])
    assert sorted(scalar(row, 'Name') for row in loaded) == ['minecraft:banner', 'minecraft:shield']
    assert all(scalar(row, 'Count') == 1 for row in loaded)
    banner = next(row for row in loaded if scalar(row, 'Name') == 'minecraft:banner')
    shield = next(row for row in loaded if scalar(row, 'Name') == 'minecraft:shield')
    assert scalar(banner, 'Damage') == 4
    assert patterns(banner['tag']) == patterns(data)
    assert 'Base' not in shield.get('tag', {}) and 'Patterns' not in shield.get('tag', {})
    assert not any(before['hopper']) and not any(before['chest'])
    assert scalar(before['blocks']['crafter']['nbt'], 'disabled_slots') == 0
    positive = read(records / 'positive-output.json')
    output = [row for row in positive['chest'] if row]
    assert len(output) == 1 and output[0]['newItemName'] == 'minecraft:oak_planks'
    assert output[0]['count'] == 4 and not any(positive['hopper'])
    assert not entries(positive['blocks']['crafter']['nbt'])
    assert read(records / '09-server-clear_output.json')['result']['positive_verified']
    restore = read(records / '15-server-restore.json')['result']
    assert restore['restored'] and restore['guard_cells_verified'] == 64
    assert restore['inventory_restored'] and restore['selected_restored']
    assert not restore['player_position_written'] and not restore['drop_cleanup']
    assert restore['foot_before'] == restore['foot_after']
    client = read(records / '16-client-restore.json')['result']
    assert client['camera_unchanged'] and not client['camera_mutation_performed']
    assert client['before'] == client['after']
    assert read(records / 'run-restoration.json') == {'success': True, 'errors': []}
    assert read(records / 'source-final.json') == {'unchanged': True}
    exit_record = read(records / 'exact-exit.json')
    assert exit_record['completed'] and not exit_record['process_or_window_mutation']
    assert exit_record['processes']['game']['exit_code'] == 0xC0000409
    assert exit_record['processes']['mcdk']['exit_code'] == 0
    for name in ('stop-01.json', 'stop-02.json'):
        assert not read(records / name)['forced']
    calls = sorted(records.glob('[0-9][0-9]-*.json'))
    assert len(calls) == 16
    for path in calls:
        row = read(path)
        assert hashlib.sha256(row['code'].encode('utf8')).hexdigest() == row['code_sha256'], path.name
    return {'verified': True, 'native_schema_observed': True,
            'output_item_tag_exact_match': True, 'ordered_patterns': patterns(data),
            'base': 4, 'outer_aux': 0, 'inner_damage': 0,
            'native_positive_oak_planks_count': 4, 'guard_cells_restored': 64,
            'execute_code_records': len(calls), 'no_shield_nbt_injection': True,
            'camera_world_inventory_restoration': True,
            'game_exit': '0xC0000409', 'mcdk_exit': 0,
            'native_rendering_tested': False, 'production_qualified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    print(json.dumps(verify(parser.parse_args().folder)))
