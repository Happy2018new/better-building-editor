"""Typed one-cell native palette readbacks, without inferred layer defaults.

An omitted extra bucket is accepted only when an independent native observation
of this exact version supplied that representation. No actor content is returned.
"""
HELPER = '''def palette_read(pos):
 palette=block.GetBlockPaletteBetweenPos(dimension,pos,pos,False)
 assert palette is not None,'Native one-cell palette unavailable'
 data=palette.SerializeBlockPalette()
 assert isinstance(data,dict),'Native palette readback unavailable'
 value={'volume':data.get('volume'),'common':None,'extra':None,
        'states_empty':type(data.get('states')) is dict and not data['states'],
        'extraStates_empty':type(data.get('extraStates')) is dict and not data['extraStates'],
        'actor_empty':type(data.get('actor')) is dict and not data['actor'],
        'void':data.get('void'),'eliminateAir':data.get('eliminateAir')}
 for key in ('common','extra'):
  if type(data.get(key)) is dict:
   value[key]=[[list(material),list(indices)] for material,indices in sorted(data[key].items())]
 return value
def palette_air(value):
 return (value['volume'] in ((1,1,1),[1,1,1]) and value['common']==config['air_encoding']['common']
  and value['extra']==config['air_encoding']['extra'] and value['states_empty']
  and value['extraStates_empty'] and value['actor_empty'])
'''


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
    if (not isinstance(ground.get('readback', {}).get('states'), dict)
            or ground['readback']['front']['name'] in ('minecraft:air', 'minecraft:unknown')):
        raise ValueError('Native ground state positive control missing')
    actual = air.get('readback', {})
    if (actual.get('front') != {'name': 'minecraft:air', 'aux': 0}
            or type(actual['front'].get('aux')) is not int or actual.get('liquid') is not None
            or actual.get('states') not in (None, {}) or tuple(air.get('volume', ())) != (1, 1, 1)
            or air.get('common') != [[['minecraft:air', 0], [0]]]
            or air.get('extra') not in ([], [[['minecraft:air', 0], [0]]])
            or any(air.get(key) != '{}' for key in ('states_repr', 'extraStates_repr', 'actor_repr'))):
        raise ValueError('Native observation did not establish the dry two-layer encoding')
    return {'common': air['common'], 'extra': air['extra']}


def valid(value, expected):
    return (isinstance(value, dict) and tuple(value.get('volume', ())) == (1, 1, 1)
            and value.get('common') == expected.get('common') and value.get('extra') == expected.get('extra')
            and all(value.get(field) is True for field in ('states_empty', 'extraStates_empty', 'actor_empty')))
