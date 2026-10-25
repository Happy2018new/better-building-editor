"""Keep the dimension selected before transport through first-packet delivery."""
import unittest
from unittest.mock import patch

import test_server_stream as fixture
from modern_projection.projection.model import Document
from modern_projection.projection.transfer import packets


class WorldRequestDimensionTests(unittest.TestCase):
    read_entity = fixture.ServerStreamTests.read_entity
    read_palette = fixture.ServerStreamTests.read_palette
    write = fixture.ServerStreamTests.write
    write_palette = fixture.ServerStreamTests.write_palette
    set_actor = fixture.ServerStreamTests.set_actor
    set_liquid = fixture.ServerStreamTests.set_liquid
    finish = fixture.ServerStreamTests.finish

    def setUp(self):
        fixture.ServerStreamTests.setUp(self)
        self.document = Document((1, 1, 1), {(0, 0, 0): ('minecraft:stone', 0)})
        self.stream = list(packets(self.document))

    def begin(self, identity, action='apply', **fields):
        args = dict(__id__='player', request=identity, action=action,
                    origin=(0, 64, 0), stream=self.stream[0])
        args.update(fields)
        self.host.request(args)

    def complete(self, identity, **fields):
        for packet in self.stream[1:]:
            args = dict(__id__='player', request=identity,
                        action='upload', stream=packet)
            args.update(fields)
            self.host.request(args)
        self.finish()

    def test_changed_dimension_rejects_before_receiver_and_next_request_succeeds(self):
        self.dimension = 1
        for identity, action in enumerate(('apply', 'check'), 1):
            with self.subTest(action=action), patch.object(
                    fixture.server, 'Receiver', side_effect=AssertionError('decoded stale request')):
                self.begin(identity, action, expectedDimension=0)
            self.assertEqual({}, self.host.uploads)
            self.assertEqual({}, self.host.jobs)
            self.assertEqual([], self.writes)
            self.assertIn('维度', self.replies[-1][2]['error'])
        self.begin(3, expectedDimension=1)
        self.complete(3)
        self.assertEqual([(0, 64, 0)], self.writes)
        self.assertEqual(1, self.palette_writes[0][1])
        self.assertEqual(1, self.allowed_checks)

    def test_malformed_explicit_dimension_rejects_even_when_equal_to_zero(self):
        for identity, dimension in enumerate((None, False, True, 0., '0', [], {}), 1):
            with self.subTest(dimension=dimension):
                self.begin(identity, expectedDimension=dimension)
                self.assertEqual({}, self.host.uploads)
                self.assertEqual({}, self.host.jobs)
                self.assertIn('维度', self.replies[-1][2]['error'])
        self.assertEqual([], self.writes)

    def test_matching_native_and_custom_dimensions_write_the_declared_dimension(self):
        for identity, dimension in enumerate((0, 1, 2, 4), 1):
            with self.subTest(dimension=dimension):
                self.dimension = dimension
                self.begin(identity, expectedDimension=dimension)
                self.complete(identity)
                self.assertEqual(dimension, self.palette_writes[-1][1])
                self.assertEqual({}, self.host.jobs)
                self.assertEqual({}, self.host.uploads)
        self.assertEqual(4, len(self.writes))
        self.assertEqual(4, self.allowed_checks)

    def test_legacy_omission_keeps_existing_transport_behavior(self):
        self.dimension = 1
        self.begin(1)
        self.complete(1)
        self.assertEqual([(0, 64, 0)], self.writes)
        self.assertEqual(1, self.palette_writes[0][1])

    def test_later_packet_cannot_replace_the_first_packets_expected_dimension(self):
        self.begin(1, expectedDimension=0)
        self.complete(1, expectedDimension=1)
        self.assertEqual([(0, 64, 0)], self.writes)
        self.assertEqual(0, self.palette_writes[0][1])

    def test_completed_upload_entry_also_enforces_its_frozen_dimension(self):
        self.dimension = 1
        self.host.request(dict(__id__='player', request=1, action='apply',
                               origin=(0, 64, 0), expectedDimension=0),
                          transferred=self.document)
        self.assertEqual({}, self.host.jobs)
        self.assertEqual([], self.writes)
        self.assertIn('维度', self.replies[-1][2]['error'])


if __name__ == '__main__':
    unittest.main()
