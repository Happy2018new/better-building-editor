"""Pure fixed resource/deadline rules for the private host watchdog."""
from datetime import datetime, timezone

MAX_HANDLES = 250000
RAPID_GROWTH = 10000
MINIMUM_COMMIT = 6 * 1024 ** 3


def remaining_seconds(deadline_iso, now=None):
    deadline = datetime.fromisoformat(deadline_iso)
    if deadline.tzinfo is None:
        raise ValueError('Guard deadline needs an explicit timezone')
    remaining = (deadline - (now or datetime.now(timezone.utc))).total_seconds()
    if remaining <= 0:
        raise ValueError('Guard deadline has already expired; do not launch or report coverage')
    return remaining


def handle_breach(current, prior):
    return (current is not None and
            (current >= MAX_HANDLES or prior is not None and current - prior >= RAPID_GROWTH))
