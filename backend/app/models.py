"""Database models for UBID entity resolution and lifecycle intelligence."""

from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
import uuid

from app.database import Base


def gen_id():
    return str(uuid.uuid4())


class MatchConfidence(str, enum.Enum):
    HIGH = "high"        # >0.9 — auto-link
    MEDIUM = "medium"    # 0.7–0.9 — human review
    LOW = "low"          # <0.7 — keep separate


class LifecycleStatus(str, enum.Enum):
    ACTIVE = "active"
    DORMANT = "dormant"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class LinkageStatus(str, enum.Enum):
    AUTO_LINKED = "auto_linked"
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class RawBusinessRecord(Base):
    """Raw record from a department system (GST, MCA, Udyam, etc.)."""
    __tablename__ = "raw_business_records"

    id = Column(String, primary_key=True, default=gen_id)
    source_system = Column(String, nullable=False)  # gst, mca, udyam, shop_establishment, etc.
    source_record_id = Column(String)  # Original ID in source system

    # Business identifiers (may be missing)
    pan = Column(String)
    gstin = Column(String)
    udyam_number = Column(String)

    # Business details
    business_name = Column(String)
    owner_name = Column(String)
    address = Column(Text)
    pincode = Column(String)
    state_code = Column(String)
    district = Column(String)
    business_type = Column(String)  # proprietorship, partnership, pvt_ltd, etc.
    sector = Column(String)  # manufacturing, services, trading
    phone = Column(String)
    email = Column(String)
    registration_date = Column(String)
    last_filing_date = Column(String)
    status_in_source = Column(String)  # active, cancelled, struck_off, etc.

    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    raw_data = Column(JSON)  # Original CSV row as JSON for audit

    # Linkage
    unified_business_id = Column(String, ForeignKey("unified_businesses.id"), nullable=True)
    unified_business = relationship("UnifiedBusiness", back_populates="raw_records")


class UnifiedBusiness(Base):
    """Unified entity with a UBID — represents one real-world business."""
    __tablename__ = "unified_businesses"

    id = Column(String, primary_key=True, default=gen_id)
    ubid = Column(String, unique=True, nullable=False)  # UBID-KA-XXXXXXXX

    # Canonical (best-guess) details
    canonical_name = Column(String)
    canonical_address = Column(Text)
    canonical_pincode = Column(String)
    canonical_pan = Column(String)
    canonical_gstin = Column(String)

    # Lifecycle
    lifecycle_status = Column(Enum(LifecycleStatus), default=LifecycleStatus.UNKNOWN)
    lifecycle_reasoning = Column(Text)  # Explainable justification
    lifecycle_updated_at = Column(DateTime)

    # Stats
    record_count = Column(Integer, default=0)  # How many raw records linked
    avg_match_score = Column(Float)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    raw_records = relationship("RawBusinessRecord", back_populates="unified_business")
    linkage_results = relationship("LinkageResult", back_populates="unified_business", cascade="all, delete-orphan")
    lifecycle_events = relationship("LifecycleEvent", back_populates="unified_business", cascade="all, delete-orphan")


class LinkageResult(Base):
    """Pairwise linkage result between two raw records."""
    __tablename__ = "linkage_results"

    id = Column(String, primary_key=True, default=gen_id)
    unified_business_id = Column(String, ForeignKey("unified_businesses.id"), nullable=True)

    record_a_id = Column(String, ForeignKey("raw_business_records.id"), nullable=False)
    record_b_id = Column(String, ForeignKey("raw_business_records.id"), nullable=False)

    match_score = Column(Float, nullable=False)  # Splink match weight (0–1)
    confidence = Column(Enum(MatchConfidence), nullable=False)
    status = Column(Enum(LinkageStatus), default=LinkageStatus.PENDING_REVIEW)

    # Explainability — which fields contributed to the match
    match_details = Column(JSON)  # {"name_similarity": 0.92, "address_similarity": 0.85, "pan_match": true, ...}

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    unified_business = relationship("UnifiedBusiness", back_populates="linkage_results")
    record_a = relationship("RawBusinessRecord", foreign_keys=[record_a_id])
    record_b = relationship("RawBusinessRecord", foreign_keys=[record_b_id])


class LifecycleEvent(Base):
    """Activity event for a unified business — drives Active/Dormant/Closed inference."""
    __tablename__ = "lifecycle_events"

    id = Column(String, primary_key=True, default=gen_id)
    unified_business_id = Column(String, ForeignKey("unified_businesses.id"), nullable=False)

    event_type = Column(String, nullable=False)  # inspection, renewal, filing, consumption_data, deregistration
    event_source = Column(String)  # Which department system
    event_date = Column(DateTime)
    description = Column(Text)
    raw_data = Column(JSON)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    unified_business = relationship("UnifiedBusiness", back_populates="lifecycle_events")


class ReviewDecision(Base):
    """Human reviewer decision on an ambiguous linkage — feeds back into the system."""
    __tablename__ = "review_decisions"

    id = Column(String, primary_key=True, default=gen_id)
    linkage_result_id = Column(String, ForeignKey("linkage_results.id"), nullable=False)
    decision = Column(String, nullable=False)  # confirm, reject
    reviewer_notes = Column(Text)
    decided_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    linkage_result = relationship("LinkageResult")
