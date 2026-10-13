"""One read-only Windows x64 process resource snapshot; no liveness classification.

Layout: Microsoft SYSTEM_PROCESS_INFORMATION documentation and phnt ntexapi.h.
https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntquerysysteminformation
https://raw.githubusercontent.com/winsiderss/phnt/master/ntexapi.h
CreateTime, CycleTime, and WorkingSetPrivateSize are phnt's named reserved fields.
"""
import ctypes
from ctypes import wintypes
import os
import time


class _UnicodeString(ctypes.Structure):
    _fields_ = [('Length', wintypes.USHORT), ('MaximumLength', wintypes.USHORT),
                ('Buffer', ctypes.c_void_p)]


class _SystemProcessInformation(ctypes.Structure):
    _fields_ = [
        ('NextEntryOffset', wintypes.ULONG), ('NumberOfThreads', wintypes.ULONG),
        ('WorkingSetPrivateSize', ctypes.c_ulonglong), ('HardFaultCount', wintypes.ULONG),
        ('NumberOfThreadsHighWatermark', wintypes.ULONG), ('CycleTime', ctypes.c_ulonglong),
        ('CreateTime', ctypes.c_longlong), ('UserTime', ctypes.c_longlong),
        ('KernelTime', ctypes.c_longlong), ('ImageName', _UnicodeString),
        ('BasePriority', wintypes.LONG), ('UniqueProcessId', ctypes.c_void_p),
        ('InheritedFromUniqueProcessId', ctypes.c_void_p), ('HandleCount', wintypes.ULONG),
        ('SessionId', wintypes.ULONG), ('UniqueProcessKey', ctypes.c_size_t),
        ('PeakVirtualSize', ctypes.c_size_t), ('VirtualSize', ctypes.c_size_t),
        ('PageFaultCount', wintypes.ULONG), ('PeakWorkingSetSize', ctypes.c_size_t),
        ('WorkingSetSize', ctypes.c_size_t), ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPagedPoolUsage', ctypes.c_size_t), ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
        ('QuotaNonPagedPoolUsage', ctypes.c_size_t), ('PagefileUsage', ctypes.c_size_t),
        ('PeakPagefileUsage', ctypes.c_size_t), ('PrivatePageCount', ctypes.c_size_t),
        ('IO', ctypes.c_longlong * 6),
    ]


def _check_layout():
    if os.name != 'nt' or ctypes.sizeof(ctypes.c_void_p) != 8:
        raise RuntimeError('This snapshot requires Windows x64')
    expected = {'CreateTime': 32, 'ImageName': 56, 'UniqueProcessId': 80,
                'HandleCount': 96, 'VirtualSize': 120, 'WorkingSetSize': 144,
                'PrivatePageCount': 200}
    if ctypes.sizeof(_SystemProcessInformation) != 256 or any(
            getattr(_SystemProcessInformation, key).offset != offset
            for key, offset in expected.items()):
        raise RuntimeError('SYSTEM_PROCESS_INFORMATION layout mismatch')
    return expected


def snapshot_processes(image_name='Minecraft.Windows.exe', target_pids=()):
    """Return one raw snapshot for exact image name or explicitly requested PIDs.

    No target process handles are opened. No exit state is inferred. The caller
    owns freshness, two-sample comparisons, and any resource capacity decision.
    Raw memory fields retain their names rather than silently changing units.
    """
    offsets = _check_layout()
    wanted = set(target_pids)
    if any(not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 for pid in wanted):
        raise ValueError('target_pids must contain positive integer PIDs')
    if image_name is not None and not isinstance(image_name, str):
        raise ValueError('image_name must be text or None')
    query = ctypes.WinDLL('ntdll').NtQuerySystemInformation
    query.argtypes = [wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG,
                      ctypes.POINTER(wintypes.ULONG)]
    query.restype = wintypes.LONG
    capacity, required = 1048576, wintypes.ULONG()
    for _ in range(6):
        if capacity > 67108864:
            raise RuntimeError('Process snapshot exceeded 64 MiB buffer limit')
        buffer = ctypes.create_string_buffer(capacity)
        status = query(5, buffer, capacity, ctypes.byref(required))
        if status == 0:
            break
        if status & 0xffffffff != 0xc0000004:
            raise OSError('NtQuerySystemInformation status %s' % hex(status & 0xffffffff))
        capacity = max(capacity * 2, required.value + 65536)
    else:
        raise RuntimeError('No complete system process snapshot after six attempts')
    if not 0 < required.value <= capacity:
        raise RuntimeError('Invalid complete system process snapshot length')
    address = ctypes.addressof(buffer)
    offset, count, rows, self_entry = 0, 0, [], None
    prefix_size = ctypes.sizeof(_SystemProcessInformation)
    while True:
        if offset + prefix_size > required.value:
            raise RuntimeError('Process record exceeds returned snapshot')
        record = _SystemProcessInformation.from_buffer(buffer, offset)
        name = record.ImageName
        if name.Length % 2 or name.Length > name.MaximumLength:
            raise RuntimeError('Invalid process image name length')
        if name.Length:
            if not name.Buffer or not address <= name.Buffer < address + required.value:
                raise RuntimeError('Process image name pointer outside returned snapshot')
            if name.Buffer + name.Length > address + required.value:
                raise RuntimeError('Process image name exceeds returned snapshot')
            text = ctypes.wstring_at(name.Buffer, name.Length // 2)
        else:
            text = ''
        pid = record.UniqueProcessId or 0
        row = {'pid': pid, 'create_time_100ns': str(record.CreateTime),
               'threads': record.NumberOfThreads, 'handles': record.HandleCount, 'name': text,
               'working_set_size_raw': record.WorkingSetSize,
               'private_page_count_raw': record.PrivatePageCount,
               'virtual_size_bytes': record.VirtualSize,
               'working_set_private_size_bytes': record.WorkingSetPrivateSize,
               'pagefile_usage_bytes': record.PagefileUsage,
               'threads_high_watermark': record.NumberOfThreadsHighWatermark,
               'cycle_time': str(record.CycleTime), 'user_time_100ns': str(record.UserTime),
               'kernel_time_100ns': str(record.KernelTime)}
        count += 1
        if pid == os.getpid():
            self_entry = row
        if pid in wanted or image_name is not None and text.lower() == image_name.lower():
            rows.append(row)
        if not record.NextEntryOffset:
            break
        if record.NextEntryOffset < prefix_size:
            raise RuntimeError('Process record offset is smaller than prefix')
        offset += record.NextEntryOffset
    if not self_entry or not self_entry['threads'] or not self_entry['create_time_100ns']:
        raise RuntimeError('Current host process snapshot sanity check failed')
    return {'captured_at_unix': time.time(), 'captured_monotonic': time.monotonic(),
            'nt_information_class': 5, 'ntstatus': status, 'returned_bytes': required.value,
            'total_entries': count, 'layout_size_bytes': prefix_size, 'layout_offsets': offsets,
            'parser_self_sanity': self_entry, 'rows': rows}
