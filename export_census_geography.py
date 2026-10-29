
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
CENSUS = BASE / "data" / "census" / "PHC5_Public_microdata.dta"
OUTPUT = BASE / "outputs" / "census_geography_codes.csv"

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

print("Reading census geography columns...")

geo = pd.read_stata(
    CENSUS,
    columns=["ml01", "ml02", "ml03"],
    convert_categoricals=False
)

# Each row is a distinct province/district/sector code combination.
geo = geo.drop_duplicates().sort_values(
    ["ml01", "ml02", "ml03"]
)

geo.to_csv(OUTPUT, index=False)

print("\nDistinct geographic combinations:", len(geo))
print("Saved to:", OUTPUT)
print("\nFirst 25 combinations:")
print(geo.head(25).to_string(index=False))
