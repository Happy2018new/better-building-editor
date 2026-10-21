"""Delegating native creation/input receipts bound to real geometry frames."""
import base64
import json
import sys
from modern_projection.projection.cell import freeze,encode as encode_cell
from modern_projection.projection.storage import integer_types
from modern_projection.projection.bridge import _native_palette


def concrete_wire(value):
    def plain(item):
        if isinstance(item,dict):return dict((key,plain(child)) for key,child in item.items())
        if isinstance(item,list):return [plain(child) for child in item]
        if isinstance(item,tuple):return tuple(plain(child) for child in item)
        if type(item).__name__=='IntegerBuffer':return ('IntegerBuffer-values',tuple(item))
        return item
    raw=repr(freeze(plain(value),budget=[1000000,64*1024*1024])).encode('utf8')
    return {'codec':'cell.freeze-repr-utf8-base64','base64':base64.b64encode(raw).decode('ascii'),'bytes':len(raw)}


def concrete_document(doc):
    return concrete_wire({'size':doc.size,'biome':doc.biome,
      'palette':tuple(encode_cell(value) for value in doc.blocks.palette),
      'chunks':tuple((key,('constant',value) if isinstance(value,integer_types)
        else ('IntegerBuffer-values',tuple(value))) for key,value in sorted(doc.blocks.chunks.items()))})


def concrete_context():
    from modern_projection.projection import render_context
    saved=sys._books_wire_observer
    hook=sys._books_wire_hook
    work=b.projection_work
    assert work is not None and work.document.blocks==s.editor.document.blocks
    assert work.liquid_profile is s.liquid_profile
    geometry=saved['geometry_function']
    geometry_code=getattr(geometry,'func_code',getattr(geometry,'__code__',None))
    frame=sys._getframe(2)
    assert frame.f_code is geometry_code,'Native call did not originate in audited original geometry'
    local=frame.f_locals
    prepared=local.get('prepared')
    data=local.get('data')
    assert isinstance(prepared,dict) and '_context_batches' not in prepared
    assert _native_palette(prepared)==data,'Actual geometry frame data differs from its prepared mapping'
    saved['retained_inputs'].append(prepared)
    top=work.prepared
    parts=top.get('_context_batches',()) if isinstance(top,dict) else ()
    source_kind='world-prepared' if any(prepared is value for origin,context,value in parts) else None
    frames=[]
    current=frame
    for unused in range(16):
        if current is None:break
        if current.f_code is geometry_code:
            values=current.f_locals
            context=values.get('context_document')
            frames.append({'name':values.get('name'),'prepared_id':id(values.get('prepared')),
              'prepared_is_work_prepared':values.get('prepared') is top and top is not None,
              'context_document_id':id(context),'context_is_work_document':context is work.document,
              'geometry_document_id':id(values.get('document')),
              'render_origin':values.get('render_origin')})
            if source_kind is None and context is work.document:source_kind='shader-spare-seed'
        current=current.f_back
    assert source_kind in ('world-prepared','shader-spare-seed'),'Unbound prepared provenance'
    private=hook['module']
    result={'fixture':sys._blueprint_qa_identity,'wire_mode':hook['mode'],'phase_key':hook['phase_key'],
      'nonce':sys._blueprint_qa_nonce,'editor_id':id(s.editor),'document_id':id(s.editor.document),
      'work_id':id(work),'work_document_id':id(work.document),'serial':work.serial,
      'origin':tuple(work.origin),'size':tuple(work.document.size),
      'profile_id':id(s.liquid_profile),'work_profile_same_object':work.liquid_profile is s.liquid_profile,
      'geometry_function_id':id(geometry),'geometry_prepared_id':id(prepared),
      'geometry_frame_data_id':id(data),'geometry_prepared_native':concrete_wire(_native_palette(prepared)),
      'geometry_frame_data':concrete_wire(data),'geometry_frames':frames,'source_kind':source_kind,
      'logical_document':concrete_document(s.editor.document),'work_document':concrete_document(work.document),
      'helper_ids':dict((key,id(getattr(render_context,key))) for key in sys._books_wire_independent['helpers']),
      'helper_call_counts':dict(private._wire_call_counts),'helper_calls':concrete_wire(private._wire_calls)}
    del frame,current
    return result


