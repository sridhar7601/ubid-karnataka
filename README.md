# UBID Platform — Unified Business Identifier for Karnataka Commerce & Industries

> **PanIIT AI for Bharat Hackathon — Theme 1**
> Cross-system entity resolution + lifecycle intelligence with **Azure GPT-4.1** narration grounded on real linkage scores. Sits as a decision-support layer alongside Karnataka's 40+ existing department systems.

---

## What it solves

Karnataka's business records live in 40+ siloed department systems (Shop Establishment, Factories, Labour, KSPCB, ESCOMs, BWSSB, Fire, Food Safety, urban / rural local bodies). The same business exists as multiple records, with no reliable join key. The brief has **two parts** — both addressed:

### Part A — Entity Resolution → UBID
- **Deterministic match** on PAN / GSTIN / Udyam (exact)
- **Probabilistic match** on business name + address + pincode (rapidfuzz Jaro-Winkler + token-sort)
- **3-tier confidence** — HIGH ≥0.9 (auto-link) · MEDIUM 0.7–0.9 (human review) · LOW <0.7 (keep separate)
- **Reviewer workflow** — confirm / reject ambiguous pairs, decisions persisted with audit trail
- **UBID anchored to PAN/GSTIN** when present; internal hash otherwise

### Part B — Lifecycle Intelligence → Active / Dormant / Closed
- **Rule-based inference** — recent filing within 12 months ⇒ Active; 12–24 months ⇒ Dormant; explicit closure signal ⇒ Closed
- **Cross-source conflict detection** — flags cases where one source says active and another says struck-off
- **Event timeline** — every state change persisted with source + timestamp
- **AI Lifecycle Verdict** (Azure GPT-4.1) — grounded narration on every UBID, escalates conflicts in plain English

**Brief non-negotiables met:** source systems unmodified · synthetic / scrambled data only · all decisions explainable + reversible · no hosted-LLM on raw PII (synthetic demo only; on-prem inference path documented).

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| npm | 9+ |

---

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env.local`:

```env
# Required for AI features (briefing, lifecycle verdict, linkage rationale)
AZURE_OPENAI_API_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/openai/deployments/your-deployment/chat/completions?api-version=2025-01-01-preview

# Optional fallback if Azure not available
# OPENAI_API_KEY=sk-...
```

> **Without API keys:** the app runs fully — every AI block falls back to deterministic templates. All entity resolution + lifecycle inference work offline.

```bash
uvicorn main:app --port 8000 --reload
```

Backend on **http://127.0.0.1:8000** · OpenAPI docs at `/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend on **http://localhost:5173** · proxies `/api` → port 8000

### Demo data

Already seeded in `backend/ubid.db`:
- **1,231 raw records** (440 GST · 351 MCA · 440 Udyam) across **real Bengaluru pincodes**
- **685 unified UBIDs** after resolution · 624 pending-review pairs
- **2,723 lifecycle events** (inspection · renewal · filing · payment · audit · closure)
- **326 businesses tagged as factories** (sector: manufacturing / construction / technology)
- Ground-truth match set in `data/synthetic_ground_truth.csv` for accuracy validation

The brief's killer query — "active factories in pincode 560058 with no inspection in last 18 months" — now returns **3 real matches** out of **46 fleet-wide candidates**.

To re-seed:

```bash
cd backend && source .venv/bin/activate
python ../demo/seed_demo.py            # re-runs entity resolution + lifecycle inference
python seed_realistic_events.py        # adds inspection/renewal/filing event timeline
```

> Per the brief's non-negotiable, real Karnataka business data is never used. All records are deterministically synthesised (Faker seed 42) with realistic Indian-origin business names, valid PAN/GSTIN/Udyam formats, and Bengaluru-Urban pincode distributions.

---

## Key features

| Feature | Where |
|---------|-------|
| **AI Morning Briefing** (Azure GPT-4.1) | `/` Dashboard — top card |
| **Smart Query** — runs the brief's killer example verbatim | `/insights` |
| **AI Query Summary** on every smart-query result | `/insights` |
| **AI Lifecycle Verdict** with conflict escalation | `/entity/<UBID>` |
| **AI Linkage Rationale** (lazy-loaded on expand) | `/resolution` — pair detail |
| Score-tiered linkage queue (HIGH / MEDIUM / LOW) | `/resolution` |
| Reviewer workflow (Confirm / Reject) with audit trail | `/resolution` |
| Cross-system conflict detection (Active in GST vs Closed in MCA) | Backend lifecycle service |
| UBID lookup by PAN / GSTIN / name + pincode | `/entities` search |
| Event timeline per UBID | `/entity/<UBID>` |

