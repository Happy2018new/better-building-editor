"""Read-only call receipts inside the three private diagnostic helper slots."""
_wire_originals=dict((key,globals()[key]) for key in
    ('_mark_floor_support','_mark_palette_floor_support','_hidden_neighbor'))
_wire_phase_key=None
_wire_call_counts={}
_wire_calls=[]


def _wire_record(name,values):
    _wire_call_counts[name]=_wire_call_counts.get(name,0)+1
    if len(_wire_calls)>=10000:raise ValueError('Diagnostic helper receipt budget exceeded')
    _wire_calls.append({'helper':name,'phase_key':_wire_phase_key,
      'core_function_id':id(_wire_originals[name]),'values':values})


def _mark_floor_support(cell,front,back):
    _wire_record('_mark_floor_support',{'front':front,'back':back,
      'prepared_common':cell.get('common') if cell is not None else None})
    return _wire_originals['_mark_floor_support'](cell,front,back)


def _mark_palette_floor_support(source,cells):
    _wire_record('_mark_palette_floor_support',{'cell_count':len(cells)})
    return _wire_originals['_mark_palette_floor_support'](source,cells)


def _hidden_neighbor(cell,target,neighbor=None):
    result=_wire_originals['_hidden_neighbor'](cell,target,neighbor)
    _wire_record('_hidden_neighbor',{'neighbor':neighbor,'hidden':result,
      'common':cell.get('common'),'target_common':target.get('common') if target is not None else None,
      'dry_wire':target.get('_dry_floor_wire') if target is not None else None,
      'dry_concrete':cell.get('_dry_concrete')})
    return result
