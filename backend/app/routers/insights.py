"""
Smart-query endpoint — cross-cutting queries on resolved entities.

Implements the brief's killer use case verbatim:
  "active factories in pin code 560058 with no inspection in the last 18 months"

This is the kind of query Karnataka Commerce & Industries cannot run today
because data is fragmented across 40+ siloed department systems. Once UBIDs
exist and lifecycle is inferred, this becomes a single SQL query.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    LifecycleEvent,
    LifecycleStatus,
    RawBusinessRecord,
    UnifiedBusiness,
)
from app.services.llm_narration import _has_llm, _hash_key, _read_cache, _write_cache, _raw_llm

router = APIRouter()


def _last_event_iso(events) -> str | None:
    """Return ISO timestamp of latest event date, regardless of tz-awareness."""
    dates = [ev.event_date for ev in events if ev.event_date]
    if not dates:
        return None
    naive = [d.replace(tzinfo=None) if d.tzinfo else d for d in dates]
    return max(naive).isoformat()


def _summarise_results(query_params: dict, total: int, sample_names: list[str]) -> str:
    """AI summary of query findings — grounded on counts + sample names only."""
    cache_key = f"insights_{_hash_key({**query_params, 'total': total})}"
    cached = _read_cache(cache_key)
    if cached:
        return cached

    if not _has_llm():
        if total == 0:
            return "No businesses match these criteria. Consider widening the filters."
        return (
            f"Query returned {total} business{'es' if total != 1 else ''}. "
            f"Examples: {', '.join(sample_names[:3])}{' ...' if total > 3 else ''}."
        )

    system = (
        "You are a Karnataka Commerce & Industries data analyst summarising a cross-system query result.\n"
        "Write 2 sentences:\n"
        "1. State the count and what the query asked (translate filter names to plain language).\n"
        "2. Recommend a follow-up — for ACTIVE+no-event queries: dispatch inspection priorities; for "
        "DORMANT or CLOSED: data-quality verification or strike-off processing.\n"
        "Use specific filter values. Do not invent business names. Under 50 words."
    )
    payload = {
        "filters": query_params,
        "total_matches": total,
        "sample_names": sample_names[:5],
    }
    try:
        text = _raw_llm(system, str(payload), max_tokens=160)
        _write_cache(cache_key, text)
        return text
    except Exception:
        return (
            f"{total} businesses match. Filters: "
            f"{', '.join(f'{k}={v}' for k, v in query_params.items() if v not in (None, ''))}."
        )


@router.get("/query")
def smart_query(
    status: Optional[str] = Query(None, description="active / dormant / closed / unknown"),
    pincode: Optional[str] = Query(None, description="6-digit pincode"),
    sector: Optional[str] = Query(None, description="manufacturing / services / trading / etc"),
    business_type: Optional[str] = Query(None, description="factories / shop / pvt_ltd / partnership"),
    event_type: Optional[str] = Query(None, description="inspection / renewal / filing / payment"),
    no_event_since_months: Optional[int] = Query(
        None, description="Find businesses with NO event of given type in this many months"
    ),
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
):
    """Cross-cutting query across resolved entities + lifecycle events.

    Example call (the brief's own scenario):
      /api/unified/insights/query?status=active&pincode=560058&business_type=factories&event_type=inspection&no_event_since_months=18
    """
    q = db.query(UnifiedBusiness)

    if status:
        try:
            q = q.filter(UnifiedBusiness.lifecycle_status == LifecycleStatus(status.lower()))
        except ValueError:
            pass

    if pincode:
        q = q.filter(UnifiedBusiness.canonical_pincode == pincode)

    # sector / business_type must come from joined raw_records (not stored on UnifiedBusiness)
    if sector or business_type:
        sub = db.query(RawBusinessRecord.unified_business_id).filter(
            RawBusinessRecord.unified_business_id.isnot(None)
        )
        if sector:
            sub = sub.filter(RawBusinessRecord.sector.ilike(f"%{sector}%"))
        if business_type:
            sub = sub.filter(
                or_(
                    RawBusinessRecord.business_type.ilike(f"%{business_type}%"),
                    RawBusinessRecord.sector.ilike(f"%{business_type}%"),
                )
            )
        sub_ids = {row[0] for row in sub.all() if row[0]}
        q = q.filter(UnifiedBusiness.id.in_(sub_ids))

    candidates = q.all()

    # No-event-since filter: in-memory because event_date is stored as DateTime per row
    if event_type and no_event_since_months:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30 * no_event_since_months)).replace(tzinfo=None)
        kept = []
        for ub in candidates:
            matching = [
                ev for ev in ub.lifecycle_events
                if ev.event_type and event_type.lower() in ev.event_type.lower()
            ]
            if not matching:
                # Never had this event type → also flag (no-recent = stricter)
                kept.append(ub)
                continue
            # Normalise event_date to naive UTC so comparison works across SQLite (naive) + new (aware) rows
            def _naive(dt):
                return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt
            most_recent = max(
                (_naive(ev.event_date) for ev in matching if ev.event_date),
                default=None,
            )
            if most_recent is None or most_recent < cutoff:
                kept.append(ub)
        candidates = kept

    total = len(candidates)
    sample_names = [c.canonical_name for c in candidates[:10] if c.canonical_name]

    rows = [
        {
            "ubid": c.ubid,
            "canonical_name": c.canonical_name,
            "canonical_pincode": c.canonical_pincode,
            "canonical_pan": c.canonical_pan,
            "lifecycle_status": c.lifecycle_status,
            "record_count": c.record_count,
            "last_event_date": (
                _last_event_iso(c.lifecycle_events)
            ),
        }
        for c in candidates[:limit]
    ]

    summary = _summarise_results(
        {
            "status": status,
            "pincode": pincode,
            "sector": sector,
            "business_type": business_type,
            "event_type": event_type,
            "no_event_since_months": no_event_since_months,
        },
        total,
        sample_names,
    )

    return {
        "total": total,
        "filters": {
            "status": status,
            "pincode": pincode,
            "sector": sector,
            "business_type": business_type,
            "event_type": event_type,
            "no_event_since_months": no_event_since_months,
        },
        "ai_summary": summary,
        "results": rows,
    }


@router.get("/preset/active-without-inspection")
def preset_active_without_inspection(
    pincode: Optional[str] = Query(None),
    months: int = Query(18),
    db: Session = Depends(get_db),
):
    """Convenience endpoint — exactly the brief's example query."""
    return smart_query(
        status="active",
        pincode=pincode,
        business_type="factories",
        event_type="inspection",
        no_event_since_months=months,
        db=db,
    )
