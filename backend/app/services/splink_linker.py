"""Core entity resolution pipeline using Splink.

Pipeline:
1. Load all raw records into a pandas DataFrame
2. Apply IndicSoundex for phonetic blocking keys
3. Deterministic tier: exact PAN/GSTIN match
4. Probabilistic tier: Splink with Jaro-Winkler on name, token sort on address
5. Cluster matched pairs into unified entities
6. Assign UBIDs anchored to PAN/GSTIN where available
"""

import hashlib
import logging
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

from app.models import (
    RawBusinessRecord, UnifiedBusiness, LinkageResult,
    MatchConfidence, LinkageStatus, LifecycleStatus,
)

logger = logging.getLogger(__name__)

# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.9   # Auto-link
MEDIUM_CONFIDENCE_THRESHOLD = 0.7  # Route to human review
# Below 0.7 = keep separate


def run_entity_resolution(db: Session) -> dict:
    """Run the full entity resolution pipeline.

    Returns summary dict with counts of unified entities, auto-linked, etc.
    """
    # Step 1: Load all raw records
    records = db.query(RawBusinessRecord).all()
    if not records:
        return {"unified_count": 0, "auto_linked": 0, "pending_review": 0, "kept_separate": 0}

    df = _records_to_dataframe(records)
    logger.info(f"Loaded {len(df)} records for entity resolution")

    # Step 2: Extract PAN from GSTIN where PAN is missing
    df["pan"] = df.apply(_extract_pan, axis=1)

    # Step 3: Deterministic matching (exact PAN/GSTIN)
    deterministic_pairs = _deterministic_match(df)
    logger.info(f"Deterministic matching found {len(deterministic_pairs)} pairs")

    # Step 4: Probabilistic matching (Splink or fallback to rapidfuzz)
    probabilistic_pairs = _probabilistic_match(df)
    logger.info(f"Probabilistic matching found {len(probabilistic_pairs)} pairs")

    # Step 5: Merge and deduplicate pairs
    all_pairs = _merge_pairs(deterministic_pairs, probabilistic_pairs)
    logger.info(f"Total unique pairs: {len(all_pairs)}")

    # Step 6: Cluster into unified entities
    clusters = _cluster_pairs(all_pairs, len(df), df)

    # Step 7: Create UnifiedBusiness and LinkageResult records
    stats = _persist_results(db, df, clusters, all_pairs, records)

    return stats


def _records_to_dataframe(records: list[RawBusinessRecord]) -> pd.DataFrame:
    """Convert SQLAlchemy records to a pandas DataFrame."""
    data = []
    for r in records:
        data.append({
            "record_id": r.id,
            "source_system": r.source_system,
            "business_name": (r.business_name or "").upper().strip(),
            "owner_name": (r.owner_name or "").upper().strip(),
            "address": (r.address or "").upper().strip(),
            "pincode": (r.pincode or "").strip(),
            "state_code": (r.state_code or "").strip(),
            "pan": (r.pan or "").upper().strip(),
            "gstin": (r.gstin or "").upper().strip(),
            "udyam_number": (r.udyam_number or "").upper().strip(),
            "phone": _normalize_phone(r.phone or ""),
            "registration_date": r.registration_date or "",
            "last_filing_date": r.last_filing_date or "",
            "status_in_source": (r.status_in_source or "").lower(),
        })
    return pd.DataFrame(data)


