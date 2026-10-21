"""Build a single private invocation and a separately readable runtime receipt."""


def dispatch_code(core, binding):
    tail = '''
import json,sys,traceback
import mod.client.extraClientApi as api
from modern_projection.projection import liquid_deployment as deployment
from modern_projection.projection import liquid_product_deployment as product
from modern_projection.projection import liquid_product_qualification_data as qualification
from modern_projection.projection import liquid_product_owner_data as owners
system=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
marker=%r
if hasattr(sys,marker):
    raise RuntimeError('Private bootstrap marker already exists; never replay')
bootstrap_receipt={'adapter_stage':'before_default_check','bootstrap_call_count':0,
                   'adapter_finally_reached':False}
saved_original=deployment.production_profile
setattr(sys,marker,{'receipt':bootstrap_receipt,'original_function':saved_original})
try:
    try:
        product.production_profile(%r)
    except ValueError as default_error:
        bootstrap_receipt['default_refusal_before_bootstrap']={
            'error_type':type(default_error).__name__,'message':str(default_error),
            'expected':str(default_error)==GATE_ERROR}
    else:
        raise RuntimeError('Normal production call unexpectedly admitted new source')
    if not bootstrap_receipt['default_refusal_before_bootstrap']['expected']:
        raise RuntimeError('Unexpected default production refusal')
    bootstrap_receipt['adapter_stage']='calling_original_core'
    bootstrap_receipt['bootstrap_call_count']=1
    bootstrap(system,deployment,product,qualification,owners,%r,%r,%r,%r,sys,bootstrap_receipt)
    bootstrap_receipt['adapter_stage']='original_core_returned'
except Exception as bootstrap_error:
    bootstrap_receipt.update(error_type=type(bootstrap_error).__name__,error=str(bootstrap_error),
                             traceback=traceback.format_exc())
finally:
    bootstrap_receipt['adapter_finally_reached']=True
    bootstrap_receipt['adapter_original_function_restored']=deployment.production_profile is saved_original
    bootstrap_receipt['session_exists_after']=system is not None and system.session is not None
    bootstrap_receipt['hud_exists_after']=system is not None and system.hud is not None
_result=json.dumps(bootstrap_receipt)
''' % (binding['bootstrap_receipt_marker'], binding['engine_version'],
       binding['engine_version'], tuple(binding['supported_water_names']),
       binding['owner_contract_sha256'], binding['old_qualification_implementation_sha256'])
    return core + tail


def readback_code(marker, retire=False):
    return '''import json,sys
from modern_projection.projection import liquid_deployment as deployment
marker=%r
saved=getattr(sys,marker,None)
if saved is None:
    result={'marker_exists':False}
else:
    result={'marker_exists':True,'receipt':dict(saved['receipt']),
            'original_function_identity_now':deployment.production_profile is saved['original_function']}
    if %r:
        if not result['receipt'].get('adapter_finally_reached') or not result['original_function_identity_now']:
            raise RuntimeError('Cannot retire a nonterminal or unrestored private bootstrap receipt')
        delattr(sys,marker)
        result['marker_retired']=not hasattr(sys,marker)
_result=json.dumps(result)
''' % (marker, retire)


def accepted_runtime(readback):
    receipt = readback.get('receipt') or {}
    return bool(readback.get('marker_exists') and readback.get('original_function_identity_now')
                and receipt.get('completed') and receipt.get('adapter_finally_reached')
                and receipt.get('adapter_original_function_restored')
                and receipt.get('original_function_restored')
                and receipt.get('bootstrap_call_count') == 1
                and receipt.get('default_refusal_before_bootstrap', {}).get('expected')
                and receipt.get('session_exists_after') and receipt.get('hud_exists_after'))
