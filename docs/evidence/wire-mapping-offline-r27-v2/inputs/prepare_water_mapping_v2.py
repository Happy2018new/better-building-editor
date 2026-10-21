"""Separate offline candidate only; frozen v1 is read, never rewritten."""
from pathlib import Path
import difflib

HERE = Path(__file__).resolve().parent
OUT = HERE / 'fixed-water-v2'


def main():
    OUT.mkdir(exist_ok=True)
    old_path = HERE / 'fixed-water-v1/water_resource_mapping_v1.py'
    old = old_path.read_text(encoding='utf8')
    marker = "        assert unpack(snapshot['applied_native_success_ledger']) == ledger"
    assert old.count(marker) == 1
    new = old.replace(marker, """        transported_ledger = unpack(snapshot['applied_native_success_ledger'])
        assert type(transported_ledger) is dict, 'Water ledger outer transport is not a dictionary'
        for entry in transported_ledger.values():
            assert type(entry) is dict and set(entry) == {'sequence', 'value'}, 'Invalid acknowledged uniform ledger entry'
            assert type(entry['sequence']) is int and entry['sequence'] > 0, 'Invalid native uniform sequence'
            value = entry['value']
            assert type(value) is dict and set(value) == {'tuple'}, 'Expected separately packed native uniform tuple'
            entry['value'] = unpack(value)
        assert transported_ledger == ledger, 'Native uniform acknowledgements differ from exported ledger'""")
    new = new.replace('wire-r27-actual-water-call-frozen-resource-mapping-v1',
                      'wire-r27-offline-water-call-frozen-resource-mapping-v2')
    # This new module still reads the same frozen three-expression manifest.
    new = new.replace("Path(__file__).parent / 'shader-change-manifest-v1.json'",
                      "Path(__file__).parent.parent / 'fixed-water-v1/shader-change-manifest-v1.json'")
    target = OUT / 'water_resource_mapping_v2.py'
    with target.open('x', encoding='utf8', newline='\n') as stream:
        stream.write(new)
    diff = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
        fromfile='frozen-v1/water_resource_mapping_v1.py', tofile='offline-v2/water_resource_mapping_v2.py'))
    with (OUT / 'mapping-exact.diff').open('x', encoding='utf8', newline='\n') as stream:
        stream.write(diff)
    print('Separate v2 candidate and exact narrow diff prepared; v1 unchanged.')


if __name__ == '__main__':
    main()
