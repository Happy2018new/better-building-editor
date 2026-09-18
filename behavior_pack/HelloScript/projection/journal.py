"""Compressed random-access world journal with a fixed-size working buffer."""
import zlib
from array import array


class Journal(object):
    ROWS = 1024

    def __init__(self, rows=()):
        self.blocks = []
        self.tail = array('i')
        self.count = 0
        self.palette = []
        self.ids = {}
        self.cached = (-1, None)
        for row in rows:
            self.append(row)

    def __len__(self):
        return self.count

    def _id(self, value):
        if value not in self.ids:
            self.ids[value] = len(self.palette)
            self.palette.append(value)
        return self.ids[value]

    def append(self, row):
        pos, before, after = row
        self.tail.extend(list(pos) + [self._id(before), self._id(after)])
        self.count += 1
        if len(self.tail) == self.ROWS * 5:
            raw = self.tail.tobytes() if hasattr(self.tail, 'tobytes') else self.tail.tostring()
            self.blocks.append(zlib.compress(raw, 1))
            self.tail = array('i')

    def __getitem__(self, index):
        if index < 0:
            index += self.count
        if not 0 <= index < self.count:
            raise IndexError(index)
        chunk, offset = divmod(index, self.ROWS)
        if chunk == len(self.blocks):
            values = self.tail
        elif self.cached[0] == chunk:
            values = self.cached[1]
        else:
            values = array('i')
            raw = zlib.decompress(self.blocks[chunk])
            if hasattr(values, 'frombytes'):
                values.frombytes(raw)
            else:
                values.fromstring(raw)
            self.cached = (chunk, values)
        start = offset * 5
        return (tuple(values[start:start + 3]), self.palette[values[start + 3]], self.palette[values[start + 4]])

    def __iter__(self):
        index = 0
        while index < self.count:
            yield self[index]
            index += 1

    def __eq__(self, other):
        return len(self) == len(other) and all(a == b for a, b in zip(self, other))

    def memory_bytes(self):
        return sum(len(data) for data in self.blocks) + len(self.tail) * 4 + self.ROWS * 20
