"""Book companions over complete logical NBT; target palettes choose cells."""
from . import block_registry
from .cell import actor_data,foreground,integer_types
from .liquid_render_plan import LiquidSurface
from .liquid_transport import RenderGroup,pack_group
from .nbt_spatial import root_payload,scalar
from .visible_actor import entity_nbt
from .visible_item_contents import content_slots

NAMES=frozenset(('minecraft:enchanting_table','minecraft:lectern'))


def _targets(document,targets):
    if targets is None:return None
    sx,sy,sz=document.size
    if tuple(targets.get('volume',()))!=(sz,sx,sy):
        raise ValueError('Book targets need the complete logical volume')
    result=set()
    for material,indices in targets.get('common',{}).items():
        if material[0] not in NAMES:continue
        for index in indices:
            if type(index) is bool or not isinstance(index,integer_types) or not 0<=index<sx*sy*sz:
                raise ValueError('Book target lies outside its logical document')
            position=(index//sz%sx,index//(sx*sz),index%sz)
            if position in result or document.get_layer(position,0)!=material:
                raise ValueError('Book target repeats or differs from its source')
            result.add(position)
    return result


def appearance(material,actor,engine_version):
    if engine_version!='3.10.0.420447':return None
    if material[0]=='minecraft:enchanting_table':
        root=root_payload(entity_nbt(actor))
        return ('enchanting_table',0) if root is not None and scalar(root,'id') in ('EnchantTable',b'EnchantTable') else None
    if material[0]=='minecraft:lectern':
        slots=content_slots(material,actor,engine_version)
        if slots and slots[0].family=='lectern' and slots[0].item['newItemName'] in (
                'minecraft:writable_book',b'minecraft:writable_book','minecraft:written_book',b'minecraft:written_book'):
            return 'lectern',{'south':0,'west':64,'north':128,'east':192}[slots[0].direction]
    return None


def iter_render_steps(document,profile,targets=None,visible=None,world=False,opacity=1.):
    selected=_targets(document,targets)
    groups={}
    for position,cell in document.blocks.items():
        yield None
        if selected is not None and position not in selected or visible is not None and not visible(position):continue
        result=appearance(foreground(cell),actor_data(cell),profile.identity[1])
        if result is None:continue
        family,rotation=result
        origin=tuple(value//4*4 for value in position)
        surface=LiquidSurface(position,0,(1.,)*4,63,'still_water_grey',('book_direction',rotation))
        groups.setdefault((origin,family),[]).append(surface)
    count=0
    models=profile.world_models if world else profile.models
    for (origin,family),surfaces in sorted(groups.items()):
        if family not in models:
            raise ValueError('Book companion model is not registered: '+family)
        for start in range(0,len(surfaces),4):
            count+=1
            if count>profile.max_groups:raise ValueError('Book companion exceeds its owned model budget')
            uniforms=pack_group(origin,tuple(surfaces[start:start+4]),(255,255,255),1.,opacity)
            yield RenderGroup((origin,('book',family,1.),start//4),models[family],origin,uniforms)
