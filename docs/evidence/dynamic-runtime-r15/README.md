# NEMC 3.10 dynamic appearance audit

The audit used one owner-bound NEMC 3.10 instance (`1.21.130.0`, engine
`3.10.0.420447`) and excluded particles. `editor.jpg` and `projection.jpg`
are the first submissions; the projection completed three native parts with
zero reported preparation failures. The background WGC captures are reliable
window captures, but `background-editor-wgc.png` and
`background-focused-wgc.png` have the same frame hash even after a camera and
zoom request. They therefore do not provide reliable per-family pixel
acceptance. No dynamic family is marked supported by this evidence.

The 37 resource-linked ordinary flipbook names are the `ordinary_flipbook`
list in `tools/audit_dynamic_runtime_r15.py`; it includes water and lava.
The runtime fixture deliberately used an expanded candidate set for the
appearance boundary: it omitted the four world-fluid names (audited by the
separate liquid work), and added `big_dripleaf`, `end_portal`,
`end_gateway`, and `conduit`. Do not use the fixture candidate array as a
replacement for the offline 37-name inventory. The three portal-family names
are tracked together because the 3.10 Combine documentation explicitly calls
end portal and end gateway unsupported.
