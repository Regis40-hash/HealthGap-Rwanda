
from pathlib import Path
import pandas as pd
import geopandas as gpd

# Project file paths
BASE_DIR = Path(__file__).resolve().parent
CENSUS_FILE = BASE_DIR / "data" / "census" / "PHC5_Public_microdata.dta"
FACILITIES_FILE = (
    BASE_DIR / "data" / "facilities" / "health_facilities.geojson"
)

print("=" * 60)
print("HEALTHGAP RWANDA: DATA INSPECTION")
print("=" * 60)

# 1. Check that both files exist
for file_path in [CENSUS_FILE, FACILITIES_FILE]:
    print(f"\nFile: {file_path.name}")
    print(f"Exists: {file_path.exists()}")

if not CENSUS_FILE.exists() or not FACILITIES_FILE.exists():
    raise FileNotFoundError(
        "A data file is missing. Check the paths above."
    )

# 2. Inspect a small census sample
print("\n--- CENSUS DATA ---")

with pd.read_stata(
    CENSUS_FILE,
    iterator=True,
    convert_categoricals=False
) as reader:
    print("Variable count:", len(reader.variable_labels()))

    # Read only the first 1,000 records into memory
    sample = reader.read(1000)

    print("Sample rows read:", len(sample))
    print("Columns:")
    print(", ".join(sample.columns))

    # Show labels for relevant fields, if present
    labels = reader.variable_labels()
    for field in [
        "ml01", "ml02", "ml03",
        "p03", "p04", "p14", "Pop_weight"
    ]:
        if field in sample.columns:
            print(f"{field}: {labels.get(field, 'No label available')}")

del sample

# 3. Inspect healthcare facility geography
print("\n--- HEALTH FACILITIES ---")

facilities = gpd.read_file(FACILITIES_FILE)

print("Total features:", len(facilities))
print("Coordinate reference system:", facilities.crs)
print("Geometry types:")
print(facilities.geometry.geom_type.value_counts().to_string())

print("\nAvailable fields:")
print(", ".join(facilities.columns))

# Summarize common facility tags if available
for field in ["amenity", "healthcare"]:
    if field in facilities.columns:
        print(f"\nTop values for {field}:")
        print(
            facilities[field]
            .fillna("Missing")
            .astype(str)
            .value_counts()
            .head(15)
            .to_string()
        )

# Check for missing or empty geometries
print("\nMissing geometries:", facilities.geometry.isna().sum())
print("Empty geometries:", facilities.geometry.is_empty.sum())

print("\nInspection complete.")
print("No individual census records were printed.")