---

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Service health |
| GET | `/api/dashboard/overview` | KPIs + AI briefing |
| POST | `/api/records/upload` | Upload department CSV |
| GET | `/api/records/` | List raw records (filterable) |
| GET | `/api/records/stats` | Per-source counts |
| POST | `/api/linkage/run` | Trigger entity resolution |
| GET | `/api/linkage/results` | Pairwise matches (filterable) |
| PUT | `/api/linkage/{id}/review` | Confirm / reject a pair |
| GET | `/api/linkage/{id}/explain-llm` | **AI rationale** for a linkage |
| GET | `/api/unified/` | List UBIDs |
| GET | `/api/unified/{ubid}` | Full UBID profile + events |
| GET | `/api/unified/{ubid}/lifecycle` | Lifecycle event timeline |
| GET | `/api/unified/{ubid}/explain-llm` | **AI lifecycle verdict** with conflict resolver |
| GET | `/api/insights/query` | **Smart Query** — cross-cutting filter (status · pincode · sector · business_type · event_type · no_event_since_months) |
| GET | `/api/insights/preset/active-without-inspection` | Brief's killer example as a one-liner endpoint |

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + SQLAlchemy 2 + SQLite (PostgreSQL-portable) |
| Entity resolution | rapidfuzz (Jaro-Winkler + token-sort) + Splink-ready |
| Frontend | React 18 + Vite + TypeScript + Tailwind v4 + lucide-react |
| AI / LLM | Azure OpenAI GPT-4.1 (enterprise) — fully optional |
| Data | Faker-seeded synthetic + ground truth (1,231 records) |

---

## Architecture

```
backend/
├── main.py                          FastAPI entry + 4 routers
├── app/
│   ├── database.py                  SQLAlchemy session
│   ├── models.py                    RawBusinessRecord · UnifiedBusiness · LinkageResult · LifecycleEvent · ReviewDecision
│   ├── routers/
│   │   ├── records.py               CSV upload + list + per-source stats
│   │   ├── linkage.py               Run resolution · pairwise queue · review · AI rationale
│   │   ├── unified.py               UBID list · profile · lifecycle · AI verdict
│   │   └── dashboard.py             KPI rollup + AI briefing
│   └── services/
│       ├── splink_linker.py         Deterministic + probabilistic matching · UBID generation
│       ├── lifecycle.py             Rule-based Active / Dormant / Closed inference
│       └── llm_narration.py         Azure GPT-4.1 grounded narration (3 use cases · disk-cached)
└── data/llm_cache/                  Cached LLM responses

frontend/
├── src/
│   ├── App.tsx                      Sticky nav · 4 routes · live pill
│   ├── api.ts                       Typed client
│   └── pages/
│       ├── Dashboard.tsx            AI briefing · stats · upload · run resolution
│       ├── ResolutionDashboard.tsx  Linkage queue · AI rationale · confirm / reject
│       ├── UnifiedEntities.tsx      Searchable UBID list
│       └── EntityProfile.tsx        UBID detail · linked records · lifecycle · AI verdict
```

---

## How AI is used (Azure GPT-4.1)

All AI outputs are **grounded** — GPT-4.1 only describes pre-computed numbers (linkage scores, lifecycle signals, source statuses). Never invents identifiers, names, or dates. Every response cached to `data/llm_cache/` after first call → demo never breaks if network is down.

| Use case | What it does |
|----------|--------------|
| **Dashboard briefing** | 3-sentence summary: linkage state + lifecycle distribution + recommended action for stewardship team |
| **Lifecycle verdict** | Per-UBID narration of the Active / Dormant / Closed decision; escalates source conflicts ("active in GST but struck-off in MCA") with next-step recommendation |
| **Linkage rationale** | Per-pair justification — strongest match feature + auto-link / review / reject recommendation |

**Production note:** per the brief's non-negotiables, hosted-LLM on raw PII is not permitted. This implementation operates on synthetic / scrambled data only. The `lib/llm_narration.py` interface is model-agnostic — production swaps Azure for on-prem inference (Llama-3 / Mistral) by changing the URL + auth header. No application code changes.

---

## Methodology — Part A (Entity Resolution)

**Two-pass approach:**

1. **Deterministic** — exact match on (PAN), (GSTIN), (Udyam number). Score = 1.0, auto-link.
2. **Probabilistic** — for remaining unmatched records, blocked by pincode, scored as:
   ```
   score = 0.50 × name_jaro_winkler
         + 0.25 × address_token_sort_ratio
         + 0.15 × pincode_match
         + 0.10 × phone_or_email_match
   ```
   Tiers: ≥0.9 auto-link · 0.7–0.9 human review · <0.7 keep separate.

