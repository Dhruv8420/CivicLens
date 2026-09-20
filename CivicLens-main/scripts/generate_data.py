"""
CivicLens — Synthetic Project Dataset Generator
=================================================

PURPOSE:
    Generates exactly 100 synthetic public-development project records
    for the CivicLens hackathon prototype/demo.

IMPORTANT DISCLAIMER:
    This is SYNTHETIC data created for demonstration and testing purposes ONLY.
    It does NOT represent real government projects, real expenditures, or real
    departments. Any resemblance to actual projects is coincidental.

WHY ANOMALIES ARE PLANTED:
    Approximately 15 records contain intentionally planted anomalous patterns.
    These anomalies are NOT labeled in the output CSV — the CivicLens detection
    engine must discover them independently. The planted anomalies cover:

    1. Cost anomaly     — unusually high original cost compared to sector peers
    2. Progress mismatch — high expenditure (%) but low physical progress (%)
    3. Cost overrun      — revised cost significantly exceeds original cost
    4. Delay             — revised completion date far beyond target date

    The remaining ~85 records are "normal" with realistic, internally consistent
    values.

DETERMINISM:
    Uses a fixed random seed (SEED = 42) so every run produces the identical
    dataset. This ensures reproducibility across dev machines.

OUTPUT:
    backend/data/sample_projects.csv  (100 rows, 14 columns)

USAGE:
    python scripts/generate_data.py
"""

