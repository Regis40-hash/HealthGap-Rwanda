
from pathlib import Path
import pandas as pd
import geopandas as gpd

BASE = Path(__file__).resolve().parent
CENSUS = BASE / "data" / "census" / "PHC5_Public_microdata.dta"
FACILITIES = BASE / "data" / "facilities" / "health_facilities.geojson"
OUTPUT = BASE / "outputs" / "sector_crosswalk_check.csv"

print("HEALTHGAP RWANDA — CROSSWALK VALIDATION")

# Read only census geography fields.
census = pd.read_stata(
    CENSUS,
    columns=["ml01", "ml02", "ml03"],
    convert_categoricals=False
)

census_sectors = census[["ml01", "ml02", "ml03"]].drop_duplicates().copy()

# Convert numeric codes such as 1101.0 to "1101".
census_sectors["district_code"] = (
    census_sectors["ml02"].astype(int).astype(str).str.zfill(2)
)
census_sectors["sector_code"] = (
    census_sectors["ml03"].astype(int).astype(str).str.zfill(4)
)

# A sector code should begin with its district code.
census_sectors["sector_district_consistent"] = (
    census_sectors["sector_code"].str[:2]
    == census_sectors["district_code"]
)

del census

fac = gpd.read_file(FACILITIES)

# Remove the "RW" prefix from codes such as RW5704.
fac_sectors = fac[
    ["adm2_pcode", "adm2_name", "adm3_pcode", "adm3_name"]
].drop_duplicates().copy()

fac_sectors["district_code"] = (
    fac_sectors["adm2_pcode"].astype(str).str.replace(
        r"^RW", "", regex=True
    )
)
fac_sectors["sector_code"] = (
    fac_sectors["adm3_pcode"].astype(str).str.replace(
        r"^RW", "", regex=True
    )
)

fac_sectors["sector_district_consistent"] = (
    fac_sectors["sector_code"].str[:2]
    == fac_sectors["district_code"]
)

census_codes = set(census_sectors["sector_code"])
facility_codes = set(fac_sectors["sector_code"])

matched = census_codes & facility_codes
facility_only = facility_codes - census_codes
census_without_facilities = census_codes - facility_codes

print("\n--- CODE MATCH RESULTS ---")
print("Distinct census sectors:", len(census_codes))
print("Distinct facility sector codes:", len(facility_codes))
print("Matching sector codes:", len(matched))
print("Facility sector codes absent from census:", len(facility_only))
print("Census sectors with no mapped facility:", len(census_without_facilities))

print("\n--- DISTRICT CODE CHECK ---")
print(
    "Census sector/district inconsistencies:",
    (~census_sectors["sector_district_consistent"]).sum()
)
print(
    "Facility sector/district inconsistencies:",
    (~fac_sectors["sector_district_consistent"]).sum()
)

# Export a review table with facility names where available.
crosswalk = census_sectors.merge(
    fac_sectors[
        ["sector_code", "adm2_name", "adm3_name"]
    ].drop_duplicates("sector_code"),
    on="sector_code",
    how="left"
)

crosswalk["has_mapped_facility_sector"] = (
    crosswalk["sector_code"].isin(facility_codes)
)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
crosswalk.to_csv(OUTPUT, index=False)

print("\nSaved review table to:", OUTPUT)
print("\nSample matched rows:")
print(
    crosswalk[crosswalk["has_mapped_facility_sector"]]
    .head(15)
    .to_string(index=False)
)

print("\nCrosswalk validation complete.")