**Union-Find clustering** — transitively merge auto-linked pairs into UBID groups.
**UBID generation** — `UBID-KA-<8-char hash of canonical PAN/GSTIN or business name>`; PAN-anchored where present so a future Central-identifier sync is a no-op.

---

## Methodology — Part B (Lifecycle)

```
ACTIVE   if last_filing_date within 12 months across any source
DORMANT  if last_filing_date 12–24 months and no closure signal
CLOSED   if any source reports cancelled / struck_off / dissolved
UNKNOWN  if no temporal signal exists
```

Cross-source conflicts (e.g., active in GST + struck-off in MCA) trigger the **AI Conflict Resolver** which reads all source statuses + recent events and recommends the next step (manual confirmation, GST portal check, on-ground inspection).

---

## Model & architecture choices (and why)

| Choice | Reason |
|--------|--------|
| **rapidfuzz instead of full Splink integration** for v1 | Splink installed and ready — adapter is a 1-day swap. rapidfuzz Jaro-Winkler + token-sort is auditable line-by-line, runs in <2s on 1.2k records, no Spark / DuckDB cluster required for demo. |
| **Rule-based lifecycle (not ML)** | Brief requires explainability and reversibility. Each verdict carries the exact event(s) that drove it. Future ML model can sit on top once labelled outcomes accumulate. |
| **Azure OpenAI GPT-4.1 for narration only — never for math** | LLMs hallucinate. We compute every score / status / count, then ask GPT-4.1 only to **describe** them. Zero invented values. |
| **SQLite for demo, PostgreSQL portable** | One-line schema swap. Existing SQLAlchemy queries unchanged. |
| **No hosted-LLM on raw PII in production** | Brief non-negotiable. The narration service interface is model-agnostic — swap Azure for on-prem Llama-3 / Mistral by changing endpoint + auth. |

---

## Risks & mitigation

| Risk | Mitigation |
|------|-----------|
| **Wrong merge** (false positive linkage) | Cost asymmetry: only HIGH (≥0.9) auto-merges. MEDIUM forced into human review. All merges reversible via reject + UBID re-issue. |
| **No real Karnataka data in demo** | Schema is column-flexible (15+ variant column names handled at upload). Round 2 sandbox data ingests via the same `/api/records/upload` endpoint. |
| **Reviewer fatigue with large queue** | Confidence-banded queue + AI rationale on each pair → reviewer can clear obvious confirms in seconds. Future: bulk-action + active learning. |
| **Hosted-LLM on PII forbidden** | Synthetic-only in repo. `llm_narration.py` is endpoint-swappable to on-prem inference (one config change). |
| **Source-system conflicts (active in A, closed in B)** | AI Conflict Resolver flags these explicitly with both statuses + recommended next step. Reviewer decides; outcome persisted. |
| **Data quality (typos, abbreviations)** | rapidfuzz Jaro-Winkler tolerates edit distance; token-sort handles word reordering. Indic transliteration ready to add for English ↔ Kannada name variants. |

---

## Implementation roadmap (Round 2 sandbox pilot)

**Phase 1 — Data integration (weeks 1–4)**
- Map 3–4 Karnataka department schemas (Shop Estab + Factories + Labour + KSPCB) to the unified record format
- Calibrate confidence thresholds per source-pair on labelled subset
- Output: same UI, real (scrambled) Karnataka records

**Phase 2 — Linkage validation (weeks 5–8)**
- Reviewer team clears top-1000 MEDIUM pairs · precision/recall measured against ground truth
- Active-learning loop: reviewer decisions feed back into Splink m-probabilities
- Output: production-grade match accuracy + calibration

**Phase 3 — Lifecycle on real event streams (weeks 9–12)**
- Wire one-way event feeds (inspections, renewals, compliance filings, ESCOM consumption)
- AI Conflict Resolver tested on real disagreements
- Output: live Active / Dormant / Closed dashboard for KCI

**Phase 4 — Production hardening (post-pilot)**
- SQLite → PostgreSQL · Splink full integration · DuckDB blocking
- Azure OpenAI → on-prem Llama-3 (per non-negotiable)
- Reviewer SSO · audit-export for KAU compliance
- Web service exposed to KCI staff via VPN

---

## Production optimisations (deferred for demo, planned for Round 2)

This is a hackathon demo running on a single laptop with SQLite. Real-world Karnataka deployment at 1M+ businesses, 40+ source systems, 100+ daily reviewers needs the following — all are deliberate gaps documented for the jury, not oversights:

### Performance & scale

