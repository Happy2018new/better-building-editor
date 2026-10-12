# Plant Destination Origin R11

Position-sensitive plant geometry receives the destination logical block origin
as three integer X/Y/Z coordinates. The default `(0, 0, 0)` preserves existing
callers. This value is a rendering input, not saved document metadata or an
acquisition-world origin.

`prepare_palette`, the context builders and `ClientBridge.geometry` accept the
optional trailing `render_origin`. Geometry is selected at `origin + logical
cell` before snow overlays, context-neighbor packing or chunk rebasing. Already
prepared palettes have resolved their geometry and are never resolved again.
World projection and missing-cell preparation pass the actual projection origin;
editor tiles pass their logical tile origin. Per-material and per-tile caches
include the location when geometry depends on it.

`plant_position.POSITION_PLANT_PROXIES` is intentionally empty. A future accepted
profile returns `(proxy_identifier, alpha_top_height)` for one destination cell,
including a plant in the snow background layer. The height supplies the complete
burial check. Tests install synthetic profiles solely to verify routing, chunk
boundaries, cache isolation and relocation. They do not accept a native mesh,
pivot, coordinate hash, or new plant state for production.

The bitmap-marker experiment changes only the isolated resource pack's poppy
texture. Its first control preserves every native alpha byte, because historical
native cross tessellation depends on alpha. Opaque envelope images are geometry
diagnostics. They cannot replace unchanged original-foliage acceptance, the
predeclared holdouts, the fixed unit-cell ROI, or the original .75 recall/.75
precision gates with three-pixel edge tolerance.
