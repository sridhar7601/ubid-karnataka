"""Dashboard rollup endpoints — KPIs + AI briefing."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import (
    RawBusinessRecord,
    UnifiedBusiness,
    LinkageResult,
    LinkageStatus,
    LifecycleStatus,
)
from app.services.llm_narration import generate_dashboard_briefing

router = APIRouter()


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    """Aggregate KPI snapshot + AI briefing for the home dashboard."""
    total_records = db.query(RawBusinessRecord).count()
    by_source = dict(
        db.query(RawBusinessRecord.source_system, func.count(RawBusinessRecord.id))
        .group_by(RawBusinessRecord.source_system)
        .all()
    )
    unified_count = db.query(UnifiedBusiness).count()

    auto_linked = (
        db.query(LinkageResult).filter(LinkageResult.status == LinkageStatus.AUTO_LINKED).count()
    )
    pending_review = (
        db.query(LinkageResult).filter(LinkageResult.status == LinkageStatus.PENDING_REVIEW).count()
    )
    confirmed = (
        db.query(LinkageResult).filter(LinkageResult.status == LinkageStatus.CONFIRMED).count()
    )
    rejected = (
        db.query(LinkageResult).filter(LinkageResult.status == LinkageStatus.REJECTED).count()
    )

    active = db.query(UnifiedBusiness).filter(UnifiedBusiness.lifecycle_status == LifecycleStatus.ACTIVE).count()
    dormant = db.query(UnifiedBusiness).filter(UnifiedBusiness.lifecycle_status == LifecycleStatus.DORMANT).count()
    closed = db.query(UnifiedBusiness).filter(UnifiedBusiness.lifecycle_status == LifecycleStatus.CLOSED).count()
    unknown = db.query(UnifiedBusiness).filter(UnifiedBusiness.lifecycle_status == LifecycleStatus.UNKNOWN).count()

    pan_anchored = db.query(UnifiedBusiness).filter(UnifiedBusiness.canonical_pan.isnot(None)).count()
    gstin_anchored = db.query(UnifiedBusiness).filter(UnifiedBusiness.canonical_gstin.isnot(None)).count()

    stats = {
        "total_records": total_records,
        "by_source": by_source,
        "unified_count": unified_count,
        "auto_linked": auto_linked,
        "pending_review": pending_review,
        "confirmed": confirmed,
        "rejected": rejected,
        "active": active,
        "dormant": dormant,
        "closed": closed,
        "unknown": unknown,
        "pan_anchored": pan_anchored,
        "gstin_anchored": gstin_anchored,
    }

    briefing = generate_dashboard_briefing(stats)

    return {
        **stats,
        "briefing": briefing,
        "anchor_coverage_pct": round(
            ((pan_anchored + gstin_anchored) / max(unified_count * 2, 1)) * 100, 1
        ),
    }
