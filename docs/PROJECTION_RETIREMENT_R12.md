# Projection retirement containment

## Ownership and recovery

Client projection actors retain their `OccupancyShader` owner until
`DestroyClientEntity` returns normally. The descriptor holds the pool, both
buffer names, attempted attachments, attached context parts, and overlay
visibility state. Registration occurs immediately after actor creation,
including late creation by an initially empty missing-only projection.

Before each destruction attempt, retirement hides the terrain bank selector
and every attempted geometry attachment through actor visibility. Each hide
has its own success journal. False returns and exceptions leave that entry
pending without updating the shader's success cache; other entries and the
destruction attempt still proceed. Successful hides are not repeated. A
successful destruction releases ownership even if a hide failed, because the
actor no longer owns the attached resources.

The geometry catalogue remains bounded to two pools with two banks each.
Both a committed actor and an actor awaiting confirmed destruction reserve
their pools. New projection preparation retries pending releases before
choosing a pool. If neither pool is free, it stops before geometry generation
or actor creation, retains the committed projection, and reports that cleanup
must be retried. Closing with both pools retained also blocks reopening until
one destruction succeeds. Close and subsequent update attempts retry cleanup.

`DestroyClientEntity` has no documented return value. A normal return,
including `None`, is the completion criterion; an exception conservatively
keeps ownership even if native code might already have removed the actor.

## Host validation

Commands run from the isolated retirement worktree:

```text
python -m unittest discover -s tests -p test_projection_retirement.py -v
python -m unittest discover -s tests -p test_bridge.py
python -m unittest discover -s tests -p test_occupancy_review.py
python -m unittest discover -s tests -p test_occupancy_initial.py
git diff --check
```

The focused suites pass: 7 retirement, 53 bridge lifecycle, 26 occupancy review,
and 4 initial occupancy tests. Retirement coverage includes multiple
generations, uniform and visibility setters returning false or raising,
partial attachment before an exception, destruction exceptions, cancellation
before binding, late occupancy actor creation, close with two surviving
generations, and successful recovery without changing the committed actor.

Scoped MOD review parsed the changed modules successfully. Its advisories
refer to existing long functions, the geometry signature, and broad exception
handling in existing follow/publication paths. No client/server import
boundary or event registration change was introduced.

No game instance was launched or controlled for this change. Host adapters
verify ownership, call sequencing, retry journals, and pool reservation; they
do not establish native visibility, native destruction timing, or resource
thread behavior. Native validation must separately confirm that retired
terrain and vanilla-material overlays become invisible and stay hidden while
destruction fails, then that a freed pool renders correctly after recovery.

The subsequent paired terrain/liquid occupancy transaction and its host
validation are recorded in `PROJECTION_PAIR_R12.md`. It preserves this
retirement ownership and pool reservation contract.
