"""Client-only, loaded-area palette scans with bounded result consumption."""
from .storage import indices, position


class OccupancyScan(object):
    def __init__(self, tracker):
        self.tracker = tracker
        self.block = tracker.bridge.factory.CreateBlock(tracker.bridge.level)
        self.cache = {}
        self.initial = None
        self.cursor = 0
        self.calls = self.sweeps = 0

    def fetch(self, key):
        t = self.tracker
        start = tuple(v*16 for v in key)
        size = tuple(min(16, t.size[i]-start[i]) for i in range(3))
        lo = tuple(t.origin[i]+start[i] for i in range(3))
        hi = tuple(lo[i]+size[i]-1 for i in range(3))
        # Both GetBlock and the bulk API can report air for unloaded chunks.
        # Only client load/unload events establish whether air is trustworthy.
        if any(not t.loaded((x, lo[1], z)) for x in (lo[0], hi[0]) for z in (lo[2], hi[2])):
            return None
        for x in set((lo[0], hi[0])):
            for y in set((lo[1], hi[1])):
                for z in set((lo[2], hi[2])):
                    actual = t.info.GetBlock((x, y, z))
                    t.reads += 1
                    if not actual or actual[0] in t.unknown_names:
                        return None
        palette = self.block.GetBlockPaletteBetweenPos(lo, hi, False)
        self.calls += 1
        if palette is None:
            return None
        data = palette.SerializeBlockPalette()
        if tuple(data.get('volume', ())) != (size[2], size[0], size[1]):
            return None
        volume = size[0]*size[1]*size[2]
        states = bytearray(volume)
        for value, cells in data['common'].items():
            state = 0 if value[0] in t.unknown_names else (1 if value[0] in t.air_names else 2)
            if len(cells) == volume:
                states[:] = bytearray([state])*volume
                break
            for cell in cells:
                states[cell] = state
        return states, size

    def begin(self, key):
        data = self.fetch(key)
        self.initial = (key, data) if data is not None else None
        if data is not None:
            self.cache[key] = data[0]

    def initial_state(self, pos):
        if self.initial is None:
            return 0
        key, (states, size) = self.initial
        if key != (pos[0] >> 4, pos[1] >> 4, pos[2] >> 4):
            return 0
        return states[((pos[1]&15)*size[0]+(pos[0]&15))*size[2]+(pos[2]&15)]

    def scan(self):
        t = self.tracker
        keys = tuple(sorted(t.targets.chunks))
        if not keys:
            return
        key = keys[self.cursor % len(keys)]
        self.cursor = (self.cursor+1) % len(keys)
        self.sweeps += int(self.cursor == 0)
        data = self.fetch(key)
        # Always return to the scheduler after the synchronous native call.
        yield True
        if data is None:
            self.cache.pop(key, None)
            return
        states, size = data
        old = self.cache.get(key)
        same = old == states
        self.cache[key] = states
        if same and 0 not in states:
            return
        for local in indices(t.targets.chunks[key]):
            # A direct interaction query may supersede this older bulk
            # snapshot between frames. Do not overwrite that newer reading.
            if self.cache.get(key) is not states:
                return
            pos = position(key, local)
            cell = ((pos[1]&15)*size[0]+(pos[0]&15))*size[2]+(pos[2]&15)
            state = states[cell]
            # Palettes omit bed feet and upper door halves; only missing
            # entries fall back to exact GetBlock, never treat them as air.
            if state == 0:
                t.read(pos)
            elif not same:
                t.observe(t.index(pos), state)
            yield True
