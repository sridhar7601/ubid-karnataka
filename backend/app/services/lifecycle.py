"""Lifecycle inference service — determines Active/Dormant/Closed status per UBID.

Uses a rules-based approach with explainable reasoning:
- Active: Recent filing/activity within the last 12 months
- Dormant: No filing/activity in 12-24 months
- Closed: Deregistration event or no activity in 24+ months
- Claude API for ambiguous cases (e.g., active in GST but struck off in MCA)
"""

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.models import UnifiedBusiness, LifecycleStatus, LifecycleEvent

logger = logging.getLogger(__name__)

# Thresholds
ACTIVE_MONTHS = 12
DORMANT_MONTHS = 24

# Events that indicate closure
CLOSURE_SIGNALS = {"deregistration", "cancellation", "strike_off", "dissolved", "wound_up"}

# Events that indicate activity
ACTIVITY_SIGNALS = {"filing", "renewal", "inspection", "return_filed", "payment", "consumption_data"}


def infer_lifecycle_status(
    unified_business: UnifiedBusiness,
    db: Session,
) -> dict:
    """Infer lifecycle status for a unified business from its linked records and events.

    Returns dict with status and reasoning.
    """
    now = datetime.now(timezone.utc)
    reasoning_parts = []

    # Check for explicit closure signals from source systems
    for record in unified_business.raw_records:
        status = (record.status_in_source or "").lower()
        if any(signal in status for signal in CLOSURE_SIGNALS):
            reasoning_parts.append(
                f"Source system '{record.source_system}' shows status '{record.status_in_source}'"
            )

    # Check lifecycle events
    events = sorted(
        unified_business.lifecycle_events,
        key=lambda e: e.event_date or e.created_at,
        reverse=True,
    )

    latest_activity = None
    has_closure_event = False

    for event in events:
        event_date = event.event_date or event.created_at
        event_type = (event.event_type or "").lower()

        if event_type in CLOSURE_SIGNALS:
            has_closure_event = True
            reasoning_parts.append(
                f"Closure event '{event.event_type}' from {event.event_source} on {event_date.strftime('%Y-%m-%d')}"
            )

        if event_type in ACTIVITY_SIGNALS:
            if latest_activity is None or event_date > latest_activity:
                latest_activity = event_date

    # Check last filing dates from raw records
    for record in unified_business.raw_records:
        if record.last_filing_date:
            try:
                filing_date = _parse_date(record.last_filing_date)
                if filing_date and (latest_activity is None or filing_date > latest_activity):
                    latest_activity = filing_date
            except (ValueError, TypeError):
                pass

    # Determine status
    if has_closure_event:
        status = LifecycleStatus.CLOSED
        reasoning_parts.append("Closure signal detected — marked as CLOSED")
    elif latest_activity:
        months_since = (now - latest_activity).days / 30.0
        if months_since <= ACTIVE_MONTHS:
            status = LifecycleStatus.ACTIVE
            reasoning_parts.append(
                f"Last activity {months_since:.0f} months ago (within {ACTIVE_MONTHS}m threshold) — ACTIVE"
            )
        elif months_since <= DORMANT_MONTHS:
            status = LifecycleStatus.DORMANT
            reasoning_parts.append(
                f"Last activity {months_since:.0f} months ago (>{ACTIVE_MONTHS}m, <{DORMANT_MONTHS}m) — DORMANT"
            )
        else:
            status = LifecycleStatus.CLOSED
            reasoning_parts.append(
                f"No activity in {months_since:.0f} months (>{DORMANT_MONTHS}m) — CLOSED"
            )
    else:
        status = LifecycleStatus.UNKNOWN
        reasoning_parts.append("No activity data available — status UNKNOWN, needs manual review")

    # Check for conflicting signals
    source_statuses = set()
    for record in unified_business.raw_records:
        if record.status_in_source:
            source_statuses.add(record.status_in_source.lower())

    has_active = any("active" in s for s in source_statuses)
    has_inactive = any(
        any(signal in s for signal in CLOSURE_SIGNALS)
        for s in source_statuses
    )

    if has_active and has_inactive:
        reasoning_parts.append(
            "CONFLICT: Active in some systems, inactive/closed in others — flagged for review"
        )
        # Don't override to UNKNOWN — keep the inferred status but flag the conflict

    reasoning = " | ".join(reasoning_parts)

    # Update the entity
    unified_business.lifecycle_status = status
    unified_business.lifecycle_reasoning = reasoning
    unified_business.lifecycle_updated_at = now
    db.commit()

    return {
        "ubid": unified_business.ubid,
        "status": status,
        "reasoning": reasoning,
        "latest_activity": latest_activity.isoformat() if latest_activity else None,
        "has_conflict": has_active and has_inactive,
    }


def update_all_lifecycle_statuses(db: Session) -> dict:
    """Run lifecycle inference for all unified businesses."""
    entities = db.query(UnifiedBusiness).all()
    results = {"active": 0, "dormant": 0, "closed": 0, "unknown": 0}

    for entity in entities:
        result = infer_lifecycle_status(entity, db)
        results[result["status"].value] += 1

    return results


def _parse_date(date_str: str) -> datetime | None:
    """Try to parse a date string in common Indian formats."""
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d %b %Y",
        "%d-%b-%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
