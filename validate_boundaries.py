
from pathlib import Path
import pandas as pd
import geopandas as gpd

ROOT = Path(__file__).resolve().parent

BOUNDARY_FILE = (
    ROOT / "data" / "boundaries" / "rwanda_sectors_2022.geojson"
)
CENSUS_FILE = ROOT / "outputs" / "sector_analysis.csv"
FACILITY_FILE = ROOT / "data" / "facilities" / "health_facilities.geojson"

print("Loading boundaries...")
boundaries = gpd.read_file(BOUNDARY_FILE)

print("\n--- BOUNDARY QUALITY CHECK ---")
print(f"Boundary records: {len(boundaries):,}")
print(f"CRS: {boundaries.crs}")
print(f"Missing sector IDs: {boundaries['sector_id'].isna().sum():,}")
print(f"Missing geometries: {boundaries.geometry.isna().sum():,}")
print(f"Empty geometries: {boundaries.geometry.is_empty.sum():,}")
print(
    "Invalid geometries: "
    f"{(~boundaries.geometry.is_valid).sum():,}"
)

# Drop only records that cannot identify a sector.
valid_boundaries = boundaries.dropna(
    subset=["sector_id", "geometry"]
).copy()

valid_boundaries["sector_code"] = (
    pd.to_numeric(valid_boundaries["sector_id"], errors="coerce")
    .astype("Int64")
    .astype("string")
    .str.zfill(4)
)

valid_boundaries = valid_boundaries.dropna(
    subset=["sector_code"]
)

print(f"\nBoundary records with sector IDs: {len(valid_boundaries):,}")
print(
    "Unique valid sector codes: "
    f"{valid_boundaries['sector_code'].nunique():,}"
)

duplicates = valid_boundaries[
    valid_boundaries.duplicated("sector_code", keep=False)
].sort_values("sector_code")

print("\n--- DUPLICATE SECTOR CODES ---")
if duplicates.empty:
    print("No duplicate sector codes.")
else:
    print(
        duplicates[
            ["sector_code", "district", "sector"]
        ].to_string(index=False)
    )

print("\nLoading sector analysis...")
analysis = pd.read_csv(
    CENSUS_FILE,
    dtype={"sector_code": str}
)
analysis["sector_code"] = analysis["sector_code"].str.zfill(4)

boundary_codes = set(valid_boundaries["sector_code"])
analysis_codes = set(analysis["sector_code"])

print("\n--- MATCHING CHECK ---")
print(f"Analysis sectors: {len(analysis_codes):,}")
print(f"Boundary sectors: {len(boundary_codes):,}")
print(f"Matching codes: {len(analysis_codes & boundary_codes):,}")
print(f"Analysis sectors without boundaries: {len(analysis_codes - boundary_codes):,}")
print(f"Boundary sectors absent from analysis: {len(boundary_codes - analysis_codes):,}")

print("\nLoading facility data...")
facilities = gpd.read_file(FACILITY_FILE)

facility_codes = (
    facilities["adm3_pcode"]
    .dropna()
    .astype(str)
    .str.replace(r"^RW", "", regex=True)
    .str.zfill(4)
)

print(f"Facility features: {len(facilities):,}")
print(f"Distinct facility sector codes: {facility_codes.nunique():,}")
print(
    "Facility sector codes matching boundaries: "
    f"{len(set(facility_codes) & boundary_codes):,}"
)

print("\nValidation complete.")
