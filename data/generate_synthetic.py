"""Generate synthetic business data simulating Karnataka department registries.

Produces 3 CSV files (GST, MCA, Udyam) with ~500 records each.
~20% are deliberate duplicates with realistic noise (name variations,
address formatting, missing fields) to test entity resolution.

Also produces a ground truth file mapping which records are the same entity.

Usage:
    python generate_synthetic.py
"""

import csv
import hashlib
import os
import random
import string
from datetime import datetime, timedelta

# Seed for reproducibility
random.seed(42)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Karnataka-specific reference data ───────────────────────────────────────

BENGALURU_PINCODES = [
    "560001", "560002", "560003", "560004", "560005", "560008", "560009",
    "560010", "560011", "560017", "560018", "560022", "560025", "560029",
    "560030", "560034", "560037", "560038", "560040", "560041", "560043",
    "560045", "560047", "560048", "560050", "560052", "560053", "560055",
    "560058", "560060", "560062", "560064", "560066", "560068", "560070",
    "560071", "560073", "560076", "560078", "560079", "560085", "560092",
    "560094", "560095", "560097", "560098", "560100", "560102", "560103",
]

DISTRICTS = ["Bengaluru Urban", "Bengaluru Rural"]

AREAS = [
    "MG Road", "Jayanagar", "Koramangala", "Indiranagar", "Whitefield",
    "Electronic City", "BTM Layout", "HSR Layout", "Marathahalli",
    "Rajajinagar", "Malleshwaram", "Basavanagudi", "JP Nagar",
    "Banashankari", "Yelahanka", "Hebbal", "Peenya", "Bommanahalli",
    "KR Puram", "Mahadevapura", "Sarjapur Road", "Bellandur",
    "Varthur", "Hoodi", "Brookefield", "ITPL Main Road",
]

ROAD_TYPES = ["Road", "Main Road", "Cross", "Layout", "Extension", "Street", "Avenue"]

BUSINESS_FIRST_NAMES = [
    "Sharma", "Kumar", "Reddy", "Gowda", "Patel", "Singh", "Rao",
    "Naidu", "Shetty", "Hegde", "Murthy", "Swamy", "Prasad", "Nair",
    "Pillai", "Menon", "Iyer", "Gupta", "Jain", "Agarwal", "Mehta",
    "Shah", "Verma", "Mishra", "Pandey", "Tiwari", "Kulkarni",
    "Patil", "Deshmukh", "Kamath", "Bhat", "Shenoy", "Pai",
]

BUSINESS_SUFFIXES = [
    "Enterprises", "Trading Co.", "Industries", "Solutions",
    "Technologies", "Pvt Ltd", "Services", "Corporation",
    "Manufacturing", "Exports", "Associates", "Brothers",
    "& Sons", "& Co.", "Agency", "Works", "Mills",
    "Constructions", "Engineers", "Traders",
]

FIRST_NAMES = [
    "Rajesh", "Suresh", "Mahesh", "Ramesh", "Ganesh", "Mukesh",
    "Priya", "Divya", "Anita", "Sunita", "Kavita", "Rekha",
    "Arun", "Varun", "Kiran", "Mohan", "Sohan", "Rohan",
    "Deepa", "Seema", "Neha", "Pooja", "Ritu", "Sanjay",
    "Vijay", "Ajay", "Manoj", "Vinod", "Pramod", "Sunil",
    "Krishna", "Lakshmi", "Venkatesh", "Nagaraj", "Raghav",
]

LAST_NAMES = BUSINESS_FIRST_NAMES  # Reuse for owners

SECTORS = ["manufacturing", "services", "trading", "construction", "technology"]
BUSINESS_TYPES = ["proprietorship", "partnership", "pvt_ltd", "llp", "public_ltd"]

STATUSES_ACTIVE = ["Active", "active", "ACTIVE", "Live", "Registered"]
STATUSES_DORMANT = ["Dormant", "Inactive", "Suspended", "Default in Filing"]
STATUSES_CLOSED = ["Cancelled", "Struck Off", "Dissolved", "Closed", "Deregistered"]


# ─── Name variation generators ────────────────────────────────────────────────

