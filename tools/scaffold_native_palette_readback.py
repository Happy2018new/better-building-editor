"""Typed one-cell native palette readbacks, without inferred layer defaults.

An omitted extra bucket is accepted only when an independent native observation
of this exact version supplied that representation. No actor content is returned.
"""
import ast

HELPER = '''def palette_read(pos):
 palette=block.GetBlockPaletteBetweenPos(dimension,pos,pos,False)
 assert palette is not None,'Native one-cell palette unavailable'
 data=palette.SerializeBlockPalette()
 assert isinstance(data,dict),'Native palette readback unavailable'
 value={'volume':data.get('volume'),'common':None,'extra':None,'states':None,'extraStates':None,
        'actor_empty':type(data.get('actor')) is dict and not data['actor'],
        'void':data.get('void'),'eliminateAir':data.get('eliminateAir')}
 for key in ('common','extra','states','extraStates'):
  if type(data.get(key)) is dict:
   value[key]=[]
   for material,content in sorted(data[key].items()):
    assert type(material) is tuple and len(material)==2 and type(material[1]) is int,'Invalid native palette material'
    if key in ('common','extra'):
     assert type(content) is list and all(type(index) is int for index in content),'Invalid native palette indices'
     content=list(content)
    else:assert type(content) is dict,'Invalid native palette state map'
    value[key].append([list(material),content])
 return value
def palette_air(value):
 return (value['volume'] in ((1,1,1),[1,1,1])
  and all(value[key]==config['air_encoding'][key] for key in ('common','extra','states','extraStates'))
  and value['actor_empty'] and value['void'] is False and value['eliminateAir'] is False)
'''


def _state_bucket(raw):
    parsed = ast.literal_eval(raw)
    if type(parsed) is not dict:
        raise ValueError('Native state bucket is not a dictionary')
    rows = []
    for material, states in sorted(parsed.items()):
        if (type(material) is not tuple or len(material) != 2 or type(material[0]) is not str
                or type(material[1]) is not int or type(states) is not dict):
            raise ValueError('Native state bucket has invalid typed material or states')
        rows.append([list(material), states])
    return rows


def encoding_from_observation(report):
    """Derive only an observed dry-air representation; keep its provenance."""
    if (report.get('schema') != 1 or report.get('kind') != 'scaffold_palette_air_readback'
            or report.get('runtime') != '1.21.120.0' or report.get('mutations') != []
            or report.get('acceptance') != {'editor': 'pending', 'full': 'pending', 'missing': 'pending'}):
        raise ValueError('Expected the independent raw native palette observation')
    rows = report.get('cells', [])
    if len(rows) != 2 or [row.get('label') for row in rows] != ['loaded_ground', 'natural_air']:
        raise ValueError('Expected loaded ground and natural-air controls')
    ground, air = rows
    ground_actual = ground.get('readback', {})
    ground_front = ground_actual.get('front', {})
    if (not isinstance(ground_actual.get('states'), dict) or type(ground_front.get('aux')) is not int
            or ground_front.get('name') in (None, 'minecraft:air', 'minecraft:unknown')
            or tuple(ground.get('volume', ())) != (1, 1, 1)
            or ground.get('common') != [[[ground_front['name'], ground_front['aux']], [0]]]
            or _state_bucket(ground.get('states_repr', 'None')) != [
                [[ground_front['name'], ground_front['aux']], ground_actual['states']]]):
        raise ValueError('Native ground state positive control missing')
    states = _state_bucket(air.get('states_repr', 'None'))
    extra_states = _state_bucket(air.get('extraStates_repr', 'None'))
    actual = air.get('readback', {})
    if (actual.get('front') != {'name': 'minecraft:air', 'aux': 0}
            or type(actual['front'].get('aux')) is not int or actual.get('liquid') is not None
            or actual.get('states') not in (None, {}) or tuple(air.get('volume', ())) != (1, 1, 1)
            or air.get('common') != [[['minecraft:air', 0], [0]]]
            or air.get('extra') not in ([], [[['minecraft:air', 0], [0]]])
            or states not in ([], [[['minecraft:air', 0], {}]]) or extra_states != []
            or air.get('actor_repr') != '{}' or air.get('void') is not False
            or air.get('eliminateAir') is not False):
        raise ValueError('Native observation did not establish the dry two-layer encoding')
    result = {'common': air['common'], 'extra': air['extra'], 'states': states, 'extraStates': extra_states}
    if not valid(dict(result, volume=air['volume'], actor_empty=True, void=False, eliminateAir=False), result):
        raise ValueError('Native observation has invalid typed layer indices')
    return result


def _typed(value):
    if isinstance(value, dict):
        return ('dict', tuple(sorted((key, _typed(item)) for key, item in value.items())))
    if isinstance(value, (tuple, list)):
        return (type(value).__name__, tuple(_typed(item) for item in value))
    return (type(value).__name__, value)


def valid(value, expected):
    if (not isinstance(value, dict) or tuple(value.get('volume', ())) != (1, 1, 1)
            or any(type(axis) is not int for axis in value['volume'])
            or value.get('actor_empty') is not True or value.get('void') is not False
            or value.get('eliminateAir') is not False):
        return False
    for key in ('common', 'extra', 'states', 'extraStates'):
        actual = value.get(key)
        if type(actual) is not list or _typed(actual) != _typed(expected.get(key)):
            return False
        for material, content in actual:
            if (type(material) is not list or len(material) != 2 or type(material[0]) is not str
                    or type(material[1]) is not int):
                return False
            if key in ('common', 'extra'):
                if type(content) is not list or any(type(index) is not int for index in content):
                    return False
            elif type(content) is not dict:
                return False
    return True
