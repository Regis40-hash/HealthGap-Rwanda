
from pathlib import Path
import geopandas as gpd

ROOT = Path(__file__).resolve().parent
FILE = ROOT / "data" / "facilities" / "health_facilities.geojson"

facilities = gpd.read_file(FILE)

for column in [
    "amenity",
    "healthcare",
    "healthcare_speciality",
    "operator_type",
]:
    print(f"\n--- {column} ---")

    if column not in facilities.columns:
        print("Column not found")
        continue

    print(
        facilities[column]
        .fillna("Missing")
        .astype(str)
        .value_counts()
        .head(20)
        .to_string()
    )

print("\n--- EXAMPLE RECORDS ---")
columns = [
    c for c in [
        "name",
        "amenity",
        "healthcare",
        "healthcare_speciality",
        "operator_type",
        "capacity_persons",
    ]
    if c in facilities.columns
]

print(facilities[columns].head(15).to_string(index=False))
