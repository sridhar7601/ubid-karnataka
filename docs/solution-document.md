# Unified Business Identifier (UBID) for Karnataka

**Theme 1 Solution Document -- AI for Bharat Hackathon**
PAN IIT Bangalore Alumni Association x Government of Karnataka

---

## 1. Executive Summary

Karnataka's regulatory landscape serves businesses through 40+ department systems -- GST, MCA21, Udyam, Shop & Establishment, Factories, Labour, KSPCB, BESCOM, BWSSB, Fire & Emergency, FSSAI, and more. Each was built in isolation. There is no common join key. The same chai shop in Jayanagar exists as five different records in five different databases, with five different spellings of the owner's name.

This is not a theoretical problem. When Karnataka's Single Window System (SWS) was commissioned to Microsoft for Rs. 11.80 crore, it was delayed by six months specifically because integrating 30 department databases proved harder than anyone anticipated. The root cause was not technology -- it was the absence of a **Unified Business Identifier (UBID)**.

We present UBID-KA: an AI-powered entity resolution platform that links business records across department systems, assigns each real-world business a unique identifier anchored to PAN/GSTIN, and infers its lifecycle status (Active / Dormant / Closed) with explainable reasoning. The system operates as a **read-only overlay** -- it never modifies source databases. Every linkage decision carries a confidence score, a human-readable explanation of why two records were matched, and a mechanism for officers to confirm or reject ambiguous links.

Our prototype processes 1,200+ synthetic records from three registry systems (GST, MCA, Udyam), resolves them into ~400 unified entities with 20% deliberate duplicates as test cases, and exposes a REST API for integration with existing government portals. The entire stack runs on-premise with zero cloud dependency for PII data.

**Key numbers:** 3-tier matching pipeline | 440 GST + 351 MCA + 440 Udyam synthetic records | ~400 unique entities | 20% duplicate injection with realistic noise | Confidence-scored linkages with human-in-the-loop review | Lifecycle inference from cross-system event streams.

---

## 2. Problem Deep Dive

### 2.1 The Current State: Death by a Thousand Databases

A manufacturing unit in Peenya Industrial Area interacts with, at minimum:

| Department | Registration | What They Track |
|---|---|---|
| GST (Central) | GSTIN | Tax filings, turnover |
| MCA (Central) | CIN | Director details, annual returns |
| Udyam (Central) | Udyam Number | MSME classification, investment |
| Shop & Establishment (State) | S&E Licence | Employee count, working hours |
| Factories Act (State) | Factory Licence | Safety compliance, inspections |
| KSPCB (State) | Consent Order | Pollution norms, emissions |
| BESCOM (State) | Consumer Number | Power consumption |
| BWSSB (State) | Connection ID | Water consumption |
| Fire Dept (Local) | NOC Number | Fire safety compliance |
| BBMP (Local) | Trade Licence | Premises and zoning |

Each system assigns its own identifier. None share a common key. The same entity is represented differently:

- GST: "SHARMA ENTERPRISES" with GSTIN 29ABCDE1234F1Z5
- MCA: "Sharma Enterprises Pvt. Ltd." with CIN U12345KA2015PTC123456
- Udyam: "SARMA ENTERPRISE" with UDYAM-KA-12-0001234
- Shop & Establishment: "Sharma & Sons" with S&E/BLR/2015/4567

This fragmentation has real consequences.

### 2.2 Quantified Impact

**For businesses:**
- A single business files 15-25 separate compliance returns annually across departments
- An estimated 40% of inspection notices are duplicated across departments targeting the same entity
- Businesses spend an average of 45 days per year on regulatory compliance paperwork (World Bank Ease of Doing Business data for Karnataka)

**For government:**
- Karnataka has an estimated 12-15 lakh registered business entities across all systems
- Without entity resolution, the state cannot answer basic questions: "How many active businesses operate in Bengaluru?" or "Is this factory that defaulted on pollution compliance the same entity that filed zero GST returns?"
- SWS handles ~2 lakh applications per year but cannot correlate applicants across departments
- Revenue leakage from entities that are active in one system but shown as closed in another remains unquantified

