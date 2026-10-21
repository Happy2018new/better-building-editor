"""Describe independent parent and visible doll geometry; no product admission."""


def describe_snapshot(snapshot,tolerance=.05):
    config=snapshot.get('config');parent=snapshot.get('viewport_parent')
    result={'logical_ready':snapshot.get('ready'),'parent_observed':parent,
        'hidden_controls':[],'active_controls':[],'geometry_contradictions':[],
        'contract_observation_complete':False,'formal_A_accepted':False}
    issues=result['geometry_contradictions']
    if not config or not parent:
        issues.append('Missing declared configuration or always-visible parent observation')
        return result
    rect=config['rect'];mode=config['mode'];controls=snapshot.get('native',[])
    def close(a,b):return len(a)==len(b) and all(abs(x-y)<=tolerance for x,y in zip(a,b))
    if not parent.get('actual_visible'):issues.append('Viewport parent is hidden')
    if not close(parent.get('size',[]),rect[2:]):issues.append('Viewport parent size differs from declared rectangle')
    if not close(parent.get('global_position',[]),rect[:2]):issues.append('Viewport parent global position differs from declared rectangle')
    if len(controls)!=3:
        issues.append('Expected exactly two skeleton controls and one stone control')
        return result
    renderer=snapshot.get('renderer') or {}
    intended=[False,False,mode=='stone']
    if mode not in ('empty','stone'):
        visible=renderer.get('visible',[])
        if len(visible)!=2 or sum(bool(v) for v in visible)!=1:
            issues.append('Renderer does not identify exactly one visible skeleton bank')
        else:intended[:2]=visible
    for index,control in enumerate(controls):
        row={'index':index,'intended_visible':bool(intended[index]),'actual':control}
        if bool(control.get('actual_visible'))!=bool(intended[index]):
            issues.append('Actual visibility differs from mode/renderer at control '+str(index))
        if not intended[index]:
            # Zero measured hidden dimensions are observed as-is, never used
            # as a substitute for the independent parent's rectangle.
            result['hidden_controls'].append(row)
            continue
        result['active_controls'].append(row)
        if not close(control.get('size',[]),rect[2:]):issues.append('Active control size differs from declared rectangle: '+str(index))
        expected=list(parent['global_position'])
        if index<2:expected[1]+=min(rect[2:])*config['offset_factor']
        if not close(control.get('global_position',[]),expected):issues.append('Active global position differs from parent plus explicit offset: '+str(index))
        if control.get('model_id',-1)==-1:issues.append('Active control lacks a native model ID: '+str(index))
        if index<2:
            ids=renderer.get('ids',[])
            if len(ids)!=2 or ids[index]!=control['model_id']:
                issues.append('Active native model ID differs from renderer bank: '+str(index))
    result['contract_observation_complete']=not issues
    return result
