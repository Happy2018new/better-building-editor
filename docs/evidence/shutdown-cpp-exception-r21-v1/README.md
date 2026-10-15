# Existing shutdown dump audit: portable evidence

Two real Microsoft DbgEng logs and independently retained C++ exception bytes
identify `std::bad_function_call` in the existing portal PID 2188 and shelf PID
25292 dumps. Both stacks reach `Minecraft_Windows+0x17e530b`, then the MSVC throw
path, exception handling, `terminate`, `abort` and `FAST_FAIL_FATAL_APP_EXIT=7`.

The engine function and underlying cause remain unknown. Invoking an empty
`std::function` is consistent with this exception type, but the particular object
or source expression is not established. Guard causality is unknown. This is
not evidence of stack corruption. No accepted unwind continues beyond the first
game return. System internal function labels are nearest exports, without PDBs.

## Evidence

- `logs/dbgeng-{2188,25292}-local.txt` are the complete real debugger outputs,
  copied byte-for-byte from the successful private audit. JSON receipts retain
  exact commands, tool/dump hashes, timestamps and every HRESULT.
- `logs/dbgeng-*-cpp-record.txt` are real `.exr` displays of the earlier captured
  C++ exception, in addition to the final fail-fast exception.
- `fragments/dump-*.json` contain programmatically extracted original dump bytes:
  headers, exception/context, selected raw module records/paths, C++ record and
  object, and captured return slots. Every slice has an original file offset,
  byte length, SHA-256 and hexadecimal bytes, bound to the full private dump SHA.
- `fragments/msvcp140-types.json` contains the exact necessary PE header and
  type-data slices extracted from the matching runtime, with full module hash
  and original offsets. The verifier decodes the original exception parameters,
  ThrowInfo, catchable-type array and type descriptors to recover
  `.?AVbad_function_call@std@@`; this is not a hand-transcribed type assertion.
- `process/portal` and `process/shelf` retain original event XML in its acquisition
  container, raw WER, selected session record and exact-exit receipt. The verifier
  reparses XML and matches PID plus creation FILETIME and WER report IDs.
- `analysis` preserves the original v2 analysis and external binary inventories.
  Legacy `copy` paths in that report describe private v2 copies, not package
  dependencies. No binary listed there is embedded here.
- `provenance.json` binds every copied file to its original audit manifest.
  `sources/pack_portable.py` performs byte extraction and copying. Its original
  private source audits are needed to rebuild acquisition, not to verify this
  portable package.

The full dumps, game/runtime/debugger DLLs, PDBs and the NuGet archive are external
and deliberately absent. Original dumps are bound by SHA-256 and private path;
they are not needed for the lightweight verification below.

## Microsoft Tool Basis

Actual DbgEng `10.0.26100.1` and DbgHelp `10.0.26100.9549` were used. Their exact
hashes, versions and valid Microsoft signer records are retained. Microsoft's
`Microsoft.Debugging.Platform.DbgEng` NuGet version `20260319.1511.0`, 21,999,785
bytes, SHA-256 `875678516f9ceed4a1c8b9b106d165106fcaa38723ad7c584c47b95b231600de`,
was inspected but contains no CDB executable and was not used as the debugger.

Download URLs, acquisition headers/time and hashes are in
`microsoft-sources.json`. The complete original Microsoft `DbgEng.h` is retained
in `inputs`; its SHA-256 is
`a9037bf9a096700082ec5d4d96a98d1d98dee6c8ed71b3eac8de64c1fd9a0f4f`.
The verifier derives `IDebugControl::Execute=66` and `WaitForEvent=93` directly
from this header, including all `STDMETHODV` declarations. The initial acquisition
receipt's incomplete parser map is retained as historical source only; the
corrected `interface-indices.json` is authoritative.

`sources/debug_existing_dump_v2.py` is the exact repaired script that generated
the accepted logs, archived unchanged. `replay_dbgeng.py` provides the portable
entry point with explicit external paths and hashes checked before DbgEng loads.

## Lightweight Verification

Requires Python 3.11+ only. It does not import ctypes, load DbgEng, require Windows,
connect to Minecraft or reexecute the debugger. It checks the complete package
inventory and recomputes process bindings, original exception/type decoding and
normalized raw trace content from the retained bytes:

```powershell
python -I -B -X utf8 <package>/verify.py
```

`--check-original-inputs` additionally checks the full private source hashes and
compares every retained byte slice against the original dump/runtime files.
It uses the private paths recorded at acquisition. Without those originals,
the package verifies its retained evidence and bindings; it cannot independently
recompute the SHA of an absent 99 MB dump or attest its original acquisition.

## Actual Debugger Reexecution

This separate operation requires Windows, both original matching dumps as
applicable, the matching Microsoft debugger DLLs and matching game/runtime images.
No such external binaries are supplied or automatically downloaded by this pack.
Use directories that contain the exact hashed images in the original inventory:

```powershell
python -I -B -X utf8 <package>/replay_dbgeng.py --case-pid 2188 --dump <external-dump> --engine <external-dbgeng.dll> --image-directory <game-images> --image-directory <system-runtime-images> --output <outside-package>/replay.txt
```

Add `--check-inputs-only` and omit `--output` to validate inputs without loading
DbgEng. Actual reexecution passively opens the dump and executes `.ecxr`, `kpn`
and module commands. It never attaches to or creates a process. Its output must
be outside this immutable package. A successful private smoke replay of this
new entry point was performed; accepted baseline logs remain the original v2
raw outputs rather than a reconstructed transcript.
