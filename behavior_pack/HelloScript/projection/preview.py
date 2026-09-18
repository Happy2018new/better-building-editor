"""Two persistent native surfaces prevent blank frames during model replacement."""


class PreviewBuffer(object):
    # The SDK returns submission success, not GPU readiness. Keep the previous
    # surface through at least three render opportunities and 75 ms. Both
    # surfaces are transparent, so warming the new renderer cannot cover it.
    SETTLE_SECONDS = .075

    def __init__(self):
        self.front = 0
        self.names = [None, None]
        self.poses = [None, None]
        self.pending = None
        self.started = 0.
        self.frames = 0
        self.initialized = False

    def update(self, name, pose, now, draw, show):
        if not self.initialized:
            show(0, False, True)
            show(1, False, False)
            self.initialized = True
        if not name:
            if any(self.names):
                show(self.front, False, True)
                show(1 - self.front, False, False)
            self.names = [None, None]
            self.pending = None
            return
        if self.names[self.front] == name:
            if self.pending is not None:
                show(1 - self.front, False, False)
                self.pending = None
        elif self.pending != name:
            back = 1 - self.front
            self.pending = None
            show(back, True, False)
            if draw(back, name, pose) is not False:
                self.names[back], self.poses[back] = name, pose
                self.pending, self.started, self.frames = name, now, 0
            else:
                show(back, False, False)
        # Orbit the retained image as well during a replacement.
        for slot in (self.front, 1 - self.front):
            if self.names[slot] is None or (slot != self.front and self.pending is None):
                continue
            if pose != self.poses[slot] and draw(slot, self.names[slot], pose) is not False:
                self.poses[slot] = pose
        if self.pending is not None:
            self.frames += 1
            if self.frames >= 3 and now - self.started >= self.SETTLE_SECONDS:
                previous = self.front
                self.front = 1 - previous
                show(self.front, True, True)
                show(previous, False, False)
                self.pending = None

    def ready(self, name):
        return self.pending is None and self.names[self.front] == name
