"""Explicitly invoked session-only resource staging; importing performs no work."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import _winapi

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from capture_native_burst import _background, _session_binding

SESSION_ID = '773c643b5cf344918e04d8b4eef2657a'
OWNER = 'frame-r11-background'
PLAN_HASH = '37d0c57015a1cb3020d42946e87355d3a17f4045d7af21ef2995e03b666403da'
AMENDMENT_HASH = 'fe7e460f9f3fa11ff6e184953eafda00f17aadf095040273d7854a9e0de185aa'
INDEX_HASH = '7ff2808448e111d531bc58666890b4dba8ca1a8c463e1765dcc0c1e7e8807e4d'


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def read_bound(path, expected):
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, 'Frozen JSON hash mismatch: ' + str(path))
    return json.loads(raw)


def file_identity(path, directory=False, reparse=False):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR,
                                                wintypes.DWORD, wintypes.DWORD]
    kernel.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    kernel.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
    kernel.GetFileInformationByHandle.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL

    class Information(ctypes.Structure):
        _fields_ = [('attributes', wintypes.DWORD), ('created', wintypes.FILETIME),
                    ('accessed', wintypes.FILETIME), ('written', wintypes.FILETIME),
                    ('volume', wintypes.DWORD), ('size_high', wintypes.DWORD),
                    ('size_low', wintypes.DWORD), ('links', wintypes.DWORD),
                    ('index_high', wintypes.DWORD), ('index_low', wintypes.DWORD)]

    flags = (0x02000000 if directory else 0) | (0x00200000 if reparse else 0)
    handle = kernel.CreateFileW(str(path), 0x80000000, 7, None, 3, flags, None)
    require(handle != ctypes.c_void_p(-1).value, 'Cannot open shader identity: ' + str(path))
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        count = kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
        require(0 < count < len(buffer), 'Cannot resolve shader physical path')
        information = Information()
        require(kernel.GetFileInformationByHandle(handle, ctypes.byref(information)),
                'Cannot read shader file ID')
        final = buffer.value
        if final.startswith('\\\\?\\'):
            final = final[4:]
        return {'final_path': str(Path(final)), 'volume': information.volume,
                'file_id': (information.index_high << 32) | information.index_low,
                'bytes': (information.size_high << 32) | information.size_low}
    finally:
        kernel.CloseHandle(handle)


class SessionPackStage:
    def __init__(self, artifacts, journal):
        self.artifacts = Path(artifacts).resolve(strict=True)
        self.session = self.artifacts.parent
        require(self.session.name == SESSION_ID and self.artifacts.name == 'artifacts',
                'Wrong owner-bound artifact directory')
        self.plan = read_bound(self.artifacts / 'frame-shader-staging-execution-plan-v1.json', PLAN_HASH)
        require(self.session == Path(self.plan['session_file']).parent,
                'Artifacts do not belong to the exact managed session')
        amendment = read_bound(self.artifacts / 'frame-shader-staging-execution-plan-v4-physical-volume-amendment.json',
                               AMENDMENT_HASH)
        self.index = read_bound(self.artifacts / 'frame-shader-staging-original-pack-v1.index.json', INDEX_HASH)
        self.source = Path(self.plan['loaded_pack_provenance']['source_pack']).resolve(strict=True)
        require(self.source == ROOT / 'resource_pack', 'Source pack escaped the assigned worktree')
        self.stage = Path(amendment['stage_pack']).absolute()
        require(self.stage == self.session / 'frame_shader_stage_v2' / 'resource_pack',
                'Stage escaped the assigned session')
        self.shader = Path(self.plan['loaded_pack_provenance']['shader_relative_path'])
        self.original_shader_hash = self.plan['loaded_pack_provenance']['shader_sha256']
        self.links = [{key: Path(row[key]).absolute() for key in
                       ('path', 'original_backup_path', 'retired_stage_path')}
                      for row in amendment['loaded_lookup_paths']]
        expected_world = Path(self.plan['loaded_pack_provenance']['world_pack_manifest']).parent
        self.world_root = expected_world.resolve(strict=True)
        require(self.world_root == Path(amendment['physical_world_root']), 'Physical world root changed')
        require(self.links[0]['path'] == expected_world / 'resource_packs' /
                'mcdk_7c6a9da7a34340868c15a60ade3d3367', 'Unexpected world lookup path')
        require(self.links[1]['path'] == self.session / 'appdata/MinecraftPE_Netease/games/com.netease/'
                'resource_packs/7c6a9da7a34340868c15a60ade3d3367', 'Unexpected appdata lookup path')
        for name, row, frozen_row in zip(('world', 'appdata'), self.links,
                                         amendment['loaded_lookup_paths']):
            boundary = self.world_root if name == 'world' else self.session
            row['boundary'] = boundary
            row['original_entry_identity'] = frozen_row['original_entry_identity']
            require(self.entry_key(file_identity(row['path'], directory=True, reparse=True)) ==
                    self.entry_key(row['original_entry_identity']), 'Original junction entry identity changed')
            require(row['original_backup_path'] == boundary / 'frame_shader_original_links_v2' / name,
                    'Original link backup escaped the exact physical boundary')
            require(row['retired_stage_path'] == boundary / 'frame_shader_retired_links_v2' / name,
                    'Retired link path escaped the exact physical boundary')
        self.journal = Path(journal).absolute()
        require(self.journal.parent.resolve(strict=True) == self.artifacts and
                not os.path.lexists(self.journal), 'A fresh session-only journal is required')
        require(not os.path.lexists(self.journal.with_name(self.journal.name + '.tmp')),
                'A fresh journal temporary path is required')
        self.report = {'schema': 1, 'session_id': SESSION_ID, 'owner': OWNER,
                       'staged': False, 'links_active': False, 'filesystem_restored': False,
                       'lookup_mutation_occurred': False, 'loaded_shader_mutation_attempted': False,
                       'production_rendering_accepted': False, 'operations': []}
        self.binding = self.window = None

    def record(self, operation, **details):
        self.report['operations'].append(dict(operation=operation, **details))
        temporary = self.journal.with_name(self.journal.name + '.tmp')
        with temporary.open('x', encoding='ascii') as output:
            output.write(json.dumps(self.report, ensure_ascii=True, indent=2) + '\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, self.journal)

    def guard(self):
        current, _ = _session_binding(self.plan['session_file'], OWNER)
        require(current['id'] == SESSION_ID and current['game_pid'] == 44536 and
                current['game_identity'] == '134362903316974407' and current['mcdk_pid'] == 42372 and
                current['mcdk_identity'] == '134362903315012341', 'Session process identity changed')
        if self.binding is not None:
            require(current == self.binding, 'Session binding changed')
        guard, window = _background(current, self.window)
        expected = self.plan['physical_window']
        require(all(window[key] == expected[key] for key in expected), 'Physical window changed')
        self.binding, self.window = current, window
        return guard

    @staticmethod
    def entry_key(identity):
        return identity['volume'], identity['file_id']

    @staticmethod
    def ordinary_ancestors(path, boundary):
        current = path
        while True:
            require(not current.is_symlink() and not current.is_junction(), 'Linked staging ancestor')
            if current == boundary:
                break
            require(current != current.parent and boundary in current.parents, 'Staging ancestor escaped session')
            current = current.parent

    def verify_pack(self, pack, shader_hash=None):
        require(pack.is_dir() and not pack.is_symlink() and not pack.is_junction(), 'Pack is not ordinary')
        paths = list(pack.rglob('*'))
        require(not any(path.is_symlink() or path.is_junction() for path in paths),
                'Pack contains linked descendants')
        actual = {path.relative_to(pack).as_posix(): path for path in paths if path.is_file()}
        require(set(actual) == {row['path'] for row in self.index['files']}, 'Pack file inventory changed')
        for row in self.index['files']:
            path = actual[row['path']]
            expected = shader_hash if shader_hash and row['path'] == self.shader.as_posix() else row['sha256']
            require(digest(path) == expected, 'Pack hash mismatch: ' + row['path'])
            if expected == row['sha256']:
                require(path.stat().st_size == row['bytes'], 'Pack size mismatch: ' + row['path'])

    def prepare(self):
        self.guard()
        self.verify_pack(self.source)
        require(not os.path.lexists(self.stage.parent), 'A fresh stage parent is required')
        self.ordinary_ancestors(self.stage.parent, self.session)
        for row in self.links:
            require(row['path'].is_junction() and row['path'].resolve(strict=True) == self.source,
                    'Original pack junction changed')
            require(not os.path.lexists(row['original_backup_path']) and
                    not os.path.lexists(row['retired_stage_path']), 'Fresh link backups are required')
        self.stage.parent.mkdir()
        self.record('stage_parent_created', path=str(self.stage.parent))
        shutil.copytree(self.source, self.stage, copy_function=shutil.copyfile)
        self.verify_pack(self.stage)
        self.verify_pack(self.source)
        self.guard()
        self.report['staged'] = True
        self.record('stage_copy_verified', files=709, bytes=45627969)

    def rename_junction(self, source, target, expected_target, journal=True):
        authorized = [row for row in self.links if (source, target) in
                      ((row['path'], row['original_backup_path']),
                       (row['path'], row['retired_stage_path']),
                       (row['original_backup_path'], row['path']))]
        require(len(authorized) == 1, 'Unreviewed junction rename pair')
        boundary = authorized[0]['boundary']
        require(source.is_junction() and source.resolve(strict=True) == expected_target,
                'Junction target changed before rename')
        original_entry = file_identity(source, directory=True, reparse=True)
        if expected_target == self.source:
            require(self.entry_key(original_entry) == self.entry_key(authorized[0]['original_entry_identity']),
                    'Original junction entry identity changed before rename')
        require(not os.path.lexists(target), 'Junction rename target is not fresh')
        existing_parent = next(path for path in target.parents if path.exists())
        require(file_identity(source.parent, directory=True)['volume'] ==
                file_identity(existing_parent, directory=True)['volume'],
                'Junction rename physical parent volumes differ')
        self.ordinary_ancestors(existing_parent.resolve(strict=True), boundary)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.ordinary_ancestors(target.parent.resolve(strict=True), boundary)
        require(file_identity(source.parent, directory=True)['volume'] ==
                file_identity(target.parent, directory=True)['volume'],
                'Junction rename physical parent volume changed')
        physical_source = source.parent.resolve(strict=True) / source.name
        physical_target = target.parent.resolve(strict=True) / target.name
        os.rename('\\\\?\\' + str(physical_source), '\\\\?\\' + str(physical_target))
        self.report['lookup_mutation_occurred'] = True
        require(target.is_junction() and target.resolve(strict=True) == expected_target and
                not os.path.lexists(source), 'Junction rename verification failed')
        require(self.entry_key(file_identity(target, directory=True, reparse=True)) ==
                self.entry_key(original_entry), 'Renamed junction entry identity changed')
        if journal:
            self.record('junction_renamed', source=str(source), target=str(target),
                        physical_source=str(physical_source), physical_target=str(physical_target),
                        expected_target=str(expected_target))

    def swap(self):
        require(self.report['staged'], 'Prepare the exact stage first')
        self.guard()
        self.verify_pack(self.source)
        self.verify_pack(self.stage)
        for row in self.links:
            self.guard()
            self.rename_junction(row['path'], row['original_backup_path'], self.source)
            physical_parent = row['path'].parent.resolve(strict=True)
            self.ordinary_ancestors(physical_parent, row['boundary'])
            require(not os.path.lexists(row['path']), 'Stage junction path is not fresh')
            try:
                # Ancestor junctions can expand a short lookup beyond Win32's directory limit.
                _winapi.CreateJunction(str(self.stage), '\\\\?\\' + str(physical_parent / row['path'].name))
            except Exception:
                if row['path'].is_dir() and not row['path'].is_junction() and not row['path'].is_symlink():
                    require(row['original_backup_path'].is_junction() and
                            self.entry_key(file_identity(row['original_backup_path'], directory=True, reparse=True)) ==
                            self.entry_key(row['original_entry_identity']), 'Original backup changed during creation failure')
                    require(row['path'].resolve(strict=True) == physical_parent / row['path'].name and
                            not any(row['path'].iterdir()), 'Partial stage entry is not the fresh empty directory')
                    os.rmdir(row['path'])
                raise
            require(row['path'].is_junction() and row['path'].resolve(strict=True) == self.stage,
                    'Created stage junction target changed')
            self.record('stage_junction_created', path=str(row['path']), target=str(self.stage))
        self.report['links_active'] = True
        self.assert_stage_shader()
        self.record('stage_shader_physical_identity_verified')

    def assert_stage_shader(self):
        self.ordinary_ancestors(self.stage / self.shader, self.session)
        original = file_identity(self.source / self.shader)
        staged = file_identity(self.stage / self.shader)
        require(Path(staged['final_path']) == self.stage / self.shader and
                (staged['volume'], staged['file_id']) != (original['volume'], original['file_id']),
                'Staged shader aliases repository source')
        for row in self.links:
            require(row['path'].is_junction() and row['path'].resolve(strict=True) == self.stage,
                    'Active pack lookup changed')
            loaded = file_identity(row['path'] / self.shader)
            require(loaded == staged, 'Loaded shader does not physically resolve to stage')
        return staged

    def write_shader(self, payload, expected_hash):
        self.guard()
        self.assert_stage_shader()
        self.verify_pack(self.source)
        require(hashlib.sha256(payload).hexdigest() == expected_hash, 'Frozen shader payload hash mismatch')
        allowed = {self.original_shader_hash,
                   self.plan['diagnostic_bundle']['nooffset_shader_sha256'],
                   self.plan['diagnostic_bundle']['translated_shader_sha256']}
        require(expected_hash in allowed, 'Unreviewed shader payload')
        target = self.stage / self.shader
        self.report['loaded_shader_mutation_attempted'] = True
        with target.open('wb') as shader:
            shader.write(payload)
            shader.flush()
            os.fsync(shader.fileno())
        require(digest(target) == expected_hash, 'Staged shader write hash mismatch')
        self.assert_stage_shader()
        self.verify_pack(self.stage, expected_hash)
        self.verify_pack(self.source)
        self.record('stage_shader_written', shader_sha256=expected_hash)

    def restore_filesystem(self):
        errors = []

        def cleanup_record(operation, **details):
            try:
                self.record(operation, **details)
            except Exception as error:
                errors.append('journal: ' + str(error))

        try:
            if self.stage.is_dir():
                self.ordinary_ancestors(self.stage / self.shader, self.session)
                stage_identity = file_identity(self.stage / self.shader)
                source_identity = file_identity(self.source / self.shader)
                require((stage_identity['volume'], stage_identity['file_id']) !=
                        (source_identity['volume'], source_identity['file_id']),
                        'Cleanup stage aliases source')
                shutil.copyfile(self.source / self.shader, self.stage / self.shader)
                self.verify_pack(self.stage)
                cleanup_record('original_stage_shader_restored')
        except Exception as error:
            errors.append('stage_shader: ' + str(error))
        for row in reversed(self.links):
            try:
                if row['original_backup_path'].is_junction():
                    require(row['original_backup_path'].resolve(strict=True) == self.source,
                            'Original backup target changed')
                    if os.path.lexists(row['path']):
                        self.rename_junction(row['path'], row['retired_stage_path'], self.stage, journal=False)
                        cleanup_record('stage_junction_retired', path=str(row['path']),
                                       retired=str(row['retired_stage_path']))
                    require(not os.path.lexists(row['path']), 'Original lookup path occupied during restore')
                    require(row['path'].parent.is_dir(), 'Original lookup parent missing')
                    self.rename_junction(row['original_backup_path'], row['path'], self.source, journal=False)
                    cleanup_record('original_junction_restored', path=str(row['path']))
                require(row['path'].is_junction() and row['path'].resolve(strict=True) == self.source,
                        'Original junction was not restored')
                require(self.entry_key(file_identity(row['path'], directory=True, reparse=True)) ==
                        self.entry_key(row['original_entry_identity']), 'Original junction entry identity was not restored')
                require(file_identity(row['path'] / self.shader) == file_identity(self.source / self.shader),
                        'Original shader physical identity was not restored')
            except Exception as error:
                errors.append(str(row['path']) + ': ' + str(error))
        try:
            self.verify_pack(self.source)
        except Exception as error:
            errors.append('original_pack: ' + str(error))
        self.report['links_active'] = False if not errors else self.report['links_active']
        self.report['filesystem_restored'] = not errors
        cleanup_record('filesystem_cleanup_completed', errors=list(errors))
        if errors:
            self.report['filesystem_restored'] = False
        return errors
