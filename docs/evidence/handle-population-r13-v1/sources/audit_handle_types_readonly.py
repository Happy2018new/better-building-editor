"""Read-only Windows handle-type census for one owned process.

The system handle table is sampled without touching the target process state.
One handle per object-type index is duplicated only to resolve its type name;
the duplicate is closed immediately. The output is raw diagnostic evidence,
not a leak diagnosis.
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import struct
import time
from collections import Counter, defaultdict
from pathlib import Path


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll")

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
OpenProcess.restype = wt.HANDLE
CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wt.HANDLE]
CloseHandle.restype = wt.BOOL
GetProcessHandleCount = kernel32.GetProcessHandleCount
GetProcessHandleCount.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
GetProcessHandleCount.restype = wt.BOOL
DuplicateHandle = kernel32.DuplicateHandle
DuplicateHandle.argtypes = [wt.HANDLE, wt.HANDLE, wt.HANDLE,
                            ctypes.POINTER(wt.HANDLE), wt.DWORD, wt.BOOL, wt.DWORD]
DuplicateHandle.restype = wt.BOOL
GetCurrentProcess = kernel32.GetCurrentProcess
GetCurrentProcess.restype = wt.HANDLE
GetProcessTimes = kernel32.GetProcessTimes
GetProcessTimes.argtypes = [wt.HANDLE] + [ctypes.POINTER(wt.FILETIME)] * 4
GetProcessTimes.restype = wt.BOOL
GetExitCodeProcess = kernel32.GetExitCodeProcess
GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
GetExitCodeProcess.restype = wt.BOOL

NtQuerySystemInformation = ntdll.NtQuerySystemInformation
NtQuerySystemInformation.argtypes = [wt.ULONG, ctypes.c_void_p, wt.ULONG,
                                      ctypes.POINTER(wt.ULONG)]
NtQuerySystemInformation.restype = wt.LONG
NtQueryObject = ntdll.NtQueryObject
NtQueryObject.argtypes = [wt.HANDLE, wt.ULONG, ctypes.c_void_p, wt.ULONG,
                           ctypes.POINTER(wt.ULONG)]
NtQueryObject.restype = wt.LONG

SYSTEM_EXTENDED_HANDLE_INFORMATION = 64
OBJECT_TYPE_INFORMATION = 2
STATUS_INFO_LENGTH_MISMATCH = -1073741820  # 0xC0000004 as signed LONG
PROCESS_DUP_HANDLE = 0x40
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
DUPLICATE_SAME_ACCESS = 0x2


def _nt_success(status):
    return status >= 0


def query_system_handles():
    size = 4 * 1024 * 1024
    for _ in range(8):
        buffer = ctypes.create_string_buffer(size)
        returned = wt.ULONG()
        status = NtQuerySystemInformation(SYSTEM_EXTENDED_HANDLE_INFORMATION,
                                           buffer, size, ctypes.byref(returned))
        if _nt_success(status):
            raw = buffer.raw
            pointer_size = ctypes.sizeof(ctypes.c_void_p)
            # On this Windows x64 host the table starts with a 16-byte header and a
            # 40-byte entry. Refuse a different ABI instead of mis-decoding.
            if pointer_size != 8:
                raise RuntimeError("This decoder requires Windows x64")
            count = struct.unpack_from("<Q", raw, 0)[0]
            offset = 16
            entry_size = 40
            if offset + count * entry_size > size:
                size = max(size * 2, offset + count * entry_size + 4096)
                continue
            return count, raw, offset, entry_size
        if ctypes.c_ulong(status & 0xffffffff).value == 0xC0000004:
            size = max(size * 2, int(returned.value) + 4096)
            continue
        raise OSError("NtQuerySystemInformation failed: 0x%08x" %
                      ctypes.c_ulong(status & 0xffffffff).value)
    raise RuntimeError("System handle table did not fit after retries")


def decode_entries(count, raw, offset, entry_size, pid):
    selected = []
    wanted = int(pid)
    for index in range(count):
        pos = offset + index * entry_size
        object_ptr, owner, handle_value, granted, creator, type_index, attrs, reserved = \
            struct.unpack_from("<QQQIHHII", raw, pos)
        if owner == wanted:
            selected.append({"handle": handle_value, "type_index": type_index,
                             "granted_access": granted, "attributes": attrs,
                             "object": object_ptr})
    return selected


def object_type_name(process, handle_value):
    duplicate = wt.HANDLE()
    if not DuplicateHandle(process, wt.HANDLE(handle_value), GetCurrentProcess(),
                            ctypes.byref(duplicate), 0, False, DUPLICATE_SAME_ACCESS):
        return None, "DuplicateHandle:%d" % ctypes.get_last_error()
    try:
        size = 4096
        for _ in range(4):
            buffer = ctypes.create_string_buffer(size)
            returned = wt.ULONG()
            status = NtQueryObject(duplicate, OBJECT_TYPE_INFORMATION,
                                   buffer, size, ctypes.byref(returned))
            if _nt_success(status):
                length, maximum, pointer = struct.unpack_from("<HH4xQ", buffer.raw, 0)
                if not pointer or length == 0 or length > 4096:
                    return None, "empty-type-name"
                try:
                    value = ctypes.wstring_at(pointer, length // 2)
                except (ValueError, OSError):
                    return None, "wstring_at-failed"
                return value, None
            if ctypes.c_ulong(status & 0xffffffff).value == 0xC0000004:
                size = max(size * 2, int(returned.value) + 4096)
                continue
            return None, "NtQueryObject:0x%08x" % ctypes.c_ulong(status & 0xffffffff).value
        return None, "type-buffer-too-small"
    finally:
        CloseHandle(duplicate)


def census(pid, expected_identity):
    started = time.time()
    access = PROCESS_DUP_HANDLE | PROCESS_QUERY_LIMITED_INFORMATION
    process = OpenProcess(access, False, int(pid))
    if not process:
        raise OSError("OpenProcess failed: %d" % ctypes.get_last_error())
    try:
        times = [wt.FILETIME() for _ in range(4)]
        code = wt.DWORD()
        if not GetProcessTimes(process, *(ctypes.byref(value) for value in times)):
            raise OSError("GetProcessTimes failed: %d" % ctypes.get_last_error())
        identity = times[0].dwLowDateTime | (times[0].dwHighDateTime << 32)
        if identity != int(expected_identity):
            raise RuntimeError("Owned process creation identity differs")
        if not GetExitCodeProcess(process, ctypes.byref(code)) or code.value != 259:
            raise RuntimeError("Owned process is no longer running")
        count, raw, offset, entry_size = query_system_handles()
        entries = decode_entries(count, raw, offset, entry_size, pid)
        by_index = Counter(row["type_index"] for row in entries)
        samples = {}
        for row in entries:
            samples.setdefault(row["type_index"], row)
        names, name_errors = {}, {}
        for type_index, row in sorted(samples.items()):
            name, error = object_type_name(process, row["handle"])
            names[str(type_index)] = name
            if error:
                name_errors[str(type_index)] = error
        by_name = Counter()
        granted = defaultdict(Counter)
        objects = defaultdict(Counter)
        object_pointer_zero_counts = Counter()
        representatives = defaultdict(list)
        for row in entries:
            name = names.get(str(row["type_index"])) or "index:%d" % row["type_index"]
            by_name[name] += 1
            granted[name]["0x%08x" % row["granted_access"]] += 1
            if row["object"]:
                objects[name][row["object"]] += 1
            else:
                object_pointer_zero_counts[name] += 1
            if len(representatives[name]) < 3:
                representatives[name].append({key: row[key] for key in
                                              ("handle", "type_index", "granted_access", "attributes")})
        handle_count = wt.DWORD()
        count_ok = bool(GetProcessHandleCount(process, ctypes.byref(handle_count)))
        return {
            "schema": 1,
            "completed": True,
            "scope": "read-only system handle-table census; no game mutation, injection or fixture",
            "pid": int(pid),
            "creation_identity": str(identity),
            "process_handle_count": int(handle_count.value) if count_ok else None,
            "process_handle_count_query_ok": count_ok,
            "system_handle_count": int(count),
            "selected_table_entries": len(entries),
            "type_counts": dict(sorted(by_name.items(), key=lambda pair: (-pair[1], pair[0]))),
            "type_indices": {str(key): int(value) for key, value in sorted(by_index.items())},
            "type_names_by_index": names,
            "type_name_errors": name_errors,
            "granted_access_counts": {name: dict(sorted(values.items()))
                                      for name, values in sorted(granted.items())},
            "object_multiplicities": {
                name: {"distinct_objects": len(values),
                       "maximum_handles_per_object": max(values.values()),
                       "handles_per_object_histogram": dict(sorted(Counter(values.values()).items()))}
                for name, values in sorted(objects.items())},
            "object_pointer_zero_counts": dict(sorted(object_pointer_zero_counts.items())),
            "representative_handles": dict(representatives),
            "elapsed_seconds": round(time.time() - started, 3),
            "method": {
                "system_information_class": SYSTEM_EXTENDED_HANDLE_INFORMATION,
                "one_duplicate_per_type_index": True,
                "duplicates_closed_immediately": True,
                "source_process_access": "PROCESS_DUP_HANDLE|PROCESS_QUERY_LIMITED_INFORMATION",
            },
        }
    finally:
        CloseHandle(process)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--identity", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("--output must be a fresh path")
    report = census(args.pid, args.identity)
    report["captured_at_unix"] = time.time()
    report["host_pid"] = os.getpid()
    payload = json.dumps(report, ensure_ascii=True, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="ascii", newline="\n")
    report["output_sha256"] = hashlib.sha256(payload.encode("ascii")).hexdigest()
    print(json.dumps({key: report[key] for key in
                      ("pid", "process_handle_count", "system_handle_count",
                       "selected_table_entries", "type_counts", "elapsed_seconds")}))


if __name__ == "__main__":
    main()
