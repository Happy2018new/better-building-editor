"""World-tool archive behavior stays isolated from the open editor."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack'))
from HelloScript.projection.model import Document
from HelloScript.projection.session import Session
from HelloScript.projection.tool_items import selection, unique_name


class MemoryBridge(object):
    def __init__(self):
        self.queue = []
        self.pages = {}
        self.library = None
        self.allow_index = True
        self.messages = []

    def later(self, delay, callback):
        self.queue.append(callback)

    def save_archive_page(self, identity, part, value):
        self.pages[(identity,part)] = value
        return True

    def save_library(self, value):
        if not self.allow_index:
            return False
        self.library = value
        return True

    def notify(self, value):
        self.messages.append(value)

    def drain(self):
        for unused in range(50):
            if not self.queue:
                return
            self.queue.pop(0)()
        raise AssertionError('archive did not finish')


class ToolImportTests(unittest.TestCase):
    def test_selection_and_unique_names(self):
        self.assertEqual(((1, 4, 2), (4, 3, 6)), selection((4, 6, 7), (1, 4, 2)))
        with self.assertRaises(ValueError):
            selection((0, 64, 0), (64, 64, 0))
        self.assertEqual('世界选区 1,2,3 (3)', unique_name((1,2,3),
            ['世界选区 1,2,3', '世界选区 1,2,3 (2)']))

    def test_import_is_new_archive_and_never_replaces_open_draft(self):
        bridge = MemoryBridge()
        session = Session(bridge)
        original = session.editor
        doc = Document((2,2,2), {(0,0,0):('minecraft:stone',0)})
        session.import_world_capture(doc, (1,64,2))
        bridge.drain()
        self.assertIs(original, session.editor)
        self.assertEqual('世界选区 1,64,2', session.library[0]['data']['name'])
        self.assertIsNone(session.world_import_document)
        session.import_world_capture(Document((1,1,1)), (1,64,2))
        bridge.drain()
        self.assertEqual('世界选区 1,64,2 (2)', session.library[1]['data']['name'])
        self.assertEqual(2, bridge.library['serial'])
        self.assertIs(original, session.editor)

    def test_failed_index_can_be_retried_without_losing_import(self):
        bridge = MemoryBridge()
        bridge.allow_index = False
        session = Session(bridge)
        session.import_world_capture(Document((1,1,1)), (3,4,5))
        bridge.drain()
        self.assertEqual([], session.library)
        self.assertIsNotNone(session.world_import_document)
        bridge.allow_index = True
        session.retry_world_import()
        bridge.drain()
        self.assertEqual(1, len(session.library))
        self.assertIsNone(session.world_import_document)

    def test_full_library_retains_pending_import_and_rejects_replacement(self):
        bridge = MemoryBridge()
        session = Session(bridge)
        session.library = [{'id':i,'data':{'name':'saved %d' % i}} for i in range(32)]
        session.library_serial = 31
        doc = Document((1,1,1))
        with self.assertRaises(ValueError):
            session.import_world_capture(doc, (1,2,3))
        self.assertIs(doc, session.world_import_document)
        with self.assertRaises(ValueError):
            session.import_world_capture(Document((2,2,2)), (4,5,6))
        self.assertIs(doc, session.world_import_document)
        session.library.pop()
        session.retry_world_import()
        bridge.drain()
        self.assertEqual(32, len(session.library))
        self.assertIsNone(session.world_import_document)

    def test_import_waits_for_io_and_save_load_cannot_replace_its_job(self):
        bridge = MemoryBridge()
        session = Session(bridge)
        previous = object()
        session.io_job = previous
        doc = Document((1,1,1))
        with self.assertRaises(ValueError):
            session.import_world_capture(doc, (1,2,3))
        self.assertIs(previous, session.io_job)
        self.assertIs(doc, session.world_import_document)
        session.io_job = None
        session.retry_world_import()
        job = session.io_job
        with self.assertRaises(ValueError):
            session.save()
        with self.assertRaises(ValueError):
            session.load(1)
        self.assertIs(job, session.io_job)
        bridge.drain()
        self.assertEqual(1, len(session.library))


if __name__ == '__main__':
    unittest.main()
