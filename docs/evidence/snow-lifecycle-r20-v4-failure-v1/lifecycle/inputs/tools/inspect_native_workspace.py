"""Inspect native workspace startup and exercise its idempotent UI initializer."""
import json
import traceback
import mod.client.extraClientApi as api

owner = api.GetSystem('ModernProjection', 'ModernProjectionClientSystem')
result = {'system': owner is not None}
if owner is not None:
    result['initialized_before'] = owner.session is not None
    try:
        owner.UiInitFinished(None)
    except Exception:
        result['initialization_error'] = traceback.format_exc()
    result['initialized_after'] = owner.session is not None
    result['bridge'] = owner.bridge is not None
    result['hud'] = owner.hud is not None
    if owner.session is not None:
        result['document'] = owner.session.editor.document.name
_result = json.dumps(result)
