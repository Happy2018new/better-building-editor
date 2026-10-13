# R13 read-only handle population diagnosis

The new focus guard is compatible with a ready game whose handle count remains
approximately 830. The large File/AFD population also appeared in R11 with the
old guard. These observations do not justify reverting the new `SetFocus` guard
or attributing every startup failure to it. They also do not identify the code
that creates the large populations observed in other R13 games.

Root requested a bounded read-only census after liquid, snow and scaffold owners
reported rising startup handles or failed readiness. The item owner supplied
session `24b38560ce6a48f7b71af108d1b7c6db`, owner `item-skeleton-r13-v1`, game
PID 53792 with creation identity `134363432612984169`. That ready game used guard
SHA `04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93` and MCDK
SHA `b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9`.
The reviewer did not start, stop, inject, activate, resize, capture or execute
SDK/MCP code in that game. Its owning agent retained control of the instance.

The existing creation-bound R11 helpers collected one handle-type census,
first/middle/last samples of the common `0x0016019f` access-mask handles, and a
second census 341.106 seconds later. The extended system handle table and
`GetProcessHandleCount` agreed on each total. Each type census took under 0.21
seconds; the three-name batch took 0.65 seconds and bounded each helper to four
seconds. All local duplicated handles and process-query handles were closed.

| Current item sample | Total handles | File objects | Common-mask File objects |
| --- | ---: | ---: | ---: |
| First census | 829 | 70 | 12 |
| Second census, +341.106 s | 830 | 71 | 12 |

All three sampled names were `\Device\Afd`, with successful name and basic-info
queries. Their handle counts including the local diagnostic duplicate were
3, 2 and 2. These name samples establish the three sampled network objects,
not every handle with the same access mask. Index 56 remained unresolved because
its representative duplication returned Windows error 50; its 223 objects have
not been silently classified. Every kernel object pointer was zero on this
host, so aggregate object multiplicity is unavailable. The helper explicitly
excludes zero pointers from that calculation.

Two preserved R11 reports supply the historical control. The old-guard smoke
PID 17276 had 168,927 total handles and 168,124 common-mask File objects; the
read-only report pins its old DLL to
`c22fa0cd0bdbfb7d9218d59573b61619111f9bd180562c9bd51c69276c11c178`.
A later revised-IPC entities startup had 52,074 total handles, with 51,395
common-mask File objects, and its three sampled names were also `\Device\Afd`.
A separate root game with the same revised MCDK remained at 830 / 827 total
handles. Thus high and low populations occurred before the new focus patch,
and high or low totals alone do not identify a guard or IPC root cause. These
older records are retained as existing historical evidence, not rerun results.

The source review does not establish an allocation cause:

- The guard callbacks perform window style/focus calls and `SetLastError`, with
  no direct kernel handle allocation. MinHook initialization is one-time.
  Indirect engine behavior after rejected focus remains an unmeasured possibility.
- The launcher creates two remote initialization threads and closes their local
  handles. It closes its module snapshot, and intentionally keeps the DLL loaded
  for the game lifetime. Those bounded startup allocations do not directly
  explain a per-frame increase of tens of thousands of File handles.
- The prior exact IPC source review found one Python socket constructor per
  listener, no socket reconstruction on receive timeout, and explicit final
  socket cleanup in the revised template. It records a start scheduling race,
  but no live evidence demonstrates repeated starts at the observed scale.
- Host-side HTTP connections and MCDK directory watchers are owned by their host
  processes. They cannot be counted as game-owned objects merely because the
  processes cooperate. The name `File` also includes sockets and device objects;
  it does not imply disk files or GPU allocations.

The original R13 cold smoke remains valid for that one launch. It cannot
generalize to every later startup, and it does not eliminate the separately
observed large-handle or IPC-readiness failures. Later runs must retain their
existing actual foreground, bounded readiness and handle-health checks. No
threshold or guard was weakened, no guessed product fix was applied, and no
additional cold launch was performed for this review. A future authorized high
startup would need its own phase-bound census and name samples or an allocation
trace to identify the source of its retained objects.

The archive `docs/evidence/handle-population-r13-v1/` contains the three current
raw observations, detached session identity/binary pins, exact reused helper
sources and the explicitly marked R11 historical records. The index preserves
original byte hashes. The corresponding latest high R13 liquid observations
belong to their owner at
`D:/bbe-r13-liquid/.runtime/liquid-native-write-r13-v1/*passive-health.json`;
they were reported to this reviewer but were not retroactively reclassified
as AFD objects after those games had stopped.
