"""Collection bounds and exact owner/source checks need no live Minecraft."""
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import collect_scaffold_runtime_support as collector
import test_scaffold_runtime_catalogue as harness


class CollectionPlanningTests(unittest.TestCase):
    def test_all_dump_states_covered_once_and_final_range_not_truncated(self):
        size = len(collector.probe.dump_states())
        ranges = collector.segment_ranges(0, size)
        indices = [index for selected in ranges for index in range(selected['start_index'], selected['start_index'] + selected['count'])]
        self.assertEqual(indices, list(range(size)))
        self.assertTrue(all(0 < selected['count'] <= 256 for selected in ranges))
        self.assertEqual(collector.segment_ranges(size - 3, 3), [{'start_index': size - 3, 'count': 3}])
        for start, count in ((False, 10), (0, True), (-1, 3), (size - 2, 3), (0, 0)):
            with self.subTest(start=start, count=count), self.assertRaises(ValueError):
                collector.segment_ranges(start, count)

    def test_source_or_archive_mutation_blocks_the_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root, output = Path(directory) / 'root', Path(directory) / 'output'
            root.mkdir()
            source = root / 'probe.py'
            source.write_bytes(b'original')
            source_pins, archive_pins = collector.supervisor.archive_sources(root, output, [source])
            collector.verify_pins(output, source_pins, archive_pins)
            archived = output / next(iter(archive_pins))
            archived.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'Archived'):
                collector.verify_pins(output, source_pins, archive_pins)
            archived.write_bytes(b'original')
            source.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Frozen'):
                collector.verify_pins(output, source_pins, archive_pins)

    def test_completed_raw_receipt_is_revalidated_before_capability_union(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            path = output / 'segment.json'
            raw = b'{"original": true}'
            path.write_bytes(raw)
            records = [{'path': path.name, 'sha256': hashlib.sha256(raw).hexdigest()}]
            self.assertEqual(list(collector.completed_reports(output, records)), [{'original': True}])
            path.write_bytes(b'{"original": false}')
            with self.assertRaisesRegex(ValueError, 'receipt changed'):
                list(collector.completed_reports(output, records))


class ExactCollectionOwnerTests(harness.RuntimeCatalogueTests):
    def test_other_session_owner_or_game_cannot_supply_a_successful_segment(self):
        report = self.complete()
        session = {'id': self.identity['session_id'], 'owner': self.identity['owner'],
                   'game_pid': self.identity['game_pid'], 'game_identity': self.identity['game_identity']}
        self.assertEqual(24, len(collector.validate_owned_segment(report, session, 'a' * 64)))
        for key in ('session_id', 'owner', 'game_pid', 'game_identity'):
            changed = copy.deepcopy(report)
            changed['identity'][key] = 'another'
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'exact managed game'):
                collector.validate_owned_segment(changed, session, 'a' * 64)
        with self.assertRaises(ValueError):
            collector.validate_owned_segment(report, session, 'b' * 64)


if __name__ == '__main__':
    unittest.main()
