"""Compact little-endian integer buffers using whitelisted struct and builtins."""
import struct
try:
    INTEGER_TYPES = (int, long)
except NameError:
    INTEGER_TYPES = (int,)


class IntegerBuffer(object):
    """Only the unsigned-short/signed-int operations used by chunks and journals.

    Byte order is explicit, so existing little-endian archives keep their wire
    format without consulting interpreter internals or a native array module.
    """
    __slots__ = ('typecode', 'itemsize', '_item', '_data')

    def __init__(self, typecode, values=()):
        if typecode not in ('H', 'i'):
            raise ValueError('Unsupported integer buffer type')
        self.typecode = typecode
        self._item = struct.Struct('<' + typecode)
        self.itemsize = self._item.size
        self._data = bytearray()
        self.extend(values)

    def __len__(self):
        return len(self._data) // self.itemsize

    def __iter__(self):
        # Chunk size is bounded to 4096 cells; unpack in C rather than calling
        # a Python generator once for each value during Counter/serialization.
        return iter(struct.unpack('<%d%s' % (len(self), self.typecode), self._data))

    def _index(self, index):
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        return index * self.itemsize

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self))
            out = IntegerBuffer(self.typecode)
            if step == 1:
                out._data = self._data[start*self.itemsize:stop*self.itemsize]
            else:
                out.extend(list(self)[index])
            return out
        return self._item.unpack_from(self._data, self._index(index))[0]

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self))
            values = IntegerBuffer(self.typecode, value)
            if step == 1:
                self._data[start*self.itemsize:max(start,stop)*self.itemsize] = values._data
            else:
                targets = list(range(start, stop, step))
                if len(targets) != len(values):
                    raise ValueError('Extended slice size mismatch')
                for target, item in zip(targets, values):
                    self[target] = item
            return
        offset = self._index(index)
        low, high = (0, 65535) if self.typecode == 'H' else (-2147483648, 2147483647)
        # Some struct implementations clear the destination before rejecting
        # an invalid value. Validate first to keep failed edits atomic.
        if not isinstance(value, INTEGER_TYPES) or not low <= value <= high:
            raise struct.error('Integer buffer value out of range')
        self._item.pack_into(self._data, offset, value)

    def __mul__(self, count):
        out = IntegerBuffer(self.typecode)
        out._data = self._data * count
        return out

    __rmul__ = __mul__

    def __eq__(self, other):
        if not isinstance(other, IntegerBuffer):
            return NotImplemented
        if self.typecode == other.typecode:
            return self._data == other._data
        return list(self) == list(other)

    def __ne__(self, other):
        return not self == other

    def extend(self, values):
        if isinstance(values, IntegerBuffer) and self.typecode == values.typecode:
            self._data.extend(values._data)
        else:
            items = tuple(values)
            self._data.extend(struct.pack('<%d%s' % (len(items), self.typecode), *items))

    def tobytes(self):
        return bytes(self._data)

    def frombytes(self, value):
        if len(value) % self.itemsize:
            raise ValueError('Misaligned integer buffer')
        self._data.extend(value)
