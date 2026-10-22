"""Product-water candidate: preserve projected points and drawable bounds.

This file is an offline proposal; no game source or live profile is changed.
The native skeleton anchor is (W/2, H/2-min(W,H)/gui) within its UI rectangle.
"""
import math


def ui_geometry_for_gui(position, size, gui):
    if (isinstance(gui, bool) or not isinstance(gui, (int, float))
            or not 1. <= gui < float('inf') or gui != round(gui)):
        raise ValueError('Product water needs a positive integer native GUI scale')
    if (len(position) != 2 or len(size) != 2
            or any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or math.isnan(value) or math.isinf(value) for value in tuple(position) + tuple(size))
            or min(size) <= 0.):
        raise ValueError('Product water needs finite UI geometry and positive dimensions')
    width, height = size
    expanded_height = max(width, height + 2. * width / float(gui))
    return ((position[0], position[1] + (height - expanded_height) / 2. + width / float(gui)),
            (width, expanded_height))
