"""Explicit private client bootstrap; never changes production acceptance data."""

GATE_ERROR = 'Product water needs complete visible acceptance for these exact rules and resources'
BRIDGE_EMPTY_FIELDS = (
    'entity', 'preparing_entity', 'projection_mesh', 'pending', 'pending_data',
    'pending_state', 'upload', 'download', 'capture_active', 'projection_work',
    'projection_occupancy', 'projection_shader', 'projection_liquid',
    'projection_entities', 'projection_retired_entities', 'projection_retired_outlines',
    'projection_retired_liquids', 'models', 'model_layouts', 'context_models',
    'frame_work', 'frame_pumps', 'frame_watchdog', 'projection_requested',
    '_projection_follow_position', '_projection_follow_restore')
MARKERS = ('_blueprint_qa_saved', '_blueprint_visual_saved',
           '_product_water_saved_profile', '_product_water_timing',
           '_sign_visual_hud_saved', '_neighbor_visual_options_saved')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def rejected(product, engine_version):
    try:
        product.production_profile(engine_version)
    except ValueError as error:
        require(str(error) == GATE_ERROR, 'Unexpected production refusal: ' + str(error))
        return True
    raise RuntimeError('Production entry did not retain the expected qualification mismatch')


def bootstrap(system, deployment, product, qualification, owners, expected_engine,
              expected_water_names, expected_owner_hash, expected_old_qualification_hash,
              sys_module, receipt):
    """Run only on the client thread after the normal constructor refused.

    All identity, launch-source and module-byte checks belong to the bound host
    adapter. This function has no IO, SDK imports, callbacks, waits or retries.
    A failed initialization is retained for ordinary instance stop, never replayed.
    """
    receipt.update(schema=1, explicit_development_candidate=True,
                   production_admission_performed=False, default_path_evidence=False,
                   profile_assignment_performed=False, completed=False,
                   original_function_restored=False)
    require(system is not None, 'Missing registered client system')
    require(system.session is None, 'Session already exists; do not reinitialize')
    bridge = system.bridge
    require(bridge is not None and bridge.session is None and bridge.alive is True,
            'Expected the idle bridge left by constructor refusal')
    require(bridge.engine_version == expected_engine, 'Unexpected client engine')
    for name in BRIDGE_EMPTY_FIELDS:
        require(hasattr(bridge, name), 'Missing expected bridge field: ' + name)
        require(not getattr(bridge, name), 'Bridge still owns work: ' + name)
    for name in ('hud', 'staff_aura', 'nearby_staff_auras'):
        require(hasattr(system, name) and getattr(system, name) is None,
                'Client system already owns UI or effects: ' + name)
    require(not bridge.survey_effects.active(), 'Survey effects are active')
    require(bridge.projection_outline.entity is None and
            not bridge.projection_outline.effects.active(), 'Projection outline is active')
    require(not any(hasattr(sys_module, name) for name in MARKERS), 'Existing private probe markers')
    require(qualification.PRODUCT_QUALIFIED is True, 'Do not disable the production gate')
    require(owners.IMPLEMENTATION_CONTRACT_SHA256 == expected_owner_hash,
            'Generated implementation owner differs from frozen host binding')
    require(qualification.QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256 ==
            expected_old_qualification_hash, 'Old qualification was changed')
    require(expected_owner_hash != expected_old_qualification_hash,
            'Expected an explicit new-source qualification mismatch')
    rejected(product, expected_engine)
    candidate = product.candidate_profile(frozen=False)
    require(candidate.supported_names == frozenset(expected_water_names),
            'Candidate must own the complete explicit water name set')
    original = deployment.production_profile
    selections = []

    def select(engine_version=None):
        require(engine_version == expected_engine, 'Unexpected engine during candidate construction')
        require(not selections, 'Candidate selection was called more than once')
        selections.append(engine_version)
        return candidate

    deployment.production_profile = select
    receipt['temporary_function_installed'] = True
    try:
        system.UiInitFinished(None)
        require(len(selections) == 1, 'Constructor did not select the explicit candidate exactly once')
        require(system.session is not None and system.bridge is not bridge,
                'Ordinary UiInitFinished did not complete new Session construction')
        require(system.bridge.session is system.session, 'New bridge Session identity mismatch')
        require(system.session.liquid_profile is candidate, 'Session did not retain the explicit candidate')
        receipt.update(profile_assignment_performed=True,
                       selected_names=sorted(candidate.supported_names),
                       selected_style=candidate.style_version,
                       selected_rules_sha256=candidate.rules_sha256,
                       owner_contract_sha256=expected_owner_hash,
                       retained_qualification_implementation_sha256=expected_old_qualification_hash,
                       constructor_selection_count=len(selections))
    finally:
        deployment.production_profile = original
        receipt['original_function_restored'] = deployment.production_profile is original
        require(receipt['original_function_restored'], 'Failed to restore exact production function identity')
    rejected(product, expected_engine)
    require(owners.IMPLEMENTATION_CONTRACT_SHA256 == expected_owner_hash and
            qualification.QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256 ==
            expected_old_qualification_hash and qualification.PRODUCT_QUALIFIED is True,
            'Qualification or owner changed during bootstrap')
    receipt['completed'] = True
    return receipt

import json,sys,traceback
import mod.client.extraClientApi as api
from modern_projection.projection import liquid_deployment as deployment
from modern_projection.projection import liquid_product_deployment as product
from modern_projection.projection import liquid_product_qualification_data as qualification
from modern_projection.projection import liquid_product_owner_data as owners
system=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
marker='_water_r27_ui_geometry_bootstrap_v2'
if hasattr(sys,marker):
    raise RuntimeError('Private bootstrap marker already exists; never replay')
bootstrap_receipt={'adapter_stage':'before_default_check','bootstrap_call_count':0,
                   'adapter_finally_reached':False}
saved_original=deployment.production_profile
setattr(sys,marker,{'receipt':bootstrap_receipt,'original_function':saved_original})
try:
    try:
        product.production_profile('3.10.0.420447')
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
    bootstrap(system,deployment,product,qualification,owners,'3.10.0.420447',('minecraft:water', 'minecraft:flowing_water'),'d0f37c33f8e054a0e906f44361edc43f49957b26b4af7853da9f2c0ca49bf20f','ef4f709969b6e96d7675529cd84ff27043706b23b723c4ee3d399497b32f4872',sys,bootstrap_receipt)
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
