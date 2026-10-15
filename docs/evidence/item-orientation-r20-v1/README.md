# Item-frame downward baseline and editor brightness controls

Production qualification remains **false**. The item-frame layout now applies
its 180-degree horizontal baseline to both upward and downward faces. Shelf
and campfire layouts remain outside this condition. No fragment shader,
shared body shader, material, mesh, or light calculation changes here.

The cold downward rotations 0, 45, and 90 degrees pass independent product,
actual native-body, and local native-edge gates. Each report completed with
restored fixtures, unchanged source snapshots, and no cleanup errors. The
previous 180-degree mismatch is retained in the earlier item-plane package
as a failed control. Native item visibility is established with the actual
player below the downward frame; an empty or stale native image cannot pass.

Brightness compares declared visible frame-body patches against each editor
frame's own hidden-item baseline before and after rendering. Existing
direction-dependent body brightness is allowed. The selected patches exclude
the source icon alpha and the editor's lower controls. Every patch must have
at least 16 pixels and at most 3 RGB levels of change; an injected 12-level
change must be rejected. The original six-face plain/enchanted controls and
the corrected downward sentinels are retained with their editor PNGs and
owner-bound receipts. This evidence supports leaving body lighting unchanged.

Full capture folders include original PNG bytes, sanitized receipts, calibration,
reports, and recomputed pixel analyses. `brightness/` retains only the editor
triplets needed for that measurement. `source/` freezes the analysis import
closure and current generated contract. Authentication tokens are omitted.
`shader-compile.json` records the 16 GLES 2/3 compile/link cases.

Run from Windows with Python, NumPy, and Pillow:

```powershell
python -B -X utf8 docs/evidence/item-orientation-r20-v1/verify_package.py --pixels
```

The verifier checks all retained bytes, rebases moved paths, and repeats the
frozen pose and brightness analyses without a game. Full ordinary-frame and
glow-frame matrices remain separate acceptance work; this package qualifies
only its measured poses and does not enable production rendering.
