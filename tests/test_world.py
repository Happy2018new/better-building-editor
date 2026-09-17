"""Exercise failed writes, preflight protection and conflict-aware undo with a fake world."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.model import AIR, Document
from projection.world import WorldJob

STONE = ('minecraft:stone', 0)
WOOD = ('minecraft:planks', 1)


class World(object):
    def __init__(self):
        self.blocks = {}
        self.protected_cells = set()
        self.unloaded = set()
        self.fail_at = None
        self.creative = True
        self.writes = 0

    def allowed(self):
        return self.creative

    def read(self, p):
        return None if p in self.unloaded else self.blocks.get(p, AIR)

    def write(self, p, value):
        if p == self.fail_at:
            return False
        self.writes += 1
        self.blocks[p] = value
        return True

    def protected(self, p, value):
        return p in self.protected_cells

    def valid(self, value):
        return value in (AIR, STONE, WOOD)


def complete(job):
    for i in range(100):
        job.step(2)
        if job.done:
            return
    raise AssertionError('job failed to finish')


class WorldTests(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.doc = Document((3, 1, 1), {(i, 0, 0): STONE for i in range(3)})

    def test_preflight_protected_or_unloaded_never_writes(self):
        for field in ('protected_cells', 'unloaded'):
            w = World()
            getattr(w, field).add((2, 0, 0))
            job = WorldJob(w, self.doc, (0, 0, 0))
            complete(job)
            self.assertTrue(job.error)
            self.assertEqual(w.writes, 0)

    def test_failure_rolls_back_earlier_batches(self):
        self.world.fail_at = (2, 0, 0)
        job = WorldJob(self.world, self.doc, (0, 0, 0))
        complete(job)
        self.assertTrue(job.error)
        self.assertTrue(all(self.world.read((i, 0, 0)) == AIR for i in range(3)))
        self.assertEqual(job.journal, [])

    def test_undo_preserves_other_player_changes(self):
        job = WorldJob(self.world, self.doc, (0, 0, 0))
        complete(job)
        self.world.blocks[(1, 0, 0)] = WOOD
        undo = WorldJob(self.world, None, (0, 0, 0), job.journal)
        complete(undo)
        self.assertEqual(undo.skipped, 1)
        self.assertEqual([self.world.read((i, 0, 0)) for i in range(3)], [AIR, WOOD, AIR])

    def test_permission_loss_during_write_rolls_back(self):
        job = WorldJob(self.world, self.doc, (0, 0, 0))
        while not job.journal:
            job.step(1)
        self.world.creative = False
        complete(job)
        self.assertTrue(job.error)
        self.assertEqual(self.world.read((0, 0, 0)), AIR)

    def test_unloaded_rollback_keeps_recovery_journal(self):
        job = WorldJob(self.world, self.doc, (0, 0, 0))
        while not job.journal:
            job.step(1)
        self.world.unloaded.add((0, 0, 0))
        self.world.fail_at = (1, 0, 0)
        complete(job)
        self.assertTrue(job.error)
        self.assertEqual(len(job.journal), 1)

    def test_survival_and_identical_blocks_never_write(self):
        self.world.creative = False
        job = WorldJob(self.world, self.doc, (0, 0, 0))
        complete(job)
        self.assertEqual(self.world.writes, 0)
        self.world.creative = True
        self.world.blocks = dict(self.doc.blocks)
        job = WorldJob(self.world, self.doc, (0, 0, 0))
        complete(job)
        self.assertEqual(self.world.writes, 0)

    def test_air_sync_is_opt_in_and_undoable(self):
        self.world.blocks[(0, 0, 0)] = STONE
        empty = Document((1, 1, 1))
        additive = WorldJob(self.world, empty, (0, 0, 0))
        complete(additive)
        self.assertEqual(self.world.read((0, 0, 0)), STONE)
        sync = WorldJob(self.world, empty, (0, 0, 0), include_air=True)
        complete(sync)
        self.assertEqual(self.world.read((0, 0, 0)), AIR)
        undo = WorldJob(self.world, None, (0, 0, 0), sync.journal)
        complete(undo)
        self.assertEqual(self.world.read((0, 0, 0)), STONE)


if __name__ == '__main__':
    unittest.main()
