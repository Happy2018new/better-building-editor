"""Read-only review of the new flat run; this does not qualify other fixtures."""
import hashlib
import json
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'round-20261022/books-wire-v1/flat-interior-actual-v3'
OUT = ROOT / 'round-20261022/root-wire-flat-v3-review'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    report_raw = (RUN / 'report.json').read_bytes()
    report = json.loads(report_raw)
    assert report['completed'] is True and report['restored'] is True
    assert report['cleanup_errors'] == []
    assert report['runtime_and_host_unchanged'] is True
    assert len(report['samples']) == 12
    retirement = json.loads((RUN / 'observer-retirement.json').read_bytes())
    assert retirement['retired'] and retirement['observer_removed'] and retirement['module_removed']
    assert retirement['factory_restored']
    assert retirement['original_factory_id'] == retirement['restored_factory_id']
    assert len(json.dumps(retirement).encode('ascii')) <= 8192
    phase_records = []
    total = 0
    for entry in report['observer_retirement']['phase_files']:
        raw = (RUN / entry['path']).read_bytes()
        assert digest(raw) == entry['sha256']
        phase = json.loads(raw)
        rows = phase['records']
        assert len(rows) == entry['records']
        counts = dict(Counter(row['phase'] for row in rows))
        assert counts == retirement['phase_counts'][phase['phase_key']]
        assert counts == {'CreatePalette': 2, 'Deserialize': 2, 'Combine': 2}
        assert all(row['phase_key'] == phase['phase_key'] for row in rows)
        phase_records.append({'path': entry['path'], 'sha256': digest(raw), 'counts': counts})
        total += len(rows)
    assert total == retirement['record_count'] == 72
    audit = report['independent_audit']
    for key in ('context_writer_same_function', 'cache_same_objects', 'profile_same_objects',
                'geometry_same_function', 'helper_same_objects', 'restored', 'cache_same_values',
                'geometry_instance_override_same'):
        assert audit[key] is True, key
    for key in ('markers', 'wire_markers', 'changed_keys'):
        assert audit[key] == [], key
    assert audit['jobs'] is False and audit['actor_count'] == 0
    image_records = []
    samples = {sample['label']: sample for sample in report['samples']}
    for label, sample in samples.items():
        assert sample['completed'] is True
        for role in ('shown', 'hidden'):
            entry = sample[role]
            raw = Path(entry['path']).read_bytes()
            assert len(raw) == entry['bytes'] and digest(raw) == entry['sha256']
            with Image.open(Path(entry['path'])) as original:
                assert original.size == (1280, 720)
            image_records.append({'label': label, 'role': role, 'sha256': digest(raw)})
    opaque = []
    for view in ('opaque_top', 'opaque_grazing'):
        rows = [samples[view + '_' + mode]['wire'] for mode in ('base', 'repeat', 'candidate', 'restored')]
        assert len({row['mask_sha256'] for row in rows}) == 1
        assert len({row['wire_rgb_sha256'] for row in rows}) == 1
        assert len({row['wire_pixels'] for row in rows}) == 1
        opaque.append({'view': view, 'same_reported_masks_and_rgb': True, 'pixels': rows[0]['wire_pixels']})
    default = {mode: samples['default_top_' + mode]['colors']['target_corner']['shown_mean_rgb']
               for mode in ('base', 'repeat', 'candidate', 'restored')}
    assert default['base'] == default['repeat'] == default['restored']
    assert default['candidate'] != default['base']
    result = {
        'schema': 1, 'passed': True, 'report_sha256': digest(report_raw),
        'review': 'Exact raw export/capture binding, phase census and restoration assertions; original PNGs separately opened by root',
        'original_images_opened': [view + '_' + mode for view in ('opaque_top', 'opaque_grazing', 'default_top')
                                   for mode in ('base', 'candidate')],
        'visual_observation': 'Default cross brightness removed; opaque red wire shape retained in top/grazing originals',
        'phases': phase_records, 'images': image_records, 'opaque': opaque,
        'default_target_rgb': default, 'retirement_restored': True,
        'native_resources_reclaimed_at_flat_report': report['native_resources_reclaimed'],
        'remaining': 'Seven original extension fixtures and final owned session shutdown; production not promoted',
        'manual_closures_added': 0,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'report.json').write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'passed': True, 'phase_records': total, 'captures_bound': len(image_records),
                      'restored': True, 'production_promoted': False}))


if __name__ == '__main__':
    main()
