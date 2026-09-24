# -*- coding: utf-8 -*-
"""Private GPU wire effects and exactly two persistent survey point markers."""
from __future__ import unicode_literals
import time
from .outline_settings import defaults, normalize

GOLD_PRESET = defaults()['golden']
# Native Facing: down, up, north, south, west, east. Shader axes: -X,+X,-Y,+Y,-Z,+Z.
NATIVE_FACES = (2, 3, 4, 5, 0, 1)


class WireEffects(object):
    """Shared renderer; survey settings are fixed by its owner, never by UI."""
    def __init__(self, bridge):
        self.bridge = bridge
        self.layers = []
        self.points = [None, None]
        self.bounds = None
        self.anchor = None
        self.camera = None
        self.started = 0.
        self.style = 'golden'
        self.options = defaults()['golden']
        self.reduced_motion = False

    def configure_style(self, style, options, reduced_motion=False):
        if style not in ('golden', 'starry'):
            raise ValueError('Unknown luminous outline style')
        options = normalize({style: options})[style]
        if (style, options, reduced_motion) == (self.style, self.options, self.reduced_motion):
            return
        self.style, self.options, self.reduced_motion = style, options, reduced_motion
        if self.active():
            self.follow(self.anchor, self.camera)

    def _records(self):
        return self.layers + [record for record in self.points if record is not None]

    def _spawn(self, kind, centre, size, face=4):
        entity = self.bridge.system.CreateClientEntityByTypeStr(
            ('modern_projection:survey_' + kind).encode('ascii'), centre, (0., 0.))
        if not entity:
            return None
        record = {'id': entity, 'centre': centre, 'size': tuple(float(v) for v in size),
                  'kind': kind, 'face': face, 'started': time.time(), 'anchor': None, 'uniforms': {}}
        self._configure(record)
        def ready():
            if any(record is item for item in self._records()):
                # Native renderer registration can lag behind entity creation.
                record['uniforms'].clear()
                self._configure(record)
        self.bridge.later(.15, ready)
        return record

    def _uniform(self, record, slot, value):
        if record['uniforms'].get(slot) == value:
            return True
        ok = self.bridge.factory.CreateActorRender(record['id']).SetEntityExtraUniforms(slot, value)
        if ok:
            record['uniforms'][slot] = value
        return ok

    def _configure(self, record):
        self.bridge.factory.CreateModel(record['id']).SetEntityShadowShow(False)
        self._update(record, time.time())
        self._move(record, self.anchor or record['centre'])

    def _update(self, record, now):
        point = record['kind'] == 'strike'
        options = GOLD_PRESET if point else self.options
        style = 0. if point or self.style == 'golden' else 1.
        flow = round(options['speed'] * .38 * 210.) / 210.
        if self.reduced_motion:
            flow = 0.
        self._uniform(record, 1, record['size'] + (flow,))
        duration = .55 if point else 1.2
        entered = min(1., max(0., (now-record['started']) / duration))
        self._uniform(record, 3, (entered, options['brightness'], style+options['width']*.1,
                                 0. if self.reduced_motion else options['orbit_speed']))
        camera = self.camera or self.anchor or record['centre']
        view = tuple(float(camera[i])-record['centre'][i] for i in range(3))
        density = options['density']
        if record['kind'] == 'guide' and isinstance(self, SurveyEffects):
            density = -density  # Only the survey guide draws the white volume.
        self._uniform(record, 4, view + (float(record['face']) if point else density,))

    def _move(self, record, anchor):
        if anchor is None:
            anchor = record['centre']
        anchor = tuple(anchor)
        if record['anchor'] == anchor:
            return True
        if not self.bridge.factory.CreatePos(record['id']).SetPosForClientEntity(anchor):
            return False
        offset = tuple(record['centre'][i]-anchor[i] for i in range(3)) + (1.,)
        if not self._uniform(record, 2, offset):
            return False
        record['anchor'] = anchor
        return True

    def replace(self, origin, size):
        bounds = (tuple(origin), tuple(size))
        if bounds == self.bounds and len(self.layers) == 3:
            return
        self.clear_box()
        self.bounds = bounds
        centre = tuple(float(origin[i])+size[i]*.5 for i in range(3))
        try:
            self.camera = tuple(self.bridge.factory.CreateCamera(self.bridge.level).GetPosition())
        except Exception:
            pass
        self.started = time.time()
        for kind in ('guide', 'wire', 'stars'):
            record = self._spawn(kind, centre, size)
            if record is not None:
                self.layers.append(record)

    def sync_points(self, positions, faces=None):
        for index in range(2):
            pos = positions[index]
            if index == 1 and pos is not None and pos == positions[0]:
                pos = None  # A one-block selection needs one visible marker.
            record = self.points[index]
            centre = tuple(float(v)+.5 for v in pos) if pos is not None else None
            native_face = faces[index] if faces is not None else None
            if index == 0 and positions[0] is not None and positions[1] == positions[0] and faces is not None:
                # Coincident endpoints share one marker at the most recently hit face.
                native_face = faces[1] if type(faces[1]) is int and 0 <= faces[1] < 6 else native_face
            face = NATIVE_FACES[native_face] if type(native_face) is int and 0 <= native_face < 6 else None
            if face is None and record is not None and record['centre'] == centre:
                face = record['face']  # Legacy callers must not move an already picked face.
            if face is None and centre is not None:
                camera = self.camera or self.anchor or tuple(centre[i]+2. for i in range(3))
                delta = tuple(camera[i]-centre[i] for i in range(3))
                axis = max(range(3), key=lambda i: abs(delta[i]))
                face = axis*2 + (1 if delta[axis] >= 0. else 0)
            if record is not None and record['centre'] == centre:
                if record['face'] != face:
                    record['face'] = face
                    self._update(record, time.time())
                continue
            if record is not None:
                self.bridge.system.DestroyClientEntity(record['id'])
            self.points[index] = None
            if centre is not None:
                self.points[index] = self._spawn('strike', centre, (1, 1, 1), face)

    def pulse_point(self, index):
        record = self.points[index]
        if record is None and index == 1:
            record = self.points[0]
        if record is not None:
            record['started'] = time.time()

    def active(self):
        return bool(self.layers or any(self.points))

    def follow(self, anchor, camera=None):
        if anchor is not None:
            self.anchor = tuple(anchor)
        if camera is not None:
            self.camera = tuple(camera)
        now = time.time()
        ok = True
        for record in self._records():
            ok = self._move(record, self.anchor) and ok
            self._update(record, now)
        return ok

    def clear_box(self):
        for record in self.layers:
            self.bridge.system.DestroyClientEntity(record['id'])
        self.layers = []
        self.bounds = None

    def clear(self):
        self.clear_box()
        for record in self.points:
            if record is not None:
                self.bridge.system.DestroyClientEntity(record['id'])
        self.points = [None, None]
        self.anchor = None
        self.camera = None


class SurveyEffects(WireEffects):
    """The survey wand always uses the approved gold preset, including points."""
    def configure_style(self, style, options, reduced_motion=False):
        raise ValueError('Survey appearance is fixed')
