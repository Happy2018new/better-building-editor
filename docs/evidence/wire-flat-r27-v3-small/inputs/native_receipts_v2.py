"""Fail closed unless real native creation, prepared input and Serialize agree."""
import base64
import hashlib


def wire_hashes(value):
    if isinstance(value,dict):
        if value.get('codec')=='cell.freeze-repr-utf8-base64':
            raw=base64.b64decode(value['base64'],validate=True)
            assert len(raw)==value['bytes'] and b'IntegerBuffer object at' not in raw
            value['host_sha256']=hashlib.sha256(raw).hexdigest()
        else:
            for child in value.values():wire_hashes(child)
    elif isinstance(value,list):
        for child in value:wire_hashes(child)


def validate_phase(snapshot,expected,helper_ids,geometry_id,seen_palette_ids):
    records=snapshot['records']
    assert records and len(records)%3==0,'Missing actual Create/Deserialize/Combine receipts'
    assert all(snapshot[key]==expected[key] for key in ('phase_key','work_id','serial','logical_document'))
    assert snapshot['work_document']==expected['logical_document']
    native_names={row[0] for values in snapshot['buffer_parts'].values() for row in values}
    made=set();kinds=set()
    for index in range(0,len(records),3):
        create,load,combine=records[index:index+3]
        assert [row['phase'] for row in (create,load,combine)]==['CreatePalette','Deserialize','Combine']
        for row in (create,load,combine):
            assert row['result'],'Native operation failed'
            for key in ('fixture','phase_key','nonce','editor_id','document_id','work_id',
              'work_document_id','serial','origin','size','profile_id','logical_document'):
                assert row[key]==expected[key],('Actual native source binding mismatch',key)
            assert row['wire_mode']==expected['mode']
            assert row['helper_ids']==helper_ids,'Actual preparation helper selection mismatch'
            assert row['geometry_function_id']==geometry_id
            assert row['work_document']==expected['logical_document']
            assert row['work_profile_same_object'] is True
            assert row['geometry_prepared_native']==row['geometry_frame_data'],'Prepared/frame input mismatch'
            assert row['geometry_prepared_id']==create['geometry_prepared_id']
            assert row['palette_id']==create['palette_id']
            assert row['source_kind'] in ('world-prepared','shader-spare-seed')
            kinds.add(row['source_kind'])
            if row['source_kind']=='world-prepared':
                assert any(frame['prepared_is_work_prepared'] for frame in row['geometry_frames'])
            else:assert any(frame['context_is_work_document'] for frame in row['geometry_frames'])
            if expected['mode']=='candidate':
                assert row['helper_call_counts'].get('_mark_floor_support',0)>0
                assert row['helper_call_counts'].get('_hidden_neighbor',0)>0
            else:assert not row['helper_call_counts'],'Private candidate was called in a base/restored phase'
        assert create['native_api']=='GetBlankBlockPalette'
        assert create['palette_id'] not in seen_palette_ids and create['palette_id'] not in made,'Native palette object was reused'
        made.add(create['palette_id'])
        assert load['native_input']==load['geometry_prepared_native']
        assert create['geometry_frame_data']==load['native_input']==combine['geometry_frame_data']
        assert load['native_serialized_after']==combine['native_serialized'],'Native Serialize changed before Combine'
        assert combine['name'] in native_names,'Native Combine result is not in the current shader buffers'
    assert kinds=={'world-prepared','shader-spare-seed'},'Both the full prepared work and fresh spare seed must actually submit'
    seen_palette_ids.update(made)
    return {'verified':True,'actual_native_creation_pairs':len(made),
      'new_retained_palette_ids':sorted(made),'source_kinds':sorted(kinds),
      'actual_prepared_and_native_input_equal':True,'actual_Serialize_chain_equal':True,
      'fresh_work_id':expected['work_id'],'serial':expected['serial'],
      'helper_call_counts':snapshot['helper_call_counts']}
