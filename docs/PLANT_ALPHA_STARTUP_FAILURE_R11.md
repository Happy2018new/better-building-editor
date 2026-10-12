# Alpha Startup Failure R11

One authorized cold-load alpha-marker attempt ran in slot 3 with the approved
IPC build, focus guard, launcher query fix and protected code-execution client.
The attempt failed before runtime readiness. No health/timer, camera, plant
fixture or native capture stage ran. No opaque marker or holdout was used, and
no production position profile was registered.

The original launch receipt reports `ready=false`, `state=failed`, and
`Code execution failed. The player may not be in the game or the target is
unavailable.` The window remained visible, unminimized and nonactivating while
other applications held foreground. The 150-second external supervisor made one
launch and completed failure handling in 76.505 seconds. Normal close failed;
the supervisor inspected both owned creation identities before force-stopping
only that session. Both owned processes were subsequently confirmed dead.

The session was `f67b34e0b2c442a594780b64d8b7b32d`, owner
`snow-r11-position`. Game PID 11260 had creation time `134362917459245243`;
MCDK PID 26396 had creation time `134362917457212643`. The isolated bitmap
override, config and launcher/client files were restored to their exact original
bytes. The installed vanilla poppy texture remained unchanged. The alpha marker
candidate was the previously declared bitmap
`46fc92e57b7a81922dd18c60a2b429be87050ce8b623fc9bfac6f9b8122de1f2`, with
every native alpha byte preserved. File preparation did not prove marker loading
or visible pixels.

Raw portable evidence is in `tools/data/plant-alpha-single-startup-r11-v3/`.
Its index SHA-256 is
`6110beaaacff545e5bcf0afcfdef81017d9605bf9c991e5d6b32002ea67d0d53`.
The original supervisor SHA-256 is
`813724a349c47e803015dabc2d8fa94a0f36f989f6d8b00e1b32c5d7df297433`;
the untouched failed launch stdout SHA-256 is
`250051ac4a62344701cfa1910a6f15891ae2b80cddbcca09a08725590d56081e`.
The archive includes exact approved sources, original-byte backups, generated
config, debug/session probe sources, pack lists, logs, alpha/native bitmaps and
the independent plan. A separate source index records the isolated project's
restored behavior/resource bytes after stopping; it is explicitly a post-stop
observation, not a claim that all resources were frozen before launch.
The archive's `.gitattributes -text` rule prevents line-ending normalization.
`tests/test_plant_alpha_startup_evidence_r11.py` verifies it without external
host paths or a live game. Dead-process and restoration fields are retained
historical receipts, not current host recertification.

The reviewed pinned MCDK source gives a narrower failure location:
`game_process.cpp:204` returns this exact message when
`ipcServer->getClientCount() == 0`. The other identical-message branch handles
calls without direct return; startup requested `direct_return=true`. The failed
read therefore had no connected debug IPC client and did not reach the
request/response framing handler. This does not identify why the client failed
to connect, and it does not establish a texture or geometry cause.

The next decisive work is an offline comparison of this generated debug pack,
world pack UUIDs/versions, session probe and config against the healthy
`773c643b5cf344918e04d8b4eef2657a` startup. Verify which game initialization
stage creates the IPC connection and whether its code, dependency manifests and
world links differ. If those bytes match, a new separately authorized native
diagnostic must record client connection/pack-load state and a passive background
startup frame before any fixture. Its vanilla versus alpha comparison must hold
the other sources and config fixed. Another identical readiness-only retry does
not distinguish those causes and is not justified by this failed attempt.

Accepted scope stays at 29 positive states / 232 height observations and eight
observed negative lower-half states. Seed-name false rows remain unobserved.
Original pixel ROI, recall/precision and edge tolerance are unchanged. No mesh
pivot, offset formula, marker pixels or native render progress was recovered.
