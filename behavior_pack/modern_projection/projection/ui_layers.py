"""Batch public UI layer writes without splitting a camera pose across frames."""
from collections import OrderedDict


def apply_layers(updates):
    latest = OrderedDict((id(control), (control, layer)) for control, layer in updates)
    values = list(latest.values())
    for index, (control, layer) in enumerate(values):
        control.SetLayer(layer, False, index == len(values) - 1)
