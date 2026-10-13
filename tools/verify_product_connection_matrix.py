"""Audit one public product matrix, then reuse independent native visual gates."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.cell import AIR, foreground
from projection.debug_product_connections import VISUAL_CASE, source_document
from projection.model import Editor, close_group_selection

SOURCE_PATHS = ('behavior_pack/modern_projection/projection/debug_product_connections.py',
                'behavior_pack/modern_projection/projection/debug_blueprints.py',
                'tools/verify_product_connection_matrix.py',
                'tools/verify_static_neighbor_world_visuals.py',
                'tools/verify_neighbor_world_visuals.py')

LOAD_BODY = '''from modern_projection.projection.debug_product_connections import source_document
doc=source_document(%r,False)
s._loaded(doc)
sys._blueprint_qa_expected={'metadata':{'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)},
 'editor_id':id(s.editor),'document_id':id(doc),'previous_document_id':None}
s.grid=False
s.focused=s.box_anchor=None
s.emit()
_result=sys._blueprint_qa_expected
'''

CENTER_BODY = '''center,view=%r,%r
s.camera_pivot=tuple(center[i]-s.scene_origin[i] for i in range(3))
s.camera_pan=(0.,0.)
s.camera_focus_request=None
s.camera_view(*view)
s.focused=s.box_anchor=None
s.emit()
_result=json.dumps({'pivot':s.camera_pivot,'scene_origin':s.scene_origin,'view':s.camera_pose})
'''


def source_fingerprints():
    return [dict(path=path, sha256=hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
            for path in SOURCE_PATHS]


def offline_report():
    from check_blueprint_neighbor_context import compare_target
    rows = []
    for case in VISUAL_CASE['cases']:
        source = source_document(case['id'])
        original = source.blocks.copy()
        closure = tuple(sorted(close_group_selection(source, (case['keep'],))))
        expected = tuple(sorted(case['group_closure']))
        context = [compare_target(source, target) for target in (case['keep'], case['occupied'])]
        editor = Editor(source)
        editor.select_box(case['keep'], case['keep'])
        before = source.blocks.copy()
        count = editor.paint_at(case['keep'], erase=True, respect_selection=False)
        after = source.blocks.copy()
        erased = all(foreground(source.get(pos)) == AIR for pos in expected)
        retained = all(foreground(source.get(pos)) != AIR for pos in case['cells'] if pos not in expected)
        undo = editor.undo() and source.blocks == before
        redo = editor.redo() and source.blocks == after
        rows.append({'case': case['id'], 'family': case['family'], 'closure': closure,
                     'expected_closure': expected, 'context': context,
                     'erase_changed': count, 'erased_group': erased, 'retained_other_bodies': retained,
                     'undo_exact': undo, 'redo_exact': redo,
                     'passed': closure == expected and all(row['passed'] for row in context) and
                               count > 0 and erased and retained and undo and redo,
                     'visual_acceptance': {'editor': None, 'full': None, 'missing': None}})
        source.blocks = original
    inventory_path = ROOT / 'tools/data/neighbor_world_evidence_r4.json'
    inventory = json.loads(inventory_path.read_text(encoding='utf8'))
    return {'schema': 1, 'fixture': VISUAL_CASE['fixture'], 'game_version': registry.source_version(),
            'palette_sha256': registry.fingerprint(), 'rows': rows,
            'source_fingerprints': source_fingerprints(),
            'passed': all(row['passed'] for row in rows), 'evidence_kind': 'CPU transactions and submitted context only',
            'existing_native_evidence': {'path': str(inventory_path.relative_to(ROOT)),
                'sha256': hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
                'accepted_cases_not_repeated': [case for row in inventory['final_pipeline'] if row['passed']
                                                for case in row['cases']]},
            'separate_actor_routes': {
                'chest': {'fixture': 'test.connections.context',
                          'runner': 'tools/verify_chest_occupied_frozen_holdout.py',
                          'occupancy': 'Real stone; dynamic/initial/recovery; no observer replacement'},
                'bed': {'fixture': 'test.entities.appearances',
                        'runner': 'tools/verify_bed_half_occupancy.py',
                        'scope': 'Existing silver directions accepted; new colors/layers still pending'}},
            'limits': ['No native pixels are certified by this report.',
                       'Generic dry runner never receives typed NBT or dual-layer actor cases.',
                       'Strict-layer group semantics remain covered by test_group_layer_identity and test_layer_groups.']}


def body_presence(shown, hidden, crop, output, threshold=16, minimum_pixels=80):
    from PIL import Image, ImageChops
    from verify_missing_neighbor_visuals import maximum, binary, count
    with Image.open(shown).convert('RGB') as first, Image.open(hidden).convert('RGB') as second:
        if first.size != second.size:
            raise ValueError('Editor capture dimensions changed')
        if not (0 <= crop[0] < crop[2] <= first.width and 0 <= crop[1] < crop[3] <= first.height):
            raise ValueError('Editor crop is outside the captured viewport')
        difference = ImageChops.difference(first, second).crop(crop)
    output.parent.mkdir(parents=True, exist_ok=True)
    difference.save(output)
    mask = binary(maximum(difference), threshold)
    pixels = count(mask)
    return {'passed': pixels >= minimum_pixels, 'pixels': pixels, 'threshold': threshold,
            'minimum_pixels': minimum_pixels, 'crop': crop, 'difference': str(output.resolve()),
            'scope': 'Body-only public case shown versus same Scene geometry hidden; aggregate visibility only',
            'independent_shape_acceptance': None}


def live_main(arguments):
    import time
    import verify_static_neighbor_world_visuals as suite
    from verify_sign_visuals import SignCheck, capture_editor, restore_editor_overlays
    from verify_sign_visuals import editor_pose_matches
    from verify_shulker_orientations import viewport_crop
    from verify_chest_editor_frozen_holdout import HIDE_EDITOR_GEOMETRY

    if '--replay' in arguments:
        raise ValueError('Product editor body captures need a product-specific replay gate')
    frozen = source_fingerprints()
    suite.configure(VISUAL_CASE)
    suite.native.CROP_FIXTURE = suite.native.CROP_FIXTURE.replace('(6,24,6)', '(6,2,6)')
    suite.native.CELL_ROIS = suite.native.CELL_ROIS.replace('(0.,1.6)', '(0.,1.)')

    def supports(cells):
        from projection.debug_blueprints import material
        for row in VISUAL_CASE['cases']:
            if len(cells) != len(row['blocks']):
                continue
            delta = tuple(cells[0][0][i] - row['blocks'][0][0][i] for i in range(3))
            expected = dict((tuple(pos[i] + delta[i] for i in range(3)), material(name, states))
                            for pos, name, states in row['blocks'])
            if dict(cells) == expected:
                return [(tuple(pos[i] + delta[i] for i in range(3)), material(name, states))
                        for pos, name, states in row['supports']]
        raise ValueError('Native write source does not match a fixed public product case')

    suite.world.native_supports = supports

    class ProductCheck(SignCheck):
        case_id = None

        def fixture(self, identity):
            result = SignCheck.fixture(self, identity)
            assert self.case_id is not None
            row = next(row for row in VISUAL_CASE['cases'] if row['id'] == self.case_id)
            loaded = self.run(LOAD_BODY % self.case_id)
            preview = self.editor_preview('body-only editor ' + self.case_id, loaded['metadata'],
                                          loaded['editor_id'], loaded['document_id'])
            center = tuple(sum(pos[i] for pos in row['cells']) / float(len(row['cells'])) + .5
                           for i in range(3))
            declared = self.run(CENTER_BODY % (center, VISUAL_CASE['editor_camera']))
            settled = self.wait('declared product editor camera settles',
                                lambda pose: editor_pose_matches(pose, VISUAL_CASE['editor_camera']),
                                lambda: self.run('_result=json.dumps(s.camera_pose)'))
            time.sleep(.4)
            shown = capture_editor(self, self.case_id + '_body_shown', {})
            controls = self.run(HIDE_EDITOR_GEOMETRY)
            try:
                time.sleep(.25)
                hidden = capture_editor(self, self.case_id + '_body_hidden', {})
            finally:
                restored = restore_editor_overlays(self, controls)
            crop = viewport_crop(self, shown)
            result['body_presence'] = body_presence(shown['path'], hidden['path'], crop,
                self.output.with_name(self.output.stem + '_' + self.case_id + '_editor_body_signal.png'))
            result['body_presence'].update(shown=shown, hidden=hidden, restored=restored,
                                          source_cells=row['cells'], supports_in_editor=False,
                                          declared_camera=declared, settled_pose=settled)
            result['public_fixture_capture'] = result['screenshot']
            result['screenshot'] = shown
            for key in ('paper_dolls', 'parts'):
                result[key] = preview[key]
            result['editor_shape_acceptance'] = None
            assert result['body_presence']['passed'], result['body_presence']
            return result

    def background_check(client, output, timeout):
        return ProductCheck(client, output, timeout, native_resolution=True, background_only=True)

    previous_case = suite.world.world_case

    def product_case(check, label, args, record):
        check.case_id = label
        previous_view = args.view
        args.view = [next(row for row in VISUAL_CASE['cases'] if row['id'] == label)['camera']['view']]
        try:
            result = previous_case(check, label, args, record)
        finally:
            args.view = previous_view
        result['editor']['body_presence'] = result['fixture']['fixture']['body_presence']
        result['editor']['image_acceptance'] = {'passed': None,
                                               'scope': 'Aggregate body presence only; independent shape remains pending'}
        result['mode_scope']['editor'] = 'Body-only presence verified; independent editor shape pending.'
        result['passed'] = result['passed'] and result['editor']['body_presence']['passed']
        return result

    suite.world.BlueprintCheck = background_check
    suite.world.world_case = product_case
    sys.argv = [str(Path(__file__).resolve())] + arguments
    saved_grid = None
    with suite.world.Client(timeout=30) as client:
        check = background_check(client, Path(arguments[0]), 60)
        saved_grid = check.run('_result=s.grid')
    output = Path(arguments[0])
    exit_code = 1
    try:
        exit_code = suite.world.main()
    finally:
        if saved_grid is not None:
            with suite.world.Client(timeout=30) as client:
                background_check(client, Path(arguments[0]), 60).run('s.grid=%r\ns.emit()\n_result=True' % saved_grid)
        if output.exists():
            report = json.loads(output.read_text(encoding='utf8'))
            report.update(source_fingerprints=frozen, source_unchanged=frozen == source_fingerprints(),
                          palette_sha256=registry.fingerprint(), game_version=registry.source_version())
            report['passed'] = report['passed'] and report['source_unchanged']
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
            if not report['passed']:
                exit_code = 1
    return exit_code


def main():
    if '--live' in sys.argv:
        return live_main([arg for arg in sys.argv[1:] if arg != '--live'])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh CPU report path')
    report = offline_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'passed': report['passed'], 'cases': len(report['rows']), 'output': str(args.output.resolve())}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
