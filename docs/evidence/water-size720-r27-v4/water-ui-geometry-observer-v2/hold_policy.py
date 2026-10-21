"""Limits for one fixed, SHA-authorized root follow-up in the owned session."""

def validate_hold(grant,owner,plan_sha256,now):
    assert grant['schema']==2 and grant['owner']==owner and grant['plan_sha256']==plan_sha256
    assert grant['begin']<=now<grant['until']-120.
    value=grant['hold']
    assert value['enabled'] is True
    seconds=value['max_seconds'];timeout=value['followup_timeout_seconds']
    assert isinstance(seconds,int) and not isinstance(seconds,bool) and 1<=seconds<=900
    assert isinstance(timeout,int) and not isinstance(timeout,bool) and 1<=timeout<=180
    return {'max_seconds':seconds,'followup_timeout_seconds':timeout}


def validate_release(value,owner,plan_sha256,session_id):
    assert value['schema']==1 and value['root_authorized'] is True
    assert value['owner']==owner and value['plan_sha256']==plan_sha256
    assert value['session_id']==session_id and value['release'] is True


def validate_authorization(value,owner,plan_sha256,session_id,actual_script_sha256,now,until,timeout):
    assert value['schema']==1 and value['root_authorized'] is True
    assert value['owner']==owner and value['plan_sha256']==plan_sha256
    assert value['session_id']==session_id and value['script_sha256']==actual_script_sha256
    assert value['diagnostic_only'] is True and value['source_mutation_allowed'] is False
    assert now+timeout+60.<until,'Leave bounded execution and restoration time'
