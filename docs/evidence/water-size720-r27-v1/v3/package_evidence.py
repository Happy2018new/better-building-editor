"""Package R27 water diagnostics, separating raw and sanitized artifact hashes."""
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
OUT = ROOT / 'docs/evidence/water-size720-r27-v1'
LIMIT = 240000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    assert not OUT.exists()
    files = {}
    for version in (1, 2, 3):
        directory = WORK.with_name('water-size720-v%d' % version)
        for path in directory.rglob('*'):
            if not path.is_file() or path.suffix not in ('.json', '.py', '.txt', '.png', '.patch'):
                continue
            relative = path.relative_to(directory)
            # Full bursts stay in runtime. Only the raw manifest and three actual frames are packaged.
            if len(relative.parts) > 1 and '_burst' in relative.parts[0] and path.name != 'manifest.json':
                continue
            files['v%d/' % version + relative.as_posix()] = path
        launch = json.loads((directory / 'launch/launch.json').read_bytes())
        registry = Path(launch['session_file'])
        session = json.loads(registry.read_bytes())
        assert session['state'] == 'stopped'
        files['v%d/registry/session.json' % version] = registry
        files['v%d/registry/mcdk.log' % version] = Path(session['log'])
    bursts = sorted(WORK.glob('*_burst'))
    for directory in bursts:
        manifest = json.loads((directory / 'manifest.json').read_bytes())
        frames = manifest.get('frames', [])
        actual = [directory / frame.get('png', '') for frame in frames if isinstance(frame.get('png'), str)]
        actual = [path for path in actual if path.is_file() and path.suffix == '.png']
        if not actual:
            actual = sorted(directory.glob('frame-*.png'))
        if actual:
            for path in (actual[0], actual[len(actual)//2], actual[-1]):
                files['v3/selected-burst/' + directory.name + '/' + path.name] = path
    secrets, paths = set(), {}

    def discover(value, path, found):
        if isinstance(value, dict):
            for key, item in value.items():
                location = path + '.' + key
                if isinstance(item, str) and len(item) >= 8 and ('token' in key.lower()
                        or key.lower() in ('authorization', 'api_key', 'apikey', 'secret')) and not key.lower().endswith('sha256'):
                    secrets.add(item)
                    found.append(location)
                else:
                    discover(item, location, found)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                discover(item, path + '[%d]' % index, found)
        elif isinstance(value, str) and value.lstrip().startswith(('{', '[')):
            try:
                nested = json.loads(value)
            except ValueError:
                return
            discover(nested, path + ':decoded_json', found)

    for name, path in files.items():
        if path.suffix == '.json':
            found = []
            discover(json.loads(path.read_bytes()), '$', found)
            paths[name] = found
    OUT.mkdir(parents=True)
    entries = []
    for name, path in sorted(files.items()):
        raw = path.read_bytes()
        entry = {'original_raw_path': str(path.resolve()), 'original_raw_sha256': sha(raw),
                 'original_raw_bytes': len(raw), 'redacted_fields': paths.get(name, [])}
        target = OUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == '.png':
            if len(raw) < LIMIT:
                encoded = raw
                encoding = 'png'
                reconstructable = True
            else:
                picture = Image.open(io.BytesIO(raw)).convert('RGB')
                quality = 90
                while True:
                    buffer = io.BytesIO()
                    picture.save(buffer, 'JPEG', quality=quality, optimize=True, subsampling=0)
                    encoded = buffer.getvalue()
                    if len(encoded) < LIMIT:
                        break
                    quality -= 5
                    assert quality >= 50
                target = target.with_suffix('.jpg')
                encoding = 'jpeg'
                reconstructable = False
                entry.update(lossy_visual_reference=True, jpeg_quality=quality, full_resolution=list(picture.size))
            target.write_bytes(encoded)
            entry.update(encoding=encoding, original_bytes_reconstructable=reconstructable,
                         derived_parts=[{'path': target.relative_to(OUT).as_posix(), 'sha256': sha(encoded), 'bytes': len(encoded)}])
        else:
            text = raw.decode('utf-8-sig')
            occurrences = 0
            for secret in sorted(secrets, key=len, reverse=True):
                occurrences += text.count(secret)
                text = text.replace(secret, '[REDACTED_SESSION_TOKEN]')
            sanitized = text.encode('utf-8')
            encoded = gzip.compress(sanitized, mtime=0) if len(sanitized) > 100000 else sanitized
            zipped = len(sanitized) > 100000
            if zipped:
                target = Path(str(target) + '.gz')
            parts = []
            chunks = [encoded[i:i+LIMIT] for i in range(0, len(encoded), LIMIT)] or [b'']
            for number, chunk in enumerate(chunks):
                destination = Path(str(target) + ('.%03d' % (number+1) if len(chunks)>1 else ''))
                destination.write_bytes(chunk)
                parts.append({'path': destination.relative_to(OUT).as_posix(), 'sha256': sha(chunk), 'bytes': len(chunk)})
            entry.update(encoding='gzip' if zipped else 'utf8', decoded_sanitized_sha256=sha(sanitized),
                decoded_sanitized_bytes=len(sanitized), redaction_occurrences=occurrences,
                original_bytes_reconstructable=sanitized==raw, derived_parts=parts)
        entries.append(entry)
    index = {'schema': 1, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
             'diagnostic_only': True, 'formal_A_accepted': False, 'world_qualification_granted': False,
             'production_admission_performed': False, 'manual_closures_added': 0,
             'source_contract_sha256': 'a564563ecf20f74b786565aaf0516575ab34c448b370a2bb2199319dc6b5c194',
             'original_raws_modified': False, 'secret_values_discovered': len(secrets),
             'entries': entries, 'burst_images_are_only_selected_spot_checks': True,
             'v2_group_suspension_retained_and_not_timing_evidence': True}
    data = (json.dumps(index, indent=2) + '\n').encode('utf-8')
    assert len(data) < 300000
    (OUT / 'index.json').write_bytes(data)
    for entry in entries:
        encoded = b''.join((OUT / part['path']).read_bytes() for part in entry['derived_parts'])
        if 'decoded_sanitized_sha256' in entry:
            decoded = gzip.decompress(encoded) if entry['encoding'] == 'gzip' else encoded
            assert sha(decoded) == entry['decoded_sanitized_sha256']
            assert not any(secret.encode('utf-8') in decoded for secret in secrets)
        assert sha(Path(entry['original_raw_path']).read_bytes()) == entry['original_raw_sha256']
    assert all(path.stat().st_size < 300000 for path in OUT.rglob('*') if path.is_file())
    print(json.dumps({'index_sha256': sha(data), 'entries': len(entries),
                      'largest_file_bytes': max(path.stat().st_size for path in OUT.rglob('*') if path.is_file()),
                      'original_raws_preserved': True, 'secret_values_in_output': 0}))


if __name__ == '__main__':
    main()
