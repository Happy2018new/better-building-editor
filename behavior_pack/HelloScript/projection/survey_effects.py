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

    def _spawn(self, kind, centre, size):
        b = self.bridge
        entity = b.system.CreateClientEntityByTypeStr(
            ('modern_projection:survey_' + kind).encode('ascii'),centre,(0.,0.))
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
        self._move(record,self.anchor or centre)

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
        for kind in ('veil','wire','stars'):
            record = self._spawn(kind,centre,size)
            if record is not None:
                self.layers.append(record)

    def strike(self, pos):
        while len(self.bursts) >= 3:
            self.bridge.system.DestroyClientEntity(self.bursts.pop(0)[0][0])
        centre = tuple(float(v)+.5 for v in pos)
        record = self._spawn('strike',centre,(1,1,1))
        if record is not None:
            self.bridge.factory.CreateActorRender(record[0]).SetEntityExtraUniforms(3,(0.,0.,0.,0.))
            self.bursts.append((record,time.time()))

    def active(self):
        return bool(self.layers or self.bursts)

    def follow(self, anchor):
        self.anchor = anchor
        for record in self.layers:
            self._move(record,anchor)
        now = time.time()
        remaining = []
        for record,started in self.bursts:
            age = (now-started)/1.8
            if age >= 1.:
                self.bridge.system.DestroyClientEntity(record[0])
            else:
                self._move(record,anchor)
                self.bridge.factory.CreateActorRender(record[0]).SetEntityExtraUniforms(3,(age,0.,0.,0.))
                remaining.append((record,started))
        self.bursts = remaining

    def clear_box(self):
        for record in self.layers:
            self.bridge.system.DestroyClientEntity(record[0])
        self.layers = []
        self.bounds = None

    def clear(self):
        self.clear_box()
        for record,unused in self.bursts:
            self.bridge.system.DestroyClientEntity(record[0])
        self.bursts = []
        self.anchor = None
