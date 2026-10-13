"""Independent owners share publication without losing failed cleanup ledgers."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'behavior_pack/modern_projection'))
from projection.cell import make_cell
from projection.item_sprite_projection import ItemProjection
from projection.item_sprite_profile import candidate_profile
from projection.liquid_projection import LiquidProjection
from projection.projection_companions import ProjectionCompanions
from projection.model import Document
from test_liquid_render import Runtime
from test_liquid_projection import profile
from test_static_frame_items import actor,frame


class CompanionTests(unittest.TestCase):
    def setUp(self):
        self.runtime=Runtime()
        self.runtime.session=SimpleNamespace(opacity=.5)
        self.document=Document((2,1,1),{(0,0,0):make_cell(frame(),('minecraft:water',0),actor()),
                                        (1,0,0):make_cell(frame(),nbt=actor(45.))})
        self.water=LiquidProjection(self.runtime,self.document,(10,64,20),profile([]),0)
        self.items=ItemProjection(self.runtime,self.document,(10,64,20),candidate_profile(),0)
        self.bundle=ProjectionCompanions((self.water,self.items))
        self.time=0.

    def finish(self):
        for unused in range(50):
            self.time+=.1
            with patch('projection.liquid_projection.time.time',return_value=self.time):
                if self.bundle.advance():return
        self.fail('Companion owners never became ready')

    def test_both_families_are_hidden_until_the_same_snapshot_is_published(self):
        serial=self.bundle.request(self.document.palette_data(),deferred=True)
        self.finish()
        self.assertEqual(2,len(self.runtime.models))
        self.assertTrue(all(self.runtime.hidden(model) for model in self.runtime.models))
        self.assertTrue(self.bundle.prepare_publication(serial))
        self.bundle.finalize_publication(serial)
        self.assertTrue(all(not self.runtime.hidden(model) for model in self.runtime.models))
        self.assertTrue(self.bundle.close())
        self.assertFalse(self.runtime.models)

    def test_item_publication_failure_restores_already_prepared_water(self):
        serial=self.bundle.request(deferred=True)
        self.finish()
        self.runtime.fail_show_model=next(iter(self.items.renderer.staging.values()))['model_id']
        self.assertFalse(self.bundle.prepare_publication(serial))
        self.assertTrue(all(self.runtime.hidden(model) for model in self.runtime.models))
        self.assertTrue(self.bundle.restore_publication())
        self.assertTrue(self.bundle.cancel_candidate(serial))
        self.assertTrue(self.bundle.close())
        self.assertFalse(self.runtime.models)

    def test_unreleased_resources_are_retained_and_retried_by_each_owner(self):
        serial=self.bundle.request(deferred=True)
        self.finish()
        self.assertTrue(self.bundle.prepare_publication(serial))
        self.bundle.finalize_publication(serial)
        self.runtime.remove_ok=False
        self.assertFalse(self.bundle.close())
        self.assertEqual(2,len(self.runtime.models))
        self.runtime.remove_ok=True
        self.assertTrue(self.bundle.close())
        self.assertFalse(self.runtime.models)

    def test_superseded_revision_cannot_publish_mixed_item_water_generations(self):
        old=self.bundle.request(deferred=True)
        self.finish()
        current=self.bundle.request(occupied=bytearray((2,0)),deferred=True)
        self.finish()
        self.assertFalse(self.bundle.prepare_publication(old))
        self.assertTrue(self.bundle.prepare_publication(current))
        self.bundle.finalize_publication(current)
        self.assertFalse(self.water.renderer.active)
        item=next(iter(self.items.renderer.active.values()))['group']
        self.assertEqual(1.,item.uniforms[3][1])
        self.assertEqual(1,int(item.uniforms[0][0])%64)
        self.assertTrue(self.bundle.close())

    def test_rejected_first_request_cancels_the_older_candidate_of_both_owners(self):
        old=self.bundle.request(deferred=True)
        self.finish()
        with patch.object(self.water,'request',side_effect=ValueError('rejected provider')):
            with self.assertRaises(ValueError):
                self.bundle.request(deferred=True)
        self.assertFalse(self.bundle.prepare_publication(old))
        self.assertFalse(self.bundle.prepare_publication(self.bundle.revision))
        self.assertFalse(self.items.renderer.staging)
        self.assertFalse(self.water.renderer.staging)
        self.assertTrue(self.bundle.close())

    def test_biome_reschedules_pending_pair_under_one_new_revision(self):
        old=self.bundle.request(deferred=True)
        self.finish()
        self.bundle.set_biome('swampland')
        current=self.bundle.revision
        self.assertGreater(current,old)
        self.finish()
        self.assertFalse(self.bundle.prepare_publication(old))
        self.assertTrue(self.bundle.prepare_publication(current))
        self.bundle.finalize_publication(current)
        self.assertEqual('swampland',self.water.document.biome)
        self.assertEqual('swampland',self.items.document.biome)
        self.assertTrue(self.bundle.close())

    def test_closed_and_finalized_bundle_cannot_publish_an_empty_candidate_list(self):
        serial=self.bundle.request(deferred=True)
        self.finish()
        self.assertTrue(self.bundle.prepare_publication(serial))
        self.bundle.finalize_publication(serial)
        self.assertFalse(self.bundle.prepare_publication(serial))
        self.assertTrue(self.bundle.close())
        with self.assertRaises(ValueError):self.bundle.request(deferred=True)
        self.assertFalse(self.bundle.prepare_publication(serial))


if __name__=='__main__':
    unittest.main()
