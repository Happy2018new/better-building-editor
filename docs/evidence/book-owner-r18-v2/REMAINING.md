# Fixed Book Worklist After Boundary Controls

Status recorded on 2026-10-15. No book product qualification was granted.
The original 65-frame owner and 65-frame ordinary default matrices completed,
restored, and passed their readback checks, but both failed visual admission
because an occupied enchanting table retained textured body faces.

## Reproduced Defects

- The original body leaves its bottom plane on a lower support when occupied.
- Four same-height half-slab neighbors retain its four side walls when the
  table target is occupied. This was observed from two sides, not inferred
  solely from the inclusive clip calculation.
- A 1/16 model-pixel bottom inset removes the original bottom texture residue,
  but leaves a low-view pale line that prevents acceptance as a seamless fix.
- A cold-started 1/64 inset retains the full bottom texture plane.
- Removing only `netease:no_crop_face_block` with original geometry retains
  both bottom and horizontal walls. Component documentation and exact tested
  assets are archived in `../book-body-crop-r18`.

The failed side component control also has a low occupied image with a visible
book after an earlier zero-count poll. Future diagnostics now record owner
counts immediately before and after capture; the old image is not treated as
successful disappearance evidence.

## Required Before Admission

1. Implement correct ownership for the bottom and four horizontal boundary
   faces while preserving the target's own exposed faces. An inclusive-phase
   range alone cannot distinguish two coincident faces with different owners.
2. Repeat bottom and four-side actual-occupancy controls. Shown geometry must
   retain native artwork, top height, all six faces, and contact with supports
   without a visible gap; occupied targets must leave no textured residue.
   Include all relevant local-context chunk positions in the regression.
3. Resolve or positively isolate the low occupied image/readback discrepancy
   using capture-time owner receipts and stable repeated native frames.
4. Freeze the accepted owner, geometry, behavior definition, and registrations;
   bind all 17 owner source files, six body files, and owned registry entries.
5. Run the revised complete 65-frame candidate matrix and inspect every sheet.
   Only then create a disposable default-test admission for that exact bundle.
6. Cold start the ordinary default path without profile assignment and run its
   complete 65-frame matrix. Inspect all sheets, verify restoration and source
   closure, then perform final reviewed qualification for the exact engine.

The unchanged native artwork and stationary lectern-page reference evidence
may be reused only while its nine resource file hashes and four owned
model/material registrations remain identical. A new body fix invalidates the
old body/owner source closure; the failed matrices cannot qualify that fix.

The ordinary table-body routing is now closed by the independent
`static_table_data.PRODUCT_QUALIFIED=False` gate. It falls back to the native
body; the previously observed 0.125-block native body offset is still open.
This is a conservative routing fallback, not a visual fix or qualification.
Explicit diagnostics temporarily use `static_table.CANDIDATE_ENABLED=True`
and restore its prior value. Enabling the book gate does not enable this body
gate, and the body remains independently unqualified.

Separate unqualified behaviors are player-proximity opening/reactions, page
text, and interaction parity. Current book evidence does not prove them.

## Saved Controls

| Evidence | Native Frames | Result |
| --- | ---: | --- |
| `../book-owner-r18-v2` | 65 | Owner readbacks pass, body image fails |
| `../book-default-r18-v1` | 65 | Ordinary default readbacks pass, body image fails |
| `../book-body-inset-r18-1-16` | 12 | Bottom texture removed, contact-line concern |
| `../book-body-inset-r18-1-64` | 12 | Bottom texture remains |
| `../book-body-inset-r18-1-64-sides` | 12 | Four horizontal walls remain |
| `../book-body-crop-r18` | 12 | Component removal retains bottom texture |
| `../book-body-crop-r18-sides` | 12 | Component removal retains side walls |

Every packaged successful procedure restored its temporary game mutations and
reported unchanged installed source hashes with no cleanup errors. Failed
pre-mutation attempts remain in their recorded runtime logs. All owned game
and MCDK processes were confirmed dead and managed stop metadata was finalized.
The disposable clone's geometry, behavior definition, and false book gate were
restored after the final control, preserving unrelated Shelf registrations.