| Concern | Demo today | Production plan |
|---------|-----------|----------------|
| **Database** | SQLite file (1.8 MB · 1k records) | PostgreSQL on managed RDS · partitioned by source_system |
| **Indexes** | None beyond Prisma defaults | Composite indexes on `(canonical_pincode, lifecycle_status)`, `(canonical_pan)`, `(canonical_gstin)`, `(unified_business_id, event_date desc)` for the smart-query hot paths |
| **Entity-resolution runtime** | rapidfuzz in-process (<2 s on 1k records) | Splink on Spark/DuckDB cluster · pincode + soundex blocking → O(N) instead of O(N²) on 1M records |
| **Linkage queue scan** | `LinkageResult.findMany` full scan | Materialised view per `(confidence, status, reviewer_id)` — sub-second pagination |
| **Lifecycle inference** | Synchronous on demand | Nightly batch via cron + on-update triggers from event ingestion |

### Caching

| Layer | Demo | Production |
|-------|------|-----------|
| **AI narration** | File cache (`data/llm_cache/*.txt`) keyed by SHA256 of payload | Redis with 24-hour TTL · CDN-fronted for Dashboard briefing |
| **Smart Query results** | Recomputed every call | Redis with 60-second TTL keyed by filter set · invalidated on linkage / event ingestion |
| **UBID profile pages** | Live SQLAlchemy query | Read-through Redis (5-min TTL) — reviewer dashboards are read-heavy |
| **Open registry lookups** (PAN/GSTIN/Udyam exact match) | Direct SQL | Bloom filter in front of DB → 99% rejected without round-trip |

### Indexing strategy

```sql
-- High-frequency reviewer queue scan
CREATE INDEX idx_linkage_queue ON linkage_results (confidence, status, match_score DESC);

-- Smart query: active in pincode X
CREATE INDEX idx_unified_pincode_status ON unified_businesses (canonical_pincode, lifecycle_status);

-- Lifecycle "no event since N months" — partial index on recent events
CREATE INDEX idx_recent_events ON lifecycle_events (unified_business_id, event_type, event_date DESC)
  WHERE event_date > NOW() - INTERVAL '24 months';

-- PAN/GSTIN anchor lookup
CREATE UNIQUE INDEX idx_unified_pan ON unified_businesses (canonical_pan) WHERE canonical_pan IS NOT NULL;
CREATE UNIQUE INDEX idx_unified_gstin ON unified_businesses (canonical_gstin) WHERE canonical_gstin IS NOT NULL;
```

### Concurrency & throughput

- **API**: Uvicorn workers behind nginx · stateless · horizontal scale by AKS replicas
- **Reviewer workflow**: Optimistic-locking on `LinkageResult.status` (version column) so two reviewers never silently overwrite each other
- **Event ingestion**: Kafka topic per source system · idempotent consumers · dead-letter queue for events that can't be joined to a UBID (brief requires these surface for review, not silently dropped)
- **AI narration**: token-bucket rate-limiter (10 req/s per IP) · async batch when queue depth > 50 to amortise LLM TPS

### Observability (Round 2)

- OpenTelemetry traces on every linkage decision + AI call (preserves the brief's *"every decision must be explainable and reversible"* mandate)
- Prometheus metrics: `linkage.auto_link_count`, `linkage.review_queue_depth`, `lifecycle.classification_drift`, `ai.cache_hit_ratio`
- Grafana dashboards for KCI ops + a 30-day match-quality regression report (precision/recall vs ground-truth labels reviewers approve)

### Security & compliance

- **No hosted-LLM on raw PII**: `lib/llm_narration.py` is endpoint-swappable — production swaps Azure OpenAI for on-prem Llama-3 / Mistral. Only the URL + auth header changes.
- **Reviewer identity**: SSO via Karnataka State eAuth · every confirm/reject signed with reviewer ID + timestamp + IP. Audit-export for KAU compliance.
- **Encryption at rest**: PG TDE + KMS-managed keys for fields containing PAN/GSTIN. Synthetic data is plaintext for demo.
- **Reversibility**: Every UBID merge can be undone — the `unified_business_id` foreign key on raw records is the only change, so a single UPDATE restores pre-merge state. ReviewDecision table is append-only.

### Cost estimate (Round 2 sandbox)

- 1 × t3.large API VM + 1 × Redis (managed) + 1 × PG (db.t3.medium): ~₹50,000 / month
- Azure OpenAI calls (cached, ~5,000/day across narrations + summaries): ~₹2,000 / month
- Total infrastructure: **~₹52K/month** for the 1M-record sandbox · scales linearly to ₹2-3 lakh/month at full Karnataka scale (40M businesses, 1B events).

---

## Submission

- **Hackathon:** PanIIT AI for Bharat
- **Theme:** 1 — Unified Business Identifier (UBID) + Active Business Intelligence (Karnataka Commerce & Industries)
- **Team:** Sridhar Suresh · Sruthi Krishnakumar
