# Rejected Snow Control, v5

This package preserves the original failed `blue_orchid h0` run on NEMC
3.10.0.420447 / Minecraft 1.21.130.0. The lifecycle process ended after
35.57 seconds, before any of the nine editing steps. Original status remains
`completed=false`, `passed=false`, `restored=true`, with no cleanup errors.
Neither workflow nor production acceptance is claimed.

The two snow captures each contain 22,503 changed pixels. Their independent
snow-side recall is 1.0, while the complete-hull precision is
0.909567613207128, below the unchanged 0.98 gate. All 2,035 pixels outside the
three-pixel hull tolerance are ink present in the blank reference but replaced
by the ordinary viewport background in the snow capture. The diagnostic
overlays show the disappearing empty-scene cube and text. No image was shifted,
aligned, filtered out of the acceptance mask, or accepted by this analysis.

The original blank and plant controls retain actual camera observations. The
failed snow control did not serialize its camera/source/state before capture.
The preceding plant camera exactly replays the snow validation numbers, but
this does not constitute an independent snow-camera observation. This missing
record is explicit in `diagnosis/diagnosis.json`; the original report is intact.

The seven original lifecycle images include blank, plant, two rejected snow
captures, and three native UI-response controls. Each has an owner-bound fresh
Windows.Graphics.Capture receipt. The game-render counter and pictured native
clock advance on both rejected snow attempts. The ready image is also included.
All 55 recorded execution-boundary commit samples exceed 6 GiB; the minimum is
7,378,378,752 bytes. Persistent library writes and production qualification
changes are false.

`control/process-exits.json` retains exact owned process exit observations:
game PID 53124 / identity 134365696670921131 exited with 0xC0000409, and MCDK
PID 596 / identity 134365696668814748 exited with 0. The first ordinary close
timed out; both processes subsequently exited, then an ordinary stop finalized
the session as stopped. No force stop was used. The exit code alone does not
establish the exit cause. The stop-command observations are separately labeled
as transcribed tool results in `control/stop-observations.json`.

Run the standalone byte and pixel verification with Pillow installed:

```powershell
python -X utf8 verify_package.py --pixels
```

The manifest binds original bytes and the pinned pure camera/geometry inputs.
This is a minimal diagnostic package, not a complete executable game archive.
