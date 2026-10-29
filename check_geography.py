
from pathlib import Path
import pandas as pd
import geopandas as gpd

BASE = Path(__file__).resolve().parent
CENSUS = BASE / "data" / "census" / "PHC5_Public_microdata.dta"
FACILITIES = BASE / "data" / "facilities" / "health_facilities.geojson"

print("HEALTHGAP RWANDA — GEOGRAPHY CHECK")

# Read only the geographic columns and population weight.
census = pd.read_stata(
    CENSUS,
    columns=["ml01", "ml02", "ml03", "Pop_weight"],
    convert_categoricals=False
)

print("\n--- CENSUS GEOGRAPHY ---")
print("Rows:", len(census))

for col in ["ml01", "ml02", "ml03"]:
    print(f"\n{col}")
    print("Data type:", census[col].dtype)
    print("Missing values:", census[col].isna().sum())
    print("Distinct values:", census[col].nunique(dropna=True))
    print("Example codes:", census[col].dropna().unique()[:12])

print("\n--- POPULATION WEIGHT ---")
print("Missing weights:", census["Pop_weight"].isna().sum())
print("Minimum:", census["Pop_weight"].min())
print("Maximum:", census["Pop_weight"].max())

# Release the census data before loading the facility file.
del census

fac = gpd.read_file(FACILITIES)

print("\n--- FACILITY ADMINISTRATIVE FIELDS ---")

for col in [
    "adm1_pcode", "adm1_name",
    "adm2_pcode", "adm2_name",
    "adm3_pcode", "adm3_name",
    "adm4_pcode", "adm4_name"
]:
    if col in fac.columns:
        values = fac[col].dropna().astype(str)
        print(f"\n{col}")
        print("Missing:", fac[col].isna().sum())
        print("Distinct values:", values.nunique())
        print("Examples:", values.unique()[:8])

print("\n--- FACILITY TYPES ---")
for col in ["amenity", "healthcare"]:
    if col in fac.columns:
        print(f"\n{col}:")
        print(
            fac[col]
            .fillna("Missing")
            .value_counts()
            .head(12)
            .to_string()
        )

print("\nGeography check complete.")
