"""Portal ownership must survive native caches and missing-projection rebuilds."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_bridge
from test_tiles import Bridge
from projection.cell import make_cell
from projection.geometry_palette import prepare_palette
from projection.model import Document
from projection.portal_profile import candidate_profile, production_profile
from projection import portal_profile
from projection.render_context import ContextBatchBuilder
from projection.session import Session


class PortalIntegrationTests(unittest.TestCase):
    def document(self):
        return Document((3,2,2),{
            (0,1,0):make_cell(('minecraft:end_portal',0),nbt={'id':{'__type__':8,'__value__':'EndPortal'}}),
            (1,1,0):make_cell(('minecraft:end_gateway',0),nbt={'custom':{'retained':True}}),
            (0,0,0):('minecraft:stone',0)})

    def test_render_only_suppression_preserves_original_cell_nbt_and_unrelated_blocks(self):
        document=self.document()
        original=deepcopy(document.to_data())
        palette=document.palette_data()
        source=deepcopy(palette)
        profile=candidate_profile()
        prepared=prepare_palette(palette,portal_profile=profile)
        self.assertEqual({('minecraft:stone',0)},set(prepared['common']))
        self.assertFalse(prepared['actor'])
        self.assertEqual(profile.identity,prepared['_portal_profile'])
        self.assertEqual(source,palette)
        self.assertEqual(original,document.to_data())
        self.assertIsNone(production_profile('3.9.0.401155'))
        with patch.object(portal_profile,'PRODUCT_QUALIFIED',False):
            self.assertIsNone(production_profile('3.10.0.420447'))
        self.assertIsNotNone(production_profile('3.10.0.420447'))

    def test_pure_portal_remains_logical_target_with_no_unsupported_native_draw(self):
        document=Document((1,1,1),{(0,0,0):('minecraft:end_portal',0)})
        builder=ContextBatchBuilder(document,document.palette_data(),portal_profile=candidate_profile())
        for unused in builder.prepare():pass
        self.assertEqual([],builder.data['_context_batches'])
        self.assertEqual([(0,0,0)],list(builder.positions))
        self.assertEqual(('minecraft:end_portal',0),document.get((0,0,0)))

    def test_editor_cache_changes_native_ownership_and_reuses_prior_owner(self):
        bridge=Bridge();session=Session(bridge)
        session._loaded(self.document());bridge.settle(session)
        before=deepcopy(session.editor.document.to_data())
        builds=len(bridge.builds)
        original=session.tiles.parts[(0,0,0)]['name']
        session.portal_profile=candidate_profile()
        session.refresh_preview();bridge.settle(session)
        self.assertEqual(builds+1,len(bridge.builds))
        session.portal_profile=candidate_profile()
        session.refresh_preview();bridge.settle(session)
        self.assertEqual(builds+1,len(bridge.builds))
        session.portal_profile=None
        session.refresh_preview();bridge.settle(session)
        self.assertEqual(original,session.tiles.parts[(0,0,0)]['name'])
        self.assertEqual(before,session.editor.document.to_data())

    def test_missing_dynamic_rebuild_keeps_portals_out_of_native_palette(self):
        from test_occupancy_review import Runtime
        from modern_projection.projection.occupancy import ProjectionOccupancy
        from modern_projection.projection.large_preview import SurfacePalette
        document=self.document();runtime=Runtime();profile=candidate_profile()
        session=SimpleNamespace(editor=SimpleNamespace(document=document,layer=None),
                                preview_hidden=lambda: (),solo_layer=False,opacity=1.,
                                projection_missing=True,portal_profile=profile)
        bridge=SimpleNamespace(session=session,factory=runtime,system=runtime,level='level',
                               projection_serial=1,alive=True,entity=None,projection_occupancy=None,
                               projection_mesh=None,models={},model_layouts={})
        tracker=ProjectionOccupancy(bridge,(100,64,100))
        session.portal_profile=None
        self.assertIs(profile,tracker.portal_profile)
        for position in document.blocks:tracker.initial_visible(position)
        tracker.snapshot=tracker.state[:];tracker.output=SurfacePalette(document.size)
        for unused in tracker.prepare():pass
        for origin,context,data in tracker.prepared['_context_batches']:
            self.assertTrue(all(value[0] not in profile.supported_names for value in data['common']))
            self.assertTrue(all(name not in profile.supported_names for name in data['actor']))


if __name__=='__main__':unittest.main()
