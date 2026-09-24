# -*- coding: utf-8 -*-
"""Private survey volume, GPU stardust and bounded short-lived comets."""
from __future__ import unicode_literals
import time


class SurveyEffects(object):
    def __init__(self, bridge):
        self.bridge = bridge
        self.layers = []
        self.bursts = []
        self.bounds = None
        self.anchor = None
        self.camera = None
        self.started = 0.
        self.flared = -10.
        self.corner = 7
        self.timing = None
        self.view = None

    def _spawn(self, kind, centre, size):
        b = self.bridge
        entity = b.system.CreateClientEntityByTypeStr(
            ('astral_survey:survey_' + kind).encode('ascii'),centre,(0.,0.))
        if not entity:
            return None
        record = [entity,centre,tuple(float(v) for v in size),None]
        self._configure(record)
        def ready():
            if record in self.layers or any(record is item[0] for item in self.bursts):
                self._configure(record)
        b.later(.15,ready)
        return record

    def _configure(self, record):
        b = self.bridge
        entity,centre,size,unused = record
        b.factory.CreateModel(entity).SetEntityShadowShow(False)
        b.factory.CreateActorRender(entity).SetEntityExtraUniforms(1,size+(1.,))
        if record in self.layers and self.timing is not None:
            b.factory.CreateActorRender(entity).SetEntityExtraUniforms(3,self.timing)
        b.factory.CreateActorRender(entity).SetEntityExtraUniforms(4,self._view(record))
        record[3] = None
        self._move(record,self.anchor or centre)

    def _view(self, record):
        camera = self.camera or self.anchor or record[1]
        return tuple(float(camera[i])-record[1][i] for i in range(3))+(float(self.corner),)

    def _move(self, record, anchor):
        if record[3] == anchor:
            return
        b = self.bridge
        if b.factory.CreatePos(record[0]).SetPosForClientEntity(anchor):
            offset = tuple(record[1][i]-anchor[i] for i in range(3))+(1.,)
            if b.factory.CreateActorRender(record[0]).SetEntityExtraUniforms(2,offset):
                record[3] = anchor

    def replace(self, origin, size):
        bounds = (tuple(origin),tuple(size))
        if bounds == self.bounds and len(self.layers) == 3:
            return
        self.clear_box()
        self.bounds = bounds
        centre = tuple(float(origin[i])+size[i]*.5 for i in range(3))
        try:
            self.camera = tuple(self.bridge.factory.CreateCamera(self.bridge.level).GetPosition())
        except Exception:
            pass
        camera = self.camera or self.anchor or centre
        # Choose once when a new box appears: orbiting the camera must not
        # teleport the dominant star between corners halfway through a beam.
        self.corner = sum((1 << i) for i in range(3) if camera[i] >= centre[i])
        self.started = time.time()
        self.timing = None
        self.view = None
        for kind in ('guide','wire','stars'):
            record = self._spawn(kind,centre,size)
            if record is not None:
                self.layers.append(record)

    def strike(self, pos):
        self.flared = time.time()
        while len(self.bursts) >= 3:
            self.bridge.system.DestroyClientEntity(self.bursts.pop(0)[0][0])
        centre = tuple(float(v)+.5 for v in pos)
        record = self._spawn('strike',centre,(1,1,1))
        if record is not None:
            self.bridge.factory.CreateActorRender(record[0]).SetEntityExtraUniforms(3,(0.,0.,0.,0.))
            self.bursts.append((record,time.time()))

    def active(self):
        return bool(self.layers or self.bursts)

    def follow(self, anchor, camera=None):
        self.anchor = anchor
        self.camera = camera or anchor
        now = time.time()
        timing = (min(1.,max(0.,(now-self.started)/1.2)),
                  min(1.,max(0.,(now-self.flared)/.55)),0.,0.)
        view_changed = self.view != self.camera
        for record in self.layers:
            self._move(record,anchor)
            if timing != self.timing or view_changed:
                render = self.bridge.factory.CreateActorRender(record[0])
                if timing != self.timing:
                    render.SetEntityExtraUniforms(3,timing)
                if view_changed:
                    render.SetEntityExtraUniforms(4,self._view(record))
        self.timing = timing
        self.view = self.camera
        remaining = []
        for record,started in self.bursts:
            age = (now-started)/1.8
            if age >= 1.:
                self.bridge.system.DestroyClientEntity(record[0])
            else:
                self._move(record,anchor)
                self.bridge.factory.CreateActorRender(record[0]).SetEntityExtraUniforms(3,(age,0.,0.,0.))
                if view_changed:
                    self.bridge.factory.CreateActorRender(record[0]).SetEntityExtraUniforms(4,self._view(record))
                remaining.append((record,started))
        self.bursts = remaining

    def clear_box(self):
        for record in self.layers:
            self.bridge.system.DestroyClientEntity(record[0])
        self.layers = []
        self.bounds = None
        self.timing = None
        self.view = None

    def clear(self):
        self.clear_box()
        for record,unused in self.bursts:
            self.bridge.system.DestroyClientEntity(record[0])
        self.bursts = []
        self.anchor = None
        self.camera = None
