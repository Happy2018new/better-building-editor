"""Reject drift in the diagnostic parser before it can conceal a dependency."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('projection_transform_probe_r29',
    ROOT / 'tools/probe_projection_transform_r29.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class ProjectionProbeSourcesTest(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'probe.py'
            path.write_text(text, encoding='utf8')
            return probe.explicit_sources(path, 'SOURCES')

    def test_literal_and_named_prefixes_match_real_declarations(self):
        for prefix in (repr(probe.MODULE), 'MODULE'):
            source = 'MODULE=%r\nSOURCES=tuple(%s+name+".py" for name in ("session","projection_transform"))' % (probe.MODULE, prefix)
            self.assertEqual(self.parse(source), (probe.MODULE + 'session.py', probe.MODULE + 'projection_transform.py'))

    def test_unknown_expression_rejected_without_execution(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported source expression'):
            self.parse('SOURCES=tuple(danger(name) for name in ("session",))')

    def test_conditional_dependency_omission_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Conditional source'):
            self.parse('SOURCES=tuple("x"+name for name in ("session",) if name!="session")')

    def test_outside_prefix_cannot_be_misreported_as_projection(self):
        with self.assertRaisesRegex(ValueError, 'leaves the reviewed'):
            self.parse('SOURCES=tuple("other/"+name+".py" for name in ("session",))')

    def test_duplicate_dependencies_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.parse('SOURCES=tuple(%r+name+".py" for name in ("session","session"))' % probe.MODULE)

    def test_ambiguous_reassignment_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Expected one explicit'):
            self.parse('SOURCES=()\nSOURCES=()')

    def test_real_current_contract_reports_missing_new_helper(self):
        result = probe.source_audit(ROOT, [probe.MODULE + 'nonexistent_r29_control.py'])
        self.assertFalse(result['all_requested_helpers_declared'])
        for scope in result['scopes'].values():
            self.assertEqual(scope['requested_helpers_missing'], [probe.MODULE + 'nonexistent_r29_control.py'])

    def test_real_owners_cover_both_new_execution_dependencies(self):
        result = probe.source_audit(ROOT, [probe.MODULE + name + '.py'
            for name in ('projection_transform', 'projection_target', 'error_text')])
        self.assertTrue(result['all_requested_helpers_declared'])

    def test_changed_helper_is_reported_even_when_it_remains_declared(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            dependencies = ('projection_transform', 'projection_target')
            source_hashes = {}
            for name in dependencies:
                path = project / (probe.MODULE + name + '.py')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('original = True\n', encoding='ascii')
                source_hashes[path.relative_to(project).as_posix()] = probe.digest(path, True)
            for filename, variable in (
                ('generate_liquid_product_owner_contract.py', 'SOURCES'),
                ('probe_portal_product_r16.py', 'SOURCES'),
                ('probe_book_native_r16.py', 'OWNER_SOURCES')):
                path = project / 'tools' / filename
                path.parent.mkdir(exist_ok=True)
                path.write_text('%s=tuple(%r+name+".py" for name in %r)\n' %
                                (variable, probe.MODULE, dependencies), encoding='ascii')
            contract = project / 'tools/data/liquid_product_owner_contract_v1.json'
            contract.parent.mkdir()
            contract.write_text(json.dumps({'source_sha256': source_hashes,
                'generator_sha256': probe.digest(project / 'tools/generate_liquid_product_owner_contract.py', True)}))
            changed = project / (probe.MODULE + 'projection_target.py')
            changed.write_text('original = False\n', encoding='ascii')
            result = probe.source_audit(project, list(source_hashes))
            self.assertTrue(result['all_requested_helpers_declared'])
            self.assertEqual([row['path'] for row in result['water_source_differences']],
                             [probe.MODULE + 'projection_target.py'])
            self.assertFalse(result['water_generator_changed'])


if __name__ == '__main__':
    unittest.main()