import csv
import os
import random
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEED = 42
NUM_RECORDS = 100
OUTPUT_DIR = os.path.join("backend", "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "sample_projects.csv")

SECTORS = ["Transport", "Energy", "Water", "Education", "Health"]

STATES = [
    "Maharashtra", "Tamil Nadu", "Karnataka", "Uttar Pradesh",
    "Rajasthan", "Gujarat", "Madhya Pradesh", "Kerala",
    "West Bengal", "Odisha", "Bihar", "Andhra Pradesh",
]

DEPARTMENTS = {
    "Transport": "Ministry of Road Transport and Highways",
    "Energy": "Ministry of New and Renewable Energy",
    "Water": "Ministry of Jal Shakti",
    "Education": "Ministry of Education",
    "Health": "Ministry of Health and Family Welfare",
}

# Project name templates per sector.
# Each tuple: (name_template, description_template)
PROJECT_TEMPLATES = {
    "Transport": [
        (
            "{state} State Highway {rid} Widening",
            "Widening and strengthening of state highway {rid} in {district} district, {state}, from 2-lane to 4-lane configuration.",
        ),
        (
            "{state} Rural Road Connectivity Phase {rid}",
            "Construction of rural all-weather roads connecting {n_villages} villages in {district} district, {state}, under PMGSY.",
        ),
        (
            "{state} Bridge Construction on River {river}",
            "Construction of a reinforced concrete bridge over River {river} in {district} district, {state}, with approach roads.",
        ),
        (
            "{state} Flyover at {district} Junction",
            "Construction of a multi-lane flyover at {district} junction, {state}, to reduce traffic congestion.",
        ),
    ],
    "Energy": [
        (
            "{state} Solar Power Plant {rid} MW",
            "Installation of a {rid} MW solar photovoltaic power plant in {district} district, {state}.",
        ),
        (
            "{state} Power Substation Upgrade {district}",
            "Upgrading the 132/33 kV power substation in {district}, {state}, to improve distribution capacity.",
        ),
        (
            "{state} Rural Electrification Scheme {rid}",
            "Electrification of {n_villages} un-electrified households in {district} district, {state}.",
        ),
        (
            "{state} Wind Energy Project Phase {rid}",
            "Installation of wind turbines with {rid} MW capacity in {district} district, {state}.",
        ),
    ],
    "Water": [
        (
            "{state} Water Pipeline Extension {district}",
            "Laying of {km} km water supply pipeline from {district} reservoir to surrounding villages in {state}.",
        ),
        (
            "{state} Water Treatment Plant {district}",
            "Construction of a {mld} MLD water treatment plant in {district} district, {state}.",
        ),
        (
            "{state} Drainage Improvement Scheme {rid}",
            "Improvement of storm water drainage system in {district} town, {state}, covering {km} km.",
        ),
        (
            "{state} Irrigation Canal Modernization {rid}",
            "Modernization and lining of irrigation canal network in {district} district, {state}, covering {km} km.",
        ),
    ],
    "Education": [
        (
            "{state} Government School Construction {district}",
            "Construction of a new government senior secondary school with {n_rooms} classrooms in {district}, {state}.",
        ),
        (
            "{state} College Infrastructure Upgrade {district}",
            "Upgrading infrastructure of government degree college in {district}, {state}, including labs and library.",
        ),
        (
            "{state} District Library Construction {district}",
            "Construction of a modern district public library in {district}, {state}, with digital resource center.",
        ),
        (
            "{state} Skill Development Center {district}",
            "Establishment of a vocational skill development center in {district} district, {state}.",
        ),
    ],
    "Health": [
        (
            "{state} District Hospital Upgrade {district}",
            "Upgrading the district hospital in {district}, {state}, with additional wards and modern equipment.",
        ),
        (
            "{state} Primary Health Center {district}",
            "Construction of a new primary health center in {district} block, {state}, with staff quarters.",
        ),
        (
            "{state} Medical College Expansion {district}",
            "Expansion of government medical college in {district}, {state}, adding {n_rooms} seats and hostel.",
        ),
        (
            "{state} Community Health Center {district}",
            "Establishment of a 30-bed community health center in {district} district, {state}.",
        ),
    ],
}

# Typical cost ranges per sector (in Lakhs). These define the "normal" band.
# Projects outside these ranges (for the same sector) will be flagged by IQR.
COST_RANGES = {
    "Transport": (500, 5000),
    "Energy": (400, 4000),
    "Water": (300, 3000),
    "Education": (200, 1500),
    "Health": (300, 2500),
}

RIVERS = ["Ganga", "Yamuna", "Godavari", "Krishna", "Narmada", "Cauvery", "Tapti"]

DISTRICTS = {
    "Maharashtra": ["Pune", "Nashik", "Nagpur", "Aurangabad", "Kolhapur"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli"],
    "Karnataka": ["Bengaluru", "Mysuru", "Hubballi", "Mangaluru", "Belagavi"],
    "Uttar Pradesh": ["Lucknow", "Agra", "Varanasi", "Kanpur", "Allahabad"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Gandhinagar"],
    "Madhya Pradesh": ["Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain"],
    "Kerala": ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kollam"],
    "West Bengal": ["Kolkata", "Howrah", "Siliguri", "Durgapur", "Asansol"],
    "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela", "Berhampur", "Sambalpur"],
    "Bihar": ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Darbhanga"],
    "Andhra Pradesh": ["Vijayawada", "Visakhapatnam", "Tirupati", "Guntur", "Nellore"],
}

STATUS_VALUES = ["Planning", "In Progress", "Completed", "Stalled"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _random_date(start: date, end: date) -> date:
    """Return a random date between start and end (inclusive)."""
    delta = (end - start).days
    if delta <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta))


def _round2(value: float) -> float:
    """Round to 2 decimal places."""
    return round(value, 2)


def _make_project_id(index: int) -> str:
    """Generate a unique project ID like PRJ-001."""
    return f"PRJ-{index:03d}"


def _generate_name_and_desc(sector: str, state: str, rid: int) -> tuple[str, str]:
    """Pick a random template for the sector and fill in placeholders."""
    templates = PROJECT_TEMPLATES[sector]
    name_tmpl, desc_tmpl = random.choice(templates)

    district = random.choice(DISTRICTS[state])
    river = random.choice(RIVERS)

    fmt = {
        "state": state,
        "district": district,
        "rid": rid,
        "river": river,
        "n_villages": random.randint(15, 80),
        "n_rooms": random.randint(8, 30),
        "km": random.randint(5, 60),
        "mld": random.randint(5, 50),
    }

    return name_tmpl.format(**fmt), desc_tmpl.format(**fmt)


# ---------------------------------------------------------------------------
# Normal record generator
# ---------------------------------------------------------------------------
def _generate_normal_record(index: int) -> dict:
    """
    Generate a single 'normal' project record with internally consistent,
    realistic values. No intentional anomalies.
    """
    sector = random.choice(SECTORS)
    state = random.choice(STATES)
    name, desc = _generate_name_and_desc(sector, state, index)

    cost_lo, cost_hi = COST_RANGES[sector]
    original_cost = _round2(random.uniform(cost_lo, cost_hi))

    # Normal: revised cost is 0–15% above original (minor routine revision)
    overrun_factor = random.uniform(1.0, 1.15)
    revised_cost = _round2(original_cost * overrun_factor)

    # Timeline: mix of older and newer projects for status variety.
    # ~80% start 2019–2023 (most will be past deadline by Sep 2026),
    # ~20% start 2024–2026 (recent — some still in Planning/In Progress).
    if random.random() < 0.80:
        start = _random_date(date(2019, 1, 1), date(2023, 6, 30))
        duration_days = random.randint(365, 365 * 3)
    else:
        start = _random_date(date(2025, 6, 1), date(2026, 8, 15))
        duration_days = random.randint(365 * 2, 365 * 4)
    target = start + timedelta(days=duration_days)

    # Determine status and physical progress consistently
    today = date(2026, 9, 18)  # Fixed "today" for reproducibility
    days_elapsed = (today - start).days
    total_days = (target - start).days
    time_fraction = min(days_elapsed / max(total_days, 1), 1.0)

    # Pick a status consistent with the timeline
    if time_fraction < 0.15:
        status = "Planning"
        physical_pct = _round2(random.uniform(0, 5))
    elif time_fraction >= 1.0:
        # Past deadline — most completed, a few stalled
        status = random.choices(
            ["Completed", "In Progress", "Stalled"], weights=[75, 15, 10]
        )[0]
        if status == "Completed":
            physical_pct = _round2(random.uniform(90, 100))
        elif status == "Stalled":
            physical_pct = _round2(random.uniform(20, 55))
        else:
            physical_pct = _round2(random.uniform(70, 95))
    else:
        status = "In Progress"
        # Physical progress roughly tracks time, with some variance
        physical_pct = _round2(
            min(100, max(0, time_fraction * 100 + random.uniform(-15, 10)))
        )

    # Expenditure roughly tracks physical progress (normal behaviour)
    expenditure_fraction = physical_pct / 100 * random.uniform(0.85, 1.15)
    expenditure = _round2(min(revised_cost, revised_cost * expenditure_fraction))

    # Revised completion date: only set if project slipped slightly
    revised_completion = None
    if status == "In Progress" and today > target:
        # Small slip: 1–6 months
        revised_completion = target + timedelta(days=random.randint(30, 180))

    return {
        "project_id": _make_project_id(index),
        "project_name": name,
        "description": desc,
        "department": DEPARTMENTS[sector],
        "state": state,
        "sector": sector,
        "original_cost_lakhs": original_cost,
        "revised_cost_lakhs": revised_cost,
        "expenditure_lakhs": expenditure,
        "physical_progress_pct": physical_pct,
        "start_date": start.isoformat(),
        "target_completion_date": target.isoformat(),
        "revised_completion_date": revised_completion.isoformat() if revised_completion else "",
        "status": status,
    }


# ---------------------------------------------------------------------------
# Anomaly planters
# ---------------------------------------------------------------------------
# Each function takes a normal record and mutates it to inject a specific
# anomaly pattern. The anomaly is NOT labeled in the CSV — the detection
# engine must discover it.

def _plant_cost_anomaly(record: dict) -> dict:
    """
    COST ANOMALY: Set original_cost_lakhs to 3.8–5× the sector's upper bound,
    making it a clear statistical outlier when compared to sector peers via IQR.
    """
    sector = record["sector"]
    _, cost_hi = COST_RANGES[sector]
    new_orig = _round2(random.uniform(cost_hi * 3.8, cost_hi * 5.0))

    # Calculate current overrun factor (if cost overrun was already applied)
    old_orig = record["original_cost_lakhs"]
    old_rev = record["revised_cost_lakhs"]
    overrun_factor = old_rev / old_orig if old_orig > 0 else 1.05

    record["original_cost_lakhs"] = new_orig
    if overrun_factor >= 1.35:
        record["revised_cost_lakhs"] = _round2(new_orig * overrun_factor)
    else:
        record["revised_cost_lakhs"] = _round2(new_orig * random.uniform(1.02, 1.10))

    # Calculate financial progress ratio (if expenditure was already set)
    old_rev_cost = max(old_rev, 1.0)
    fin_pct = record["expenditure_lakhs"] / old_rev_cost
    if fin_pct >= 0.50:
        record["expenditure_lakhs"] = _round2(record["revised_cost_lakhs"] * min(fin_pct, 0.90))
    else:
        pct = record["physical_progress_pct"] / 100
        record["expenditure_lakhs"] = _round2(
            record["revised_cost_lakhs"] * pct * random.uniform(0.9, 1.1)
        )
    return record


def _plant_progress_mismatch(record: dict) -> dict:
    """
    EXPENDITURE vs PHYSICAL PROGRESS MISMATCH: High financial spend (70–90%
    of budget) but very low physical completion (5–15%). This creates a gap
    of 55+ percentage points, well above the 25-point detection threshold.
    """
    record["status"] = "In Progress"
    record["physical_progress_pct"] = _round2(random.uniform(5, 15))
    spend_pct = random.uniform(0.70, 0.90)
    record["expenditure_lakhs"] = _round2(
        record["revised_cost_lakhs"] * spend_pct
    )
    return record


def _plant_cost_overrun(record: dict) -> dict:
    """
    COST OVERRUN: revised_cost is 60–110% higher than original_cost,
    well above the 20% detection threshold.
    """
    overrun_factor = random.uniform(1.60, 2.10)
    old_rev = max(record["revised_cost_lakhs"], 1.0)
    fin_pct = record["expenditure_lakhs"] / old_rev

    record["revised_cost_lakhs"] = _round2(
        record["original_cost_lakhs"] * overrun_factor
    )

    if fin_pct >= 0.50:
        record["expenditure_lakhs"] = _round2(
            record["revised_cost_lakhs"] * min(fin_pct, 0.90)
        )
    else:
        record["expenditure_lakhs"] = _round2(
            min(record["expenditure_lakhs"], record["revised_cost_lakhs"] * 0.7)
        )
    return record


def _plant_delay(record: dict) -> dict:
    """
    DELAY: Project is significantly overdue. revised_completion_date is set
    1.5–2+ years prior to reference date (2026-09-18), with status 'In Progress'.
    """
    record["status"] = "In Progress"
    ref_date = date(2026, 9, 18)
    delay_past_days = random.randint(500, 730)
    revised_date = ref_date - timedelta(days=delay_past_days)
    target_date = revised_date - timedelta(days=random.randint(180, 365))

    record["target_completion_date"] = target_date.isoformat()
    record["revised_completion_date"] = revised_date.isoformat()

    if record["physical_progress_pct"] > 20:
        record["physical_progress_pct"] = _round2(random.uniform(30, 65))
        spend_pct = record["physical_progress_pct"] / 100 * random.uniform(0.9, 1.3)
        record["expenditure_lakhs"] = _round2(
            record["revised_cost_lakhs"] * min(spend_pct, 0.85)
        )
    return record


# ---------------------------------------------------------------------------
# Master anomaly plan
# ---------------------------------------------------------------------------
# Maps record index → anomaly planter function.
# These indices are chosen to spread anomalies across the dataset.
# Some records receive a SINGLE anomaly type; a few receive overlapping anomalies.
#
# Total unique anomalous records: 15
# Breakdown:
#   Cost anomaly only:        indices 7, 23, 55, 78                                 (4)
#   Progress mismatch only:   indices 12, 38, 64, 91                                (4)
#   Cost overrun only:        indices 45                                            (1)
#   Delay only:               indices 58                                            (1)
#   2-way Overlaps:           indices 19 (mismatch+overrun), 31 (mismatch+delay),  (3)
#                             72 (cost anomaly+overrun)
#   3-way Overlap:            index 85 (cost anomaly+mismatch+delay)                (1)
#   4-way Overlap:            index 50 (cost anomaly+overrun+mismatch+delay)        (1)
#
ANOMALY_PLAN: dict[int, list] = {
    7:  [_plant_cost_anomaly],
    12: [_plant_progress_mismatch],
    19: [_plant_progress_mismatch, _plant_cost_overrun],
    23: [_plant_cost_anomaly],
    31: [_plant_progress_mismatch, _plant_delay],
    38: [_plant_progress_mismatch],
    45: [_plant_cost_overrun],
    50: [_plant_cost_anomaly, _plant_cost_overrun, _plant_progress_mismatch, _plant_delay],
    55: [_plant_cost_anomaly],
    58: [_plant_delay],
    64: [_plant_progress_mismatch],
    72: [_plant_cost_anomaly, _plant_cost_overrun],
    78: [_plant_cost_anomaly],
    85: [_plant_cost_anomaly, _plant_progress_mismatch, _plant_delay],
    91: [_plant_progress_mismatch],
}

# Human-readable mapping for development/testing reference (NOT in CSV)
ANOMALY_REFERENCE = {
    7:  "Cost anomaly (unusually high cost for sector)",
    12: "Expenditure vs physical progress mismatch",
    19: "Compound: Expenditure vs physical progress mismatch + Cost overrun",
    23: "Cost anomaly (unusually high cost for sector)",
    31: "Compound: Expenditure vs physical progress mismatch + Delay",
    38: "Expenditure vs physical progress mismatch",
    45: "Cost overrun (revised >> original)",
    50: "Compound: 4-way Overlap (Cost anomaly + Cost overrun + Progress mismatch + Delay)",
    55: "Cost anomaly (unusually high cost for sector)",
    58: "Delay (revised completion >> target)",
    64: "Expenditure vs physical progress mismatch",
    72: "Compound: Cost anomaly + Cost overrun",
    78: "Cost anomaly (unusually high cost for sector)",
    85: "Compound: 3-way Overlap (Cost anomaly + Progress mismatch + Delay)",
    91: "Expenditure vs physical progress mismatch",
}


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------
def generate_dataset() -> list[dict]:
    """
    Generate 100 synthetic project records.

    1. Create 100 normal baseline records.
    2. Apply anomaly planters to the 15 designated indices.
    3. Return the final list of records (anomalies are NOT labeled).
    """
    random.seed(SEED)
    records = []

    for i in range(1, NUM_RECORDS + 1):
        record = _generate_normal_record(i)

        # Apply anomaly planters if this index is in the plan
        if i in ANOMALY_PLAN:
            for planter in ANOMALY_PLAN[i]:
                record = planter(record)

        records.append(record)

    return records


def save_csv(records: list[dict], filepath: str) -> None:
    """Write records to CSV."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    fieldnames = [
        "project_id",
        "project_name",
        "description",
        "department",
        "state",
        "sector",
        "original_cost_lakhs",
        "revised_cost_lakhs",
        "expenditure_lakhs",
        "physical_progress_pct",
        "start_date",
        "target_completion_date",
        "revised_completion_date",
        "status",
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def print_anomaly_reference() -> None:
    """
    Print the anomaly reference for DEVELOPMENT/TESTING purposes only.
    This information is NOT included in the CSV output.
    """
    print("\n" + "=" * 70)
    print("PLANTED ANOMALY REFERENCE (for dev/testing — NOT in CSV)")
    print("=" * 70)
    for idx in sorted(ANOMALY_REFERENCE):
        pid = _make_project_id(idx)
        print(f"  {pid}  ->  {ANOMALY_REFERENCE[idx]}")
    print(f"\nTotal anomalous records: {len(ANOMALY_REFERENCE)}")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("CivicLens — Synthetic Dataset Generator")
    print("-" * 40)
    print(f"Seed:    {SEED}")
    print(f"Records: {NUM_RECORDS}")
    print(f"Output:  {OUTPUT_FILE}")
    print()

    records = generate_dataset()
    save_csv(records, OUTPUT_FILE)

    print(f"[OK] Generated {len(records)} records -> {OUTPUT_FILE}")
    print_anomaly_reference()
