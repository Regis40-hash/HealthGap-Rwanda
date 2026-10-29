
from pathlib import Path
import pandas as pd
import geopandas as gpd

ROOT = Path(__file__).resolve().parent

census_file = ROOT / "data" / "census" / "PHC5_Public_microdata.dta"
facilities_file = ROOT / "data" / "facilities" / "health_facilities.geojson"

# Inspect the actual census geography values.
census = pd.read_stata(
    census_file,
    columns=["ml01", "ml02", "ml03"],
    convert_categoricals=False,
)

print("\n--- CENSUS GEOGRAPHIC CODES ---")
print(census[["ml01", "ml02", "ml03"]].head(10).to_string(index=False))

print("\n--- DISTINCT DISTRICT CODES (ml02) ---")
print(sorted(census["ml02"].dropna().unique().tolist())[:40])

print("\n--- DISTINCT SECTOR CODES (ml03) ---")
print(sorted(census["ml03"].dropna().unique().tolist())[:40])

# Inspect the actual facility sector codes.
facilities = gpd.read_file(facilities_file)

print("\n--- FACILITY ADMINISTRATIVE CODES ---")
print(
    facilities[
        ["adm2_pcode", "adm2_name", "adm3_pcode", "adm3_name"]
    ].head(15).to_string(index=False)
)

print("\n--- SAMPLE FACILITY SECTOR CODES ---")
print(
    facilities["adm3_pcode"]
    .dropna()
    .astype(str)
    .drop_duplicates()
    .head(20)
    .to_list()
)
