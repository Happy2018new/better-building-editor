"""Eight small legal/source-preserving representatives, never world placement."""

AIR=('minecraft:air',0)
WHITE=('minecraft:white_concrete',0)
STONE=('minecraft:stone',0)
WATER=('minecraft:water',0)
WIRE=('minecraft:redstone_wire',15)


def fixture(name):
    target=(15,16,15) if name=='flat-boundary' else (3,2,3)
    x,y,z=target
    cells={(x+dx,y-1,z+dz):(WHITE,AIR) for dx in (-1,0,1) for dz in (-1,0,1)}
    wires=[target]
    if name.startswith('flat') or name.startswith('negative'):
        wires.extend((x+dx,y,z+dz) for dx,dz in ((-1,0),(1,0),(0,-1),(0,1)))
    elif name=='ascending':
        cells[(x+1,y,z)]=(WHITE,AIR)
        wires.append((x+1,y+1,z))
    elif name=='descending':
        cells.pop((x+1,y-1,z))
        cells[(x+1,y-2,z)]=(WHITE,AIR)
        wires.append((x+1,y-1,z))
    else:raise ValueError(name)
    for pos in wires:cells[pos]=(WIRE,AIR)
    if name=='negative-wet-wire':
        for pos in wires:cells[pos]=(WIRE,WATER)
    elif name=='negative-wet-support':
        for px,py,pz in wires:cells[(px,py-1,pz)]=(WHITE,WATER)
    elif name=='negative-two-solid':
        for px,py,pz in wires:cells[(px,py-1,pz)]=(WHITE,STONE)
    elif name=='negative-stone-support':
        for pos,(front,back) in list(cells.items()):
            if front==WHITE:cells[pos]=(STONE,back)
    elif name not in ('flat-interior','flat-boundary','ascending','descending'):
        raise ValueError(name)
    # Physical target and camera positions match across logical 16 boundaries.
    origin_shift=tuple((1,1,1)[i]-target[i] for i in range(3))
    corners=[(px+dx,py+dy,pz+dz) for px,py,pz in wires
        for dx in (.02,.98) for dy in (0.,.15) for dz in (.02,.98)]
    return {'id':'wire-r27.'+name,'name':name,'size':(32,32,32),'target':target,
        'origin_shift':origin_shift,'cells':[(pos,front,back) for pos,(front,back) in sorted(cells.items())],
        'wire_positions':wires,'wire_bounds_points':corners,'focus':(x+.5,y+.05,z+.5),
        'poses':{'top':(0.,4.5,-5.5),'grazing':(4.,1.25,-4.)},
        'color_regions':{
            'target_corner':[(x+dx,y,z+dz) for dx,dz in ((.08,.08),(.30,.08),(.30,.30),(.08,.30))],
            'reference_corner':[(x-1+dx,y,z-1+dz) for dx,dz in ((.08,.08),(.30,.08),(.30,.30),(.08,.30))]},
        'world_writes':False,'negative':name.startswith('negative')}


NAMES=('flat-interior','flat-boundary','ascending','descending','negative-wet-wire',
    'negative-wet-support','negative-two-solid','negative-stone-support')
