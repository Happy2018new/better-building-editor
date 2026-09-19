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
        self.retry_at = 0.
        self.restore = False

    def invalidate(self):
        """Visibility/layout changes can discard the native render submission."""
        self.poses = [None, None]
        self.restore = True

    def update(self, name, pose, now, draw, show):
        if not self.initialized:
            show(0, False, True)
            show(1, False, False)
            self.initialized = True
        if self.restore:
            self.restore = False
            show(self.front, bool(self.names[self.front]), True)
            if self.pending is not None:
                # Restart the warm-up after a hidden/reshaped renderer returns.
                back = 1 - self.front
                show(back, True, False)
                if draw(back, self.pending, pose) is not False:
                    self.poses[back] = pose
                else:
                    show(back, False, False)
                    self.pending, self.names[back] = None, None
                    self.retry_at = now + .25
                self.started, self.frames = now, 0
        if self.pending is not None:
            # Do not replace a surface or resubmit its pose while a native model
            # upload is warming. Undo, filtering and a second edit may arrive
            # before that job finishes. Keep drawing the previous front instead.
            self.frames += 1
            if self.frames < 3 or now - self.started < self.SETTLE_SECONDS:
                if self.names[self.front] and pose != self.poses[self.front]:
                    if draw(self.front, self.names[self.front], pose) is not False:
                        self.poses[self.front] = pose
                return
            if self.pending == name:
                previous = self.front
                self.front = 1 - previous
                show(self.front, True, True)
                show(previous, False, False)
                # Promotion changes native depth/visibility. Re-submit the
                # settled model once even if the camera stayed completely still.
                self.poses[self.front] = None
            else:
                show(1 - self.front, False, False)
            self.pending = None
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
        elif now >= self.retry_at:
            back = 1 - self.front
            self.pending = None
            show(back, True, False)
            if draw(back, name, pose) is not False:
                self.names[back], self.poses[back] = name, pose
                self.pending, self.started, self.frames = name, now, 0
            else:
                show(back, False, False)
                self.retry_at = now + .25
        # Orbit the retained image as well during a replacement.
        for slot in (self.front,):
            if self.names[slot] is None or (slot != self.front and self.pending is None):
                continue
            if pose != self.poses[slot] and draw(slot, self.names[slot], pose) is not False:
                self.poses[slot] = pose
        if self.pending is not None:
            self.frames = 1

    def ready(self, name):
        return self.pending is None and self.names[self.front] == name
