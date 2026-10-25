# -*- coding: utf-8 -*-
"""Readable exception details for Python 2 SDK and Python 3 host callbacks."""
from __future__ import unicode_literals
# Future unicode literals make this unicode on Python 2 and str on Python 3.
text_type = type('')


def error_text(error):
    args = getattr(error, 'args', ())
    if len(args) == 1 and isinstance(args[0], bytes):
        return args[0].decode('utf8', 'replace')
    try:
        return text_type(error)
    except UnicodeError:
        # Some native SDK exceptions expose UTF-8 bytes through __str__.
        return str(error).decode('utf8', 'replace')
