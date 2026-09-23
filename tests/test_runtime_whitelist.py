"""Release imports and compact-buffer compatibility independent of game SDK."""
import sys
import struct
import base64
import zlib
import unittest
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack/HelloScript'))
from audit_runtime_imports import audit, imports
from projection.packed import IntegerBuffer


class RuntimeWhitelistTests(unittest.TestCase):
    def test_every_shipped_module_is_whitelisted_or_project_owned(self):
        report = audit()
        self.assertGreater(report['files'], 70)
        self.assertEqual([], report['violations'])

    def test_scan_catches_local_multiline_and_dynamic_imports(self):
        source = 'import math, sys as system\nfrom .local import (Thing,\n Other)\ndef f():\n import gui\n __import__("array")\n print "Python 2"\n'
        self.assertEqual([(1,'math'),(1,'sys'),(2,'.local'),(5,'gui'),(6,'<dynamic:__import__>')], imports(source))

    def test_compact_buffer_matches_legacy_integer_values_and_wire_bytes(self):
        for code, values in (('H',[0,1,255,256,32768,65535]),('i',[-2147483648,-42,0,42,2147483647])):
            old, new = array(code,values), IntegerBuffer(code,values)
            self.assertEqual(list(old),list(new))
            self.assertEqual(struct.pack('<%d%s'%(len(values),code),*values),new.tobytes())
            self.assertEqual(len(values)*new.itemsize,len(new.tobytes()))
            loaded = IntegerBuffer(code)
            loaded.frombytes(new.tobytes())
            self.assertEqual(new,loaded)
            self.assertEqual(list(old[::-1]),list(new[::-1]))
            self.assertEqual(old[-1],new[-1])
            self.assertNotEqual(0,new)

    def test_plane_slices_and_copy_on_write_preserve_source(self):
        source = IntegerBuffer('H',[7])*4096
        candidate = IntegerBuffer('H',source)
        candidate[256:512] = IntegerBuffer('H',[65535])*256
        candidate[0] = 9
        self.assertEqual([7]*4096,list(source))
        self.assertEqual([65535]*256,list(candidate[256:512]))
        self.assertEqual(9,candidate[0])
        self.assertEqual(8192,len(candidate.tobytes()))
        candidate[1:4] = [2,3,4]
        self.assertEqual([9,2,3,4,7],list(candidate[:5]))

    def test_old_mixed_chunk_archive_keeps_identical_bytes(self):
        from projection.model import Document
        from projection.codec import to_data
        from projection.storage import position
        values = array('H', (i % 3 for i in range(4096)))
        if sys.byteorder != 'little':
            values.byteswap()
        payload = base64.b64encode(zlib.compress(values.tobytes(), 1)).decode('ascii')
        packet = {'version':2, 'size':[16,16,16], 'name':'legacy', 'biome':'forest',
                  'palette':[['minecraft:air',0], ['minecraft:stone',0], ['minecraft:planks',1]],
                  'chunks':[[0,0,0,payload]], 'blockCount':2730}
        restored = Document.from_data(packet)
        self.assertEqual('forest', restored.biome)
        self.assertEqual(packet['chunks'], to_data(restored)['chunks'])
        for index in range(4096):
            self.assertEqual(tuple(packet['palette'][index % 3]), restored.get(position((0,0,0), index)))

    def test_buffer_rejects_bad_lengths_and_overflow_without_mutation(self):
        value = IntegerBuffer('H',[2,3])
        for operation in (lambda:value.frombytes(b'x'),lambda:value.__setitem__(0,65536),
                          lambda:value.__setitem__(slice(0,1),[-1])):
            with self.assertRaises((ValueError,struct.error)):
                operation()
            self.assertEqual([2,3],list(value))
        for index in (-3,2):
            with self.assertRaises(IndexError):
                value[index]


if __name__ == '__main__':
    unittest.main()