def _name_variations(name: str) -> list[str]:
    """Generate realistic Indian business name variations."""
    variations = [name]

    # Abbreviations
    if "Private Limited" in name:
        variations.append(name.replace("Private Limited", "Pvt Ltd"))
        variations.append(name.replace("Private Limited", "Pvt. Ltd."))
    if "Pvt Ltd" in name:
        variations.append(name.replace("Pvt Ltd", "Private Limited"))
        variations.append(name.replace("Pvt Ltd", "Pvt. Ltd."))

    # Common Indian name phonetic variants
    for orig, repl in [
        ("Sharma", "Sarma"), ("Krishna", "Krushna"), ("Murthy", "Murthi"),
        ("Murthy", "Moorthy"), ("Reddy", "Reddi"), ("Shetty", "Shetti"),
        ("Gowda", "Gouda"), ("Swamy", "Swami"), ("Prasad", "Prashad"),
        ("Kumar", "Kumaar"), ("& Sons", "and Sons"), ("& Co.", "and Company"),
        ("Trading Co.", "Trading Company"), ("Technologies", "Tech"),
    ]:
        if orig in name:
            variations.append(name.replace(orig, repl))

    # Case variations
    variations.append(name.upper())

    # Typos (swap two adjacent chars)
    if len(name) > 5:
        pos = random.randint(2, len(name) - 3)
        typo = name[:pos] + name[pos + 1] + name[pos] + name[pos + 2:]
        variations.append(typo)

    return variations


def _address_variations(address: str) -> list[str]:
    """Generate address format variations."""
    variations = [address]

    for orig, repl in [
        ("Road", "Rd"), ("Rd", "Road"), ("Street", "St"), ("St", "Street"),
        ("Main Road", "Main Rd"), ("Cross", "Crs"),
        ("Bengaluru", "Bangalore"), ("Bangalore", "Bengaluru"),
        ("No.", "Number"), ("No.", "#"),
    ]:
        if orig in address:
            variations.append(address.replace(orig, repl))

    # Add/remove pincode formatting
    variations.append(address.replace(" - ", " "))
    variations.append(address.replace(", ", ","))

    return variations


def _owner_name_variations(name: str) -> list[str]:
    """Generate owner name variations."""
    variations = [name]
    parts = name.split()
    if len(parts) >= 2:
        # Initial + last name
        variations.append(f"{parts[0][0]}. {parts[-1]}")
        # Last name, First name
        variations.append(f"{parts[-1]}, {parts[0]}")

    # Phonetic variants
    for orig, repl in [
        ("Rajesh", "Raajesh"), ("Suresh", "Sureesh"), ("sh", "shh"),
        ("Kumar", "Kumaar"), ("Krishna", "Krushna"), ("Venkatesh", "Venkateesh"),
    ]:
        if orig in name:
            variations.append(name.replace(orig, repl))

    return variations


# ─── ID generators ────────────────────────────────────────────────────────────

def _generate_pan() -> str:
    """Generate a realistic PAN (AAAAA9999A format)."""
    letters = "".join(random.choices(string.ascii_uppercase, k=3))
    type_char = random.choice("PCFHAT")  # P=Person, C=Company, F=Firm, etc.
    last_letter = random.choice(string.ascii_uppercase)
    digits = "".join(random.choices(string.digits, k=4))
    return f"{letters}{type_char}{last_letter}{digits}{random.choice(string.ascii_uppercase)}"


