"""Versioned flat-family resources with independent UI/world calibration gates."""
from . import block_registry
from . import item_sprite_data as source
from .item_sprite_plan import PAYLOAD_VERSION


class _ItemProfiles(dict):
    """Index variants by identifier; durability is not a different silhouette."""
    def __init__(self, rows):
        dict.__init__(self, rows)
        self.by_name = {}
        for (name, aux), row in rows.items():
            self.by_name.setdefault(name, []).append(row)

    def get(self, key, default=None):
        direct = dict.get(self, key)
        if direct is not None:
            return direct
        name, aux = key
        for row in self.by_name.get(name, ()):
            durability = row.get('max_durability', 0)
            if aux in row.get('observed_aux', ()) or durability and 0 <= aux <= durability:
                return row
        return default


class ItemSpriteProfile(object):
    def __init__(self, engine_version=None, include_frame_blocks=True):
        if (source.SCHEMA_VERSION != 1 or source.PAYLOAD_VERSION != PAYLOAD_VERSION or
                source.SOURCE_VERSION != block_registry.source_version() or
                source.PALETTE_SHA256 != block_registry.fingerprint()):
            raise ValueError('Item sprite resources need regeneration for this block registry')
        self.items = source.ITEMS
        self.engine_version = engine_version
        self.content_families = ('frame',)
        self.max_groups = source.MAX_GROUPS
        if engine_version is not None:
            from . import item_icon_data as icons
            if (icons.SCHEMA_VERSION != 1 or icons.LAYOUT_VERSION != PAYLOAD_VERSION or
                    engine_version != icons.ENGINE_VERSION):
                raise ValueError('Measured item icons need regeneration for this engine')
            self.items = _ItemProfiles(icons.ITEMS)
            self.max_groups = icons.MAX_GROUPS
            self.content_families = ('frame', 'shelf', 'campfire')
            if include_frame_blocks:
                from .frame_block_item_profile import candidate_items
                self.items = _ItemProfiles(_merge_items(self.items, candidate_items(engine_version)))
        self.world_scale, self.world_rotation = (16.,) * 3, (0.,) * 3

    @staticmethod
    def ui_pose(unit, pitch, yaw, size):
        return unit / min(size), pitch - 90., 0., yaw

    @staticmethod
    def ui_offset(size):
        return 0., min(size) / 4.


def candidate_profile(engine_version=None):
    return ItemSpriteProfile(engine_version)


def _merge_items(original, additional):
    if set(original).intersection(additional):
        raise ValueError('Flat icons and frame block geometry have overlapping item owners')
    result = dict(original)
    result.update(additional)
    return result


def frame_block_candidate_profile(engine_version, materials=('opaque', 'cutout', 'translucent')):
    from .frame_block_item_profile import candidate_items
    profile = ItemSpriteProfile(engine_version, include_frame_blocks=False)
    profile.items = _ItemProfiles(candidate_items(engine_version, materials))
    profile.content_families = ('frame',)
    return profile


def measured_frame_block_candidate_profile(engine_version):
    from .frame_block_measured_profile import candidate_items
    profile = ItemSpriteProfile(engine_version, include_frame_blocks=False)
    profile.items = _ItemProfiles(candidate_items(engine_version))
    profile.content_families = ('frame',)
    return profile


def _with_shelf_items(profile, rows):
    from .shelf_body import accepts_item_contents
    if not hasattr(profile, 'frame_items'):
        profile.frame_items = profile.items
    combined = dict(profile.items)
    for key, row in rows.items():
        combined.setdefault(key, row)
    profile.items = _ItemProfiles(combined)
    profile.shelf_items = _ItemProfiles(rows)
    profile.shelf_accepts = accepts_item_contents
    if 'shelf' not in profile.content_families:
        profile.content_families += ('shelf',)
    return profile


def shelf_candidate_profile(engine_version):
    from .shelf_item_profile import candidate_items
    profile = ItemSpriteProfile(engine_version, include_frame_blocks=False)
    profile.items, profile.content_families = {}, ()
    return _with_shelf_items(profile, candidate_items(engine_version))


def ordinary_frame_candidate_profile(engine_version):
    from .ordinary_frame_item_profile import candidate_items
    profile = ItemSpriteProfile(engine_version, include_frame_blocks=False)
    profile.items = _ItemProfiles(candidate_items(engine_version))
    profile.frame_items = profile.items
    profile.content_families = ('frame',)
    return profile


def production_profile(engine_version=None):
    if engine_version is not None:
        from . import item_icon_data as icons
        from .frame_block_item_profile import production_items
        from .frame_block_measured_profile import production_items as measured_production_items
        from .shelf_item_profile import production_items as shelf_production_items
        from .ordinary_frame_item_profile import production_items as ordinary_production_items
        # A narrowly measured replacement owns a pair also present in the old catalog.
        blocks = dict(production_items(engine_version))
        blocks.update(measured_production_items(engine_version))
        shelves = shelf_production_items(engine_version)
        ordinary = ordinary_production_items(engine_version)
        if engine_version != icons.ENGINE_VERSION:
            return None
        if not icons.PRODUCTION_QUALIFIED:
            if not blocks and not shelves and not ordinary:
                return None
            profile = ItemSpriteProfile(engine_version, include_frame_blocks=False)
            profile.items = _ItemProfiles(_merge_items(blocks, ordinary))
            profile.frame_items = profile.items
            profile.content_families = ('frame',) if blocks or ordinary else ()
            return _with_shelf_items(profile, shelves) if shelves else profile
        digest = icons.QUALIFICATION_SHA256
        if (not isinstance(digest, str) or len(digest) != 64 or
                any(value not in '0123456789abcdef' for value in digest)):
            raise ValueError('Measured item deployment requires visible acceptance')
        if icons.QUALIFICATION_RESOURCE_SHA256 != icons.RESOURCE_SHA256:
            raise ValueError('Measured item qualification belongs to a different resource contract')
        profile = ItemSpriteProfile(engine_version, include_frame_blocks=False)
        profile.items = _ItemProfiles(_merge_items(profile.items, blocks))
        frames = dict(profile.items)
        frames.update(ordinary)
        profile.frame_items = _ItemProfiles(frames)
        families = icons.QUALIFIED_FAMILIES
        if (not isinstance(families, tuple) or not families or
                any(family not in profile.content_families for family in families)):
            raise ValueError('Measured item qualification requires explicit supported content families')
        profile.content_families = families if not (blocks or ordinary) or 'frame' in families else ('frame',) + families
        return _with_shelf_items(profile, shelves) if shelves else profile
    if not source.PRODUCTION_QUALIFIED:
        return None
    digest = source.QUALIFICATION_SHA256
    if (not isinstance(digest, str) or len(digest) != 64 or
            any(value not in '0123456789abcdef' for value in digest)):
        raise ValueError('Item sprite deployment requires its visible acceptance fingerprint')
    if source.QUALIFICATION_RESOURCE_SHA256 != source.RESOURCE_SHA256:
        raise ValueError('Item sprite qualification belongs to a different resource contract')
    return candidate_profile()
