"""Measured banner-only PaperDoll depth contract for one engine bundle."""
SCHEMA_VERSION = 1
ENGINE_VERSION = '3.10.0.420447'
FAMILY = ('minecraft:standing_banner', 'minecraft:wall_banner')
VIEW_ORIGIN = 450.0
BLOCK_SCALE = 0.64
MEASUREMENT_SHA256 = '3c281616d98fb18c81475e8e3c5dec2db4a7a714205fbc2949716fa272b3bdf2'
RESOURCE_CONTRACT_SHA256 = '518b2b2a493df82af93ea55efa64147c71296ac813391097684667f6f8086873'
PRODUCT_QUALIFIED = True
QUALIFICATION_SHA256 = '9d134731ef546f9d276628ac87299c4da54cbbf8de74fcd4ee0ac92c26b6724f'
REQUIRED_GATES = frozenset(('editor', 'transform', 'zoom', 'layers', 'cutaway',
                            'projection_full', 'projection_missing', 'occupancy',
                            'restoration', 'opacity', 'default_path'))
GATES = dict((name, True) for name in REQUIRED_GATES)


def identity():
    return (SCHEMA_VERSION, ENGINE_VERSION, VIEW_ORIGIN, BLOCK_SCALE,
            MEASUREMENT_SHA256, RESOURCE_CONTRACT_SHA256, QUALIFICATION_SHA256,
            PRODUCT_QUALIFIED)


def production_names(engine_version):
    if engine_version != ENGINE_VERSION or not PRODUCT_QUALIFIED:
        return ()
    fingerprints = (MEASUREMENT_SHA256, RESOURCE_CONTRACT_SHA256, QUALIFICATION_SHA256)
    if (SCHEMA_VERSION != 1 or set(GATES) != REQUIRED_GATES or
            any(value is not True for value in GATES.values()) or
            any(len(value) != 64 or any(character not in '0123456789abcdef'
                                      for character in value) for value in fingerprints)):
        raise ValueError('Banner editor route needs complete acceptance for its measured family')
    return FAMILY
