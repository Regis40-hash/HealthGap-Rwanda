
from pathlib import Path
import pandas as pd
import geopandas as gpd

BASE = Path(__file__).resolve().parent
CENSUS = BASE / "data" / "census" / "PHC5_Public_microdata.dta"
FACILITIES = BASE / "data" / "facilities" / "health_facilities.geojson"

print("HEALTHGAP RWANDA — GEOGRAPHIC CROSSWALK CHECK")

# Inspect census variable names and labels without loading all records.
with pd.io.stata.StataReader(CENSUS) as reader:
    labels = reader.variable_labels()

print("\n--- CENSUS VARIABLES RELATED TO GEOGRAPHY ---")
for name, label in labels.items():
    text = f"{name} {label}".lower()
    if any(term in text for term in [
        "province", "district", "sector", "cell", "village",
        "province name", "district name"
    ]):
        print(f"{name}: {label}")

# Inspect administrative names and codes in the facility data.
fac = gpd.read_file(FACILITIES)

print("\n--- FACILITY DISTRICTS ---")
for code, name in (
    fac[["adm2_pcode", "adm2_name"]]
    .drop_duplicates()
    .sort_values(["adm2_name"])
    .itertuples(index=False, name=None)
):
    print(f"{code}: {name}")

print("\n--- FACILITY SECTORS (FIRST 40) ---")
sectors = (
    fac[["adm3_pcode", "adm3_name", "adm2_name"]]
    .drop_duplicates()
    .sort_values(["adm2_name", "adm3_name"])
)
print(sectors.head(40).to_string(index=False))

print("\nCrosswalk inspection complete.")
