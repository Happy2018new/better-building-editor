"""Exercise failed writes, air synchronization and automatic rollback."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
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

    def test_air_sync_is_opt_in(self):
        self.world.blocks[(0, 0, 0)] = STONE
        empty = Document((1, 1, 1))
        additive = WorldJob(self.world, empty, (0, 0, 0))
        complete(additive)
        self.assertEqual(self.world.read((0, 0, 0)), STONE)
        sync = WorldJob(self.world, empty, (0, 0, 0), include_air=True)
        complete(sync)
        self.assertEqual(self.world.read((0, 0, 0)), AIR)

    def test_write_exception_after_mutation_is_recovered_without_stuck_job(self):
        original=self.world.write
        def broken(pos,value):
            result=original(pos,value)
            if value==STONE: raise RuntimeError('readback/setter failure')
            return result
        self.world.write=broken
        job=WorldJob(self.world,self.doc,(0,0,0))
        complete(job)
        self.assertTrue(job.error)
        self.assertEqual(AIR,self.world.read((0,0,0)))

    def test_native_normalization_is_used_for_plan_and_recovery_journal(self):
        legacy=('minecraft:wool',14)
        self.world.canonical=lambda value: STONE if value==legacy else value
        job=WorldJob(self.world,Document((1,1,1),{(0,0,0):legacy}),(0,0,0))
        complete(job)
        self.assertFalse(job.error)
        self.assertEqual(STONE,job.journal[0][2])

    def test_equivalent_legacy_target_is_not_reported_as_changed(self):
        legacy=('minecraft:grass',0)
        modern=('minecraft:grass_block',0)
        self.world.blocks[(0,0,0)] = legacy
        self.world.canonical=lambda value: modern if value == legacy else value
        self.world.valid=lambda value: value in (AIR, legacy, modern, STONE, WOOD)
        job = WorldJob(self.world, Document((1,1,1), {(0,0,0): modern}), (0,0,0))
        complete(job)
        self.assertFalse(job.error)
        self.assertEqual(0, self.world.writes)

    def test_changed_pending_target_is_replaced_using_current_rollback_value(self):
        self.world.blocks[(1,0,0)] = WOOD
        job = WorldJob(self.world, self.doc, (0,0,0))
        while not job.journal:
            job.step(1)
        self.world.blocks[(1,0,0)] = AIR
        self.world.fail_at = (2,0,0)
        complete(job)
        self.assertIn('方块写入失败', job.error)
        self.assertEqual(AIR, self.world.read((0,0,0)))
        self.assertEqual(AIR, self.world.read((1,0,0)))

    def test_native_neighbor_state_change_does_not_abort_overwrite(self):
        leaves = ('minecraft:oak_leaves',2)
        updated = ('minecraft:oak_leaves',3)
        self.world.blocks[(1,0,0)] = leaves
        original = self.world.write
        def write(pos, value):
            result = original(pos, value)
            if pos == (0,0,0) and value == STONE:
                self.world.blocks[(1,0,0)] = updated
            return result
        self.world.write = write
        job = WorldJob(self.world, self.doc, (0,0,0))
        complete(job)
        self.assertFalse(job.error)
        self.assertTrue(all(self.world.read((i,0,0)) == STONE for i in range(3)))
        self.assertEqual(updated, job.journal[1][1])

    def test_newly_protected_target_aborts_and_rolls_back(self):
        job = WorldJob(self.world, self.doc, (0,0,0))
        while not job.journal:
            job.step(1)
        self.world.protected_cells.add((1,0,0))
        complete(job)
        self.assertIn('受保护', job.error)
        self.assertEqual(AIR, self.world.read((0,0,0)))
        self.assertEqual(AIR, self.world.read((1,0,0)))

    def test_rollback_keeps_later_external_edits(self):
        job = WorldJob(self.world, self.doc, (0,0,0))
        while not job.journal:
            job.step(1)
        self.world.blocks[(0,0,0)] = WOOD
        self.world.fail_at = (1,0,0)
        complete(job)
        self.assertTrue(job.error)
        self.assertEqual(WOOD, self.world.read((0,0,0)))


if __name__ == '__main__':
    unittest.main()
