"""Install and restore the pinned poppy resource only in an owned test project."""
import hashlib
import json
from pathlib import Path

from generate_centered_plant_candidate import candidate
from generate_static_plant_proxies import SOURCE


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=True, indent=2) + '\n').encode('ascii')


def write_journal(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_bytes(encode(value))
    temporary.replace(path)


def resource_changes(project, directory):
    """Validate frozen candidate bytes before computing four exact resource edits."""
    project, directory = Path(project).resolve(), Path(directory).resolve()
    index = json.loads((directory / 'index.json').read_bytes())
    expected = candidate(json.loads(SOURCE.read_bytes()), 'poppy')
    if index.get('schema') != 1 or index.get('plant') != 'poppy' or index.get('production_acceptance') is not False:
        raise ValueError('Unsupported centered plant candidate manifest')
    for filename, value in expected.items():
        path, pin = directory / filename, index['files'][filename]
        if digest(path) != pin['sha256'] or path.stat().st_size != pin['bytes'] or json.loads(path.read_bytes()) != value:
            raise ValueError('Centered plant candidate changed: ' + filename)
    registration = expected['registration.json']
    identifier = registration['identifier']
    blocks_path = project / 'resource_pack/blocks.json'
    terrain_path = project / 'resource_pack/textures/terrain_texture.json'
    blocks, terrain = (json.loads(path.read_bytes()) for path in (blocks_path, terrain_path))
    if identifier in blocks or registration['texture_key'] in terrain['texture_data']:
        raise ValueError('Diagnostic resource already registered')
    blocks[identifier] = registration['appearance']
    terrain['texture_data'][registration['texture_key']] = registration['texture_entry']
    return {
        'resource_pack/blocks.json': encode(blocks),
        'resource_pack/textures/terrain_texture.json': encode(terrain),
        'behavior_pack/netease_blocks/diagnostic_centered_poppy.json': (directory / 'behavior.json').read_bytes(),
        'resource_pack/models/netease_block/diagnostic_centered_poppy.json': (directory / 'model.json').read_bytes(),
    }


def install(project, directory, output):
    """Journal original bytes before the first mutation; never overwrite a prior run."""
    project, output = Path(project).resolve(), Path(output).resolve()
    if not output.is_relative_to(project):
        raise ValueError('Candidate journal must stay in its owned project')
    journal = output / 'centered-plant-resources.json'
    if journal.exists():
        raise ValueError('Candidate installation journal already exists')
    changes = resource_changes(project, directory)
    rows = []
    for relative, raw in changes.items():
        path = project / relative
        is_added = relative.endswith('/diagnostic_centered_poppy.json')
        if is_added and path.exists():
            raise ValueError('Diagnostic resource path already exists: ' + relative)
        backup = output / ('centered-original-' + str(len(rows)) + '.bin')
        if path.exists():
            backup.write_bytes(path.read_bytes())
        rows.append({'relative': relative, 'original_absent': not path.exists(),
                     'backup': str(backup) if path.exists() else None,
                     'staged': str(output / ('centered-install-' + str(len(rows)) + '.bin')),
                     'original_sha256': digest(path) if path.exists() else None,
                     'installed_sha256': hashlib.sha256(raw).hexdigest(), 'attempted': False})
    value = {'schema': 1, 'project': str(project), 'production_acceptance': False, 'rows': rows}
    write_journal(journal, value)
    for row in rows:
        row['attempted'] = True
        write_journal(journal, value)
        path = project / row['relative']
        path.parent.mkdir(parents=True, exist_ok=True)
        staged = Path(row['staged'])
        staged.write_bytes(changes[row['relative']])
        if digest(staged) != row['installed_sha256']:
            raise ValueError('Centered resource staged bytes changed')
        staged.replace(path)
    return value


def restore(project, output):
    """Restore own writes and original absence; refuse externally changed bytes."""
    project, output = Path(project).resolve(), Path(output).resolve()
    journal = output / 'centered-plant-resources.json'
    if not journal.exists():
        return {'installed': False, 'restored': True, 'errors': []}
    value = json.loads(journal.read_bytes())
    if Path(value['project']).resolve() != project or not output.is_relative_to(project):
        raise ValueError('Centered candidate journal belongs to another project')
    errors = []
    for row in reversed(value['rows']):
        path = (project / row['relative']).resolve()
        if not path.is_relative_to(project):
            raise ValueError('Centered candidate path escaped project')
        staged = Path(row['staged']).resolve()
        if not staged.is_relative_to(output):
            raise ValueError('Centered resource staged path escaped journal')
        if staged.exists():
            if digest(staged) == row['installed_sha256']:
                staged.unlink()
            else:
                errors.append('External staged resource change: ' + row['relative'])
        current = digest(path) if path.exists() else None
        if current not in (row['installed_sha256'], row['original_sha256']):
            errors.append('External resource change: ' + row['relative'])
            continue
        if row['original_absent']:
            if path.exists():
                path.unlink()
        else:
            backup = Path(row['backup']).resolve()
            if not backup.is_relative_to(output) or digest(backup) != row['original_sha256']:
                errors.append('Candidate backup changed: ' + row['relative'])
                continue
            staged.write_bytes(backup.read_bytes())
            staged.replace(path)
    result = {'installed': True, 'restored': not errors, 'errors': errors}
    (output / 'centered-plant-restoration.json').write_bytes(encode(result))
    return result
