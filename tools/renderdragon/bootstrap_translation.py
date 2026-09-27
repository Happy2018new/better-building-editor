"""Fetch pinned upstream compiler sources into .runtime and build SPIRV-Cross.

Run in a Visual Studio Developer PowerShell with Python 3.10+, CMake and Ninja.
This does not install, modify or launch Minecraft. DXC is provided separately.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path(__file__).with_name('toolchain_sources.json')
OMIT = ('reference', 'shaders', 'shaders-hlsl', 'shaders-msl',
        'shaders-no-opt', 'shaders-opt', 'tests')


def extract(archive, target, strip_root=False):
    target.mkdir(parents=True, exist_ok=True)
    root = target.resolve()
    with zipfile.ZipFile(archive) as zipped:
        for info in zipped.infolist():
            member = PurePosixPath(info.filename)
            # Check traversal before dropping the top-level archive directory.
            if member.is_absolute() or '..' in member.parts or ':' in info.filename:
                raise ValueError('Unsafe archive path: ' + info.filename)
            parts = member.parts[1:] if strip_root else member.parts
            if not parts or (strip_root and parts[0] in OMIT):
                continue
            destination = target.joinpath(*parts).resolve()
            if not destination.is_relative_to(root):
                raise ValueError('Archive path escapes destination')
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with zipped.open(info) as source, destination.open('wb') as output:
                    shutil.copyfileobj(source, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cmake', default='cmake')
    parser.add_argument('--ninja', default='ninja')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--build-root', type=Path, default=Path(tempfile.gettempdir()),
                        help='Short ASCII temporary parent for CMake/Ninja on Windows')
    args = parser.parse_args()
    out = ROOT / '.runtime/renderdragon/translation_tools'
    out.mkdir(parents=True, exist_ok=True)
    tools = json.loads(CONFIG.read_text(encoding='utf8'))
    for key, item in tools.items():
        archive = out / ('glslang.zip' if key == 'glslang' else 'cross.zip')
        if not archive.exists():
            temporary = archive.with_suffix('.download')
            request = urllib.request.Request(item['url'], headers={'User-Agent': 'modern-projection'})
            with urllib.request.urlopen(request, timeout=90) as response, temporary.open('wb') as output:
                shutil.copyfileobj(response, output)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('Download SHA-256 mismatch: ' + key)
            temporary.replace(archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Cached archive SHA-256 mismatch: ' + key)
        if key != 'glslang':
            continue
        target = out / 'glslang'
        marker = target / '.verified_archive'
        if not marker.exists() or marker.read_text('ascii') != item['sha256']:
            # Flattening the source and omitting unused test fixtures avoids
            # Windows MAX_PATH failures in the upstream reference directories.
            extract(archive, target)
            marker.write_text(item['sha256'], encoding='ascii')
    ninja = shutil.which(args.ninja)
    if not ninja:
        parser.error('Ninja executable not found: ' + args.ninja)
    build_root = args.build_root.resolve()
    if not str(build_root).isascii():
        parser.error('--build-root must use ASCII characters for this CMake/Ninja toolchain')
    build_root.mkdir(parents=True, exist_ok=True)
    destination = out / 'cross_build'
    destination.mkdir(parents=True, exist_ok=True)
    # Older Windows Ninja records ANSI dependencies. Even a successful first
    # build can fail on the next run when the repository has a Unicode path.
    with tempfile.TemporaryDirectory(prefix='mp-cross-', dir=build_root) as temp:
        source, build = Path(temp) / 'src', Path(temp) / 'build'
        extract(out / 'cross.zip', source, strip_root=True)
        subprocess.run([args.cmake, '-S', source.as_posix(), '-B', build.as_posix(), '-G', 'Ninja',
                        '-DCMAKE_MAKE_PROGRAM=' + Path(ninja).resolve().as_posix(),
                        '-DCMAKE_BUILD_TYPE=Release', '-DSPIRV_CROSS_ENABLE_TESTS=OFF',
                        '-DSPIRV_CROSS_ENABLE_MSL=ON', '-DSPIRV_CROSS_ENABLE_CPP=ON',
                        '-DSPIRV_CROSS_ENABLE_C_API=OFF'], check=True)
        subprocess.run([args.cmake, '--build', build.as_posix(), '--target', 'spirv-cross',
                        '--parallel', str(args.workers)], check=True)
        shutil.copyfile(build / 'spirv-cross.exe', destination / 'spirv-cross.exe')
    print(json.dumps({'glslang': str(out / 'glslang/bin/glslang.exe'),
                      'spirv_cross': str(destination / 'spirv-cross.exe')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
