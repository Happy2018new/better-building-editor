"""Exercise bounded writes, continued failures and cancellation."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.cell import make_cell
from projection.model import AIR, Document
from projection.world import WorldJob

STONE = ('minecraft:stone', 0)
WOOD = ('minecraft:planks', 1)


class World(object):
    def __init__(self):
        self.blocks = {}
        self.failed = set()
        self.attempts = []

    def write(self, pos, value, origin):
        self.attempts.append((pos, value, origin))
        if pos in self.failed:
            return False
        self.blocks[pos] = value
        return True


def complete(job):
    for unused in range(100):
        job.step(2)
        if job.done:
            return
    raise AssertionError('job failed to finish')


class WorldTests(unittest.TestCase):
    def test_failed_cell_is_recorded_and_later_cells_are_written(self):
        world = World()
        world.failed.add((1, 64, 0))
        doc = Document((3, 1, 1), {(i, 0, 0): STONE for i in range(3)})
        job = WorldJob(world, doc, (0, 64, 0))
        complete(job)
        self.assertEqual(3, job.cursor)
        self.assertEqual((2, 1), (job.written, job.failed))
        self.assertEqual([(0, 64, 0), (1, 64, 0), (2, 64, 0)],
                         [row[0] for row in world.attempts])
        self.assertEqual(STONE, world.blocks[(2, 64, 0)])
        self.assertIn('2 格成功，1 格失败', job.error)
        self.assertIn('首处失败 (1, 64, 0)：写入接口返回失败', job.error)
        self.assertEqual([((1, 64, 0), '写入接口返回失败')], job.failures)

    def test_write_exception_is_a_cell_failure_and_does_not_stop_job(self):
        world = World()
        original = world.write

        def write(pos, value, origin):
            if pos == (1, 0, 0):
                raise RuntimeError('setter failed')
            return original(pos, value, origin)

        world.write = write
        doc = Document((3, 1, 1), {(i, 0, 0): STONE for i in range(3)})
        job = WorldJob(world, doc, (0, 0, 0))
        complete(job)
        self.assertEqual((2, 1), (job.written, job.failed))
        self.assertEqual(STONE, world.blocks[(2, 0, 0)])
        self.assertEqual((1, 0, 0), job.failures[0][0])
        self.assertEqual('setter failed', job.failures[0][1])

    def test_unexpected_sdk_exception_is_recorded_and_later_cells_are_written(self):
        world = World()
        original = world.write

        def write(pos, value, origin):
            if pos == (1, 0, 0):
                raise Exception('native setter fault')
            return original(pos, value, origin)

        world.write = write
        doc = Document((3, 1, 1), {(i, 0, 0): STONE for i in range(3)})
        job = WorldJob(world, doc, (0, 0, 0))
        complete(job)
        self.assertEqual((2, 1), (job.written, job.failed))
        self.assertEqual(STONE, world.blocks[(2, 0, 0)])
        self.assertEqual('native setter fault', job.failures[0][1])

    def test_cancel_stops_only_future_writes(self):
        world = World()
        doc = Document((3, 1, 1), {(i, 0, 0): STONE for i in range(3)})
        job = WorldJob(world, doc, (0, 64, 0))
        job.step(1)
        self.assertEqual(1, job.written)
        job.cancel()
        complete(job)
        self.assertTrue(job.cancelled)
        self.assertEqual(1, job.cursor)
        self.assertEqual(1, len(world.attempts))
        self.assertIn('已写入 1 格', job.error)

    def test_optional_validation_receives_local_position_and_document_before_writing(self):
        world = World()
        checked = []
        doc = Document((3, 1, 1), {(i, 0, 0): STONE for i in range(3)})

        def validate(document, local, value):
            checked.append((document, local, value, len(world.attempts)))
            if local == (1, 0, 0):
                raise ValueError('invalid compound part')

        world.validate_write = validate
        job = WorldJob(world, doc, (5, 64, 9))
        # The optional adapter hook is resolved once for the job.
        world.validate_write = lambda *args: self.fail('hook must be cached')
        complete(job)
        self.assertEqual([(doc, (0, 0, 0), STONE, 0),
                          (doc, (1, 0, 0), STONE, 1),
                          (doc, (2, 0, 0), STONE, 1)], checked)
        self.assertEqual([(5, 64, 9), (7, 64, 9)],
                         [row[0] for row in world.attempts])
        self.assertEqual((2, 1), (job.written, job.failed))
        self.assertEqual([((6, 64, 9), 'invalid compound part')], job.failures)

    def test_cancel_stops_future_validation_and_native_writes(self):
        world = World()
        checked = []
        world.validate_write = lambda doc, local, value: checked.append(local)
        doc = Document((3, 1, 1), {(i, 0, 0): STONE for i in range(3)})
        job = WorldJob(world, doc, (5, 64, 9))
        job.step(1)
        job.cancel()
        complete(job)
        self.assertEqual([(0, 0, 0)], checked)
        self.assertEqual([(5, 64, 9)], [row[0] for row in world.attempts])

    def test_cancel_preserves_first_failure_coordinate_and_reason(self):
        world = World()
        world.failed.add((5, 64, 9))
        doc = Document((3, 1, 1), {(i, 0, 0): STONE for i in range(3)})
        job = WorldJob(world, doc, (5, 64, 9))
        job.step(2)
        job.cancel()
        complete(job)
        self.assertEqual((1, 1), (job.written, job.failed))
        self.assertEqual(2, len(world.attempts))
        self.assertIn('首处失败 (5, 64, 9)：写入接口返回失败', job.error)

    def test_include_air_is_opt_in(self):
        world = World()
        doc = Document((1, 1, 1), {(0, 0, 0): STONE})
        additive = WorldJob(world, Document((1, 1, 1)), (0, 0, 0))
        complete(additive)
        self.assertEqual([], world.attempts)
        sync = WorldJob(world, Document((1, 1, 1)), (0, 0, 0), include_air=True)
        world.blocks[(0, 0, 0)] = STONE
        complete(sync)
        self.assertEqual(AIR, world.blocks[(0, 0, 0)])

    def test_document_iteration_preserves_lower_y_compound_order_and_full_cells(self):
        lower = make_cell(('minecraft:oak_door', 0), AIR)
        upper = make_cell(('minecraft:oak_door', 8), AIR)
        doc = Document((1, 2, 1), {(0, 1, 0): upper, (0, 0, 0): lower})
        world = World()
        job = WorldJob(world, doc, (5, 64, 9))
        complete(job)
        self.assertEqual([(5, 64, 9), (5, 65, 9)],
                         [row[0] for row in world.attempts])
        self.assertEqual([lower, upper], [row[1] for row in world.attempts])
        self.assertEqual((5, 64, 9), world.attempts[0][2])


if __name__ == '__main__':
    unittest.main()