def _generate_gstin(pan: str, state_code: str = "29") -> str:
    """Generate a GSTIN from PAN. Format: 29AAAAA9999A1Z5"""
    entity_num = random.choice(string.digits + "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    # Simplified check digit
    check = random.choice(string.digits + "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return f"{state_code}{pan}{entity_num}Z{check}"


def _generate_udyam() -> str:
    """Generate a Udyam registration number. Format: UDYAM-KA-00-0000000"""
    district = f"{random.randint(1, 30):02d}"
    serial = f"{random.randint(1, 9999999):07d}"
    return f"UDYAM-KA-{district}-{serial}"


def _generate_phone() -> str:
    """Generate an Indian mobile number."""
    prefix = random.choice(["9", "8", "7", "6"])
    return f"+91{prefix}{''.join(random.choices(string.digits, k=9))}"


def _generate_email(owner_name: str, business_name: str) -> str:
    """Generate a plausible email."""
    domain = random.choice(["gmail.com", "yahoo.co.in", "rediffmail.com", "outlook.com"])
    local = owner_name.lower().replace(" ", ".").replace(",", "")
    return f"{local}@{domain}"


def _random_date(start_year: int, end_year: int) -> str:
    """Generate a random date string."""
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = (end - start).days
    dt = start + timedelta(days=random.randint(0, delta))
    fmt = random.choice(["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"])
    return dt.strftime(fmt)


# ─── Entity generator ─────────────────────────────────────────────────────────

class BusinessEntity:
    """Represents one real-world business with all its ground truth data."""

    def __init__(self, entity_id: int):
        self.entity_id = entity_id
        self.pan = _generate_pan()
        self.gstin = _generate_gstin(self.pan) if random.random() > 0.15 else ""
        self.udyam = _generate_udyam() if random.random() > 0.6 else ""

        last_name = random.choice(BUSINESS_FIRST_NAMES)
        self.business_name = f"{last_name} {random.choice(BUSINESS_SUFFIXES)}"
        self.owner_name = f"{random.choice(FIRST_NAMES)} {last_name}"

        self.pincode = random.choice(BENGALURU_PINCODES)
        self.area = random.choice(AREAS)
        self.address = f"No. {random.randint(1, 500)}, {random.choice(['1st', '2nd', '3rd', '4th', '5th'])} {random.choice(ROAD_TYPES)}, {self.area}, Bengaluru - {self.pincode}"
        self.district = random.choice(DISTRICTS)
        self.phone = _generate_phone()
        self.email = _generate_email(self.owner_name, self.business_name)
        self.sector = random.choice(SECTORS)
        self.business_type = random.choice(BUSINESS_TYPES)
        self.registration_date = _random_date(2000, 2022)

        # Lifecycle status
        status_roll = random.random()
        if status_roll < 0.65:
            self.status = "active"
            self.last_filing = _random_date(2025, 2026)
        elif status_roll < 0.85:
            self.status = "dormant"
            self.last_filing = _random_date(2023, 2024)
        else:
            self.status = "closed"
            self.last_filing = _random_date(2020, 2022)

    def to_gst_record(self, add_noise: bool = False) -> dict:
        """Generate a GST registry record."""
        name = random.choice(_name_variations(self.business_name)) if add_noise else self.business_name
        addr = random.choice(_address_variations(self.address)) if add_noise else self.address
        owner = random.choice(_owner_name_variations(self.owner_name)) if add_noise else self.owner_name

        status_map = {
            "active": random.choice(STATUSES_ACTIVE),
            "dormant": random.choice(STATUSES_DORMANT),
            "closed": random.choice(STATUSES_CLOSED),
        }

        return {
            "gstin": self.gstin if (self.gstin and random.random() > 0.05) else "",
            "pan_number": self.pan if random.random() > 0.1 else "",
            "business_name": name,
            "proprietor": owner if random.random() > 0.2 else "",
            "registered_address": addr,
            "pin_code": self.pincode if random.random() > 0.05 else "",
            "state": "Karnataka",
            "district_name": self.district,
            "constitution": self.business_type,
            "business_activity": self.sector,
            "contact_number": self.phone if random.random() > 0.3 else "",
            "email_id": self.email if random.random() > 0.4 else "",
            "date_of_registration": self.registration_date,
            "last_return_date": self.last_filing,
            "registration_status": status_map[self.status],
        }

    def to_mca_record(self, add_noise: bool = False) -> dict:
        """Generate an MCA (Ministry of Corporate Affairs) record."""
        name = random.choice(_name_variations(self.business_name)) if add_noise else self.business_name
        addr = random.choice(_address_variations(self.address)) if add_noise else self.address
        owner = random.choice(_owner_name_variations(self.owner_name)) if add_noise else self.owner_name

        status_map = {
            "active": "Active",
            "dormant": "Dormant under section 455",
            "closed": random.choice(["Struck Off", "Dissolved", "Under Liquidation"]),
        }

        return {
            "cin": f"U{random.randint(10000, 99999)}KA{self.registration_date[-4:]}PTC{random.randint(100000, 999999)}",
            "company_name": name,
            "entity_type": self.business_type.replace("_", " ").title(),
            "director_name": owner if random.random() > 0.15 else "",
            "full_address": addr,
            "pincode": self.pincode if random.random() > 0.08 else "",
            "state_name": "KARNATAKA",
            "city": self.district,
            "pan": self.pan if random.random() > 0.2 else "",
            "industry": self.sector,
            "incorporation_date": self.registration_date,
            "last_annual_return": self.last_filing if random.random() > 0.15 else "",
            "current_status": status_map[self.status],
        }

    def to_udyam_record(self, add_noise: bool = False) -> dict:
        """Generate a Udyam/MSME registry record."""
        name = random.choice(_name_variations(self.business_name)) if add_noise else self.business_name
        addr = random.choice(_address_variations(self.address)) if add_noise else self.address
        owner = random.choice(_owner_name_variations(self.owner_name)) if add_noise else self.owner_name

        return {
            "udyam_number": self.udyam if self.udyam else _generate_udyam(),
            "enterprise_name": name,
            "applicant_name": owner,
            "premises_address": addr,
            "pin": self.pincode if random.random() > 0.05 else "",
            "state": "KARNATAKA" if random.random() > 0.3 else "Karnataka",
            "district": self.district,
            "mobile": self.phone.replace("+91", "") if random.random() > 0.2 else "",
            "email_address": self.email if random.random() > 0.5 else "",
            "nic_code": f"{random.randint(10, 99)}{random.randint(100, 999)}",
            "activity": self.sector,
            "established_date": self.registration_date,
            "last_activity_date": self.last_filing if random.random() > 0.25 else "",
            "entity_status": "Active" if self.status == "active" else "Inactive",
        }


def generate_data(
    n_entities: int = 400,
    duplicate_rate: float = 0.2,
    records_per_system: int = 500,
):
    """Generate synthetic data for 3 registry systems."""
    print(f"Generating {n_entities} unique business entities...")
    entities = [BusinessEntity(i) for i in range(n_entities)]

    # Create duplicate pool (~20% of entities appear in multiple systems with noise)
    n_duplicates = int(n_entities * duplicate_rate)
    duplicate_entities = random.sample(entities, n_duplicates)

    ground_truth = []  # (entity_id, source_system, record_index)

    # ─── GST Registry ─────────────────────────────────────────────────────
    gst_records = []
    for i, entity in enumerate(entities):
        gst_records.append(entity.to_gst_record(add_noise=False))
        ground_truth.append({"entity_id": entity.entity_id, "source": "gst", "record_idx": i})

    # Add noisy duplicates
    for entity in duplicate_entities[:n_duplicates // 2]:
        idx = len(gst_records)
        gst_records.append(entity.to_gst_record(add_noise=True))
        ground_truth.append({"entity_id": entity.entity_id, "source": "gst", "record_idx": idx})

    # ─── MCA Registry ─────────────────────────────────────────────────────
    mca_records = []
    # Only companies/LLPs appear in MCA (not all proprietorships)
    mca_entities = [e for e in entities if e.business_type in ("pvt_ltd", "llp", "public_ltd", "partnership")]
    for i, entity in enumerate(mca_entities):
        mca_records.append(entity.to_mca_record(add_noise=False))
        ground_truth.append({"entity_id": entity.entity_id, "source": "mca", "record_idx": i})

    # Add noisy duplicates
    for entity in random.sample(mca_entities, min(n_duplicates // 3, len(mca_entities))):
        idx = len(mca_records)
        mca_records.append(entity.to_mca_record(add_noise=True))
        ground_truth.append({"entity_id": entity.entity_id, "source": "mca", "record_idx": idx})

    # ─── Udyam Registry ───────────────────────────────────────────────────
    udyam_records = []
    # MSMEs — mix of all types
    udyam_entities = random.sample(entities, min(records_per_system, len(entities)))
    for i, entity in enumerate(udyam_entities):
        udyam_records.append(entity.to_udyam_record(add_noise=False))
        ground_truth.append({"entity_id": entity.entity_id, "source": "udyam", "record_idx": i})

    # Add noisy duplicates
    for entity in duplicate_entities[n_duplicates // 2:]:
        idx = len(udyam_records)
        udyam_records.append(entity.to_udyam_record(add_noise=True))
        ground_truth.append({"entity_id": entity.entity_id, "source": "udyam", "record_idx": idx})

    # ─── Write CSVs ───────────────────────────────────────────────────────
    _write_csv(os.path.join(OUTPUT_DIR, "synthetic_businesses_gst.csv"), gst_records)
    _write_csv(os.path.join(OUTPUT_DIR, "synthetic_businesses_mca.csv"), mca_records)
    _write_csv(os.path.join(OUTPUT_DIR, "synthetic_businesses_udyam.csv"), udyam_records)
    _write_csv(os.path.join(OUTPUT_DIR, "synthetic_ground_truth.csv"), ground_truth)

    print(f"\nGenerated:")
    print(f"  GST:    {len(gst_records)} records")
    print(f"  MCA:    {len(mca_records)} records")
    print(f"  Udyam:  {len(udyam_records)} records")
    print(f"  Ground truth: {len(ground_truth)} entries ({n_entities} unique entities)")
    print(f"\nFiles written to: {OUTPUT_DIR}")


def _write_csv(path: str, records: list[dict]):
    """Write records to a CSV file."""
    if not records:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)


if __name__ == "__main__":
    generate_data()
