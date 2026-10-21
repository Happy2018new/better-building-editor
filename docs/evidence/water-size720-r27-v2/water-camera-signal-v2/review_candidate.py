"""Offline real-image and synthetic controls for the private signal change."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from PIL import Image, ImageChops, ImageDraw

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_camera_projection as original


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = WORK / 'offline-review-v1.json'
    assert not output.exists()
    binding = json.loads((WORK / 'binding-v1.json').read_bytes())
    source, target = Path(binding['base_path']), Path(binding['candidate_path'])
    assert sha(source) == binding['base_sha256']
    assert sha(target) == binding['candidate_sha256']
    spec = importlib.util.spec_from_file_location('private_camera_signal_r27', target)
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    result = dict(schema=1, MC_started=False, shared_tool_modified=False,
        runtime_qualification_granted=False, host_sha256=sha(Path(__file__)),
        binding_sha256=sha(WORK/'binding-v1.json'), real_cases=[], controls=[], passed=False)

    def save():
        output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')

    def control(name, condition, **details):
        result['controls'].append(dict(name=name, passed=bool(condition), **details))
        save()
        assert condition, name

    def support(shown, hidden):
        return candidate.maximum(candidate.signal(shown, hidden)).point(lambda v: 255 if v > 20 else 0)

    def count(mask):
        return mask.histogram()[255]

    try:
        trees = [ast.parse(path.read_bytes()) for path in (source, target)]
        unrelated = [{node.name: ast.dump(node, include_attributes=False) for node in tree.body
                      if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name != 'stone_signal'}
                     for tree in trees]
        control('All other functions retain identical AST', unrelated[0] == unrelated[1])
        stone = next(node for node in trees[1].body if isinstance(node, ast.FunctionDef) and node.name == 'stone_signal')
        names = {node.id for node in ast.walk(stone) if isinstance(node, ast.Name)}
        control('Signal extractor cannot call analytic projection or fitting',
                not names & {'project_points', 'projected_mask', 'hull', 'fit_fov'})
        reports = [ROOT/'.runtime/round-20261022/water-size720-v2/product-v2-camera-native-v1.json',
                   ROOT/'.runtime/round-20261021/trace-lifetime-v2/experiment-isolated-v1/product-v2-camera-native-v1.json']
        for report_path in reports:
            report = json.loads(report_path.read_bytes())
            for row in report['views']:
                shown, hidden = Path(row['shown']['path']), Path(row['hidden']['path'])
                for capture in (row['shown'], row['hidden']):
                    assert sha(Path(capture['path'])) == capture['sha256']
                before = original.stone_signal(shown, hidden)
                after = candidate.stone_signal(shown, hidden)
                contribution = support(shown, hidden)
                fit = candidate.fit_fov(after, row['pose'], report['vertical_fov'])
                passed = (fit['boundary_rms_pixels'] <= 2 and fit['mask_iou'] >= .95
                          and fit['outline_recall_2px'] >= .985 and fit['outline_precision_2px'] >= .985)
                additions = ImageChops.subtract(after, before)
                result['real_cases'].append(dict(report_path=str(report_path), report_sha256=sha(report_path),
                    view=row['view'], shown_sha256=sha(shown), hidden_sha256=sha(hidden), size=list(after.size),
                    original_bounds=list(before.getbbox()), candidate_bounds=list(after.getbbox()),
                    added_pixels=count(additions), unsupported_added_pixels=count(ImageChops.subtract(additions, contribution)),
                    fit=fit, passed_original_limits=passed))
                control('Preserved %s %s satisfies unchanged fit limits' % (after.size, row['view']), passed)
                control('Every final new real pixel has contribution: %s %s' % (after.size, row['view']),
                        count(ImageChops.subtract(additions, contribution)) == 0)
                control('Original real outline retained: %s %s' % (after.size, row['view']),
                        count(ImageChops.subtract(before, after)) == 0)
                try:
                    candidate.stone_signal(shown, shown)
                except AssertionError:
                    control('Unchanged pair rejected: %s %s' % (after.size, row['view']), True)
                else:
                    control('Unchanged pair rejected: %s %s' % (after.size, row['view']), False)

        fixture_dir = WORK / 'controls'
        fixture_dir.mkdir(exist_ok=True)
        for gap, magnitude in ((1, 255), (2, 255), (3, 255), (1, 20), (1, 21), (1, 0)):
            shown = Image.new('RGB', (256, 256), (40, 80, 180))
            hidden = shown.copy()
            ImageDraw.Draw(shown).rectangle((96, 80, 159, 175), fill=(120, 120, 120))
            ImageDraw.Draw(shown).rectangle((96, 126, 159, 125+gap), fill=(132, 156, 178))
            if magnitude != 255:
                ImageDraw.Draw(hidden).rectangle((96,126,159,125+gap),
                    fill=tuple(v-magnitude for v in (132,156,178)))
            stem = 'gap%d-contribution%d' % (gap, magnitude)
            shown_path, hidden_path = fixture_dir/(stem+'-shown.png'), fixture_dir/(stem+'-hidden.png')
            shown.save(shown_path)
            hidden.save(hidden_path)
            before = original.stone_signal(shown_path, hidden_path)
            after = candidate.stone_signal(shown_path, hidden_path)
            full = after.getbbox() == (96, 80, 160, 176)
            should_bridge = gap <= 2 and magnitude > 20
            control('Synthetic %s retains contribution and seam limits' % stem, full == should_bridge,
                    original_bounds=list(before.getbbox()), candidate_bounds=list(after.getbbox()),
                    full_cube_recovered=full, expected_recovered=should_bridge,
                    shown_sha256=sha(shown_path), hidden_sha256=sha(hidden_path),
                    unsupported_added_pixels=count(ImageChops.subtract(ImageChops.subtract(after, before),
                        support(shown_path, hidden_path))))
        v1_path = WORK.with_name('water-camera-signal-v1')/'candidate/tools/verify_camera_projection.py'
        v1_spec = importlib.util.spec_from_file_location('private_camera_signal_r27_v1_retained', v1_path)
        v1 = importlib.util.module_from_spec(v1_spec)
        v1_spec.loader.exec_module(v1)
        books = ROOT/'.runtime/round-20261022/books-editor-v1/camera-signal-review-v1'
        result['independent_counterexamples'] = []
        for gap in (1, 2):
            shown_path = books/('endbridges-gap%d-shown.png' % gap)
            hidden_path = books/('endbridges-gap%d-hidden.png' % gap)
            before = original.stone_signal(shown_path, hidden_path)
            rejected_v1 = v1.stone_signal(shown_path, hidden_path)
            after = candidate.stone_signal(shown_path, hidden_path)
            contribution = support(shown_path, hidden_path)
            v1_unsupported = count(ImageChops.subtract(ImageChops.subtract(rejected_v1, before), contribution))
            v2_unsupported = count(ImageChops.subtract(ImageChops.subtract(after, before), contribution))
            missing = sum(after.getpixel((x,y)) == 0 for y in range(125,125+gap) for x in range(84,172))
            result['independent_counterexamples'].append(dict(gap=gap,
                shown_path=str(shown_path), hidden_path=str(hidden_path),
                shown_sha256=sha(shown_path), hidden_sha256=sha(hidden_path),
                rejected_v1_sha256=sha(v1_path), v1_unsupported_added_pixels=v1_unsupported,
                candidate_unsupported_added_pixels=v2_unsupported,
                low_contribution_center_missing_pixels=missing,
                old_outline_removed_pixels=count(ImageChops.subtract(before, after))))
            control('Independent gap%d reproduces v1 indirect fill failure' % gap, v1_unsupported == 88*gap)
            control('Independent gap%d final additions need contribution' % gap, v2_unsupported == 0)
            control('Independent gap%d missing information remains missing' % gap, missing == 88*gap)
            control('Independent gap%d original outline remains a subset' % gap,
                    count(ImageChops.subtract(before, after)) == 0)
        control('Shared tool bytes remain unchanged after replay', sha(source) == binding['base_sha256'])
        result['passed'] = True
    finally:
        save()
    print(json.dumps(dict(passed=result['passed'], real_cases=len(result['real_cases']),
        controls=len(result['controls']), unsupported_new_pixels_in_real_cases=sum(row['unsupported_added_pixels']
            for row in result['real_cases']), review_sha256=sha(output))))


if __name__ == '__main__':
    main()
