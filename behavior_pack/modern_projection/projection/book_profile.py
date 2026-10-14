"""Candidate book companions; native table/lectern bodies remain untouched."""
from .cell import integer_types

ENGINE_VERSION='3.10.0.420447'
SCHEMA_VERSION=1
PRODUCT_QUALIFIED=False


class BookProfile(object):
    supported_names=()
    world_scale=(16.,16.,16.)
    world_rotation=(0.,0.,0.)

    @staticmethod
    def ui_pose(unit,pitch,yaw,size):
        return unit/min(size),pitch-90.,0.,yaw

    @staticmethod
    def ui_offset(size):
        return 0.,min(size)/4.

    def __init__(self,max_groups=128):
        if type(max_groups) is bool or not isinstance(max_groups,integer_types) or max_groups<1:
            raise ValueError('Book companion needs a positive owned model budget')
        self.max_groups=max_groups
        self.models=dict((name,'modern_projection_book_'+name) for name in ('enchanting_table','lectern'))
        self.world_models=dict((name,value+'_world') for name,value in self.models.items())
        self.identity=(SCHEMA_VERSION,ENGINE_VERSION,'native_artwork_idle_book_v1',max_groups)


def candidate_profile(max_groups=128):
    return BookProfile(max_groups)


def production_profile(engine_version=None,max_groups=128):
    # Admission needs both ordinary product owners and their pixel matrix.
    return None
