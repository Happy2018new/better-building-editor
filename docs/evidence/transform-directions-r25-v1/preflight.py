from __future__ import unicode_literals
import hashlib
import json
import os
import sys

ROOT = os.getcwdu() if sys.version_info[0] == 2 else os.getcwd()
sys.path.insert(0, os.path.join(ROOT, 'behavior_pack', 'modern_projection'))
from projection import debug_blueprints as blue
from projection.debug_transform_acceptance import PREFIX, build, prepare, CASES
from projection.model import Editor, Document

identity = PREFIX + 't02'
assert identity in dict((row[0], row) for row in blue.BLUEPRINTS)
source = build(identity)
assert source.size == (32, 10, 32) and len(source.blocks) == 60
assert blue.build(identity).blocks == source.blocks
reopened = Document.from_data(json.loads(json.dumps(source.to_data())))
assert reopened.blocks == source.blocks
operations = ('rotate_y90', 'rotate_y180', 'rotate_y270', 'mirror_x', 'mirror_y', 'mirror_z')
inverse = ('rotate_y270', 'rotate_y180', 'rotate_y90', 'mirror_x', 'mirror_y', 'mirror_z')
rows = []
for operation, opposite in zip(operations, inverse):
    editor = Editor(build(identity))
    assert prepare(editor, identity)
    before = dict(editor.document.blocks.items())
    editor.run(operation)
    transformed = dict(editor.document.blocks.items())
    semantic = {'cells': sorted(transformed.items()), 'selection': sorted(editor.selection),
                'start': editor.start, 'end': editor.end}
    encoded = json.dumps(semantic, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode('ascii')
    assert editor.undo() and before == dict(editor.document.blocks.items())
    assert editor.redo() and transformed == dict(editor.document.blocks.items())
    editor.run(opposite)
    assert before == dict(editor.document.blocks.items())
    rows.append({'operation': operation, 'semantic_sha256': hashlib.sha256(encoded).hexdigest()})
print(json.dumps({'fixture': identity, 'cells': 60, 'public_registered': True,
                  'roundtrip': True, 'six_operations_undo_redo_inverse': rows}, sort_keys=True))
