# -*- coding: utf-8 -*-
"""Register and close one Scene preview owner; preserve existing failure semantics."""
from __future__ import unicode_literals


def own_preview(session, preview, controls, family, missing_ok=False):
    if preview is None:
        return
    preview_field = family + '_preview'
    controls_field = family + '_controls'
    error_field = family + '_error'
    setattr(session, preview_field, preview)
    setattr(session, controls_field, controls)

    def cleanup():
        controls.close()
        preview.close()
        current = (getattr(session, preview_field, None) if missing_ok
                   else getattr(session, preview_field))
        if current is preview:
            setattr(session, preview_field, None)
            setattr(session, controls_field, None)
            setattr(session, error_field, '')
    return cleanup
