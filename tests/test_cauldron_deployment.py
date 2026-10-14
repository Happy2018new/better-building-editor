"""Prevent unqualified engine/resource/data changes from inheriting acceptance."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'behavior_pack/modern_projection'))
sys.path.insert(0,str(ROOT/'tools'))
from projection import cauldron_deployment as deployment
from projection import cauldron_qualification_data as qualification
from projection import cauldron_resource_data as resources
from projection.cauldron_native_data import SOURCE_SHA256
from projection.cauldron_profile import ENGINE_VERSION, candidate_profile
from projection.cell import actor_data, foreground
from projection.debug_cauldron_blueprints import CASES, source_document
from qualify_cauldron_r15 import IMPLEMENTATION, REPORTS, identity, validate_sources


class CauldronDeploymentTests(unittest.TestCase):
    def test_exact_engine_enables_verified_profile_and_unknown_versions_remain_native(self):
        profile=deployment.production_profile(ENGINE_VERSION)
        candidate=candidate_profile()
        self.assertIsNotNone(profile)
        self.assertEqual(candidate.identity,profile.identity[:len(candidate.identity)])
        self.assertEqual(candidate.models,profile.models)
        self.assertEqual(candidate.world_models,profile.world_models)
        for version in (None,'3.9.0','3.10.0.420448','3.11.0'):
            self.assertIsNone(deployment.production_profile(version))
        with patch.object(qualification,'PRODUCT_QUALIFIED',False):
            self.assertIsNone(deployment.production_profile(ENGINE_VERSION))

    def test_changed_resources_data_or_missing_gate_rejects_previous_visible_acceptance(self):
        for field in ('QUALIFICATION_RESOURCE_CONTRACT_SHA256',
                      'QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256',
                      'QUALIFICATION_NATIVE_DATA_SHA256','QUALIFICATION_SHA256'):
            with self.subTest(field=field), patch.object(qualification,field,'changed'):
                with self.assertRaises(ValueError):
                    deployment.production_profile(ENGINE_VERSION)
        for gate in deployment.REQUIRED_GATES:
            gates=dict(qualification.GATES,**{gate:False})
            with self.subTest(gate=gate),patch.object(qualification,'GATES',gates):
                with self.assertRaises(ValueError):
                    deployment.production_profile(ENGINE_VERSION)

    def test_current_bundle_and_kept_evidence_match_the_generated_runtime_gate(self):
        evidence=ROOT/'docs/evidence/cauldron-product-r15'
        raw=(evidence/'qualification.json').read_bytes()
        manifest=json.loads(raw)
        self.assertEqual(qualification.QUALIFICATION_SHA256,hashlib.sha256(raw).hexdigest())
        self.assertEqual(SOURCE_SHA256,manifest['native_data_sha256'])
        self.assertEqual(resources.RESOURCE_CONTRACT_SHA256,manifest['resource_contract_sha256'])
        self.assertEqual(resources.IMPLEMENTATION_CONTRACT_SHA256,
                         identity(manifest['implementation_sha256']))
        self.assertEqual(set(IMPLEMENTATION),set(manifest['implementation_sha256']))
        for relative,expected in manifest['evidence_sha256'].items():
            self.assertEqual(expected,hashlib.sha256((evidence/relative).read_bytes()).hexdigest(),relative)
        reports=[json.loads((evidence/name).read_bytes()) for name in REPORTS]
        contract=json.loads((ROOT/'tools/data/cauldron_resource_contract_nemc310_v1.json').read_bytes())
        self.assertEqual(manifest['implementation_sha256'],validate_sources(ROOT,reports,contract))

    def test_every_public_gallery_appearance_has_a_qualified_top(self):
        profile=deployment.production_profile(ENGINE_VERSION)
        self.assertEqual(33,len(CASES))
        for row in CASES:
            document=source_document(row['id'])
            cell=document.get((3,3,3))
            before=document.to_data()
            with self.subTest(case=row['id']):
                self.assertIsNotNone(profile.top(foreground(cell),actor_data(cell),document.biome))
                self.assertEqual(before,document.to_data())


if __name__=='__main__':
    unittest.main()
