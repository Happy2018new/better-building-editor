"""Candidate book companions; native table/lectern bodies remain untouched."""
from .cell import integer_types
from . import book_qualification_data as qualification

ENGINE_VERSION='3.10.0.420447'
SCHEMA_VERSION=1
PRODUCT_QUALIFIED=qualification.PRODUCT_QUALIFIED
RESOURCE_CONTRACT_SHA256='1754f445fd66c4aac605bf7c8d938f0a7fda20f3d9066b6b089bbd0195543322'
REQUIRED_GATES=frozenset(('owner_matrix','raster_regression','lectern_page_surface',
                          'body_boundary_pixels','dense_cover_motion','source_closure','default_path'))


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

    @staticmethod
    def ui_offset_for_gui(size,gui):
        """Compensate the native skeleton anchor at the actual GUI scale."""
        if (isinstance(gui,bool) or not isinstance(gui,integer_types+(float,))
                or not 1.<=gui<float('inf') or gui!=round(gui)):
            raise ValueError('Book preview needs a positive integer native GUI scale')
        return 0.,min(size)/float(gui)

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
    if engine_version!=ENGINE_VERSION or PRODUCT_QUALIFIED is not True:
        return None
    gates=qualification.GATES
    required=REQUIRED_GATES
    if qualification.QUALIFICATION_STAGE=='isolated_default_test':
        required=required-frozenset(('default_path',))
    fingerprint=qualification.QUALIFICATION_SHA256
    if (qualification.SCHEMA_VERSION!=1 or
            qualification.QUALIFICATION_ENGINE_VERSION!=ENGINE_VERSION or
            qualification.QUALIFICATION_RESOURCE_CONTRACT_SHA256!=RESOURCE_CONTRACT_SHA256 or
            qualification.QUALIFICATION_STAGE not in ('product','isolated_default_test') or
            len(fingerprint)!=64 or any(value not in '0123456789abcdef' for value in fingerprint) or
            not isinstance(gates,dict) or set(gates)!=REQUIRED_GATES or
            any(gates[name] is not True for name in required)):
        raise ValueError('Book companions need reviewed qualification for their exact resource and owner bundle')
    return candidate_profile(max_groups)
