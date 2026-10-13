# Single-Door V13b Native Observation And Offline Replay

One owner-bound protected background attempt ran after independent acceptance of
commit `91a38d854be738c3292caf0cfec1c15b3c8ec89e` and prepared manifest
`0c95fdd3bbd25cebf682aa47a970e656232ce98364cef4a7f0dc6d36716ab154`.
There was no second launch, input, activation, resize, camera/player change, WGC,
screenshot, reload or production mapping change.

## Original Native Records

Session `8a49cffa2b9a4ba090d84101483d76e7`, owner
`transforms-r11-door-pair-v13b`, started at 03:01:12 Asia/Shanghai on October 13.
Game PID 15132 had creation identity `134363052783213168`; MCDK PID 57324 had
identity `134363052780851242`. The guarded launch reported background-safe and
noactivate true. Its launch phase took 99.851 seconds. Available probe work was
93.435 seconds after full startup/reap reserves. Supervisor elapsed was 122.529
seconds, within the reviewed 240-second total.

The load gate kept four initial feet readings `(0.5,32768,0.5)` verbatim and
rejected them without chunk queries or fixture writes. At load elapsed 2.734 and
3.766 seconds, feet were `(0.5,-60,0.5)` and all target chunks loaded. The two
stable samples passed at elapsed 4.361 seconds. No coordinates were clamped and
the player was not moved by the probe.

The in-bounds lower/upper cells were `(4,-48,4)` and `(4,-47,4)`; support was
`(4,-49,4)`. Seventeen reserve cells were confirmed air without liquid before
mutation, and SETUP repeated chunk, world/player/dimension/runtime, feet and
marker guards. The support setter returned true and actual support was stone.
The lower SetBlockNew returned true and already created an exact upper half.
The explicit upper SetBlockNew returned false while actual lower/upper remained
wooden door aux 0/8. Both SetBlockStates returned true. Actual typed server
states were south, closed, hinge false, with lower/upper bits false/true.

Both delayed observations retained that exact typed server pair. Client GetBlock
before and after each palette read reported lower wooden door aux 0, upper aux 8,
and stone support. The chunk was tracked as loaded. The whole-pair and lower
palettes were available; the upper-only palette was unavailable. No upper typed
state was inferred from its legacy aux.

The original host diagnosis nevertheless reported `pair_palette_invalid` and
`Pair palette volume must be (1,1,2)` in both observations. Its original
`data_replication_verified`, `client_typed_pair_verified` and
`physical_orientation_accepted` remain false; supervisor `ok` remains false.
Those raw receipts are immutable, including exact launcher stdout, all RPC
responses, approved source copies, generated config, stopped session and log.

## Separate Offline Correction

Thawing each actual serialized palette produces byte-string metadata keys on
the Python 3 host because the SDK capture came from Python 2. Every top-level
key has type bytes. `raw.get('volume')` is None, while `raw.get(b'volume')` is
exactly `(1,1,2)`. The old text-key lookup therefore rejects valid metadata before
reading the already captured material and typed-state layers.

The corrected host scorer decodes only top-level palette metadata keys. It also
rejects byte/text keys that collide after decoding. Existing material/property
decoding, bounds/index checks, typed comparisons, client front checks and upper
omission rules continue to apply. The live runner pins the corrected scorer SHA,
but this correction has not been launched natively and authorizes no new launch.

`tools/replay_native_single_door_v13b.py` loads the frozen original scorer to
reproduce each original failure exactly, then applies the corrected scorer to
the same stored observations. Its distinct `offline-replay.json` retains the
original verdicts and raw-probe SHA. It records zero new launches, SDK or native
calls and confirms the raw source bytes did not change.

Both corrected offline diagnoses are `documented_upper_omission_observed`:
observed lower typed states match south/closed/hinge false, palette index 0 is
covered, index 1 is omitted, and actual client fronts plus support match before
and after the reads. Data replication is verified from these existing records.
Upper typed verification, full typed-pair verification, physical orientation,
capture reliability and production transform acceptance remain false. This is
one unchanged south/closed pair, not a rotation, reflection or geometry matrix.

## Cleanup And Verification

CLEAR journaled all 17 reserve cells and restored air, with player unchanged and
no cleanup errors. Client GetBlock confirmed all 17 cells air. Normal stop
returned `Game has not closed`; the exact owned force stop succeeded. Independent
read-only Win32 process-handle inspection found both owned identities absent,
protected frame session `773c643b5cf344918e04d8b4eef2657a` still on its original
identity, and the foreground ChatGPT window/PID/identity unchanged. No SDK or
input call was sent to that retained frame.

Independent hashes confirm instances.py restored to `e485a7b2...`, the original
local mcdk.py restored to `3aa4555a...`, and .mcdev.json returned to absence.
Resource stability is not accepted; the attempt did not collect a before-cleanup
resource sample and one passive sample cannot establish stability.

The frozen family is `tools/data/native_single_door_observed_r11_v13b/`.
Regression checks use actual frozen Python 2 byte-key palettes, verify both
original failures, replay both observations without constructing a runtime
client, retain absent typed upper state, reject ambiguous byte/text keys, and
check original stdout/source hashes and independent cleanup receipts.
