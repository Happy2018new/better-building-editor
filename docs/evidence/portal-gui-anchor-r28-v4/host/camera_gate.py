"""Exact camera completion gates shared by the host and offline real-camera test."""
from __future__ import division
import math


def numeric_pose(value, length, label):
    assert type(value) in (tuple, list) and len(value)==length,label
    assert all(type(item) in (int,float) and not math.isnan(item) and not math.isinf(item)
               for item in value),label
    return tuple(value)


def camera_settled(row):
    value=row['camera_readback']
    pose=numeric_pose(row['camera_pose'],3,'Session camera pose')
    actual=numeric_pose(value['pose'],3,'actual Scene camera pose')
    target=numeric_pose(value['target'],3,'actual Scene camera target')
    velocity=numeric_pose(value['velocity'],2,'actual Scene camera velocity')
    assert value['session_matches_scene'] and pose==actual,'Session and mounted Scene camera differ'
    assert value['at_target']==(actual==target),'Actual camera completion flag differs from values'
    assert type(value['dragging']) is bool,'Camera dragging flag shape'
    return actual==target and not value['dragging'] and velocity==(0.,0.)


def camera_matches_request(row,requested):
    target=numeric_pose(requested,3,'requested pose')
    if not camera_settled(row):return False
    actual=tuple(row['camera_pose'])
    return all((actual[i]-target[i]+180.)%360.-180.==0. for i in (0,1)) and actual[2]==target[2]


def assert_frame_identity(before,after):
    assert before['editor_id']==after['editor_id'] and before['document_id']==after['document_id']
    assert before['camera_pose']==after['camera_pose'],'Camera pose changed across capture'
    assert camera_settled(before) and camera_settled(after),'Camera was not snapped to its actual target'
    for key in ('scene_fiber_id','camera_object_id','target'):
        assert before['camera_readback'][key]==after['camera_readback'][key],key
