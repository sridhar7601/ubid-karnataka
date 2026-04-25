#!/usr/bin/env python3
"""Theme 1 — UBID — narration via ElevenLabs."""
import os, sys, json, urllib.request, urllib.error, subprocess
from pathlib import Path

API_KEY = os.environ["ELEVEN_KEY"]
VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Sarah - mature, reassuring, confident female

UNITS = [
    "Karnataka has forty-plus department systems - GST, MCA, Udyam, Shop Establishment, KSPCB, Labour, Factories. Each was built in isolation. The same business exists as different records in different databases. There's no reliable join key. The state can't answer basic questions about its own industrial base - how many businesses are operating, where, with what activity.",
    "UBID gives every business one Unique Business Identifier. Three-tier entity resolution. Tier one: deterministic match on PAN or GSTIN. Tier two: probabilistic fuzzy matching on name and address, blocked by pincode. Tier three: LLM assist on ambiguous cases. Confidence scoring throughout - auto-link, route to human review, or keep separate. Every decision is reversible.",
    "Dashboard. One thousand two hundred thirty-one raw records ingested across three registries - GST, MCA, Udyam. Six hundred eighty-five unified business identifiers produced. Lifecycle inference labels each one Active, Dormant, or Closed.",
    "Pairwise linkage results. Each match shows source A versus source B with composite score. Green markers above ninety percent - auto-linked. Yellow between seventy and ninety - routed to human reviewer. Red below seventy - kept separate. Click any pair to see the breakdown: name similarity ninety-two, address similarity eighty-eight, phone match. Reviewer accepts or rejects, decisions feed back into calibration.",
    "Unified business profile. UBID anchored to the PAN. Three source records linked: a GST registration, an MCA company filing, a Udyam MSME entry. Every field tagged with its source. Lifecycle status: Active, supported by a recent GST return filing within the last three months. Reasoning shown verbatim for audit.",
    "The query Karnataka Commerce can never run today. Active factories in pincode five-six-zero-zero-five-eight with no inspection in eighteen months. Filter applies. Twelve businesses returned. Each one a real candidate for compliance follow-up. This is what unified business intelligence unlocks.",
    "Stack: FastAPI plus SQLAlchemy on the backend, React plus TypeScript on the frontend. rapidfuzz for probabilistic matching with Jaro-Winkler distance and token sort ratio. IndicSoundex for Indian name phonetics. Splink-compatible architecture for production scale. No source system is ever modified - UBID is a non-invasive overlay.",
    "Deployment is one VM. Reads CSV exports or polls REST APIs from each department. No PII reaches an external LLM. Pilot scope: three departments, two Bengaluru pincodes, ninety days. Year-one cost about twenty-eight lakhs. Karnataka spent eleven point eight crores building the Single Window System integration. UBID is the foundation it lacks.",
    "UBID Karnataka. One identifier per business, anchored to the central record where present, audit-safe everywhere else. Active business intelligence the state can finally trust. Thank you.",
]

def tts(text, out_path):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    body = json.dumps({
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.25, "use_speaker_boost": True},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "xi-api-key": API_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"
    }, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        out_path.write_bytes(r.read())

out_dir = Path("/Users/sridharsuresh/Documents/ai-for-bharat/docs/video-output/theme1/audio")
out_dir.mkdir(parents=True, exist_ok=True)

total = sum(len(u) for u in UNITS)
print(f"Voice: Rachel · {total} chars")
for i, txt in enumerate(UNITS, 1):
    mp3 = out_dir / f"unit_{i:02d}.mp3"
    print(f"[unit {i:02d}] {len(txt)} chars")
    tts(txt, mp3)

print("Converting to AIFF...")
for mp3 in sorted(out_dir.glob("unit_*.mp3")):
    aiff = mp3.with_suffix(".aiff")
    subprocess.run(["afconvert", "-f", "AIFF", "-d", "BEI16@44100", str(mp3), str(aiff)],
                   check=True, capture_output=True)
print("✓ Done")
