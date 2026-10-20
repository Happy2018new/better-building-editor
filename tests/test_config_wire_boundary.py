"""Real SDK config text must decode before strict semantic archive validation."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
for name in ('mod', 'mod.client', 'mod.client.extraClientApi'):
    sys.modules.setdefault(name, types.ModuleType(name))
from projection.bridge import ClientBridge
from projection.cell import actor_data, make_cell
from projection.model import AIR, Document
from projection import archive, semantic_wire


def sdk_text(value):
    if isinstance(value, str):
        return value.encode('utf8')
    if isinstance(value, (list, tuple)):
        return [sdk_text(item) for item in value]
    if isinstance(value, dict):
        return {sdk_text(key): sdk_text(item) for key, item in value.items()}
    return value


class Config:
    def __init__(self):
        self.data = {}
        self.calls = []

    def CreateConfigClient(self, level):
        return self

    def GetConfigData(self, key, global_config):
        self.calls.append((key, global_config))
        return copy.deepcopy(self.data.get(key))

    def SetConfigData(self, key, value, global_config):
        self.data[key] = sdk_text(value)
        return True


class ConfigWireBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.bridge = ClientBridge.__new__(ClientBridge)
        self.bridge.factory, self.bridge.level = self.config, 'level'
        self.actor = {'bytes': b'\x00\xff\x80', 'text': '中文物品',
                      'tuple': (True, 1, 1.0), b'raw-key': b'raw-value',
                      'Items': [{'Name': 'minecraft:apple', 'Count': 7}]}

    def document(self, size=(2, 2, 2)):
        return Document(size, {(0, 0, 0): make_cell(('minecraft:chest', 2),
                        ('minecraft:water', 0), self.actor)}, name='中文双层建筑')

    def test_inline_library_sdk_bytes_restore_layers_and_typed_nbt(self):
        doc = self.document()
        self.bridge.save_library({'version': 1, 'serial': 1,
                                 'buildings': [{'id': 1, 'data': doc.to_data()}]})
        stored = copy.deepcopy(self.config.data['modern_projection_library'])
        restored = Document.from_data(self.bridge.load_library()['buildings'][0]['data'])
        self.assertEqual(doc.name, restored.name)
        self.assertEqual(doc.blocks, restored.blocks)
        self.assertEqual(self.actor, actor_data(restored.get((0, 0, 0))))
        self.assertEqual(stored, self.config.data['modern_projection_library'])
        self.assertEqual(('modern_projection_library', True), self.config.calls[-1])

    def test_paged_archive_and_semantic_preferences_decode_same_wire_format(self):
        doc = self.document((64, 16, 64))
        header = list(archive.save_steps(self.bridge, doc, 1))[-1]
        self.bridge.save_library({'buildings': [{'data': header}]})
        header = self.bridge.load_library()['buildings'][0]['data']
        restored = list(archive.load_steps(self.bridge, 1, header))[-1]
        self.assertEqual(doc.name, restored.name)
        self.assertEqual(doc.blocks, restored.blocks)
        preferences = {'version': 2, 'cellVersion': 1, 'registry': semantic_wire.provenance(),
                       'palette': [semantic_wire.encode_material(('minecraft:oak_stairs', 4))]}
        self.bridge.save_preferences(preferences)
        actual = self.bridge.load_preferences()
        source = semantic_wire.validate_header(actual)
        self.assertEqual(('minecraft:oak_stairs', 4),
                         semantic_wire.decode_material(actual['palette'][0], source))

    def test_invalid_utf8_typed_header_and_nbt_remain_rejected(self):
        self.config.data['modern_projection_library'] = {b'name': b'\xff'}
        with self.assertRaises(UnicodeDecodeError):
            self.bridge.load_library()
        for field, value in (('cellVersion', True), ('registry', {'version': 'future', 'sha256': 'bad'})):
            data = self.document().to_data()
            data[field] = value
            self.bridge.save_library({'buildings': [{'data': data}]})
            with self.assertRaises(ValueError):
                Document.from_data(self.bridge.load_library()['buildings'][0]['data'])
        from projection.cell import _tree
        self.bridge.save_library({'actor': ['int', '1.0']})
        with self.assertRaises(ValueError):
            _tree(self.bridge.load_library()['actor'])
        self.assertIsNone(self.bridge.load_archive_page(99, 0))

    def test_actual_python2_session_save_sdk_readback_and_reload_inline_and_paged(self):
        python2 = Path(os.environ.get('PROJECTION_PY2', 'D:/Program/Python27/python.exe'))
        if not python2.exists():
            self.skipTest('Actual project Python 2 interpreter is unavailable')
        code = r'''# coding: utf8
import sys,types,copy,json
sys.path.insert(0,'behavior_pack/modern_projection')
for name in ('mod','mod.client','mod.client.extraClientApi'):
 sys.modules.setdefault(name,types.ModuleType(name))
sys.modules['mod'].client=sys.modules['mod.client']
sys.modules['mod.client'].extraClientApi=sys.modules['mod.client.extraClientApi']
from projection.bridge import ClientBridge
from projection.session import Session
from projection.model import Document,Editor,AIR
from projection.cell import make_cell,actor_data
from projection.semantic_wire import validate_header
def sdk(value):
 if isinstance(value,unicode):return value.encode('utf8')
 if isinstance(value,(list,tuple)):return [sdk(item) for item in value]
 if isinstance(value,dict):return dict((sdk(key),sdk(item)) for key,item in value.items())
 return value
class Bridge(ClientBridge):
 def __init__(self):self.factory=self;self.level='level';self.data={};self.queue=[]
 def CreateConfigClient(self,level):return self
 def GetConfigData(self,key,glob):return copy.deepcopy(self.data.get(key))
 def SetConfigData(self,key,value,glob):self.data[key]=sdk(value);return True
 def later(self,delay,callback):self.queue.append(callback)
 def drain(self):
  for unused in range(10000):
   if not self.queue:return
   self.queue.pop(0)()
  raise AssertionError('IO did not settle')
actor={b'bytes':b'\x00\xff\x80',u'text':u'\u4e2d\u6587',u'list':[True,1,1.0],u'tuple':(True,1,1.0),u'huge':1<<40}
for size in ((2,2,2),(64,16,64)):
 b=Bridge();s=Session(b);s.refresh_preview=lambda:None
 doc=Document(size,{(0,0,0):make_cell(('minecraft:chest',2),('minecraft:water',0),actor)},name=u'\u4e2d\u6587\u5efa\u7b51')
 s.editor=Editor(doc);s.name=doc.name
 s.save();b.drain()
 assert len(s.library)==1 and s.library_serial==1
 raw=b.GetConfigData('modern_projection_library',True)
 assert isinstance(raw['buildings'][0]['data']['registry']['sha256'],str)
 try:validate_header(raw['buildings'][0]['data'])
 except ValueError:pass
 else:raise AssertionError('Pre-fix SDK bytes unexpectedly accepted')
 index=b.load_library();s.library=index['buildings'];s.library_serial=index['serial']
 assert isinstance(s.library[0]['data']['registry']['sha256'],unicode)
 s.load(1);b.drain()
 assert s.editor.document is not doc
 assert s.editor.document.blocks==doc.blocks
 assert s.editor.document.name==doc.name
 assert actor_data(s.editor.document.get((0,0,0)))==actor
 assert type(actor_data(s.editor.document.get((0,0,0)))[u'list'][0]) is bool
 assert type(actor_data(s.editor.document.get((0,0,0)))[u'list'][1]) is int
 assert type(actor_data(s.editor.document.get((0,0,0)))[u'list'][2]) is float
 assert type(actor_data(s.editor.document.get((0,0,0)))[u'tuple']) is tuple
 assert type(actor_data(s.editor.document.get((0,0,0)))[b'bytes']) is str
 assert type(actor_data(s.editor.document.get((0,0,0)))[u'text']) is unicode
 assert not s.editor.undo_stack and not s.editor.redo_stack
 assert s.editor.selection==Editor(s.editor.document).selection
 b.data['modern_projection_library']={b'name':b'\xff'}
 try:b.load_library()
 except UnicodeDecodeError:pass
 else:raise AssertionError('Invalid UTF8 accepted')
print(json.dumps({'python2':'passed','inline':True,'paged':True,'typed_nbt':True,'invalid_utf8_rejected':True}))
'''
        result = subprocess.run([str(python2), '-B', '-c', code], cwd=str(ROOT),
                                capture_output=True, text=True, encoding='utf8')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(json.loads(result.stdout)['typed_nbt'])


if __name__ == '__main__':
    unittest.main()
