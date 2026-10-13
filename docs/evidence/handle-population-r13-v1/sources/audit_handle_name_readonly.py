"""Resolve one owned handle name; run this helper with a host timeout."""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import struct

import audit_handle_types_readonly as audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--identity', type=int, required=True)
    parser.add_argument('--handle', type=int, required=True)
    args = parser.parse_args()
    process = audit.OpenProcess(0x1040, False, args.pid)
    if not process:
        raise OSError(ctypes.get_last_error())
    duplicate = wt.HANDLE()
    try:
        times = [wt.FILETIME() for _ in range(4)]
        if not audit.GetProcessTimes(process, *(ctypes.byref(value) for value in times)):
            raise OSError(ctypes.get_last_error())
        identity = times[0].dwLowDateTime | (times[0].dwHighDateTime << 32)
        if identity != args.identity:
            raise RuntimeError('Owned creation identity differs')
        if not audit.DuplicateHandle(process, wt.HANDLE(args.handle), audit.GetCurrentProcess(),
                                      ctypes.byref(duplicate), 0, False, 2):
            raise OSError('DuplicateHandle:%d' % ctypes.get_last_error())
        basic = ctypes.create_string_buffer(56)
        basic_returned = wt.ULONG()
        basic_status = audit.NtQueryObject(duplicate, 0, basic, len(basic),
                                           ctypes.byref(basic_returned))
        object_counts = None
        if basic_status >= 0:
            attrs, access, handles, pointers = struct.unpack_from('<IIII', basic.raw, 0)
            object_counts = {'attributes': attrs, 'granted_access': access,
                             'handle_count_including_local_duplicate': handles,
                             'pointer_count': pointers}
        size = 65536
        buffer = ctypes.create_string_buffer(size)
        returned = wt.ULONG()
        status = audit.NtQueryObject(duplicate, 1, buffer, size, ctypes.byref(returned))
        name = None
        if status >= 0:
            length, maximum, pointer = struct.unpack_from('<HH4xQ', buffer.raw, 0)
            if pointer and 0 < length < size:
                name = ctypes.wstring_at(pointer, length // 2)
        print(json.dumps({'pid': args.pid, 'creation_identity': str(identity),
                          'handle': args.handle, 'name': name,
                          'status': '0x%08x' % (status & 0xffffffff),
                          'basic_status': '0x%08x' % (basic_status & 0xffffffff),
                          'object_basic': object_counts}))
    finally:
        if duplicate:
            audit.CloseHandle(duplicate)
        audit.CloseHandle(process)


if __name__ == '__main__':
    main()
