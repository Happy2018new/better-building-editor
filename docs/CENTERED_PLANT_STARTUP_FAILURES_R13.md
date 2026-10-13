# Centered poppy R13 startup results V1 and V2

Neither attempt reached the h0 plant matrix. No candidate render acceptance is
claimed. Original plans, runtime receipts, executed host inputs and cleanup
evidence are retained in `tools/data/snow-centered-r13-failed-startups/`.

V1 failed during host preparation with `SameFileError`: the plan's input
`instances.py` was its destination. It made zero game launches and captured
zero PNGs. Its one backup was restored, no candidate resources were installed,
cleanup errors were empty, and elapsed time was 2.550 seconds. The next plan
froze separate exact copies of the three preparation inputs.

V2 made one owned launch with the repaired noactivation guard. The launcher
failed its unchanged 90-second SDK-readiness deadline before client
initialization. Session `549fe764de7f4f1db42f03b4285fe7ec` never reached world
readiness. Its game was PID 12932, creation `134363434932341658`; MCDK was PID
53880, creation `134363434928773444`. Actual foreground remained the same
non-game window. No activation, desktop input or resize was requested.

The first scheduled pre-ready capture also failed: the frozen observer used
its short worktree as the shared archive root. Although the plan pinned a
valid original WGC helper, the observer compared it with a nonexistent
`D:/bbe-r13-snow/.runtime/worktree-archive-r7/...` default. Zero PNGs were
produced. The lack of a reliable background image was explicitly reported.
This capture-path failure and the launcher-readiness timeout are distinct;
neither establishes whether the candidate geometry works.

V2 sampled pre-ready game handles at 1,408, 13,332, 25,314, 35,171 and
43,434. These observations do not establish a renderer cause or accepted
resource health. The existing post-ready growth rule never applied because
world readiness was not reached. Total elapsed time through cleanup was
117.086 seconds, within the 240-second bound. Both exact owned process
identities were independently absent, all four diagnostic resource edits
were restored to original bytes/absence, host files and native texture were
restored, and cleanup errors were empty. No native fixture, camera or product
projection mutation began.

The subsequent source correction validates the frozen plan's capture path
and SHA against the approved single-WGC byte hash before binding that exact
path into the isolated observer module. A short worktree no longer needs
the runtime archive at its own root. A preparation-source preflight now
rejects copying a frozen input onto itself before any mutation. Fourteen
candidate tests and 49 startup tests passed, including changed-helper refusal
and short-worktree coverage. These checks do not replace a new real control.
