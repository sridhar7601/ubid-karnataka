"""
Seed realistic lifecycle events + business-type tags for demo realism.

Problem solved: out-of-the-box DB had 0 lifecycle events and no factories,
so the brief's killer query ('active factories in 560058 with no inspection
in last 18 months') returned 0. After this script, that query returns
~5-10 hits and other queries get realistic event timelines.

Run:  source .venv/bin/activate && python seed_realistic_events.py
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models import (
    LifecycleEvent,
    LifecycleStatus,
    RawBusinessRecord,
    UnifiedBusiness,
)

random.seed(42)  # deterministic demo

EVENT_TYPES = [
    ("inspection", "BBMP / Factory Inspector", "Routine compliance inspection"),
    ("renewal", "Shop Establishment Dept", "Trade licence renewal"),
    ("filing", "GST Network", "Monthly GSTR-3B filing"),
    ("payment", "BESCOM", "Electricity bill paid"),
    ("audit", "KSPCB", "Pollution-control consent renewal"),
]

# Pincodes to deliberately under-inspect (drive the brief's killer query)
KILLER_QUERY_PINCODES = ["560058", "560048", "560043"]


def _random_event_date(now: datetime, max_months_ago: int) -> datetime:
    days_ago = random.randint(0, max_months_ago * 30)
    return now - timedelta(days=days_ago)


def main() -> None:
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    # 1. Re-tag some businesses to be factories (the brief's example uses "factories")
    # Pick ~30% of businesses with sector in {manufacturing, construction, technology} → factory
    candidates = (
        db.query(RawBusinessRecord)
        .filter(RawBusinessRecord.sector.in_(["manufacturing", "construction", "technology"]))
        .all()
    )
    factory_count = 0
    for rec in candidates:
        if random.random() < 0.45:
            rec.business_type = "factory"
            factory_count += 1
    db.commit()
    print(f"[1/3] Re-tagged {factory_count} businesses as 'factory'")

    # 2. Generate lifecycle events for every UBID
    db.query(LifecycleEvent).delete()
    db.commit()

    ubids = db.query(UnifiedBusiness).all()
    event_count = 0
    no_recent_inspection_in_killer_zones = 0

    for ub in ubids:
        is_killer_pincode = ub.canonical_pincode in KILLER_QUERY_PINCODES
        is_active = ub.lifecycle_status == LifecycleStatus.ACTIVE

        # Determine event density by status
        if ub.lifecycle_status == LifecycleStatus.CLOSED:
            n_events = random.randint(2, 4)  # historical events, then closure
        elif ub.lifecycle_status == LifecycleStatus.DORMANT:
            n_events = random.randint(1, 3)
        elif ub.lifecycle_status == LifecycleStatus.ACTIVE:
            n_events = random.randint(3, 7)
        else:
            n_events = random.randint(0, 2)

        # Decide if this active+factory in killer pincode should be "no recent inspection"
        skip_recent_inspection = (
            is_active
            and is_killer_pincode
            and any(r.business_type == "factory" for r in ub.raw_records)
            and random.random() < 0.6  # 60% of active factories in killer pincodes are under-inspected
        )
        if skip_recent_inspection:
            no_recent_inspection_in_killer_zones += 1

        for _ in range(n_events):
            event_type, source, desc_template = random.choice(EVENT_TYPES)

            # Compute date — for "skip_recent_inspection" cases, push inspections past 18 months
            if skip_recent_inspection and event_type == "inspection":
                event_date = _random_event_date(now, 36) - timedelta(days=540)  # >18 months ago
            elif ub.lifecycle_status == LifecycleStatus.CLOSED:
                event_date = _random_event_date(now, 36) - timedelta(days=720)
            elif ub.lifecycle_status == LifecycleStatus.DORMANT:
                event_date = _random_event_date(now, 30) - timedelta(days=365)
            elif ub.lifecycle_status == LifecycleStatus.ACTIVE:
                event_date = _random_event_date(now, 14)
            else:
                event_date = _random_event_date(now, 24)

            ev = LifecycleEvent(
                unified_business_id=ub.id,
                event_type=event_type,
                event_source=source,
                event_date=event_date,
                description=f"{desc_template} for {ub.canonical_name}",
            )
            db.add(ev)
            event_count += 1

        # Closed businesses get an explicit closure marker
        if ub.lifecycle_status == LifecycleStatus.CLOSED:
            db.add(
                LifecycleEvent(
                    unified_business_id=ub.id,
                    event_type="closure",
                    event_source="MCA",
                    event_date=now - timedelta(days=random.randint(180, 720)),
                    description="Struck off — MCA registry",
                )
            )
            event_count += 1

    db.commit()
    print(f"[2/3] Generated {event_count} lifecycle events across {len(ubids)} UBIDs")
    print(f"[3/3] {no_recent_inspection_in_killer_zones} active factories in killer pincodes "
          f"({', '.join(KILLER_QUERY_PINCODES)}) have NO inspection in last 18 months")
    print(f"\n→ The brief's killer query should now return {no_recent_inspection_in_killer_zones} results.")

    db.close()


if __name__ == "__main__":
    main()
