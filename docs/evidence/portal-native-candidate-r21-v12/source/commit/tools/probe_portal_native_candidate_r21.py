"""Inspect six normal-clock candidate views through existing editor/world owners."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

os.environ['OPENBLAS_NUM_THREADS'] = '1'

from audit_native_visual_r15 import save, WGC
from capture_native_window import capture
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from probe_portal_product_r16 import document, PORTAL_STATUS
from probe_portal_reference_r19 import (near_player, portal_pixels, server, view,
                                        SAVE_PLAYER, RESTORE_PLAYER)
from probe_product_water import snapshot_digest, snapshot_sources
from verify_debug_blueprints import BlueprintCheck, Client, INSTALL_PROBE, RESTORE
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code

FAMILIES = ('end_gateway', 'end_portal')
LIMIT = 6 * 1024 ** 3


class CandidateCheck(BlueprintCheck):
    def __init__(self, client, args, report):
        super().__init__(client, args.output / 'report.json', 40.)
        self.args, self.report, self.counter, self.cleaning = args, report, 0, False

    def boundary(self, name):
        row = dict(commit_at_boundary(), boundary=name)
        row['passed'] = row['commit_available_bytes'] >= LIMIT
        self.report['memory_boundaries'].append(row)
        save(self.args.output / 'report.json', self.report)
        if not self.cleaning and not row['passed']:
            raise RuntimeError('Available commit is below 6 GiB at ' + name)
        if not self.cleaning and time.monotonic() > self.report['runtime_deadline']:
            raise TimeoutError('The narrow candidate runtime budget expired')

    def run(self, code):
        self.counter += 1
        label = '%03d' % self.counter
        self.boundary('before_client_' + label)
        save(self.args.output / 'calls' / (label + '-request.json'), {'code': code, 'is_client': True})
        result = super().run(code)
        save(self.args.output / 'calls' / (label + '-result.json'), result)
        self.boundary('after_client_' + label)
        return result

    def state(self):
        return self.run(PORTAL_STATUS)

    def ready(self, world=False):
        def valid(row):
            if row['preview_error'] or row['portal']['error']:
                raise RuntimeError('Portal owner failed: ' + repr(row))
            if world:
                active = row['projection']
                portals = row['portal_world']
                return (active['active'] and active['ready'] and not active['preparing'] and
                        not active['error'] and portals and
                        all(value['ready'] and not value['error'] and value['models'] for value in portals))
            return (row['ready'] and not row['pending'] and not row['tile_running'] and
                    not row['dirty'] and row['portal']['owned'] and row['portal']['ready'] and
                    not row['portal']['pending'] and bool(row['portal']['groups']))
        return self.wait('native candidate ' + ('world' if world else 'editor'), valid, self.state)

    def frame(self, label, camera=None):
        before = self.state()
        self.boundary('before_capture_' + label)
        receipt = capture(self.args.session, self.args.owner, self.args.output / (label + '.png'), WGC)
        self.boundary('after_capture_' + label)
        after = self.state()
        for key in ('camera', 'rotation', 'screen', 'editor_camera', 'editor_depth'):
            assert before[key] == after[key], key
        assert receipt['ok'] and receipt['reliable'] and receipt['foreground_unchanged']
        assert not receipt['agent_activation_allowed']
        row = {'capture': receipt, 'before': before, 'after': after, 'camera': camera}
        if camera is not None:
            row['visibility'] = portal_pixels(self.args.output / (label + '.png'), camera)
        self.report['captures'][label] = row
        save(self.args.output / 'report.json', self.report)
        return row


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ.update(MCDEV_SESSION_FILE=args.session, MCDEV_OWNER=args.owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    sources = snapshot_sources(args.project)
    started = time.monotonic()
    report = {'schema': 1, 'owner': args.owner, 'started_at': datetime.now(timezone.utc).isoformat(),
              'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'source_contract_sha256': snapshot_digest(sources), 'captures': {}, 'rows': {},
              'memory_metric': 'CommitLimit-CommitTotal', 'minimum_commit_bytes': LIMIT,
              'physical_memory_is_a_gate': False, 'memory_boundaries': [],
              'runtime_deadline': started + 150., 'runtime_budget_seconds': 150.,
              'normal_time': True, 'completed': False, 'restored': False,
              'cleanup_errors': [], 'qualification': False, 'pixel_acceptance': False,
              'limits': ['One fixed editor pose and one near world pose per family only.',
                         'Missing mode uses the empty world; occupancy transitions remain open.',
                         'Native UI matrix bindings/appearance, animation speed/direction and opacity remain open.']}
    installed = visual = profile_saved = player_saved = False
    with Client(timeout=30) as client:
        check = CandidateCheck(client, args, report)
        try:
            check.run(INSTALL_PROBE)
            installed = True
            check.run(SAVE_VISUAL)
            visual = True
            report['profile'] = check.run('''from modern_projection.projection.portal_profile import native_candidate_profile,native_production_profile
assert native_production_profile(api.GetEngineVersion()) is None
assert not hasattr(sys,'_portal_candidate_r21_saved')
sys._portal_candidate_r21_saved=(s.portal_profile,s.grid)
s.portal_profile=native_candidate_profile()
_result={'identity':s.portal_profile.identity,'models':s.portal_profile.models,
 'world_models':s.portal_profile.world_models,'native_default_enabled':False}
''')
            profile_saved = True
            report['player_before'] = server(check, SAVE_PLAYER)
            player_saved = True
            for family in FAMILIES:
                data = document(family)
                report['rows'][family] = {'load': check.run('''from modern_projection.projection.model import Document
if s.projection_active:b.stop_projection()
s.tiles.cancel();s.tiles.parts.clear();s.tiles.context=None
s._loaded(Document.from_data(json.loads(%r)))
s.grid=False;s.opacity=1.
s.camera_view(35.,25.,3.)
owner.open_workspace()
_result={'source':s.editor.document.to_data(),'profile':s.portal_profile.identity}
''' % json.dumps(data))}
                assert report['rows'][family]['load']['source'] == data
                report['rows'][family]['editor_ready'] = check.ready()
                time.sleep(.6)
                check.frame(family + '_editor')
                origin = check.run('''foot=b.player_origin()
s.origin=(foot[0],foot[1]+12,foot[2])
_result=s.origin
''')
                for missing in (False, True):
                    route = 'missing' if missing else 'full'
                    check.run('''if navigator.top is not None:navigator.pop()
s.origin=tuple(%r);s.opacity=1.;s.projection_missing=%r;s.projection_outline=False
b.project()
_result=True
''' % (origin, missing))
                    report['rows'][family][route + '_ready'] = check.ready(True)
                    offset = (0., 3.0 if family == 'end_portal' else 0., -4.5)
                    report['rows'][family][route + '_player'] = near_player(check, offset)
                    camera = view(check, offset, family)
                    time.sleep(.6)
                    row = check.frame(family + '_' + route, camera)
                    check.run('b.stop_projection()\n_result=True')
                    if not row['visibility']['visible']:
                        report['rows'][family][route + '_surface_absent'] = True
                        raise RuntimeError('Native candidate surface is absent: ' + family + '_' + route)
            report['completed'] = True
        finally:
            check.cleaning = True
            if player_saved:
                try:
                    report['player_restore'] = server(check, RESTORE_PLAYER)
                except Exception as error:
                    report['cleanup_errors'].append('player: ' + str(error))
            if visual:
                try:
                    check.run('b.stop_projection()\n_result=True')
                    if profile_saved:
                        check.run('s.portal_profile,s.grid=sys._portal_candidate_r21_saved\ndel sys._portal_candidate_r21_saved\n_result=True')
                    check.run(camera_restore_code(False))
                    check.run('''saved=sys._blueprint_visual_saved
s.origin=saved['origin'];s.opacity=saved['opacity']
s.projection_missing=saved['missing'];s.projection_outline=saved['outline']
del sys._blueprint_visual_saved
_result=True
''')
                except Exception as error:
                    report['cleanup_errors'].append('visual: ' + str(error))
            if installed:
                try:
                    opened = check.run('_result=sys._blueprint_qa_saved["workspace"]')
                    check.run(RESTORE)
                    if not opened and check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                except Exception as error:
                    report['cleanup_errors'].append('editor: ' + str(error))
            report['restored'] = not report['cleanup_errors']
            report['source_unchanged'] = snapshot_sources(args.project) == sources
            report['elapsed_seconds'] = time.monotonic() - started
            report['finished_at'] = datetime.now(timezone.utc).isoformat()
            save(args.output / 'report.json', report)
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'source_unchanged', 'elapsed_seconds')}))
    assert report['completed'] and report['restored'] and report['source_unchanged']
    assert len(report['captures']) == 6


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
