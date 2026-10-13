# Single-Door V12 Invalid-Load Failure

The one authorized V12 attempt reached protected SDK readiness and then failed
before writing either door half. It is not door replication, typed upper state,
physical orientation, screenshot, or capture-reliability evidence.

The original preflight read feet `(0.5, 32768.0, 0.5)` in dimension 0, runtime
`1.21.120.0`, and derived origin `(4, 32780, 4)`. The support setter at
`(4, 32779, 4)` returned `false`; the immediate support read remained air with
null states. Setup recorded `AssertionError: Support not stone`. Door setter
steps are empty, and both actual halves remained air with null states. No delayed
observations or whole-pair diagnosis ran. The read is consistent with unsettled
world/player loading; this attempt did not include a documented chunk-load check
and cannot distinguish every cause of the invalid anchor.

The launcher phase took 85.250 seconds, finishing at supervisor elapsed 87.073
seconds. Probe started at 87.087 with only 22.913 seconds available under the old
110-second work limit. Probe itself took 1.650 seconds. The supervisor completed
all cleanup at 102.389 seconds, below its 150-second total limit. Initial process
discovery succeeded on its first observation at 7.821 seconds. The approved host
readiness fix was exercised; SDK routing readiness did not establish a usable
player anchor.

Fixture cleanup reported restored, no errors, and unchanged player; the client
read all 17 reserved positions as air. Because those positions were outside world
bounds, these air reads are retained as actual observations rather than proof of
a usable fixture region. Normal stop reported a still-open game; exact owned
force stop completed. Independent host inspection at
`2026-10-12T17:55:27.176419+00:00` found the V12 game PID 46016 and MCDK PID 41960
absent. The protected frame PID 44536 retained its creation identity. No SDK or
input calls were sent to that frame. Installed launcher/client/config inputs were
restored byte-for-byte, with the originally absent local config absent again.

Frozen evidence is in `tools/data/native_single_door_load_failure_r11_v12/`.
`manifest.json` inventories exact bytes: original supervisor and probe receipts,
raw launcher stdout, generated config, session stop receipt, original installed
and restored input bytes, executed probe/helper/supervisor sources, own MCDK log,
and independent cleanup audit. Earlier V10, V11, and prepared V12 evidence is
unchanged. No further native attempt is authorized by this result.
