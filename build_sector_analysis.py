
from pathlib import Path

import pandas as pd
import geopandas as gpd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent

CENSUS_FILE = ROOT / "data" / "census" / "PHC5_Public_microdata.dta"
FACILITIES_FILE = ROOT / "data" / "facilities" / "health_facilities.geojson"
CROSSWALK_FILE = ROOT / "outputs" / "sector_crosswalk_check.csv"
OUTPUT_FILE = ROOT / "outputs" / "sector_analysis.csv"

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. CHECK INPUT FILES
# ============================================================

for path in [CENSUS_FILE, FACILITIES_FILE, CROSSWALK_FILE]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

print("All required files were found.")


# ============================================================
# 3. LOAD CENSUS GEOGRAPHY AND POPULATION WEIGHTS
# ============================================================

print("\nLoading census data...")

census = pd.read_stata(
    CENSUS_FILE,
    columns=["ml01", "ml02", "ml03", "Pop_weight"],
    convert_categoricals=False,
)

for col in ["ml01", "ml02", "ml03", "Pop_weight"]:
    census[col] = pd.to_numeric(census[col], errors="coerce")

census = census.dropna(
    subset=["ml01", "ml02", "ml03", "Pop_weight"]
).copy()

# IMPORTANT:
# ml03 already contains the complete sector code, e.g. 1101.
# Do NOT concatenate ml02 and ml03.
census["sector_code"] = (
    census["ml03"].round().astype(int).astype(str)
)

print(f"Census records used: {len(census):,}")
print(f"Distinct census sectors: {census['sector_code'].nunique():,}")


# ============================================================
# 4. CALCULATE SECTOR POPULATION ESTIMATES
# ============================================================

print("\nCalculating sector population estimates...")

population = (
    census.groupby("sector_code", as_index=False)
    .agg(
        estimated_population=("Pop_weight", "sum"),
        census_records=("Pop_weight", "size"),
    )
)

print(f"Sectors with population estimates: {len(population):,}")


# ============================================================
# 5. LOAD SECTOR NAMES FROM THE EXISTING CROSSWALK
# ============================================================

print("\nLoading sector crosswalk...")

crosswalk = pd.read_csv(
    CROSSWALK_FILE,
    dtype={"sector_code": str},
)

if "sector_code" not in crosswalk.columns:
    raise ValueError("The crosswalk must contain sector_code.")

crosswalk["sector_code"] = (
    crosswalk["sector_code"].astype("string").str.strip()
)

crosswalk = crosswalk.dropna(subset=["sector_code"]).copy()

# Keep only sector names and district names if available.
name_columns = [
    col for col in ["sector_code", "adm2_name", "adm3_name"]
    if col in crosswalk.columns
]

crosswalk = crosswalk[name_columns].drop_duplicates(
    subset=["sector_code"]
)

print(f"Crosswalk sectors: {len(crosswalk):,}")


# ============================================================
# 6. LOAD HEALTH FACILITY FEATURES
# ============================================================

print("\nLoading health facility data...")

facilities = gpd.read_file(FACILITIES_FILE)

required = ["adm3_pcode", "amenity", "healthcare"]
missing = [col for col in required if col not in facilities.columns]

if missing:
    raise ValueError(f"Missing facility columns: {missing}")

print(f"Mapped facility features loaded: {len(facilities):,}")


# ============================================================
# 7. STANDARDIZE FACILITY SECTOR CODES
# ============================================================

# Example: RW1101 -> 1101
facilities["sector_code"] = (
    facilities["adm3_pcode"]
    .astype("string")
    .str.strip()
    .str.upper()
    .str.replace(r"^RW", "", regex=True)
)

facilities.loc[
    facilities["adm3_pcode"].isna(),
    "sector_code"
] = pd.NA

facilities["amenity_clean"] = (
    facilities["amenity"]
    .astype("string")
    .str.strip()
    .str.lower()
)

facilities["healthcare_clean"] = (
    facilities["healthcare"]
    .astype("string")
    .str.strip()
    .str.lower()
)

# Basic preliminary categories based on available OSM tags.
# These categories are not a clinical classification.
facilities["is_pharmacy_feature"] = (
    facilities["amenity_clean"].eq("pharmacy")
    | facilities["healthcare_clean"].eq("pharmacy")
)

