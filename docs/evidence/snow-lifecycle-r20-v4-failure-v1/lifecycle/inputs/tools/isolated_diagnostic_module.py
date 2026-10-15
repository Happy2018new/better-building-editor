"""Load a diagnostic specialization without mutating another tool's globals.

Only host-side reviewed Python files adjacent to this module are supported.
Frozen live evidence retains the exact source closure used before this loader.
"""
from pathlib import Path
from types import ModuleType
import sys
import uuid


def load(name):
    if not name.isidentifier():
        raise ValueError('Expected one adjacent diagnostic module name')
    path=Path(__file__).resolve().parent/(name+'.py')
    module=ModuleType('_isolated_'+name+'_'+uuid.uuid4().hex)
    module.__file__=str(path)
    # Register every independent instance so the owner source-closure walk
    # observes nested variants as well as the final public runtime module.
    sys.modules[module.__name__]=module
    try:
        exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
    except BaseException:
        del sys.modules[module.__name__]
        raise
    return module
