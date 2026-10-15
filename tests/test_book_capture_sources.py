"""Material mutations must invalidate book evidence even with an old contract."""
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from probe_book_native_r16 import (book_sources, candidate_setup, CANDIDATE_RESTORE,
                                   BookAudit, CLIENT)


class BookCaptureSourceTests(unittest.TestCase):
    def test_actual_materials_are_fingerprinted_without_diagnostic_aliases(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            files = {
                'tools/data/book_resource_contract_nemc310_v1.json': {'output_sha256': {}},
                'resource_pack/models/netease_models.json': {},
                'resource_pack/materials/entity.material': {'materials': {}},
            }
            registry = files['resource_pack/models/netease_models.json']
            materials = files['resource_pack/materials/entity.material']['materials']
            for family in ('enchanting_table', 'lectern'):
                for suffix in ('', '_world'):
                    name = 'modern_projection_book_' + family + suffix
                    registry[name] = {'material': name}
                    materials[name + ':entity_for_skeleton_alpha'] = {
                        '+states': ['Blending'], '-states': ['DisableDepthWrite'],
                        'vertexShader': 'shaders/book.vertex',
                        'fragmentShader': 'shaders/book.fragment',
                    }
            for relative, value in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding='ascii')
            for suffix in ('vertex', 'fragment'):
                path = root / ('resource_pack/shaders/book.' + suffix)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('shader fixture', encoding='ascii')
            before = book_sources(root)
            first = next(iter(materials.values()))
            first['+states'].append('DisableCulling')
            (root / 'resource_pack/materials/entity.material').write_text(
                json.dumps({'materials': materials}), encoding='ascii')
            after = book_sources(root)
            self.assertEqual(before['contract_sha256'], after['contract_sha256'])
            self.assertEqual(before['files'], after['files'])
            self.assertNotEqual(before['materials'], after['materials'])

    def test_owner_changes_invalidate_evidence_without_a_resource_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for relative, data in (
                    ('tools/data/book_resource_contract_nemc310_v1.json', {'output_sha256': {}}),
                    ('resource_pack/models/netease_models.json', dict(
                        (name, {'material': name}) for name in (
                            'modern_projection_book_lectern', 'modern_projection_book_lectern_world',
                            'modern_projection_book_enchanting_table', 'modern_projection_book_enchanting_table_world'))),
                    ('resource_pack/materials/entity.material', {'materials': dict(
                        (name + ':entity_for_skeleton_alpha', {'vertexShader':'shaders/book.vertex',
                            'fragmentShader':'shaders/book.fragment'}) for name in (
                            'modern_projection_book_lectern', 'modern_projection_book_lectern_world',
                            'modern_projection_book_enchanting_table', 'modern_projection_book_enchanting_table_world'))})):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data), encoding='ascii')
            for suffix in ('vertex', 'fragment'):
                shader = root / ('resource_pack/shaders/book.' + suffix)
                shader.parent.mkdir(parents=True, exist_ok=True)
                shader.write_text('book shader fixture', encoding='ascii')
            owner = root / 'behavior_pack/modern_projection/projection/world_projection.py'
            owner.parent.mkdir(parents=True)
            owner.write_text('book owner version one', encoding='ascii')
            before = book_sources(root)
            owner.write_text('book owner version two', encoding='ascii')
            after = book_sources(root)
            self.assertEqual(before['files'], after['files'])
            self.assertEqual(before['materials'], after['materials'])
            self.assertNotEqual(before['owner_files'], after['owner_files'])

    def test_candidate_setup_and_restore_keep_the_portal_owner_unchanged(self):
        original = object()
        portal = object()
        events = []
        session = SimpleNamespace(book_profile=original, portal_profile=portal, emit=events.append)
        profile = SimpleNamespace(models={'lectern': 'ui'}, world_models={'lectern': 'world'}, identity=(1,))
        package = ModuleType('modern_projection.projection.book_profile')
        package.candidate_profile = lambda: profile
        body = SimpleNamespace(CANDIDATE_ENABLED=False)
        projection_package = ModuleType('modern_projection.projection')
        projection_package.static_table = body
        scope = {'sys': SimpleNamespace(), 's': session}
        with patch.dict(sys.modules, {'modern_projection.projection.book_profile': package,
                                     'modern_projection.projection': projection_package}):
            exec(candidate_setup('raster_')[len(CLIENT):], scope)
            self.assertTrue(body.CANDIDATE_ENABLED)
            self.assertIs(profile, session.book_profile)
            exec(CANDIDATE_RESTORE[len(CLIENT):], scope)
        self.assertEqual({'lectern': 'raster_ui'}, profile.models)
        self.assertEqual({'lectern': 'raster_world'}, profile.world_models)
        self.assertIs(portal, session.portal_profile)
        self.assertIs(original, session.book_profile)
        self.assertIs(portal, session.portal_profile)
        self.assertFalse(hasattr(scope['sys'], '_book_r16_saved'))
        self.assertFalse(hasattr(scope['sys'], '_book_r18_body_saved'))
        self.assertFalse(body.CANDIDATE_ENABLED)
        self.assertEqual(['preview', 'preview'], events)

    def test_frame_receipt_reads_opacity_from_the_active_book_group(self):
        owner = type('BookProjection', (), {})()
        owner.renderer = SimpleNamespace(active={1: {'group': SimpleNamespace(
            model_name='modern_projection_book_lectern_world', uniforms=(None,None,None,(1.,1.,1.,.7)))}})
        preview = SimpleNamespace(groups={1: object()})
        session = SimpleNamespace(projection_active=True, book_profile=SimpleNamespace(identity=(1,)),
                                  book_preview=preview, book_controls=object())
        audit = SimpleNamespace(args=SimpleNamespace(model_prefix=''))
        def execute(label, code):
            scope = {'b': SimpleNamespace(projection_liquid=owner), 's': session}
            exec(code[len(CLIENT):], scope)
            return scope['_result']
        audit.execute = execute
        with patch('probe_book_native_r16.BannerAudit.frame', return_value={}):
            result = BookAudit.frame(audit, 'full_lectern.book_motion0')
        self.assertEqual([.7], result['book_models']['world_opacity'])
        self.assertTrue(result['book_models']['preview_owned'])


if __name__ == '__main__':
    unittest.main()
