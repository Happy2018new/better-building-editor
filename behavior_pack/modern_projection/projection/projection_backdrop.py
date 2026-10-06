# -*- coding: utf-8 -*-
"""Opaque depth guard sharing the projection's native block geometry."""
from .biomes import shader_index


def create_projection_actors(bridge, origin, anchor):
    """Create both actors before their shared renderer warmup starts."""
    entity = bridge.system.CreateClientEntityByTypeStr(
        b'modern_projection:anchor', anchor, (0., 0.))
    if not entity:
        raise ValueError('Could not create projection actor')
    try:
        backdrop = ProjectionBackdrop(bridge, origin, anchor)
    except (ValueError, TypeError, RuntimeError):
        bridge.system.DestroyClientEntity(entity)
        raise
    return entity, backdrop


class ProjectionBackdrop(object):
    def __init__(self, bridge, origin, anchor):
        self.bridge, self.origin, self.anchor = bridge, origin, anchor
        self.entity = bridge.system.CreateClientEntityByTypeStr(
            b'modern_projection:anchor', anchor, (0., 0.))
        if not self.entity:
            raise ValueError('Could not create projection backdrop')
        self.render = self.position = None
        self.names, self.visible = (), {}

    def offset(self, anchor):
        origin = self.origin
        return (anchor[0]-origin[0]-.5, origin[1]-anchor[1], anchor[2]-origin[2]-.5)

    def tint(self, biome):
        if not self.render.SetEntityExtraUniforms(4, (19488., float(shader_index(biome)), 0., 0.)):
            raise ValueError('Could not update projection backdrop shader')

    def bind(self, names, active, biome):
        b = self.bridge
        b.factory.CreateModel(self.entity).SetEntityShadowShow(False)
        self.render = b.factory.CreateActorRender(self.entity)
        self.position = b.factory.CreatePos(self.entity)
        self.tint(biome)
        self.names = tuple(names)
        offset = self.offset(self.anchor)
        for name in self.names:
            if (not self.render.AddActorBlockGeometry(name, offset, (0., 180., 0.)) or
                    not self.render.EnableActorBlockGeometryTransparent(name, False)):
                raise ValueError('Could not attach projection backdrop')
        self.select(active)

    def select(self, active):
        if self.bridge.session.opacity <= 0.:
            active = None
        previous = dict(self.visible)
        try:
            for name in self.names:
                visible = name == active
                if self.visible.get(name) == visible:
                    continue
                if not self.render.SetActorBlockGeometryVisible(name, visible):
                    raise ValueError('Could not switch projection backdrop buffer')
                self.visible[name] = visible
        except (ValueError, TypeError, RuntimeError):
            # Restore before allowing the transparent selector to commit.
            self.restore_visibility(previous)
            raise

    def restore_visibility(self, previous):
        # A rollback must restore the actual committed visibility, including
        # its old opacity, rather than derive it from the current session.
        for name, value in previous.items():
            if self.visible.get(name) != value:
                if not self.render.SetActorBlockGeometryVisible(name, value):
                    raise RuntimeError('Could not restore projection backdrop visibility')
                self.visible[name] = value
        self.visible = dict(previous)

    def follow(self, anchor):
        if anchor == self.anchor:
            return True
        offset = self.offset(anchor)
        if not self.position.SetPosForClientEntity(anchor):
            return False
        changed = []
        for name in self.names:
            if not self.render.SetActorBlockGeometryOffset(name, offset):
                # The bridge retains its last committed anchor on failure.
                # Restore the native transform too: returning to that anchor
                # on the next frame can legitimately skip another follow call.
                self.restore_transform(changed)
                return False
            changed.append(name)
        self.anchor = anchor
        return True

    def restore_transform(self, changed):
        offset = self.offset(self.anchor)
        restored = self.position.SetPosForClientEntity(self.anchor)
        for name in changed:
            if not self.render.SetActorBlockGeometryOffset(name, offset):
                restored = False
        if not restored:
            raise RuntimeError('Could not restore projection backdrop transform')

    def clear(self):
        if self.entity is not None:
            self.bridge.system.DestroyClientEntity(self.entity)
        self.entity = None
        self.render = self.position = None
