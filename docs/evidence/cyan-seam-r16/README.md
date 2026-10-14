# Cyan Cube Face-Seam Comparison

Engine: NEMC `3.10.0.420447`, MCBE `1.21.130`. This investigation responds to
the user's thin background line around the cyan support cube of a lectern
fixture. It is a reproduction record, not a fix qualification.

The independent source contains one `minecraft:cyan_concrete` cell at local
`(3,2,3)` in an `8 x 8 x 8` logical document, with no NBT and no book companion.
It passes through the ordinary production geometry preparation and full
projection route. Opacity is exactly `1.0`. `report.json` retains the source,
native Combine receipt, projection model, origin, target entity and shader
uniforms. The companion profiles may be present in Session, but the cyan cell
does not produce portal, book, liquid or item companion groups.

The camera compares 45-degree and 135-degree views at the same world position,
first with a projected cube and then with a real cyan cube. Projection is
stopped before writing the real control. The server journals the original air,
confirms the real cube after writing, and the client separately reads back
`minecraft:cyan_concrete, 0` before capture. `finally` restores the original
world block, projection, editor and camera. All four reliable raw PNGs and
their original capture receipts are committed here, with two enlarged contact
sheets under `review`. Both sheets were opened and inspected.

The projection has a thin light/background line along the boundary between
the top and side faces that is not present in the real control at the same
camera. Thus the book companion is not required to reproduce this ordinary
projection defect. The user's highlighted vertical boundary is not completely
resolved by these two exact camera samples and remains part of the open
investigation. This record does not establish whether the underlying cause is
the native mesh, the project vertex transform, coverage or depth behavior.

The first discarded run `.runtime/cyan-seam-r16-v1` used a location 32 blocks
above the player. Server readback succeeded, but the real cube never appeared
in the screenshot, so it is not a valid visual control. The accepted
investigation uses `.runtime/cyan-seam-r16-v2`, a nearby loaded height segment,
a ten-second delay and explicit client readback. No claim is inferred from
the discarded run. The probe now rejects missing client readback.
