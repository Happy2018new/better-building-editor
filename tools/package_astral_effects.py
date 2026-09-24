"""Archive the frozen, independent astral VFX, never the current game effects."""
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'extras/astral_survey_v1'


def build(target=None):
    target = target or ROOT / 'dist/astral_survey_v1.zip'
    target.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in SOURCE.rglob('*') if p.is_file()
                   and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo'))
    checksums = []
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(SOURCE).as_posix()
            data = path.read_bytes()
            checksums.append(hashlib.sha256(data).hexdigest() + '  ' + relative)
            entry = zipfile.ZipInfo('astral_survey_v1/' + relative, (2026, 9, 24, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
        entry = zipfile.ZipInfo('astral_survey_v1/SHA256SUMS.txt', (2026, 9, 24, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(entry, '\n'.join(checksums) + '\n')
    print(str(target), target.stat().st_size, 'bytes')
    return target


if __name__ == '__main__':
    build()
