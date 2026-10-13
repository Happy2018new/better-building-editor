"""Resolve at most three creation-bound handles with bounded helper timeouts."""
import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import audit_handle_types_readonly as audit


def collect(pid, identity, mask, timeout):
    started = time.time()
    process = audit.OpenProcess(0x1040, False, pid)
    if not process:
        raise OSError("OpenProcess:%d" % ctypes.get_last_error())
    try:
        times = [wt.FILETIME() for _ in range(4)]
        code = wt.DWORD()
        if not audit.GetProcessTimes(process, *(ctypes.byref(value) for value in times)):
            raise OSError("GetProcessTimes:%d" % ctypes.get_last_error())
        actual = times[0].dwLowDateTime | (times[0].dwHighDateTime << 32)
        if actual != identity:
            raise RuntimeError("Owned creation identity differs")
        if not audit.GetExitCodeProcess(process, ctypes.byref(code)) or code.value != 259:
            raise RuntimeError("Owned process is no longer running")
        count, raw, offset, entry_size = audit.query_system_handles()
        entries = audit.decode_entries(count, raw, offset, entry_size, pid)
        candidates = [row for row in entries if row["granted_access"] == mask]
        positions = sorted({0, len(candidates) // 2, len(candidates) - 1}) if candidates else []
        samples = []
        helper = Path(__file__).with_name("audit_handle_name_readonly.py")
        for position in positions:
            row = candidates[position]
            sample = {key: row[key] for key in ("handle", "type_index", "granted_access", "attributes")}
            sample["candidate_position"] = position
            try:
                result = subprocess.run(
                    [sys.executable, "-X", "utf8", str(helper), "--pid", str(pid),
                     "--identity", str(identity), "--handle", str(row["handle"])],
                    capture_output=True, text=True, timeout=timeout,
                )
                sample["returncode"] = result.returncode
                if result.returncode == 0:
                    sample["query"] = json.loads(result.stdout)
                else:
                    sample["error"] = result.stderr[-2000:]
            except subprocess.TimeoutExpired:
                # subprocess.run terminates only its local query helper.
                sample["error"] = "local helper timeout"
            samples.append(sample)
        return {"schema": 1, "pid": pid, "creation_identity": str(identity),
                "captured_at_unix": started, "completed_at_unix": time.time(),
                "selected_table_entries": len(entries), "candidate_access_mask": "0x%08x" % mask,
                "candidate_count": len(candidates), "samples": samples,
                "scope": "read-only names; at most three local duplicates; no target handle close or game action",
                "elapsed_seconds": round(time.time() - started, 3), "host_pid": os.getpid()}
    finally:
        audit.CloseHandle(process)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--identity", type=int, required=True)
    parser.add_argument("--mask", type=lambda value: int(value, 0), default=0x0016019f)
    parser.add_argument("--timeout", type=float, default=4.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("--output must be a fresh path")
    if not 0 < args.timeout <= 5:
        parser.error("--timeout must be in (0, 5]")
    report = collect(args.pid, args.identity, args.mask, args.timeout)
    payload = json.dumps(report, ensure_ascii=True, indent=2) + "\n"
    args.output.write_text(payload, encoding="ascii", newline="\n")
    print(json.dumps({"output_sha256": hashlib.sha256(payload.encode("ascii")).hexdigest(), **report}))


if __name__ == "__main__":
    main()
