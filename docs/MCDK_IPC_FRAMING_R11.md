# MCDK IPC Partial-Receive Fix R11

The MCDK v1.6.1 debug receiver loses TCP framing when its 50ms socket timeout fires
after receiving part of a header or payload. For example, a six-byte header for
type 100 and length 10 begins `[0,100,0,0,0,10]`. If only its first two bytes arrive
before timeout, the original outer loop discards them and treats the remaining
four bytes plus the start of the JSON payload as another header. A deterministic
host reproduction reads type 0 and length 686882 from `[0,0,0,10,123,34]`.

This is a source-level IPC defect with host reproduction. It has not been shown
to cause the observed game freeze or large AFD socket-object population, and is
not evidence of shader routing, native rendering acceptance or SDK scan failure.

## Patch and Source Pin

The tracked patch is `tools/mcdk_patches/ipc-framing-r11.patch`. It targets only
`mods/INCLUDE_TEST_MOD/DEBUG_ENV_SCRIPT/IPCSystem.py` in the official
[MCDevTool repository](https://github.com/GitHub-Zero123/MCDevTool), tag v1.6.1,
commit `cefdfb5ce220e0cc3e9df6d80b2ff87be8b98802`.

| Source | Identity |
| --- | --- |
| Official Git blob | `2b3f0d45f6119f374a8e45a6199796321509c105` |
| Official source SHA256, LF and no final newline | `09c8fb609d32008784114c3d34a729c4bb83e53ebfa06bf4ae279a35cf3437b9` |
| Observed Windows official/generated source SHA256, CRLF | `6f3f1cbfde8d767992464c37c20b42d1030fa17d2e87f84a45bfe18229c3ca14` |
| Frozen fixture SHA256, LF with one final newline | `a9d7d9cac39633701efc9f31d20931681dabf535a9bb053aecc77da36b35fe33` |
| Patched source SHA256, LF with one final newline | `07116d149b80f7b7176806fcb27608e8d421a1ac62b3770e1abccdc20b127520` |

`tools/data/mcdk_ipc_runtime_v1.6.1.py` freezes the official source for
fresh-checkout tests. The sole fixture normalization beyond CRLF-to-LF is adding
the conventional final newline. Tests verify both hashes and remove that newline
before applying the patch, checking against the exact official Git source.
The patch itself adds a conventional final newline.
The fixture is evidence, not a replacement game module.

## Changed Behavior

- `_recvAll` catches a receive timeout inside its own loop, retaining already
  received bytes until the requested header or payload is complete, EOF occurs,
  or the socket fails. Packet dispatch never restarts at the middle of a frame.
- The listener closes its local socket in `finally`, including connection and
  receive failure. It clears `self.sock` only when that reference still points to
  its own socket, so an old listener cannot erase a replacement connection.
- `close()` closes the socket even if `shutdown()` reports a socket error.

This change introduces no reconnect loop, new runtime import, game-thread SDK
operation or shader/material mutation. It preserves the existing 50ms poll
interval, public API and Python 2-compatible syntax. The existing listener still
owns one socket and one background thread.

## Validation and Use

Run the host tests from this repository:

```powershell
python -X utf8 -m unittest discover -s tests -p test_mcdk_ipc_framing_r11.py -v
```

The 13 tests verify the original failure, split headers, split payloads, actual
JSON-request dispatch, repeated idle timeouts, packet order, EOF, receive failure,
connection failure, shutdown failure, cleanup close failure, replacement-socket
identity and close interrupting a partially received header. Tests read the frozen
source, run `git apply --check` and apply the shipped patch in a temporary directory,
then AST-load the actual IPC class with a deterministic fake socket. They import
no game module and create no real network connection.

For an exact official v1.6.1 checkout, run the following before rebuilding:

```powershell
git -C <official-checkout> apply --check <repo>/tools/mcdk_patches/ipc-framing-r11.patch
git -C <official-checkout> apply <repo>/tools/mcdk_patches/ipc-framing-r11.patch
```

The isolated retry source already contains this patch. Apply it once. Rebuild in
a new output directory so the embedded debug template changes; do not overwrite
the existing validated executable. After launch, verify the actual generated
IPCSystem.py SHA, session creation identity, IPC replies and game progress during
a short owned smoke test. The root task owns that build and native smoke.

The 13 host tests and patch application checks passed. The new test and this
document pass the normal staged whitespace check. The frozen official fixture
retains its upstream whitespace-only line, and unified-diff blank context lines
retain their required single-space prefix. These evidence files pass the staged
check with only `blank-at-eol` disabled; their bytes are not reformatted to silence
the default check. No live game or previous executable was modified by this work.
Native contract smoke and attribution of the AFD objects remain separate evidence.

## Upstream License

The frozen official source is redistributed under the upstream BSD 3-Clause
license. The following notice is retained verbatim from the pinned repository:

```text
BSD 3-Clause License

Copyright (c) 2025, Zero123

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```
