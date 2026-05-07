"""
Demo reset — wipes all data so you can demo the upload flow from empty state.

Run BEFORE recording the demo if you want to show:
  1. Empty dashboard (0 records, 0 UBIDs)
  2. Drag-drop GST.csv → counts update
  3. Drag-drop MCA.csv + Udyam.csv → counts update
  4. Click "Run Resolution" → 685 UBIDs appear
  5. Click "Smart Query" → killer query returns results

After: re-run `python seed_realistic_events.py` to repopulate lifecycle events
       (entity resolution alone doesn't create them).

Usage:
  source .venv/bin/activate && python reset_for_demo.py
"""

from app.database import SessionLocal
from app.models import (
    LifecycleEvent,
    LinkageResult,
    RawBusinessRecord,
    ReviewDecision,
    UnifiedBusiness,
)


def main() -> None:
    db = SessionLocal()
    # Order matters because of foreign keys
    db.query(LifecycleEvent).delete()
    db.query(ReviewDecision).delete()
    db.query(LinkageResult).delete()
    # Detach raw records from UBIDs first (FK constraint)
    db.query(RawBusinessRecord).update({"unified_business_id": None})
    db.query(UnifiedBusiness).delete()
    db.query(RawBusinessRecord).delete()
    db.commit()
    print("✓ Database wiped — ready to demo upload flow.")
    print("  Next steps for the demo:")
    print("  1. http://localhost:5173 → drag synthetic_businesses_gst.csv onto upload (source=GST)")
    print("  2. Repeat with MCA and Udyam CSVs")
    print("  3. Click 'Run Resolution' → 685 UBIDs appear")
    print("  4. Run `python seed_realistic_events.py` to add lifecycle events")
    print("  5. Visit /insights and click 'Active factories without recent inspection'")
    db.close()


if __name__ == "__main__":
    main()