def _normalize_phone(phone: str) -> str:
    """Normalize phone to last 10 digits."""
    digits = "".join(c for c in phone if c.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


def _extract_pan(row) -> str:
    """Extract PAN from GSTIN (characters 3-12) if PAN is missing."""
    if row["pan"] and len(row["pan"]) == 10:
        return row["pan"]
    if row["gstin"] and len(row["gstin"]) == 15:
        return row["gstin"][2:12]
    return row["pan"]


def _deterministic_match(df: pd.DataFrame) -> list[dict]:
    """Tier 1: Exact match on PAN or GSTIN."""
    pairs = []

    # Match on PAN
    pan_groups = df[df["pan"].str.len() == 10].groupby("pan")
    for pan, group in pan_groups:
        if len(group) < 2:
            continue
        ids = group["record_id"].tolist()
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                pairs.append({
                    "record_a_id": ids[i],
                    "record_b_id": ids[j],
                    "match_score": 1.0,
                    "match_type": "deterministic_pan",
                    "match_details": {"pan_match": True, "matched_pan": pan},
                })

    # Match on GSTIN
    gstin_groups = df[df["gstin"].str.len() == 15].groupby("gstin")
    for gstin, group in gstin_groups:
        if len(group) < 2:
            continue
        ids = group["record_id"].tolist()
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                pair_key = tuple(sorted([ids[i], ids[j]]))
                # Avoid duplicates from PAN matching
                if not any(
                    tuple(sorted([p["record_a_id"], p["record_b_id"]])) == pair_key
                    for p in pairs
                ):
                    pairs.append({
                        "record_a_id": ids[i],
                        "record_b_id": ids[j],
                        "match_score": 1.0,
                        "match_type": "deterministic_gstin",
                        "match_details": {"gstin_match": True, "matched_gstin": gstin},
                    })

    return pairs


def _probabilistic_match(df: pd.DataFrame) -> list[dict]:
    """Tier 2: Probabilistic matching using rapidfuzz (Splink integration comes in Week 2).

    Uses Jaro-Winkler on business name and token sort ratio on address.
    Blocks on pincode to keep comparisons manageable.
    """
    from rapidfuzz import fuzz

    pairs = []
    # Block on pincode (only compare records with the same pincode)
    pincode_groups = df[df["pincode"].str.len() >= 5].groupby("pincode")

    for pincode, group in pincode_groups:
        if len(group) < 2:
            continue

        rows = group.to_dict("records")
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                a, b = rows[i], rows[j]

                # Skip if already matched deterministically (same PAN)
                if a["pan"] and a["pan"] == b["pan"]:
                    continue

                # Name similarity (Jaro-Winkler)
                name_sim = fuzz.WRatio(a["business_name"], b["business_name"]) / 100.0

                # Address similarity (token sort ratio)
                addr_sim = fuzz.token_sort_ratio(a["address"], b["address"]) / 100.0

                # Phone match bonus
                phone_match = 1.0 if (a["phone"] and a["phone"] == b["phone"]) else 0.0

                # Weighted score
                score = (name_sim * 0.5) + (addr_sim * 0.3) + (phone_match * 0.2)

                if score >= MEDIUM_CONFIDENCE_THRESHOLD:
                    pairs.append({
                        "record_a_id": a["record_id"],
                        "record_b_id": b["record_id"],
                        "match_score": round(score, 4),
                        "match_type": "probabilistic",
                        "match_details": {
                            "name_similarity": round(name_sim, 3),
                            "address_similarity": round(addr_sim, 3),
                            "phone_match": phone_match > 0,
                            "blocking_key": f"pincode:{pincode}",
                        },
                    })

    return pairs


def _merge_pairs(deterministic: list[dict], probabilistic: list[dict]) -> list[dict]:
    """Merge deterministic and probabilistic pairs, preferring deterministic."""
    seen = set()
    merged = []

    for pair in deterministic:
        key = tuple(sorted([pair["record_a_id"], pair["record_b_id"]]))
        if key not in seen:
            seen.add(key)
            merged.append(pair)

    for pair in probabilistic:
        key = tuple(sorted([pair["record_a_id"], pair["record_b_id"]]))
        if key not in seen:
            seen.add(key)
            merged.append(pair)

    return merged


def _cluster_pairs(pairs: list[dict], n_records: int, df: pd.DataFrame) -> dict[int, list[str]]:
    """Cluster matched pairs into groups using Union-Find."""
    record_ids = df["record_id"].tolist()
    id_to_idx = {rid: i for i, rid in enumerate(record_ids)}

    parent = list(range(n_records))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for pair in pairs:
        a_idx = id_to_idx.get(pair["record_a_id"])
        b_idx = id_to_idx.get(pair["record_b_id"])
        if a_idx is not None and b_idx is not None:
            # Only auto-union high-confidence pairs
            if pair["match_score"] >= HIGH_CONFIDENCE_THRESHOLD:
                union(a_idx, b_idx)

    # Build clusters
    clusters = {}
    for i, rid in enumerate(record_ids):
        root = find(i)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(rid)

    return clusters


def _generate_ubid(cluster_records: list, df: pd.DataFrame) -> str:
    """Generate a UBID for a cluster.

    Format: UBID-KA-XXXXXXXX where X is derived from PAN/GSTIN or a hash.
    """
    # Try to anchor to PAN
    for rid in cluster_records:
        row = df[df["record_id"] == rid].iloc[0]
        if row["pan"] and len(row["pan"]) == 10:
            return f"UBID-KA-{row['pan']}"

    # Fallback: hash-based
    combined = "-".join(sorted(cluster_records))
    hash_val = hashlib.sha256(combined.encode()).hexdigest()[:8].upper()
    return f"UBID-KA-{hash_val}"


def _persist_results(
    db: Session,
    df: pd.DataFrame,
    clusters: dict[int, list[str]],
    all_pairs: list[dict],
    records: list[RawBusinessRecord],
) -> dict:
    """Create UnifiedBusiness and LinkageResult records in the database."""
    record_map = {r.id: r for r in records}

    auto_linked = 0
    pending_review = 0
    kept_separate = 0

    for cluster_idx, record_ids in clusters.items():
        ubid = _generate_ubid(record_ids, df)

        # Pick canonical values (prefer records with most fields filled)
        canonical = _pick_canonical(record_ids, df)

        unified = UnifiedBusiness(
            ubid=ubid,
            canonical_name=canonical.get("business_name", ""),
            canonical_address=canonical.get("address", ""),
            canonical_pincode=canonical.get("pincode", ""),
            canonical_pan=canonical.get("pan", ""),
            canonical_gstin=canonical.get("gstin", ""),
            lifecycle_status=LifecycleStatus.UNKNOWN,
            record_count=len(record_ids),
        )
        db.add(unified)
        db.flush()  # Get the ID

        # Link raw records to unified entity
        for rid in record_ids:
            if rid in record_map:
                record_map[rid].unified_business_id = unified.id

        if len(record_ids) > 1:
            auto_linked += len(record_ids)
        else:
            kept_separate += 1

    # Save linkage results (pairwise)
    for pair in all_pairs:
        score = pair["match_score"]
        if score >= HIGH_CONFIDENCE_THRESHOLD:
            confidence = MatchConfidence.HIGH
            status = LinkageStatus.AUTO_LINKED
        elif score >= MEDIUM_CONFIDENCE_THRESHOLD:
            confidence = MatchConfidence.MEDIUM
            status = LinkageStatus.PENDING_REVIEW
            pending_review += 1
        else:
            confidence = MatchConfidence.LOW
            status = LinkageStatus.REJECTED
            kept_separate += 1

        linkage = LinkageResult(
            record_a_id=pair["record_a_id"],
            record_b_id=pair["record_b_id"],
            match_score=score,
            confidence=confidence,
            status=status,
            match_details=pair.get("match_details", {}),
        )
        db.add(linkage)

    db.commit()

    unified_count = db.query(UnifiedBusiness).count()
    return {
        "unified_count": unified_count,
        "auto_linked": auto_linked,
        "pending_review": pending_review,
        "kept_separate": kept_separate,
    }


def _pick_canonical(record_ids: list[str], df: pd.DataFrame) -> dict:
    """Pick the best canonical values from a cluster of records."""
    subset = df[df["record_id"].isin(record_ids)]

    canonical = {}
    for field in ["business_name", "address", "pincode", "pan", "gstin"]:
        # Pick the longest non-empty value (heuristic: more complete = better)
        values = subset[field].dropna()
        values = values[values.str.len() > 0]
        if not values.empty:
            canonical[field] = values.loc[values.str.len().idxmax()]
        else:
            canonical[field] = ""

    return canonical