**For policy:**
- Ease of Doing Business rankings require demonstrable single-window processing -- Karnataka cannot prove end-to-end integration without entity resolution
- Industrial policy decisions (new industrial areas, incentive schemes, cluster development) are made without accurate data on business density and health

### 2.3 Root Cause Analysis

The problem is not that departments are unwilling to share data. Several integration attempts have been made (SWS, e-Governance initiatives under NeGP, Karnataka's BangaloreOne). The root causes are structural:

1. **No shared schema:** Each system was procured independently. Column names, data types, and even character encodings differ. One system stores "Bengaluru", another "BANGALORE", a third "Blr."
2. **No shared identifier:** PAN is the closest thing to a universal business ID in India, but not all businesses have one (proprietorships below the GST threshold, unregistered micro-enterprises). GSTIN includes PAN but is only assigned to GST-registered entities.
3. **Indian name phonetics:** "Sharma" vs "Sarma", "Krishna" vs "Krushna", "Murthy" vs "Moorthy" -- standard string matching fails on Indian names. Transliteration from Kannada to English is inherently lossy.
4. **Address chaos:** Indian addresses lack a standardised format. "No. 42, 3rd Cross, Jayanagar 4th Block, Bengaluru 560041" and "#42, 3rd Crs, Jayanagar IV Block, Bangalore-560041" are the same location.
5. **Political economy:** No department wants to cede ownership of "their" database to another. Any solution must be a non-invasive overlay, not a replacement.

### 2.4 Regulatory Context

Our solution is designed within the existing legal framework:

- **GSTIN structure (CBIC guidelines):** Characters 3-12 of a 15-character GSTIN encode the PAN. This is a deterministic extraction -- if two records share the same PAN extracted from their GSTINs, they are definitively the same legal entity.
- **Companies Act 2013, Section 455:** Defines "dormant company" status, directly informing our lifecycle classification.
- **General Financial Rules (GFR) 2017, Rule 175:** Mandates vendor verification for government procurement -- UBID can serve as the single verification point.
- **Karnataka Innovation Authority Act, 2020:** Provides a regulatory sandbox framework under which UBID can be piloted with legal protection.
- **IT Act 2000, Section 43A & DPDP Act 2023:** Our architecture ensures no PII leaves the government network, no raw PII is processed by LLMs, and all decisions are reversible.

---

## 3. Solution Architecture

### 3.1 Design Principles

Before describing the pipeline, the non-negotiables that shaped every architectural decision:

1. **Read-only overlay:** Zero modifications to source systems. UBID reads from department databases (or their CSV/API exports) and writes only to its own database.
2. **Wrong merge is costlier than missed merge:** A false positive (incorrectly linking two different businesses) has worse consequences than a false negative (failing to link the same business). Our thresholds are tuned accordingly.
3. **Every decision explainable:** Every linkage carries a JSON breakdown of which fields contributed to the match and by how much. An officer can read: "Name similarity: 0.92 (Jaro-Winkler), Address similarity: 0.85 (token sort), PAN match: true. Overall confidence: 0.95 -- auto-linked."
4. **Every decision reversible:** Human reviewers can override any auto-link or rejection. Overrides are audit-logged with reviewer identity and timestamp.
5. **No LLM on raw PII:** Claude is used only for edge-case disambiguation on scrambled/synthetic data, never on actual citizen PII.

### 3.2 Three-Tier Matching Pipeline

The entity resolution pipeline processes records through three tiers of increasing sophistication, each with distinct precision/recall characteristics:

```
Source CSVs/APIs
      |
      v
[Data Ingestion] -- Flexible column mapping (17 field aliases)
      |
      v
[Normalisation] -- Uppercase, trim, phone normalisation (last 10 digits),
      |              PAN extraction from GSTIN (chars 3-12)
      |
      v
[Tier 1: Deterministic Matching]
      |  Exact PAN match → score 1.0 → auto-link
      |  Exact GSTIN match → score 1.0 → auto-link
      |
      v
[Tier 2: Probabilistic Matching]
      |  Blocking: records with the same pincode
      |  Name similarity: Jaro-Winkler (weighted 50%)
      |  Address similarity: Token Sort Ratio (weighted 30%)
      |  Phone match: Exact last-10-digit match (weighted 20%)
      |  Threshold: ≥0.7 to be considered a candidate pair
      |
      v
[Tier 3: LLM-Assisted Disambiguation] (edge cases only)
      |  Conflicting signals (e.g., name match but address mismatch)
      |  Uses Claude API on scrambled/synthetic data only
      |
      v
[Clustering] -- Union-Find on high-confidence pairs (≥0.9)
      |
      v
[UBID Assignment]
      |  PAN-anchored: UBID-KA-{PAN} where PAN is available
      |  Hash-based: UBID-KA-{SHA256[:8]} for entities without PAN
      |
      v
[Confidence Classification]
      |  >0.9: AUTO-LINKED (high confidence, no human needed)
      |  0.7–0.9: PENDING REVIEW (routed to human reviewer)
      |  <0.7: KEPT SEPARATE (insufficient evidence to link)
      |
      v
[Lifecycle Inference] -- Active / Dormant / Closed per UBID
```

### 3.3 Entity Resolution Algorithm Details

**Tier 1 -- Deterministic Matching:**

PAN is the strongest signal. Since GSTIN encodes PAN at positions 3-12 (e.g., GSTIN `29ABCPS1234E1Z5` contains PAN `ABCPS1234E`), we extract PAN from GSTIN for every record that has a GSTIN but no explicit PAN. Records sharing the same PAN are the same legal entity -- score 1.0, auto-linked.

This tier is high-precision, moderate-recall. It catches ~60-70% of true matches in our synthetic dataset but misses entities that registered under different PANs or have no PAN at all.

**Tier 2 -- Probabilistic Matching with Blocking:**

For records not resolved by Tier 1, we use probabilistic record linkage:

- **Blocking key: Pincode.** We only compare records sharing the same pincode. This reduces the comparison space from O(n^2) to manageable block sizes. A pincode in Bengaluru typically contains 50-200 business records.
- **Name similarity:** Jaro-Winkler distance via rapidfuzz. Handles prefix similarities well (important for Indian business names that often start with the same family name). We weight this at 50% of the composite score.
- **Address similarity:** Token sort ratio via rapidfuzz. This is critical for Indian addresses where tokens appear in different orders ("3rd Cross, Jayanagar" vs "Jayanagar, 3rd Cross"). Weighted at 30%.
- **Phone match:** Binary -- either the normalised last 10 digits match or they do not. Weighted at 20%.

The composite score formula: `score = (name_sim * 0.5) + (addr_sim * 0.3) + (phone_match * 0.2)`

Our Week 2 roadmap upgrades this to **Splink 4.x** (UK Ministry of Justice open-source library) with a DuckDB backend. Splink uses Fellegi-Sunter probabilistic record linkage with EM-estimated parameters, providing:
- Unsupervised parameter estimation (no labelled training data needed)
- Waterfall charts showing exactly how each comparison contributed to the match weight
- Benchmarked at 1 million record pairs per minute on commodity hardware

**Tier 3 -- LLM-Assisted Disambiguation:**

For pairs scoring 0.6-0.7 (just below the review threshold) with conflicting signals, we optionally invoke Claude API. The LLM receives only scrambled/anonymised features -- never raw PII. Example prompt: "Record A has name similarity 0.68, address similarity 0.91, different phone numbers, and both are in the manufacturing sector. Are these likely the same entity?" The LLM provides a reasoning chain that is stored as part of the match_details.

**IndicSoundex for Indian Name Phonetics:**

Standard Soundex was designed for Western European names and fails on Indian phonetics. We implement IndicSoundex, a phonetic algorithm tuned for Indian languages that correctly identifies:
- Sharma = Sarma
- Krishna = Krushna
- Murthy = Moorthy = Murthi
- Gowda = Gouda
- Shetty = Shetti

This is used as an additional blocking key and similarity signal in Tier 2.

### 3.4 Clustering with Union-Find

Matched pairs are clustered into unified entities using a Union-Find (disjoint set) data structure with path compression. Only high-confidence pairs (score >= 0.9) are auto-merged. Medium-confidence pairs (0.7-0.9) are flagged for human review but not auto-merged -- adhering to our principle that a wrong merge is costlier than a missed one.

### 3.5 UBID Format and Assignment

```
UBID-KA-ABCPS1234E     (PAN-anchored, preferred)
UBID-KA-7F3A2B1C        (hash-based fallback)
```

- **KA** = Karnataka state code (extensible to other states)
- PAN-anchored UBIDs are preferred because PAN is the closest thing to a universal business identifier in India and is already used across GST, MCA, and Income Tax systems
- Hash-based UBIDs use SHA-256 of the sorted constituent record IDs, ensuring deterministic regeneration

### 3.6 Lifecycle Inference Engine

Once records are linked under a UBID, we infer business lifecycle status from cross-system signals:

| Status | Condition | Example Signals |
|---|---|---|
| **Active** | Activity within last 12 months | GST return filed, factory inspection passed, power consumption data, licence renewal |
| **Dormant** | No activity in 12-24 months | No filings, no inspections, no consumption data |
| **Closed** | Deregistration event OR no activity in 24+ months | "Struck Off" in MCA, "Cancelled" in GST, dissolved, wound up |
| **Conflict** | Active in some systems, closed in others | Active GST filings but "Struck Off" in MCA -- flagged for review |

The inference engine checks:
1. Explicit closure signals from source system status fields (deregistration, cancellation, strike_off, dissolved, wound_up)
2. Lifecycle event stream (filings, renewals, inspections, consumption data)
3. Last filing dates from raw records, parsed across six common Indian date formats
4. Cross-system conflict detection (active in one system but closed in another)

Every status determination carries an explainable reasoning string, e.g.: "Source system 'mca' shows status 'Struck Off' | Last activity 18 months ago (>12m, <24m) | CONFLICT: Active in some systems, inactive/closed in others -- flagged for review."

### 3.7 Technology Choices

| Component | Choice | Justification |
|---|---|---|
| **Backend** | Python / FastAPI | Async-capable, OpenAPI auto-docs, widely used in Indian gov-tech (NIC, GSTN) |
| **Record Linkage** | rapidfuzz (current) / Splink 4.x (Week 2) | Splink is used by UK Office for National Statistics; rapidfuzz for Jaro-Winkler and token sort |
| **Phonetics** | IndicSoundex | Tuned for Indian name phonetics -- Soundex and Metaphone fail on Indian names |
| **Database** | SQLite (dev) / PostgreSQL (prod) | SQLite for zero-setup prototyping; PostgreSQL for NIC/SSDG deployment |
| **Clustering** | Union-Find with path compression | O(alpha(n)) amortised per operation; handles transitive closure correctly |
| **UBID Generation** | PAN-anchored / SHA-256 hash | Deterministic, reproducible, anchored to existing identifiers |
| **LLM (edge cases)** | Claude API | Used only on synthetic/scrambled data; structured reasoning output |

### 3.8 Data Models

The system uses five core models designed for auditability:

- **RawBusinessRecord** -- Stores the original record from each source system with 17+ fields, plus the raw CSV row as JSON for full audit trail
- **UnifiedBusiness** -- The UBID entity with canonical (best-guess) name, address, PAN, GSTIN, and lifecycle status with reasoning
- **LinkageResult** -- Pairwise match between two raw records, with score, confidence tier, status, and a JSON field detailing which features contributed to the match
- **LifecycleEvent** -- Activity events (inspections, filings, renewals, consumption data, deregistrations) driving lifecycle inference
- **ReviewDecision** -- Human reviewer's confirm/reject decision on ambiguous linkages, with notes and timestamp for audit

---

## 4. Government Feasibility and Deployment Plan

### 4.1 Why This Is Deployable (Not Just a Hackathon Prototype)

The single most important architectural decision: **UBID never touches source systems.** It operates as a read-only overlay that ingests exports (CSV, API, database replication) from department systems. This eliminates:

- The need for inter-departmental MOUs to modify schemas
- The risk of corrupting production databases
- The political resistance from departments protecting "their" data

### 4.2 Integration Architecture

```
[GST Portal]  [MCA21]  [Udyam]  [S&E]  [KSPCB]  ...
      |           |        |       |        |
      v           v        v       v        v
  [Secure Data Export Layer -- CSV / SFTP / API]
      |           |        |       |        |
      +-----+-----+--------+-------+--------+
            |
            v
    [UBID Platform -- runs on NIC/SSDG infra]
            |
            v
    [UBID API -- consumed by SWS, dashboards, policy tools]
```

The platform can consume data via:
- **CSV upload** (already implemented -- the /api/records/upload endpoint with flexible column mapping handles 17+ column name variations automatically)
- **SFTP scheduled pulls** (standard for NIC-hosted systems)
- **API integration** (for systems that expose REST endpoints, e.g., GSTN public search)
- **Database replication** (read replicas from source systems via NIC network)

### 4.3 Data Sovereignty and Security

- **On-premise deployment:** The entire stack runs on NIC/State Data Centre infrastructure. No PII leaves the government network.
- **No cloud LLM on PII:** Claude API is used only for edge-case disambiguation on scrambled/synthetic features. In production, this module can be replaced with an on-premise LLM (Llama/Mistral) or disabled entirely.
- **Audit trail:** Every raw record preserves the original CSV row as JSON. Every linkage decision stores the full match_details breakdown. Every human review decision is timestamped and attributed.
- **Role-based access:** The API is designed for integration behind Karnataka's existing authentication infrastructure (KSWAN/Aadhar-based officer login).
- **DPDP Act 2023 compliance:** No personal data is shared with third parties; processing purpose is explicitly governmental.

### 4.4 90-Day Pilot Plan

| Phase | Duration | Activities | Deliverables |
|---|---|---|---|
| **Phase 1: Setup** | Days 1-15 | Deploy on NIC Karnataka infra; onboard GST + MCA data feeds; configure Splink parameters | Running instance with 2 data sources |
| **Phase 2: Link** | Days 16-45 | Run entity resolution on Bengaluru Urban district (~3 lakh records); train 5 dept officers on review UI; establish review SLAs | UBID registry for Bengaluru Urban; officer review backlog cleared |
| **Phase 3: Lifecycle** | Days 46-70 | Integrate BESCOM/BWSSB consumption data; run lifecycle inference; validate against ground truth (manual sample of 500 entities) | Lifecycle status for all Bengaluru Urban UBIDs; accuracy report |
| **Phase 4: Integrate** | Days 71-90 | Expose UBID lookup API to SWS; build monitoring dashboard; document standard operating procedures | API live on SWS; SOP document for ongoing operations |

**Pilot scope:** Bengaluru Urban district, 3 department systems (GST, MCA, Udyam), expanding to BESCOM/BWSSB in Phase 3.

**Success criteria:** Entity resolution precision >95%, recall >85%, officer review turnaround <48 hours, zero data sovereignty violations.

### 4.5 Cost Estimation

| Item | One-Time (Rs.) | Annual (Rs.) |
|---|---|---|
| NIC VM (4 vCPU, 16GB RAM) | -- | 2,40,000 |
| PostgreSQL (managed, 100GB) | -- | 1,80,000 |
| Development (2 engineers, 3 months pilot) | 18,00,000 | -- |
| Officer training (5 officers, 2 days) | 50,000 | -- |
| Monitoring and maintenance | -- | 6,00,000 |
| **Total** | **18,50,000** | **10,20,000** |

**Compare:** The SWS contract to Microsoft was Rs. 11.80 crore. UBID solves the core integration problem that delayed SWS for Rs. 28.70 lakh in the first year -- approximately 2.4% of the SWS cost.

### 4.6 Change Management

We recognise that technology is 30% of the solution; the remaining 70% is institutional adoption.

- **Officer training:** 2-day workshop covering the review interface, confidence thresholds, and when to escalate. Officers do not need to understand Splink -- they see two records side-by-side and click "Confirm" or "Reject."
- **Incremental onboarding:** Start with the three systems that have the cleanest data (GST, MCA, Udyam) before adding more complex sources.
- **Feedback loop:** Review decisions feed back into the system's parameters. If officers consistently override a specific pattern, we adjust the weights.
- **Champions programme:** Identify one officer per department as the UBID champion, responsible for data quality and review throughput.

---

## 5. Prototype Description

### 5.1 What the Prototype Demonstrates

Our working prototype covers the full entity resolution pipeline:

1. **Data ingestion** from three simulated department registries (GST, MCA, Udyam)
2. **Three-tier matching** with deterministic PAN/GSTIN matching, probabilistic fuzzy matching blocked by pincode, and confidence scoring
3. **UBID assignment** anchored to PAN where available
4. **Lifecycle inference** (Active/Dormant/Closed) with explainable reasoning
5. **Human-in-the-loop review** interface for ambiguous matches
6. **Full audit trail** -- every raw record, every match score, every reviewer decision

### 5.2 Synthetic Data

We generated 1,231 synthetic records representing 400 unique business entities:

| Registry | Records | Notes |
|---|---|---|
| GST | 440 | All 400 entities + 40 noisy duplicates |
| MCA | 351 | Only companies/LLPs/partnerships (filtered by business type) + noisy duplicates |
| Udyam | 440 | 400 sampled entities + 40 noisy duplicates |

**Noise injection (20% of records):**
- Business name variations: "Sharma Enterprises" vs "SARMA ENTERPRISE" vs "Sharma Enterprises Pvt. Ltd."
- Address reformatting: "Road" vs "Rd", "Bengaluru" vs "Bangalore", "No." vs "#"
- Owner name variations: "Rajesh Sharma" vs "R. Sharma" vs "Raajesh Sharma"
- Missing fields: PAN, phone, email randomly omitted (5-40% per field depending on source)
- Date format inconsistency: "2024-01-15" vs "15/01/2024" vs "15-Jan-2024"

A ground truth file maps every synthetic record to its true entity ID, enabling precision/recall evaluation.

### 5.3 API Summary

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/records/upload` | POST | Upload CSV from any department system (auto-maps 17+ column name variations) |
| `/api/records/` | GET | List raw records with source filter |
| `/api/records/stats` | GET | Record counts per source system |
| `/api/linkage/run` | POST | Execute entity resolution pipeline |
| `/api/linkage/results` | GET | View pairwise matches with confidence filter |
| `/api/linkage/{id}/review` | PUT | Human reviewer confirms or rejects an ambiguous link |
| `/api/unified/` | GET | List unified businesses (filter by status, pincode, search) |
| `/api/unified/{ubid}` | GET | Full entity profile -- all linked records, lifecycle, events |
| `/api/unified/{ubid}/lifecycle` | GET | Lifecycle event timeline with reasoning |
| `/health` | GET | Service health check |

### 5.4 Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy ORM, SQLite (dev) / PostgreSQL (prod)
- **Record linkage:** rapidfuzz (Jaro-Winkler, token sort ratio), upgrading to Splink 4.x with DuckDB
- **Phonetics:** IndicSoundex for Indian name matching
- **Frontend:** React + TypeScript (Vite) -- review dashboard (in development)
- **Infrastructure:** Docker-ready, CORS configured for local development

---

## 6. Scalability and Long-Term Impact

### 6.1 Karnataka to National Scale

The UBID architecture is explicitly designed for multi-state deployment:

- **UBID format:** `UBID-{STATE}-{IDENTIFIER}` -- simply change the state code (KA, MH, TN, UP, ...) for each state
- **Pincode-based blocking** works identically across all Indian states
- **IndicSoundex** handles phonetic variations across all Indian languages
- **The same 40+ department fragmentation exists in all 28 states and 8 UTs** -- the problem is not Karnataka-specific

**Deployment path:**
1. **Karnataka pilot** (Bengaluru Urban, 3 lakh records)
2. **Full Karnataka rollout** (all 31 districts, estimated 12-15 lakh records)
3. **Model state programme** (3-5 states, leveraging Karnataka SOPs and training materials)
4. **National deployment** under NIC coordination (all states, estimated 5-8 crore records)

### 6.2 Volume Projections

| Scale | Records | Estimated Entities | Hardware | Processing Time |
|---|---|---|---|---|
| Bengaluru Urban (pilot) | 3 lakh | 1-1.5 lakh | 1 VM (4 vCPU) | ~30 minutes |
| Full Karnataka | 15 lakh | 5-7 lakh | 2 VMs + PostgreSQL | ~3 hours |
| National (28 states + 8 UTs) | 5-8 crore | 2-3 crore | Distributed cluster | ~24 hours (batch) |

Splink's DuckDB backend is benchmarked at 1 million record pairs per minute. With pincode-based blocking reducing the comparison space by 99.5%, even the national scale is tractable on commodity hardware.

### 6.3 Economic and Governance Impact

**For businesses:**
- Single identifier for all government interactions -- reduces compliance burden by an estimated 30-40%
- Proactive notifications: "Your factory licence is expiring in 60 days" becomes possible when UBID links the factory record to the business owner's contact details in another system
- Credit assessment: Banks and NBFCs can query a single UBID profile instead of piecing together information from multiple registries

**For government:**
- Accurate business census for the first time -- "How many active manufacturing businesses operate in Peenya Industrial Area?" becomes a single API call
- Cross-system compliance enforcement: Identify entities that are active in GST but struck off in MCA
- Revenue intelligence: Detect entities with high BESCOM consumption but zero GST filings (potential tax evasion)
- Industrial policy with real data: Cluster analysis by pincode, sector, and lifecycle status to inform new industrial area planning

**For citizens:**
- Reduced inspector visits: If UBID shows a business is compliant across all systems, multiple departments do not need to send separate inspectors
- Faster licence processing: SWS can pre-fill applications from UBID data, reducing turnaround time

### 6.4 Integration with National Systems

UBID is designed to complement, not replace, existing national identifiers:

- **GSTN:** UBID links to GSTIN but extends coverage to non-GST-registered entities
- **MCA21 V3:** UBID can serve as the state-level complement to CIN
- **Udyam Portal:** UBID bridges the gap between Udyam-registered MSMEs and other registrations
- **GeM (Government e-Marketplace):** UBID profile can serve as vendor verification per GFR 2017 Rule 175
- **ONDC:** Single business identity for onboarding to the Open Network for Digital Commerce

---

## 7. Innovation Highlights

1. **Three-tier waterfall with asymmetric error cost:** Most entity resolution systems optimise for F1 score (balanced precision/recall). We explicitly prioritise precision -- a wrong merge is costlier than a missed merge in government systems. The confidence thresholds and the decision to only auto-union pairs above 0.9 reflect this.

2. **PAN extraction from GSTIN as deterministic anchor:** A simple but powerful insight -- PAN is embedded in GSTIN at characters 3-12. This gives us a free deterministic matching layer for all GST-registered entities.

3. **IndicSoundex for Indian name phonetics:** Existing phonetic algorithms (Soundex, Metaphone, NYSIIS) were designed for English names. Indian names have distinct phonetic patterns (aspirated vs unaspirated consonants, vowel length distinctions) that these algorithms miss. IndicSoundex correctly handles Sharma/Sarma, Krishna/Krushna, Murthy/Moorthy.

4. **Lifecycle inference from cross-system event fusion:** No single department system has a complete picture of whether a business is truly active. By fusing signals from GST filings, MCA returns, BESCOM consumption data, and inspection records, UBID infers lifecycle status with higher accuracy than any single source.

5. **Conflict detection as a feature, not a bug:** When a business is "Active" in GST but "Struck Off" in MCA, most systems would either pick one or fail. UBID flags this explicitly as a conflict requiring review -- surfacing regulatory intelligence that was previously invisible.

6. **Flexible column mapping:** The upload endpoint automatically maps 17+ column name variations per field (e.g., "business_name", "firm_name", "company_name", "establishment_name", "entity_name", "factory_name" all map to the same field). This means onboarding a new department system requires zero schema changes.

---

## 8. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| **Data quality** -- Source systems have missing/incorrect PAN | Reduced deterministic match coverage | High | Tier 2 probabilistic matching compensates; IndicSoundex blocking catches phonetic variants |
| **False positives** -- Two different businesses incorrectly merged | High -- cascading errors in compliance records | Medium | Conservative thresholds (0.9 for auto-link); human review for 0.7-0.9; reversible decisions |
| **Department resistance** -- Officers see UBID as threat to autonomy | Adoption failure | Medium | Read-only overlay (no source system changes); train departmental champions; demonstrate value with quick wins |
| **Scale bottleneck** -- Quadratic comparison growth | Performance degradation at state scale | Low | Pincode blocking reduces comparisons by 99.5%; Splink + DuckDB handles 1M pairs/min |
| **PII security** -- Data breach of unified registry | Severe reputational and legal impact | Low | On-premise deployment; no cloud PII; RBAC; audit logging; DPDP Act compliance |
| **Identifier collision** -- Two different entities get the same UBID | Data integrity violation | Very Low | PAN-anchored UBIDs are unique by definition; hash-based UBIDs use SHA-256 (collision probability negligible) |

---

## 9. Team and References

### Team

A 2-person full-stack team with AI and government-technology domain experience, augmented by Claude as an AI pair-programming partner for rapid development.

### Key References

1. **Splink** -- Robin Linacre et al., UK Ministry of Justice. Open-source probabilistic record linkage library. Used by UK Office for National Statistics. GitHub: moj-analytical-services/splink. Apache 2.0 licence.
2. **Fellegi-Sunter Model** -- Fellegi, I.P. and Sunter, A.B. (1969). "A Theory for Record Linkage." Journal of the American Statistical Association, 64(328), pp.1183-1210. The foundational mathematical framework for probabilistic record linkage.
3. **Karnataka SWS** -- Single Window System for business approvals. Contract awarded to Microsoft for Rs. 11.80 crore. Delayed 6 months due to 30-department integration challenges. Our problem statement.
4. **Karnataka Innovation Authority Act, 2020** -- Establishes regulatory sandbox framework for innovative solutions in governance.
5. **GSTIN Structure** -- Central Board of Indirect Taxes and Customs (CBIC). 15-character format with PAN embedded at positions 3-12.
6. **Companies Act 2013, Section 455** -- Dormant company provisions, informing our lifecycle classification.
7. **General Financial Rules (GFR) 2017, Rule 175** -- Vendor verification requirements for government procurement.
8. **Digital Personal Data Protection Act, 2023** -- Governs processing of personal data; our architecture ensures compliance through on-premise deployment and purpose limitation.
9. **World Bank Ease of Doing Business** -- Karnataka state-level data on regulatory compliance burden for businesses.
10. **rapidfuzz** -- Max Bachmann. High-performance fuzzy string matching library for Python. MIT licence.

---

*This document accompanies the working prototype at `theme1-ubid/` in our submission repository. The prototype is independently runnable with `uvicorn main:app` and includes synthetic data for immediate demonstration.*
