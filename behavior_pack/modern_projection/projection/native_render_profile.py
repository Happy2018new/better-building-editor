"""Explicit native routes backed by the 3.10 round-15 palette observations.

Enabling a name requires choosing its measured coordinate route. This module
does not enable a renderer from the runtime version alone. Empty shulker
actors, absent head meshes and stale banner patterns remain outside this set.
"""
from collections import namedtuple
import math
from .cell import integer_types, text_type
from .nbt_spatial import root_payload, scalar
from .visible_actor import render_actor

SCHEMA_VERSION = 2
RUNTIME_VERSION = '3.10.0.420447'
OBSERVED_NAMES = frozenset(('minecraft:chest', 'minecraft:copper_chest',
                            'minecraft:ender_chest', 'minecraft:bed',
                            'minecraft:flower_pot', 'minecraft:standing_banner',
                            'minecraft:wall_banner'))
CHEST_BOOLEANS = ('chestMainSubChest', 'chestIsGlobalChest', 'chestIsLargeChest')
CHEST_NUMBERS = ('chestModelOffset', 'chestOpenness', 'chestOldOpenness')
_Profile = namedtuple('_Profile', 'model_local context scene_names')


def _integer(value, lower, upper):
    return (isinstance(value, integer_types) and type(value) is not bool and
            lower <= value <= upper)


def _number(value):
    return (isinstance(value, integer_types + (float,)) and type(value) is not bool
            and (not isinstance(value, float) or not math.isnan(value) and not math.isinf(value)))


def _banner_payload(name, root):
    standing = name == 'minecraft:standing_banner'
    if scalar(root, 'bannerIsStanding') is not standing:
        return False
    if not _integer(scalar(root, 'bannerDirection'), 0 if standing else 2, 15 if standing else 5):
        return False
    # Only the actual item-placed two-pattern record has a color observation.
    # Typed NBT writes produced a stale zero-pattern client payload in 3.10.
    if not _integer(scalar(root, 'bannerPatternCount'), 2, 2):
        return False
    if not _integer(scalar(root, 'bannerType'), 0, 0):
        return False
    if not _integer(scalar(root, 'bannerBaseColor'), 0, 15):
        return False
    for index in range(2):
        if not _integer(scalar(root, 'bannerColor%d' % index), 0, 15):
            return False
        pattern = scalar(root, 'bannerPattern%d' % index)
        if not isinstance(pattern, (bytes, text_type)) or not pattern:
            return False
    return True


def _chest_payload(name, root):
    if any(type(scalar(root, key)) is not bool for key in CHEST_BOOLEANS):
        return False
    if any(not _number(scalar(root, key)) for key in CHEST_NUMBERS):
        return False
    if not _integer(scalar(root, 'facingDirection'), 2, 5):
        return False
    # Round 15 captures only single bodies; paired half visibility needs its
    # own observation before replacing the existing independent half proxies.
    if scalar(root, 'chestIsLargeChest') or not scalar(root, 'chestMainSubChest'):
        return False
    if scalar(root, 'chestIsGlobalChest') != (name == 'minecraft:ender_chest'):
        return False
    if name == 'minecraft:copper_chest':
        return (scalar(root, 'chestIsCopperChest') is True and
                _integer(scalar(root, 'chestCopperType'), 0, 0))
    return True


class NativeRenderProfile(_Profile):
    """Immutable per-session selection; replace it to change routing.

    ``model_local`` names bypass packed neighbor coordinates. ``context``
    names retain them. Both lists must be explicitly provided by the caller
    after observing that route on the target runtime. Production selection
    is a separate measured subset; candidates are not enabled implicitly.
    """
    __slots__ = ()

    def __new__(cls, model_local=(), context=(), scene_names=None):
        local, packed = frozenset(model_local), frozenset(context)
        if local & packed:
            raise ValueError('A native body must have exactly one coordinate route')
        if (local | packed) - OBSERVED_NAMES:
            raise ValueError('Native body has no usable round-15 observation')
        scene = local | packed if scene_names is None else frozenset(scene_names)
        if scene - (local | packed):
            raise ValueError('Scene body must have an explicit native coordinate route')
        return _Profile.__new__(cls, local, packed, scene)

    @property
    def identity(self):
        return (SCHEMA_VERSION, RUNTIME_VERSION, tuple(sorted(self.model_local)),
                tuple(sorted(self.context)), tuple(sorted(self.scene_names)))

    def coordinate_mode(self, material, actor):
        name = material[0]
        mode = ('model_local' if name in self.model_local else
                'context' if name in self.context else None)
        if mode is None:
            return None
        root = root_payload(render_actor(actor))
        if root is None:
            return None
        if name == 'minecraft:bed':
            valid = (_integer(scalar(root, 'color'), 0, 15) and
                     _integer(scalar(root, 'direction'), 0, 3))
        elif name == 'minecraft:flower_pot':
            valid = isinstance(scalar(root, 'flowerPotPlant'), (bytes, text_type))
        elif name in ('minecraft:standing_banner', 'minecraft:wall_banner'):
            valid = _banner_payload(name, root)
        else:
            valid = _chest_payload(name, root)
        return mode if valid else None


def coordinate_mode(profile, material, actor):
    return None if profile is None else profile.coordinate_mode(material, actor)


def profile_identity(profile):
    return None if profile is None else profile.identity


def for_preview(profile):
    """Limit editor meshes to names with independent shared-depth evidence."""
    if profile is None or profile.scene_names == profile.model_local | profile.context:
        return profile
    return NativeRenderProfile(profile.model_local & profile.scene_names,
                               profile.context & profile.scene_names, profile.scene_names)


def production_profile(runtime_version):
    """Select the round-15 qualified bodies; every cell still needs payload.

    Beds remain proxies: the captured single head actor does not establish
    independent head/foot geometry under partial occupancy. Empty shulker
    data and missing head meshes likewise do not establish a route. Native
    chest UI depth differs from terrain; editor previews keep their proxies.
    """
    if runtime_version != RUNTIME_VERSION:
        return None
    return NativeRenderProfile(model_local=(
        'minecraft:chest', 'minecraft:copper_chest', 'minecraft:ender_chest'),
        context=('minecraft:flower_pot',), scene_names=('minecraft:flower_pot',))
