"""Public SDK layer writes; large camera order changes are spread across frames."""
from collections import OrderedDict


def apply_layers(updates):
    # Keep only the last request for each native control. The final SetLayer
    # requests the public refresh directly, without a duplicate layer write.
    latest = OrderedDict((id(control), (control, layer)) for control, layer in updates)
    values = list(latest.values())
    for index, (control, layer) in enumerate(values):
        control.SetLayer(layer, False, index == len(values)-1)


class PendingLayers(object):
    """Coalesce superseded order changes without intercepting engine routing."""
    def __init__(self):
        self.pending = OrderedDict()

    def add(self, updates):
        for control, layer in updates:
            self.pending[id(control)] = (control, layer)

    def flush(self, controls, limit=4):
        alive = set(id(control) for control in controls)
        for identity in list(self.pending):
            if identity not in alive:
                self.pending.pop(identity)
        batch = []
        while self.pending and len(batch) < limit:
            unused, entry = self.pending.popitem(last=False)
            batch.append(entry)
        apply_layers(batch)
