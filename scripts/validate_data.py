"""
CivicLens — Dataset Validation Script
Validates the generated sample_projects.csv against all schema and data
quality requirements.
"""

import pandas as pd
import sys

CSV_PATH = "backend/data/sample_projects.csv"

REQUIRED_COLUMNS = [
    "project_id", "project_name", "description", "department", "state",
    "sector", "original_cost_lakhs", "revised_cost_lakhs", "expenditure_lakhs",
    "physical_progress_pct", "start_date", "target_completion_date",
    "revised_completion_date", "status",
]

EXPECTED_SECTORS = {"Transport", "Energy", "Water", "Education", "Health"}
VALID_STATUSES = {"Planning", "In Progress", "Completed", "Stalled"}


def validate():
    print("=" * 60)
    print("CivicLens Dataset Validation")
    print("=" * 60)

    df = pd.read_csv(CSV_PATH)
    errors = []

    # 1. Row count
    print(f"\n[1] Row count: {len(df)}", end="")
    if len(df) == 100:
        print("  [PASS]")
    else:
        print("  [FAIL]")
        errors.append(f"Expected 100 rows, got {len(df)}")

    # 2. Column count and names
    print(f"[2] Column count: {len(df.columns)}", end="")
    if list(df.columns) == REQUIRED_COLUMNS:
        print("  [PASS]")
    else:
        print("  [FAIL]")
        missing = set(REQUIRED_COLUMNS) - set(df.columns)
        extra = set(df.columns) - set(REQUIRED_COLUMNS)
        if missing:
            errors.append(f"Missing columns: {missing}")
        if extra:
            errors.append(f"Extra columns: {extra}")

    # 3. project_id uniqueness
    dupes = df["project_id"].duplicated().sum()
    print(f"[3] project_id unique: {dupes} duplicates", end="")
    if dupes == 0:
        print("  [PASS]")
    else:
        print("  [FAIL]")
        errors.append(f"{dupes} duplicate project_ids")

    # 4. Missing values (revised_completion_date allowed to be empty)
    required_cols = [c for c in REQUIRED_COLUMNS if c != "revised_completion_date"]
    missing_counts = df[required_cols].isnull().sum()
    total_missing = missing_counts.sum()
    print(f"[4] Missing values (required fields): {total_missing}", end="")
    if total_missing == 0:
        print("  [PASS]")
    else:
        print("  [FAIL]")
        for col, cnt in missing_counts.items():
            if cnt > 0:
                errors.append(f"Missing values in {col}: {cnt}")

    # 5. Valid dates
    date_issues = 0
    for col in ["start_date", "target_completion_date"]:
        try:
            pd.to_datetime(df[col], format="%Y-%m-%d")
        except Exception as e:
            date_issues += 1
            errors.append(f"Invalid dates in {col}: {e}")

    # Check revised_completion_date where not empty
    revised = df["revised_completion_date"].dropna()
    revised = revised[revised != ""]
    try:
        pd.to_datetime(revised, format="%Y-%m-%d")
    except Exception as e:
        date_issues += 1
        errors.append(f"Invalid revised_completion_date: {e}")

    print(f"[5] Date validation: {date_issues} issues", end="")
    print("  [PASS]" if date_issues == 0 else "  [FAIL]")

    # 6. target_completion_date > start_date
    starts = pd.to_datetime(df["start_date"])
    targets = pd.to_datetime(df["target_completion_date"])
    bad_dates = (targets <= starts).sum()
    print(f"[6] target > start_date: {bad_dates} violations", end="")
    if bad_dates == 0:
        print("  [PASS]")
    else:
        print("  [FAIL]")
        errors.append(f"{bad_dates} rows where target <= start")

    # 7. physical_progress_pct in [0, 100]
    bad_pct = ((df["physical_progress_pct"] < 0) | (df["physical_progress_pct"] > 100)).sum()
    print(f"[7] physical_progress_pct [0-100]: {bad_pct} violations", end="")
    if bad_pct == 0:
        print("  [PASS]")
    else:
        print("  [FAIL]")
        errors.append(f"{bad_pct} rows with invalid physical_progress_pct")

    # 8. Costs positive
    bad_orig = (df["original_cost_lakhs"] <= 0).sum()
    bad_rev = (df["revised_cost_lakhs"] <= 0).sum()
    print(f"[8] Costs positive: orig={bad_orig}, revised={bad_rev} violations", end="")
    if bad_orig == 0 and bad_rev == 0:
        print("  [PASS]")
    else:
        print("  [FAIL]")
        errors.append(f"Non-positive costs: original={bad_orig}, revised={bad_rev}")

    # 9. expenditure non-negative
    bad_exp = (df["expenditure_lakhs"] < 0).sum()
    print(f"[9] Expenditure non-negative: {bad_exp} violations", end="")
    if bad_exp == 0:
        print("  [PASS]")
    else:
        print("  [FAIL]")
        errors.append(f"{bad_exp} rows with negative expenditure")

    # 10. revised_cost >= original_cost
    bad_overrun = (df["revised_cost_lakhs"] < df["original_cost_lakhs"]).sum()
    print(f"[10] revised >= original cost: {bad_overrun} violations", end="")
    if bad_overrun == 0:
        print("  [PASS]")
    else:
        print("  [FAIL]")
        errors.append(f"{bad_overrun} rows where revised < original cost")

    # 11. Sector distribution
    print(f"\n[11] Sector distribution:")
    sector_counts = df["sector"].value_counts()
    for s in EXPECTED_SECTORS:
        cnt = sector_counts.get(s, 0)
        print(f"     {s}: {cnt}")
    unexpected = set(df["sector"].unique()) - EXPECTED_SECTORS
    if unexpected:
        errors.append(f"Unexpected sectors: {unexpected}")
        print(f"     [FAIL] Unexpected: {unexpected}")
    else:
        print("     [PASS]")

    # 12. Status distribution
    print(f"\n[12] Status distribution:")
    status_counts = df["status"].value_counts()
    for s in VALID_STATUSES:
        cnt = status_counts.get(s, 0)
        print(f"     {s}: {cnt}")
    unexpected_status = set(df["status"].unique()) - VALID_STATUSES
    if unexpected_status:
        errors.append(f"Unexpected statuses: {unexpected_status}")
        print(f"     [FAIL] Unexpected: {unexpected_status}")
    else:
        print("     [PASS]")

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"VALIDATION FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("ALL VALIDATIONS PASSED")
    print("=" * 60)

    # Show first 5 rows
    print("\nFirst 5 rows (selected columns):")
    display_cols = [
        "project_id", "sector", "state", "original_cost_lakhs",
        "revised_cost_lakhs", "expenditure_lakhs", "physical_progress_pct", "status",
    ]
    print(df[display_cols].head(5).to_string(index=False))

    # Show basic stats
    print(f"\nCost stats (original_cost_lakhs):")
    print(f"  Min:    {df['original_cost_lakhs'].min()}")
    print(f"  Max:    {df['original_cost_lakhs'].max()}")
    print(f"  Mean:   {df['original_cost_lakhs'].mean():.2f}")
    print(f"  Median: {df['original_cost_lakhs'].median():.2f}")


if __name__ == "__main__":
    validate()
