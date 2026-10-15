# Native Lectern Authored-Book Control

Offline preparation only. Root has not authorized a new launch. The completed
actual-cardinal40 raw report and captures are never modified by this control.

The previous fixture inserted a blank minecraft:writable_book using a real
inventory item and PlayerUseItemToPos. All four server readbacks contain
hasBook=1, book.Name=writable_book and totalPages=0. Its client palette actor
is empty and no independent complete client book NBT was acquired. The book
looks absent in all four native world frames. That oracle is unvalidated;
this is neither a native-book pixel pass nor a product-book pixel failure.

The shortest follow-up uses the existing frozen
.runtime/projects/root-signed-book-r21-v1 unchanged, with separately assigned
owner book-r20-native-oracle-v1. The existing loot table already contains
authored written_book A, title R21 Native Authored Book A, author R21 Native
Loot, and two nonempty pages. No new project copy or JSON mutation is needed.

probe_native_book_oracle.py has only verify and run commands. It never
starts, activates or stops a game, sends desktop input, resizes a window,
enables the lectern candidate, opens a UI, or runs projection. Root must
assign the MC and WGC window, verify the intended cold project and owner,
and bind exact exit handles before run.

One east3/unpowered native lectern stands on one cyan block. Two empty world
frames precede native loot acquisition and actual inventory insertion.
GetLootItems(..., getUserData=True) supplies the full item; no typed book
metadata is manufactured. Its complete native userData must survive actual
inventory readback unchanged. The insertion uses PlayerUseItemToPos only.
The host records complete server and independent complete client block NBT
and client palette data. It requires book/hasBook/page/totalPages convergence,
positive totalPages, written_book Count1 and every native userData tag
preserved on both sides. Failure leaves the native book oracle unqualified.
After convergence it captures three advancing phases of the single native
lectern from the fixed (3,2.4,5) oblique camera. Even successful data does
not automatically qualify visible book pixels; root must inspect the five
raw native-resolution images.

The host requires at least 6 GiB available commit by canonical
GetPerformanceInfo and fewer than 200k owned handles at natural boundaries.
Its 120-second acquisition budget always leaves finally restoration active.
It restores the owned inventory slot and compares all 36 slots, restores
the world to independently checked air, restores the player/camera and
environment, and verifies the exact frozen source again. Normal stop,
exact exit codes and stopped registration remain root's external lifecycle.

Verification uses no game calls:

```powershell
python -B -X utf8 .runtime/lectern-body-candidate-r21/probe_native_book_oracle.py verify
```

Only after a new explicit allocation:

```powershell
python -B -X utf8 .runtime/lectern-body-candidate-r21/probe_native_book_oracle.py run --session ASSIGNED_SESSION --capture-exe APPROVED_SINGLE_FRAME_WGC --output FRESH_OUTPUT
```

The existing single-frame helper SHA256 is
cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8.
Source digest is
2db60ade9dae57a155f6da01f715abee5cc2aa5abae4506ac40a3003e1b42e4a.
All four hot reload settings remain false. Production, powered appearance,
book parity and lifecycle qualification remain closed.
