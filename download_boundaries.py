
from pathlib import Path
import geopandas as gpd

ROOT = Path(__file__).resolve().parent

OUTPUT_DIR = ROOT / "data" / "boundaries"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "rwanda_sectors_2022.geojson"

URL = (
    "https://moegis.environment.gov.rw/server/rest/services/"
    "Hosted/Administrative_boundaries/FeatureServer/1/query"
    "?where=1%3D1"
    "&outFields=*"
    "&returnGeometry=true"
    "&outSR=4326"
    "&f=geojson"
)

print("Downloading Rwanda sector boundaries...")

try:
    boundaries = gpd.read_file(URL)

    if boundaries.empty:
        raise ValueError("The service returned no boundary features.")

    required_columns = ["sector_id", "district", "sector"]

    missing = [
        col for col in required_columns
        if col not in boundaries.columns
    ]

    if missing:
        raise ValueError(
            f"Expected boundary fields are missing: {missing}\n"
            f"Available fields: {list(boundaries.columns)}"
        )

    boundaries["sector_code"] = (
        boundaries["sector_id"]
        .astype("string")
        .str.strip()
        .str.zfill(4)
    )

    boundaries.to_file(
        OUTPUT_FILE,
        driver="GeoJSON",
    )

    print("\nDownload successful.")
    print(f"Boundary features: {len(boundaries):,}")
    print(
        "Unique sector codes: "
        f"{boundaries['sector_code'].nunique():,}"
    )
    print(f"Saved to: {OUTPUT_FILE}")

    print("\nSample records:")
    print(
        boundaries[
            ["sector_code", "district", "sector"]
        ].head(10).to_string(index=False)
    )

except Exception as exc:
    print("\nBoundary download failed.")
    print(f"Reason: {exc}")
    print(
        "\nCheck your internet connection. If the service is "
        "unavailable, we can try another official GIS source."
    )
