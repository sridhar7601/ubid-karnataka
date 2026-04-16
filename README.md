# UBID Karnataka — Unified Business Identifier Platform

An AI-powered entity resolution platform that links business records scattered across Karnataka's 40+ department systems (GST, MCA, Udyam, Shop Establishment, KSPCB, and more) into a single unified registry. Each real-world business receives a unique identifier (UBID) anchored to PAN/GSTIN, with an explainable confidence score for every linkage and an inferred lifecycle status (Active / Dormant / Closed). The system operates as a read-only overlay — it never modifies source databases — and includes a human-in-the-loop review interface for ambiguous matches.

> **PanIIT AI for Bharat Hackathon** — Theme 1: Unified Business Identifier and Active Business Intelligence

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Synthetic Data

```bash
cd data && python generate_synthetic.py
```

## Architecture

Three-tier matching pipeline:

1. **Deterministic** — Exact PAN/GSTIN match (PAN extracted from GSTIN chars 3–12). Auto-linked.
2. **Probabilistic** — Fuzzy matching blocked by pincode: name (Jaro-Winkler 50%), address (token sort 30%), phone (20%).
3. **LLM-Assisted** — Claude API for edge cases on synthetic data only.

| Confidence | Threshold | Action        |
|------------|-----------|---------------|
| High       | ≥ 0.9     | Auto-linked   |
| Medium     | 0.7 – 0.9 | Human review  |
| Low        | < 0.7     | Kept separate |

**Lifecycle inference:** Active / Dormant / Closed based on filings, inspections, and deregistration events.

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite/PostgreSQL
- **Record linkage:** rapidfuzz, Splink 4.x, DuckDB, IndicSoundex
- **Frontend:** React, TypeScript, Tailwind CSS, Vite
- **LLM:** Claude API (edge cases only)

## Documentation

See [docs/solution-document.md](docs/solution-document.md) for the full solution write-up.