facilities["is_other_health_feature"] = (
    facilities["amenity_clean"].isin(
        ["hospital", "clinic", "doctors", "dentist"]
    )
    | facilities["healthcare_clean"].isin(
        [
            "hospital",
            "clinic",
            "health_post",
            "doctor",
            "dentist",
            "laboratory",
            "centre",
            "counselling",
            "physiotherapist",
        ]
    )
)

facilities["is_other_health_feature"] &= (
    ~facilities["is_pharmacy_feature"]
)


# ============================================================
# 8. COUNT FACILITY FEATURES BY SECTOR
# ============================================================

print("\nCounting mapped health facility features...")

facility_counts = (
    facilities.dropna(subset=["sector_code"])
    .groupby("sector_code", as_index=False)
    .agg(
        mapped_feature_count=("sector_code", "size"),
        mapped_pharmacy_features=("is_pharmacy_feature", "sum"),
        mapped_other_health_features=("is_other_health_feature", "sum"),
    )
)

print(
    "Sectors with mapped facility features: "
    f"{facility_counts['sector_code'].nunique():,}"
)


# ============================================================
# 9. VALIDATE THE CODE MATCH BEFORE MERGING
# ============================================================

census_codes = set(population["sector_code"])
facility_codes = set(facility_counts["sector_code"])

matched_codes = census_codes & facility_codes
unmatched_facility_codes = facility_codes - census_codes

print("\n--- SECTOR MATCH VALIDATION ---")
print(f"Census sector codes: {len(census_codes):,}")
print(f"Facility sector codes: {len(facility_codes):,}")
print(f"Matching sector codes: {len(matched_codes):,}")
print(f"Facility codes not in census: {len(unmatched_facility_codes):,}")


# ============================================================
# 10. MERGE ALL SECTORS, INCLUDING SECTORS WITH ZERO MATCHES
# ============================================================

print("\nCombining sector data...")

result = population.merge(
    crosswalk,
    on="sector_code",
    how="left",
    validate="one_to_one",
)

result = result.merge(
    facility_counts,
    on="sector_code",
    how="left",
    validate="one_to_one",
)

count_columns = [
    "mapped_feature_count",
    "mapped_pharmacy_features",
    "mapped_other_health_features",
]

for col in count_columns:
    result[col] = result[col].fillna(0).astype(int)

for col in ["adm2_name", "adm3_name"]:
    if col not in result.columns:
        result[col] = "Name unavailable"
    else:
        result[col] = result[col].fillna("Name unavailable")


# ============================================================
# 11. CALCULATE DESCRIPTIVE INDICATORS
# ============================================================

result["mapped_features_per_10000_people"] = (
    result["mapped_feature_count"]
    / result["estimated_population"].where(
        result["estimated_population"] > 0
    )
    * 10000
)

result["mapped_pharmacy_features_per_10000_people"] = (
    result["mapped_pharmacy_features"]
    / result["estimated_population"].where(
        result["estimated_population"] > 0
    )
    * 10000
)

result = result.sort_values(
    "estimated_population",
    ascending=False,
).reset_index(drop=True)


# ============================================================
# 12. SAVE RESULTS
# ============================================================

result.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8",
)


# ============================================================
# 13. PRINT SUMMARY
# ============================================================

print("\n" + "=" * 60)
print("SECTOR ANALYSIS COMPLETE")
print("=" * 60)

print(f"Output file: {OUTPUT_FILE}")
print(f"Sectors in output: {len(result):,}")
print(
    "Sectors with mapped features: "
    f"{(result['mapped_feature_count'] > 0).sum():,}"
)
print(
    "Sectors with no matching mapped features: "
    f"{(result['mapped_feature_count'] == 0).sum():,}"
)
print(
    "Total mapped features counted: "
    f"{result['mapped_feature_count'].sum():,}"
)

print("\nExample sectors:")

print(
    result[
        [
            "sector_code",
            "adm2_name",
            "adm3_name",
            "estimated_population",
            "mapped_feature_count",
            "mapped_pharmacy_features",
            "mapped_other_health_features",
            "mapped_features_per_10000_people",
        ]
    ].head(15).to_string(index=False)
)

print("\nInterpretation cautions:")
print("- OSM features are not necessarily unique or verified operating facilities.")
print("- Zero mapped features does not prove that no real facility exists.")
print("- Confirm official NISR weight instructions before publishing population totals.")
print("- Feature counts alone do not measure travel distance, capacity, or care quality.")
