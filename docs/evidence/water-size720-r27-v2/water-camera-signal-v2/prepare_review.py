"""Extend the unchanged v1 replay with final-output and independent counterexample controls."""
from pathlib import Path

WORK = Path(__file__).resolve().parent
old = WORK.with_name('water-camera-signal-v1')/'review_candidate.py'
text = old.read_text('utf-8')
needle = "                control('Preserved %s %s satisfies unchanged fit limits' % (after.size, row['view']), passed)"
assert text.count(needle) == 1
text = text.replace(needle, needle + "\n" + '''                control('Every final new real pixel has contribution: %s %s' % (after.size, row['view']),
                        count(ImageChops.subtract(additions, contribution)) == 0)
                control('Original real outline retained: %s %s' % (after.size, row['view']),
                        count(ImageChops.subtract(before, after)) == 0)''')
needle = "        control('Shared tool bytes remain unchanged after replay', sha(source) == binding['base_sha256'])"
assert text.count(needle) == 1
extra = '''        v1_path = WORK.with_name('water-camera-signal-v1')/'candidate/tools/verify_camera_projection.py'
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
'''
text = text.replace(needle, extra+needle)
with (WORK/'review_candidate.py').open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(text)
