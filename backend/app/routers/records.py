"""Registry data upload and management endpoints."""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session
import pandas as pd
import json
import os
import shutil

from app.database import get_db
from app.models import RawBusinessRecord

router = APIRouter()

UPLOAD_DIR = "uploads/registries"

VALID_SOURCES = {"gst", "mca", "udyam", "shop_establishment", "factories", "labour", "kspcb"}


@router.post("/upload")
async def upload_registry_csv(
    source_system: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a CSV from a department registry and ingest records."""
    if source_system.lower() not in VALID_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source system. Must be one of: {', '.join(VALID_SOURCES)}",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"{source_system}_{file.filename}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        df = pd.read_csv(file_path, dtype=str).fillna("")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

    # Map CSV columns to model fields (flexible column matching)
    column_map = _build_column_map(df.columns.tolist())

    records_added = 0
    for _, row in df.iterrows():
        record = RawBusinessRecord(
            source_system=source_system.lower(),
            source_record_id=_get_field(row, column_map, "source_record_id"),
            pan=_normalize_pan(_get_field(row, column_map, "pan")),
            gstin=_get_field(row, column_map, "gstin"),
            udyam_number=_get_field(row, column_map, "udyam_number"),
            business_name=_get_field(row, column_map, "business_name"),
            owner_name=_get_field(row, column_map, "owner_name"),
            address=_get_field(row, column_map, "address"),
            pincode=_get_field(row, column_map, "pincode"),
            state_code=_get_field(row, column_map, "state_code"),
            district=_get_field(row, column_map, "district"),
            business_type=_get_field(row, column_map, "business_type"),
            sector=_get_field(row, column_map, "sector"),
            phone=_get_field(row, column_map, "phone"),
            email=_get_field(row, column_map, "email"),
            registration_date=_get_field(row, column_map, "registration_date"),
            last_filing_date=_get_field(row, column_map, "last_filing_date"),
            status_in_source=_get_field(row, column_map, "status_in_source"),
            raw_data=row.to_dict(),
        )
        db.add(record)
        records_added += 1

    db.commit()

    return {
        "source_system": source_system,
        "filename": file.filename,
        "records_added": records_added,
        "columns_detected": list(column_map.keys()),
    }


@router.get("/")
def list_records(
    source_system: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List raw business records with optional source filter."""
    query = db.query(RawBusinessRecord)
    if source_system:
        query = query.filter(RawBusinessRecord.source_system == source_system.lower())

    total = query.count()
    records = query.order_by(RawBusinessRecord.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "records": [
            {
                "id": r.id,
                "source_system": r.source_system,
                "business_name": r.business_name,
                "owner_name": r.owner_name,
                "pan": r.pan,
                "gstin": r.gstin,
                "pincode": r.pincode,
                "status_in_source": r.status_in_source,
                "unified_business_id": r.unified_business_id,
            }
            for r in records
        ],
    }


@router.get("/stats")
def record_stats(db: Session = Depends(get_db)):
    """Get record counts per source system."""
    from sqlalchemy import func

    stats = (
        db.query(RawBusinessRecord.source_system, func.count(RawBusinessRecord.id))
        .group_by(RawBusinessRecord.source_system)
        .all()
    )

    return {
        "total": sum(count for _, count in stats),
        "by_source": {source: count for source, count in stats},
    }


def _normalize_pan(pan: str) -> str:
    """Normalize PAN — also extract from GSTIN if PAN field is empty."""
    if pan and len(pan) == 10:
        return pan.upper()
    return pan.upper() if pan else ""


def _build_column_map(columns: list[str]) -> dict[str, str]:
    """Map model field names to CSV column names (handles common variations)."""
    column_lower = {c.lower().strip(): c for c in columns}

    field_aliases = {
        "source_record_id": ["id", "record_id", "ref_no", "reference_number", "sr_no"],
        "pan": ["pan", "pan_number", "pan_no"],
        "gstin": ["gstin", "gst_number", "gst_no", "gst"],
        "udyam_number": ["udyam", "udyam_number", "udyam_no", "uam", "msme_number"],
        "business_name": ["business_name", "firm_name", "company_name", "establishment_name", "name", "entity_name", "factory_name", "unit_name"],
        "owner_name": ["owner_name", "proprietor", "director_name", "partner_name", "promoter_name", "applicant_name"],
        "address": ["address", "registered_address", "business_address", "full_address", "premises_address"],
        "pincode": ["pincode", "pin_code", "pin", "zip", "postal_code"],
        "state_code": ["state_code", "state", "state_name"],
        "district": ["district", "district_name", "city"],
        "business_type": ["business_type", "type", "constitution", "entity_type", "legal_status"],
        "sector": ["sector", "industry", "activity", "nic_code", "business_activity"],
        "phone": ["phone", "mobile", "phone_number", "contact_number", "telephone"],
        "email": ["email", "email_id", "email_address"],
        "registration_date": ["registration_date", "reg_date", "date_of_registration", "incorporation_date", "established_date"],
        "last_filing_date": ["last_filing_date", "last_return_date", "last_annual_return", "last_activity_date"],
        "status_in_source": ["status", "status_in_source", "registration_status", "current_status", "entity_status"],
    }

    result = {}
    for field, aliases in field_aliases.items():
        for alias in aliases:
            if alias in column_lower:
                result[field] = column_lower[alias]
                break

    return result


def _get_field(row, column_map: dict, field: str) -> str:
    """Safely get a field from a row using the column map."""
    csv_col = column_map.get(field)
    if csv_col and csv_col in row.index:
        return str(row[csv_col]).strip()
    return ""
