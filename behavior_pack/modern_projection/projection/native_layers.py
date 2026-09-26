"""Public SDK layer writes for the three-axis orientation widget.

Model tiles have stable layers; never split a camera pose's depth order across
frames. That exposed mixed front/back chunks during continuous orbit.
"""
from collections import OrderedDict


def apply_layers(updates):
    # Keep only the last request for each native control. The final SetLayer
    # requests the public refresh directly, without a duplicate layer write.
    latest = OrderedDict((id(control), (control, layer)) for control, layer in updates)
    values = list(latest.values())
    for index, (control, layer) in enumerate(values):
        control.SetLayer(layer, False, index == len(values)-1)
