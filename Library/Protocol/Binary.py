import math
import struct

class BinaryAPI:

    UINT8 = struct.Struct('<B')
    UINT16 = struct.Struct('<H')
    INT32 = struct.Struct('<i')
    INT64 = struct.Struct('<q')
    FLOAT64 = struct.Struct('<d')
    _primitives_ = {'B': UINT8, 'i': INT32, 'q': INT64, 'd': FLOAT64}

    __slots__ = ('_layout_', '_struct_', '_size_', '_has_nullable_')

    def __init__(self, *layout: str) -> None:
        self._layout_ = layout
        self._has_nullable_ = any(t == 'D' for t in layout)
        if any(t == 's' for t in layout):
            self._struct_ = None
            self._size_ = None
            return
        fmt = '<' + ''.join('d' if t == 'D' else t for t in layout)
        self._struct_ = struct.Struct(fmt)
        self._size_ = self._struct_.size

    def pack(self, *values) -> bytes:
        if len(values) != len(self._layout_):
            raise ValueError(f"Expected {len(self._layout_)} values, got {len(values)}")
        if self._struct_ is not None:
            if self._has_nullable_:
                return self._struct_.pack(*(
                    math.nan if t == 'D' and v is None else v
                    for t, v in zip(self._layout_, values)
                ))
            return self._struct_.pack(*values)
        parts: list[bytes] = []
        for t, v in zip(self._layout_, values):
            if t == 's':
                if v is None:
                    parts.append(self.UINT16.pack(0))
                else:
                    encoded = v.encode('utf-8')
                    parts.append(self.UINT16.pack(len(encoded)))
                    parts.append(encoded)
            elif t == 'D':
                parts.append(self.FLOAT64.pack(math.nan if v is None else v))
            else:
                parts.append(self._primitives_[t].pack(v))
        return b''.join(parts)

    def unpack(self, data: bytes, offset: int = 0) -> tuple:
        if self._struct_ is not None:
            raw = self._struct_.unpack_from(data, offset)
            if self._has_nullable_:
                return tuple(
                    None if t == 'D' and math.isnan(v) else v
                    for t, v in zip(self._layout_, raw)
                )
            return raw
        values: list = []
        off = offset
        for t in self._layout_:
            if t == 's':
                length = self.UINT16.unpack_from(data, off)[0]
                off += 2
                if length == 0:
                    values.append(None)
                else:
                    values.append(data[off:off + length].decode('utf-8'))
                    off += length
            elif t == 'D':
                v = self.FLOAT64.unpack_from(data, off)[0]
                values.append(None if math.isnan(v) else v)
                off += 8
            else:
                s = self._primitives_[t]
                values.append(s.unpack_from(data, off)[0])
                off += s.size
        return tuple(values)

__all__ = ["BinaryAPI"]