# -*- coding: utf-8 -*-
"""Validated, independent preferences for private world projection outlines."""
from __future__ import unicode_literals

STYLES = ('rainbow', 'golden', 'starry')
LIMITS = {'speed': (.25, 6.), 'orbit_speed': (.25, 3.),
          'brightness': (.35, 1.5), 'density': (.3, 1.8), 'width': (.5, 2.)}


def defaults():
    return dict((style, {'speed': 3. if style == 'rainbow' else 1.8 if style == 'golden' else 1.,
                         'orbit_speed': 1., 'brightness': 1., 'density': 1., 'width': 1.})
                for style in STYLES)


def valid_parameter(name, value):
    return (name in LIMITS and type(value) in (int, float)
            and LIMITS[name][0] <= value <= LIMITS[name][1])


def normalize(value):
    result = defaults()
    if isinstance(value, dict):
        for style in STYLES:
            record = value.get(style)
            if isinstance(record, dict):
                for name in LIMITS:
                    if valid_parameter(name, record.get(name)):
                        result[style][name] = float(record[name])
    return result