class ConcretePaletteReceipt(object):
    def __init__(self,target):self.target=target
    def __getattr__(self,name):return getattr(self.target,name)
    def DeserializeBlockPalette(self,data):
        record=concrete_context()
        record.update(phase='Deserialize',palette_id=id(self.target),native_input=concrete_wire(data))
        assert record['native_input']==record['geometry_frame_data']
        sys._books_wire_observer['records'].append(record)
        result=self.target.DeserializeBlockPalette(data)
        record['result']=result
        record['native_serialized_after']=concrete_wire(self.target.SerializeBlockPalette())
        return result


class ConcreteBlockReceipt(object):
    def __init__(self,target):self.target=target
    def __getattr__(self,name):return getattr(self.target,name)
    def GetBlankBlockPalette(self):
        record=concrete_context()
        record.update(phase='CreatePalette',native_api='GetBlankBlockPalette')
        sys._books_wire_observer['records'].append(record)
        palette=self.target.GetBlankBlockPalette()
        record.update(result=palette is not None,palette_id=id(palette))
        if palette is not None:sys._books_wire_observer['retained_palettes'].append(palette)
        return ConcretePaletteReceipt(palette) if palette is not None else None


class ConcreteGeometryReceipt(object):
    def __init__(self,target):self.target=target
    def __getattr__(self,name):return getattr(self.target,name)
    def CombineBlockPaletteToGeometry(self,palette,name,mode=0):
        target=palette.target if isinstance(palette,ConcretePaletteReceipt) else palette
        record=concrete_context()
        record.update(phase='Combine',palette_id=id(target),name=name,mode=mode,
          native_serialized=concrete_wire(target.SerializeBlockPalette()))
        sys._books_wire_observer['records'].append(record)
        result=self.target.CombineBlockPaletteToGeometry(target,name,mode)
        record['result']=result
        return result


class ConcreteFactoryReceipt(object):
    def __init__(self,target):self.target=target
    def __getattr__(self,name):return getattr(self.target,name)
    def CreateBlock(self,level):return ConcreteBlockReceipt(self.target.CreateBlock(level))
    def CreateBlockGeometry(self,level):return ConcreteGeometryReceipt(self.target.CreateBlockGeometry(level))


def concrete_install():
    assert not hasattr(sys,'_books_wire_observer')
    sys._books_wire_observer={'factory':b.factory,'records':[],
      'geometry_function':getattr(type(b).geometry,'im_func',type(b).geometry),
      'retained_palettes':[],'retained_inputs':[],'retained_phase_objects':[]}
    b.factory=ConcreteFactoryReceipt(b.factory)
    sys._books_wire_observer['installed_factory']=b.factory


def concrete_retire():
    saved=sys._books_wire_observer
    summary=None
    try:
        assert b.factory is saved['installed_factory'] and isinstance(b.factory,ConcreteFactoryReceipt)
        records=saved['records']
        assert len(records)<=4096,'Native record count exceeds bounded retirement receipt'
        phases={}
        for record in records:
            key=record['phase_key']
            assert isinstance(key,(str,type(u''))) and 0<len(key)<=192
            assert key in phases or len(phases)<12,'More than twelve native phase keys'
            phase=record['phase']
            assert phase in ('CreatePalette','Deserialize','Combine')
            counts=phases.setdefault(key,{'CreatePalette':0,'Deserialize':0,'Combine':0})
            counts[phase]+=1
        summary={'schema':'wire-native-retirement-v3','retired':True,
          'record_count':len(records),'phase_counts':phases,
          'original_factory_id':id(saved['factory']),'installed_factory_id':id(saved['installed_factory'])}
        assert len(json.dumps(summary).encode('ascii'))<=8192,'Retirement receipt exceeds eight KiB'
    finally:
        b.factory=saved['factory']
        del sys._books_wire_observer
    summary.update(factory_restored=b.factory is saved['factory'],
      restored_factory_id=id(b.factory),observer_removed=not hasattr(sys,'_books_wire_observer'))
    assert len(json.dumps(summary).encode('ascii'))<=8192,'Final retirement receipt exceeds eight KiB'
    return summary
