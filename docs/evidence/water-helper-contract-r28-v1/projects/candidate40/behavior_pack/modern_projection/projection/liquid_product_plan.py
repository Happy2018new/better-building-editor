"""Select product-owned water draws without changing shared surface planning.

Both liquid families are validated against the complete immutable source before
selection. Only draw targets are narrowed; shape neighbors and logical layers
remain available, including native lava barriers. The shared planner keeps its
strict legacy behavior and the other surface owners' qualified implementation.
"""
from .liquid_render_plan import (WATER_NAMES, _document_requests, _target_requests,
                                 iter_group_steps as shared_group_steps, render_steps)


def iter_group_steps(document, provider, targets=None, visible=None):
    names = frozenset(provider.supported_names)
    if not names.issubset(WATER_NAMES):
        raise ValueError('Product water draw ownership must contain only water names')
    sx, sy, sz = document.size
    selected = {'volume': (sz, sx, sy), 'common': {}, 'extra': {}}
    requests = _document_requests(document) if targets is None else _target_requests(document, targets)
    for request in requests:
        if request is None:
            yield None
            continue
        pos, layer, value = request
        if value[0] in names:
            x, y, z = pos
            index = (y * sx + x) * sz + z
            selected[('common', 'extra')[layer]].setdefault(value, []).append(index)
    for group in shared_group_steps(document, provider, selected, visible):
        yield group


def iter_groups(document, provider, targets=None, visible=None):
    for group in iter_group_steps(document, provider, targets, visible):
        if group is not None:
            yield group


def projection_plan(document, profile, targets, visible, opacity):
    groups = iter_group_steps(document, profile.provider_factory(document), targets, visible)
    return render_steps(groups, profile.world_models, opacity, profile.max_groups)
