"""
Azure OpenAI GPT-4.1 narration overlay for UBID platform.

Grounded — LLM only describes pre-computed numbers (linkage scores, lifecycle status,
event timestamps). Never invents identifiers, names, or dates. Disk-cached.

Brief non-negotiables:
- No hosted-LLM use on raw PII → only scrambled / synthetic data is sent.
- Production deployment swaps Azure for on-prem Llama-3 / Mistral by changing the
  endpoint + auth header — no caller code changes.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

# Load .env.local from backend/ (same dir as main.py)
_BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(_BACKEND_DIR / ".env.local")
load_dotenv(_BACKEND_DIR / ".env")

CACHE_DIR = _BACKEND_DIR / "data" / "llm_cache"


def _hash_key(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def _read_cache(key: str) -> str | None:
    path = CACHE_DIR / f"{key}.txt"
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None


def _write_cache(key: str, text: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.txt").write_text(text, encoding="utf-8")


def _has_llm() -> bool:
    return bool(os.environ.get("AZURE_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def _raw_llm(system_prompt: str, user_content: str, max_tokens: int = 220) -> str:
    """Single LLM call. Azure preferred, OpenAI fallback. Synchronous (FastAPI handles concurrency)."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    azure_key = os.environ.get("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    if azure_key and azure_endpoint:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                azure_endpoint,
                headers={"Content-Type": "application/json", "api-key": azure_key},
                json={"messages": messages, "max_tokens": max_tokens, "temperature": 0.2},
            )
            r.raise_for_status()
            data = r.json()
            return (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()

    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        raise RuntimeError("No LLM API key configured")
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {openai_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.2,
            },
        )
        r.raise_for_status()
        data = r.json()
        return (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()


# ─── 1. Dashboard Briefing ────────────────────────────────────────────────────
def generate_dashboard_briefing(stats: dict[str, Any]) -> str:
    """
    stats keys:
      - total_records, by_source (dict), unified_count, auto_linked,
        pending_review, rejected, active, dormant, closed, unknown
    """
    cache_key = f"briefing_{_hash_key(stats)}"
    cached = _read_cache(cache_key)
    if cached:
        return cached

    if not _has_llm():
        return (
            f"{stats.get('total_records', 0)} raw records collapsed into "
            f"{stats.get('unified_count', 0)} UBIDs. "
            f"{stats.get('auto_linked', 0)} auto-linked, "
            f"{stats.get('pending_review', 0)} pending review. "
            f"Lifecycle: {stats.get('active', 0)} active, "
            f"{stats.get('dormant', 0)} dormant, {stats.get('closed', 0)} closed."
        )

    system = (
        "You are the AI ops assistant for Karnataka Commerce & Industries' UBID platform. "
        "Write a 3-sentence morning briefing for the data-stewardship team. Structure:\n"
        "1. Linkage state: total raw records → UBIDs, auto-linked count, review queue depth.\n"
        "2. Lifecycle distribution: active / dormant / closed counts; flag if review queue is large.\n"
        "3. Action: which queue or conflict cluster the team should clear first.\n"
        "Use plain government-administrative English. Under 70 words."
    )
    try:
        text = _raw_llm(system, json.dumps(stats), max_tokens=220)
        _write_cache(cache_key, text)
        return text
    except Exception:
        return (
            f"{stats.get('total_records', 0)} records → {stats.get('unified_count', 0)} UBIDs. "
            f"{stats.get('pending_review', 0)} pairs await reviewer. "
            f"Active {stats.get('active', 0)}, dormant {stats.get('dormant', 0)}, closed {stats.get('closed', 0)}."
        )


# ─── 2. Lifecycle conflict resolver ──────────────────────────────────────────
def explain_lifecycle(payload: dict[str, Any]) -> str:
    """
    payload keys:
      - ubid, business_name, status (active/dormant/closed/unknown)
      - reasoning (rule-based text)
      - sources: list of {source_system, status_in_source, last_filing_date}
      - events: list of {type, timestamp, source}
      - has_conflict (bool)
    """
    cache_key = f"lifecycle_{_hash_key(payload)}"
    cached = _read_cache(cache_key)
    if cached:
        return cached

    if not _has_llm():
        base = payload.get("reasoning") or "No deterministic signal available."
        if payload.get("has_conflict"):
            return f"{base} Manual review recommended — sources disagree on status."
        return base

    system = (
        "You are a Karnataka Commerce & Industries data steward writing a 2-sentence "
        "lifecycle verdict for an executive memo. Structure:\n"
        "1. State the verdict (Active / Dormant / Closed) and the strongest signal that supports it "
        "(most recent activity event, source-system status, filing recency).\n"
        "2. If sources conflict, explicitly call out the conflict (which system says what) and recommend "
        "the next step (manual confirmation, GST portal check, on-ground inspection).\n"
        "Use specific dates and source names from the payload — do NOT invent dates. Under 60 words."
    )
    try:
        text = _raw_llm(system, json.dumps(payload, default=str), max_tokens=180)
        _write_cache(cache_key, text)
        return text
    except Exception:
        return payload.get("reasoning") or "Verdict pending — see evidence timeline below."


# ─── 3. Linkage match explanation ────────────────────────────────────────────
def explain_linkage(payload: dict[str, Any]) -> str:
    """
    payload keys:
      - link_id, score (0-1), confidence (high/medium/low)
      - record_a, record_b: each with name, address, pincode, pan, gstin
      - features (dict): name_score, address_score, pincode_match, pan_match, gstin_match
    """
    cache_key = f"linkage_{_hash_key(payload)}"
    cached = _read_cache(cache_key)
    if cached:
        return cached

    if not _has_llm():
        feats = payload.get("features", {})
        bits = []
        if feats.get("pan_match"):
            bits.append("PAN exact-match")
        if feats.get("gstin_match"):
            bits.append("GSTIN exact-match")
        if (feats.get("name_score") or 0) >= 0.85:
            bits.append("name fuzzy-match high")
        if feats.get("pincode_match"):
            bits.append("pincode match")
        evidence = ", ".join(bits) if bits else "weak signals across the board"
        return (
            f"Score {payload.get('score', 0):.2f} — {payload.get('confidence', '')}. "
            f"Evidence: {evidence}."
        )

    system = (
        "You are an entity-resolution analyst writing a 2-sentence justification for a linkage decision:\n"
        "1. State the strongest match feature (PAN / GSTIN exact, name fuzzy ≥0.9, address ≥0.8, "
        "pincode same) — call out specific scores from the features dict.\n"
        "2. Recommend disposition: AUTO-LINK (high confidence), HUMAN REVIEW (medium), KEEP SEPARATE "
        "(low). Mention the single biggest reason for ambiguity if medium.\n"
        "Be terse. Use the actual scores. Under 50 words."
    )
    try:
        text = _raw_llm(system, json.dumps(payload, default=str), max_tokens=140)
        _write_cache(cache_key, text)
        return text
    except Exception:
        return f"Score {payload.get('score', 0):.2f}: {payload.get('confidence', '')} confidence. See feature details."
