"""Unified business entity endpoints — UBID lookup and lifecycle."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import UnifiedBusiness, LifecycleStatus

router = APIRouter()


@router.get("/")
def list_unified_businesses(
    status: str | None = None,
    pincode: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List unified business entities with optional filters.

    Enables queries like: 'active factories in pincode 560058 with no recent inspection'
    """
    query = db.query(UnifiedBusiness)

    if status:
        query = query.filter(UnifiedBusiness.lifecycle_status == LifecycleStatus(status))
    if pincode:
        query = query.filter(UnifiedBusiness.canonical_pincode == pincode)
    if search:
        query = query.filter(
            UnifiedBusiness.canonical_name.ilike(f"%{search}%")
            | UnifiedBusiness.ubid.ilike(f"%{search}%")
            | UnifiedBusiness.canonical_pan.ilike(f"%{search}%")
            | UnifiedBusiness.canonical_gstin.ilike(f"%{search}%")
        )

    total = query.count()
    entities = query.order_by(UnifiedBusiness.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "entities": [
            {
                "id": e.id,
                "ubid": e.ubid,
                "canonical_name": e.canonical_name,
                "canonical_pincode": e.canonical_pincode,
                "canonical_pan": e.canonical_pan,
                "canonical_gstin": e.canonical_gstin,
                "lifecycle_status": e.lifecycle_status,
                "record_count": e.record_count,
                "avg_match_score": e.avg_match_score,
            }
            for e in entities
        ],
    }


@router.get("/{ubid}")
def get_unified_business(ubid: str, db: Session = Depends(get_db)):
    """Get full entity profile for a UBID — all linked records and lifecycle."""
    entity = db.query(UnifiedBusiness).filter(
        (UnifiedBusiness.ubid == ubid) | (UnifiedBusiness.id == ubid)
    ).first()

    if not entity:
        raise HTTPException(status_code=404, detail="Unified business not found")

    return {
        "id": entity.id,
        "ubid": entity.ubid,
        "canonical_name": entity.canonical_name,
        "canonical_address": entity.canonical_address,
        "canonical_pincode": entity.canonical_pincode,
        "canonical_pan": entity.canonical_pan,
        "canonical_gstin": entity.canonical_gstin,
        "lifecycle_status": entity.lifecycle_status,
        "lifecycle_reasoning": entity.lifecycle_reasoning,
        "record_count": entity.record_count,
        "linked_records": [
            {
                "id": r.id,
                "source_system": r.source_system,
                "source_record_id": r.source_record_id,
                "business_name": r.business_name,
                "owner_name": r.owner_name,
                "pan": r.pan,
                "gstin": r.gstin,
                "address": r.address,
                "pincode": r.pincode,
                "status_in_source": r.status_in_source,
                "registration_date": r.registration_date,
                "last_filing_date": r.last_filing_date,
            }
            for r in entity.raw_records
        ],
        "lifecycle_events": [
            {
                "id": ev.id,
                "event_type": ev.event_type,
                "event_source": ev.event_source,
                "event_date": ev.event_date.isoformat() if ev.event_date else None,
                "description": ev.description,
            }
            for ev in entity.lifecycle_events
        ],
    }


@router.get("/{ubid}/lifecycle")
def get_lifecycle_timeline(ubid: str, db: Session = Depends(get_db)):
    """Get lifecycle event timeline for a unified business."""
    entity = db.query(UnifiedBusiness).filter(
        (UnifiedBusiness.ubid == ubid) | (UnifiedBusiness.id == ubid)
    ).first()

    if not entity:
        raise HTTPException(status_code=404, detail="Unified business not found")

    return {
        "ubid": entity.ubid,
        "current_status": entity.lifecycle_status,
        "reasoning": entity.lifecycle_reasoning,
        "events": [
            {
                "event_type": ev.event_type,
                "event_source": ev.event_source,
                "event_date": ev.event_date.isoformat() if ev.event_date else None,
                "description": ev.description,
            }
            for ev in sorted(entity.lifecycle_events, key=lambda e: e.event_date or e.created_at, reverse=True)
        ],
    }
