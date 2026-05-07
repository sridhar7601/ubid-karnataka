"""Seed demo data for Theme 1: UBID Platform.

Loads the synthetic CSVs, runs entity resolution, and infers lifecycle statuses.
Pre-populates the database so the demo shows results immediately.

Usage:
    cd backend
    python ../demo/seed_demo.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database import init_db, SessionLocal
from app.models import RawBusinessRecord, UnifiedBusiness, LinkageResult, LifecycleEvent, ReviewDecision
import pandas as pd


DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')


def seed():
    init_db()
    db = SessionLocal()

    # Clear existing data
    db.query(ReviewDecision).delete()
    db.query(LifecycleEvent).delete()
    db.query(LinkageResult).delete()
    for r in db.query(RawBusinessRecord).all():
        r.unified_business_id = None
    db.commit()
    db.query(UnifiedBusiness).delete()
    db.query(RawBusinessRecord).delete()
    db.commit()

    # Load CSVs
    sources = {
        'gst': os.path.join(DATA_DIR, 'synthetic_businesses_gst.csv'),
        'mca': os.path.join(DATA_DIR, 'synthetic_businesses_mca.csv'),
        'udyam': os.path.join(DATA_DIR, 'synthetic_businesses_udyam.csv'),
    }

    total_loaded = 0
    for source, path in sources.items():
        if not os.path.exists(path):
            print(f"  WARNING: {path} not found, skipping")
            continue

        df = pd.read_csv(path, dtype=str).fillna('')
        count = 0

        for _, row in df.iterrows():
            record = RawBusinessRecord(
                source_system=source,
                business_name=_get(row, ['business_name', 'company_name', 'enterprise_name']),
                owner_name=_get(row, ['proprietor', 'director_name', 'applicant_name']),
                pan=_get(row, ['pan', 'pan_number']),
                gstin=_get(row, ['gstin', 'gst_number']),
                udyam_number=_get(row, ['udyam_number']),
                address=_get(row, ['registered_address', 'full_address', 'premises_address']),
                pincode=_get(row, ['pin_code', 'pincode', 'pin']),
                state_code=_get(row, ['state', 'state_name']),
                district=_get(row, ['district_name', 'district', 'city']),
                business_type=_get(row, ['constitution', 'entity_type']),
                sector=_get(row, ['business_activity', 'industry', 'activity']),
                phone=_get(row, ['contact_number', 'mobile']),
                email=_get(row, ['email_id', 'email_address']),
                registration_date=_get(row, ['date_of_registration', 'incorporation_date', 'established_date']),
                last_filing_date=_get(row, ['last_return_date', 'last_annual_return', 'last_activity_date']),
                status_in_source=_get(row, ['registration_status', 'current_status', 'entity_status']),
                raw_data=row.to_dict(),
            )
            db.add(record)
            count += 1

        db.commit()
        total_loaded += count
        print(f"  Loaded {count} records from {source}")

    print(f"\nTotal records loaded: {total_loaded}")

    # Run entity resolution
    print("\nRunning entity resolution...")
    from app.services.splink_linker import run_entity_resolution
    result = run_entity_resolution(db)
    print(f"  Unified entities: {result['unified_count']}")
    print(f"  Auto-linked records: {result['auto_linked']}")
    print(f"  Pending review: {result['pending_review']}")
    print(f"  Kept separate: {result['kept_separate']}")

    # Run lifecycle inference
    print("\nInferring lifecycle statuses...")
    from app.services.lifecycle import update_all_lifecycle_statuses
    lifecycle = update_all_lifecycle_statuses(db)
    print(f"  Active: {lifecycle.get('active', 0)}")
    print(f"  Dormant: {lifecycle.get('dormant', 0)}")
    print(f"  Closed: {lifecycle.get('closed', 0)}")
    print(f"  Unknown: {lifecycle.get('unknown', 0)}")

    db.close()
    print("\nDemo data seeded successfully!")
    print("Start the backend: uvicorn main:app --reload --port 8001")


def _get(row, field_names):
    """Try multiple field names, return first non-empty match."""
    for name in field_names:
        if name in row.index and str(row[name]).strip():
            return str(row[name]).strip()
    return ''


if __name__ == "__main__":
    seed()
