"""Entity resolution (linkage) endpoints — run Splink and review matches."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    RawBusinessRecord, UnifiedBusiness, LinkageResult,
    LinkageStatus, MatchConfidence,
)
from app.services.splink_linker import run_entity_resolution

router = APIRouter()


@router.post("/run")
async def run_linkage(db: Session = Depends(get_db)):
    """Run entity resolution across all uploaded registry records.

    Uses Splink for probabilistic record linkage with IndicSoundex blocking.
    High-confidence matches are auto-linked; ambiguous matches go to review.
    """
    record_count = db.query(RawBusinessRecord).count()
    if record_count == 0:
        raise HTTPException(status_code=400, detail="No records uploaded yet")

    result = run_entity_resolution(db)

    return {
        "input_records": record_count,
        "unified_entities": result["unified_count"],
        "auto_linked": result["auto_linked"],
        "pending_review": result["pending_review"],
        "kept_separate": result["kept_separate"],
    }


@router.get("/results")
def get_linkage_results(
    confidence: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get pairwise linkage results with optional filters."""
    query = db.query(LinkageResult)

    if confidence:
        query = query.filter(LinkageResult.confidence == MatchConfidence(confidence))
    if status:
        query = query.filter(LinkageResult.status == LinkageStatus(status))

    total = query.count()
    results = query.order_by(LinkageResult.match_score.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "results": [
            {
                "id": r.id,
                "record_a": {
                    "id": r.record_a.id,
                    "source": r.record_a.source_system,
                    "name": r.record_a.business_name,
                    "pan": r.record_a.pan,
                },
                "record_b": {
                    "id": r.record_b.id,
                    "source": r.record_b.source_system,
                    "name": r.record_b.business_name,
                    "pan": r.record_b.pan,
                },
                "match_score": r.match_score,
                "confidence": r.confidence,
                "status": r.status,
                "match_details": r.match_details,
            }
            for r in results
        ],
    }


@router.put("/{linkage_id}/review")
def review_linkage(
    linkage_id: str,
    decision: str,  # "confirm" or "reject"
    notes: str = "",
    db: Session = Depends(get_db),
):
    """Human reviewer confirms or rejects an ambiguous linkage."""
    from app.models import ReviewDecision

    linkage = db.query(LinkageResult).filter(LinkageResult.id == linkage_id).first()
    if not linkage:
        raise HTTPException(status_code=404, detail="Linkage result not found")

    if decision not in ("confirm", "reject"):
        raise HTTPException(status_code=400, detail="Decision must be 'confirm' or 'reject'")

    linkage.status = LinkageStatus.CONFIRMED if decision == "confirm" else LinkageStatus.REJECTED

    review = ReviewDecision(
        linkage_result_id=linkage_id,
        decision=decision,
        reviewer_notes=notes,
    )
    db.add(review)
    db.commit()

    return {
        "linkage_id": linkage_id,
        "new_status": linkage.status,
        "decision": decision,
    }


@router.get("/{linkage_id}/explain-llm")
def explain_linkage_with_llm(linkage_id: str, db: Session = Depends(get_db)):
    """AI-grounded linkage justification (Azure GPT-4.1).

    Describes the strongest match feature (PAN, GSTIN, name fuzzy, address) and
    recommends auto-link / review / reject. All fields come from the persisted
    match_details — LLM never invents scores.
    """
    from app.services.llm_narration import explain_linkage

    link = db.query(LinkageResult).filter(LinkageResult.id == linkage_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Linkage result not found")

    md = link.match_details or {}
    payload = {
        "link_id": link.id,
        "score": link.match_score,
        "confidence": link.confidence,
        "record_a": {
            "name": link.record_a.business_name if link.record_a else None,
            "address": link.record_a.address if link.record_a else None,
            "pincode": link.record_a.pincode if link.record_a else None,
            "pan": link.record_a.pan if link.record_a else None,
            "gstin": link.record_a.gstin if link.record_a else None,
            "source": link.record_a.source_system if link.record_a else None,
        },
        "record_b": {
            "name": link.record_b.business_name if link.record_b else None,
            "address": link.record_b.address if link.record_b else None,
            "pincode": link.record_b.pincode if link.record_b else None,
            "pan": link.record_b.pan if link.record_b else None,
            "gstin": link.record_b.gstin if link.record_b else None,
            "source": link.record_b.source_system if link.record_b else None,
        },
        "features": md,
    }

    return {
        "linkage_id": link.id,
        "ai_narration": explain_linkage(payload),
        "score": link.match_score,
        "confidence": link.confidence,
    }
