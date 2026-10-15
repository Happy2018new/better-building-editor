# Authentic Native Shield Rendering Comparison

NEMC 3.10.0.420447; owner `shield-r20-v7-authentic`; game PID 39728,
creation identity `134365633584760870`. Nine unedited owner-bound native WGC
images compare the exact shield output retained by the earlier native crafter
package. No product rendering path is enabled. Four automatic reload flags
are false. The frozen BP/RP digest is
`3ba87e51a23e547b192246790bd40c6999ff5f745accc06cbc3ed5ae6aeee06b`.

## Confirmed Native Positive

The authentic raw item is copied unchanged: outer aux 0, typed integer Base 4,
typed integer inner Damage 0, and ordered `bo:1`, `cr:14`, `mc:11` patterns.
`references/authentic-shield.json` is a byte-exact provenance copy.
`records/inputs.json` retains both the source and submitted payload.

Image 01 shows native SetUiItem controls above three unbound host bodies.
Image 02 shows newly attached shields and sword below the same controls.
This negative/positive pair was actually reviewed before the remaining seven
captures. The small orange markers belong to the host model and are not
accepted as item attachments. The host model is an existing composite item
icon mesh with a root bone; it is not an invisible empty host.

With the fixed bind rotation `(90, 0, 0)` and scale `1/16`, yaw 0 shows the
wooden shield reverse. In image 04, yaw 180 exposes the authentic front with
blue base and all three ordered patterns. Image 05 shows an edge and rear
handle. These establish a real native skeleton item attachment that consumes
the authentic Base tag, including visible thickness. They do not establish
the correct frame-local pose, full item proportions or quantitative thickness.

## Differences And Open Gates

The native UI shield above it shows a white base with the same visible
patterns. The verifier measures zero blue pixels and 12,651 white pixels in
the fixed UI inspection crop, while the bone-front crop contains 1,084 blue
pixels. The exact same authentic userdata is retained for both calls. The
route difference is observed; its cause is not established.

Images 06 and 07 are actual native frames populated through native item use.
Their Item.tag matches the authentic payload exactly and ItemRotation is 0.
The authentic frame exposes wooden reverse material; the plain frame shows
a flat green interior rectangle. Neither is accepted as a patterned-front
reference. Native frame block aux/states were not recorded in this version;
support face 2 and both camera configurations are retained in execute-code
receipts. `observations.json` records the smallest next diagnostic: opposing
native frame faces, explicit states/normals and a sword positive, four images
maximum. That follow-up has not started.

Images 08 and 09 show native RenderEntity attachments as an owned raw overlay
on a real editor workspace containing one stone. This is candidate visibility
and rotation only. Item Scene integration, shared depth/occlusion, opacity,
full/missing projection and correct frame-local pose remain open. The overlay
extends across editor panels and is not an accepted product layout.

Banner item shape, its short lower stalk, item pose and thickness are separate
gates. Standing/wall banner block geometry does not satisfy those gates.

## Restoration And Replay

Fifteen execute-code records preserve exact source and SHA256. All 96 guard
cells, inventory, selected slot, player foot, camera/FOV/locks, editor and
workspace are restored; item bindings and owned actors are removed. No
fixture drops remain and the frozen source closure is unchanged.

The first ordinary stop timed out. No force or repeated close was sent while
the exact process remained live. The observer, attached immediately after
ready, recorded game exit `0xC0000409` and MCDK exit 0. A later stop only
finalized already exited processes. Normal lifecycle acceptance remains false.

Run `python host/verify.py .` from this package. It verifies provenance,
payload equality, source hashes, exact binding/actual-frame readbacks,
restoration, all nine native WGC identity/freshness/hash receipts, the fixed
color crops, exact exits and every manifest byte. `inspection-crops.png` is
a derived nearest-neighbor viewing aid; all originals remain under `images/`.
No session routing token is included. Product qualification remains false.
