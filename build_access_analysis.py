
from pathlib import Path

import pandas as pd
import geopandas as gpd
import folium
from shapely.geometry import Point


# ============================================================
# 1. PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent

BOUNDARY_FILE = (
    ROOT / "data" / "boundaries" / "rwanda_sectors_2022.geojson"
)
FACILITY_FILE = ROOT / "data" / "facilities" / "health_facilities.geojson"
ANALYSIS_FILE = ROOT / "outputs" / "sector_analysis.csv"

OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "geographic_access_analysis.csv"
OUTPUT_MAP = OUTPUT_DIR / "healthgap_access_map.html"


# ============================================================
# 2. LOAD AND CLEAN SECTOR BOUNDARIES
# ============================================================

print("Loading sector boundaries...")

boundaries = gpd.read_file(BOUNDARY_FILE)

boundaries = boundaries.dropna(
    subset=["sector_id", "geometry"]
).copy()

boundaries["sector_code"] = (
    pd.to_numeric(boundaries["sector_id"], errors="coerce")
    .astype("Int64")
    .astype("string")
    .str.zfill(4)
)

boundaries = boundaries.dropna(
    subset=["sector_code", "geometry"]
).copy()

# Repair invalid polygons if possible.
invalid_before = int((~boundaries.geometry.is_valid).sum())

if invalid_before:
    print(f"Repairing {invalid_before} invalid geometries...")
    boundaries["geometry"] = boundaries.geometry.make_valid()

# Remove empty geometries after repair.
boundaries = boundaries[
    boundaries.geometry.notna() & ~boundaries.geometry.is_empty
].copy()

# A single sector must correspond to one boundary feature.
# If repair creates multiple parts, dissolve them by sector code.

boundaries = boundaries.dissolve(
    by="sector_code",
    as_index=False,
    aggfunc="first",
)

# Create province outlines from the cleaned sector boundaries.
province_boundaries = boundaries[
    boundaries["province"].notna()
].dissolve(by="province")

province_boundaries = province_boundaries.reset_index()

print(f"Usable sector boundaries: {len(boundaries):,}")
print(f"Province outlines prepared: {len(province_boundaries):,}")



# ============================================================
# 3. LOAD SECTOR ANALYSIS
# ============================================================

print("\nLoading sector population and facility counts...")

analysis = pd.read_csv(
    ANALYSIS_FILE,
    dtype={"sector_code": str},
)

analysis["sector_code"] = (
    analysis["sector_code"].astype(str).str.zfill(4)
)

# Avoid duplicating name columns when joining.
columns_to_keep = [
    "sector_code",
    "estimated_population",
    "mapped_feature_count",
    "mapped_pharmacy_features",
    "mapped_other_health_features",
    "mapped_features_per_10000_people",
]

analysis = analysis[columns_to_keep].drop_duplicates(
    subset=["sector_code"]
)


# ============================================================
# 4. LOAD FACILITY LOCATIONS
# ============================================================

print("\nLoading mapped health facility features...")

facilities = gpd.read_file(FACILITY_FILE)

# Provisional facility categories based on OSM tags and names.
# These are screening labels, not verified clinical classifications.

def classify_facility(row):
    amenity = str(row.get("amenity", "") or "").lower()
    healthcare = str(row.get("healthcare", "") or "").lower()
    name = str(row.get("name", "") or "").lower()

    # Identify pharmacies first.
    if (
        amenity in {"pharmacy", "drugstore"}
        or healthcare == "pharmacy"
        or "pharmacy" in name
        or "drugstore" in name
    ):
        return "pharmacy"

    # Names can be more informative than inconsistent OSM tags.
    if any(term in name for term in [
        "health post",
        "health centre",
        "health center",
        "clinic",
    ]):
        return "primary_care_named"

    if healthcare in {"clinic", "health_post", "centre"}:
        return "primary_care_tagged"

    # Hospital-like records, based on available tags or names.
    if (
        "hospital" in name
        or amenity == "hospital"
        or healthcare == "hospital"
    ):
        return "hospital_like"

    return "other_or_uncertain"


facilities["facility_group"] = facilities.apply(
    classify_facility,
    axis=1,
)

print("\nProvisional facility categories:")
print(facilities["facility_group"].value_counts().to_string())

facilities = facilities[
    facilities.geometry.notna() & ~facilities.geometry.is_empty
].copy()

# Use point locations directly. For polygon features, use a point
# guaranteed to lie inside each polygon.
facilities["geometry"] = facilities.geometry.representative_point()

# Only retain features with a usable geometry and sector code.
facilities = facilities.dropna(
    subset=["adm3_pcode", "geometry"]
).copy()

facilities["sector_code"] = (
    facilities["adm3_pcode"]
    .astype(str)
    .str.strip()
    .str.upper()
    .str.replace(r"^RW", "", regex=True)
    .str.zfill(4)
)

print(f"Facility features with usable locations: {len(facilities):,}")


# ============================================================
# 5. REPROJECT TO METRES
# ============================================================

# EPSG:32736 is UTM zone 36S, appropriate for Rwanda.
# Distances will be in metres rather than degrees.
boundaries_m = boundaries.to_crs("EPSG:32736")
facilities_m = facilities.to_crs("EPSG:32736")

# Use one representative point per sector for this initial screening.
boundaries_m["sector_point"] = (
    boundaries_m.geometry.representative_point()
)

sector_points = boundaries_m[
    ["sector_code", "sector_point"]
].copy()

sector_points = gpd.GeoDataFrame(
    sector_points,
    geometry="sector_point",
    crs=boundaries_m.crs,
)

sector_points = sector_points.rename_geometry("geometry")


# ============================================================
# 6. FIND NEAREST MAPPED FEATURE
# ============================================================


print("\nCalculating nearest-feature distances by category...")

if facilities_m.empty:
    raise ValueError(
        "No facility locations are available for distance analysis."
    )


def nearest_distance_for(facility_subset, output_column):
    """Return one nearest-feature distance per sector, in metres."""

    if facility_subset.empty:
        return pd.DataFrame({
            "sector_code": sector_points["sector_code"].values,
            output_column: float("nan"),
        })

    joined = gpd.sjoin_nearest(
        sector_points,
        facility_subset[["geometry"]],
        how="left",
        distance_col=output_column,
    )

    joined = (
        joined.sort_values(output_column)
        .drop_duplicates(subset=["sector_code"])
    )

    return joined[["sector_code", output_column]].copy()


# Distance to any mapped feature, preserving the original indicator.
nearest = nearest_distance_for(
    facilities_m,
    "nearest_feature_distance_m",
)

# Separate exploratory indicators.
category_columns = {
    "pharmacy": "nearest_pharmacy_distance_m",
    "hospital_like": "nearest_hospital_like_distance_m",
    "primary_care_named": "nearest_named_primary_care_distance_m",
    "primary_care_tagged": "nearest_tagged_primary_care_distance_m",
}

for category, distance_column in category_columns.items():
    subset = facilities_m[
        facilities_m["facility_group"] == category
    ]

    category_distances = nearest_distance_for(
        subset,
        distance_column,
    )

    nearest = nearest.merge(
        category_distances,
        on="sector_code",
        how="left",
        validate="one_to_one",
    )

# Combine the two provisional primary-care groups into one indicator.
named = nearest["nearest_named_primary_care_distance_m"]
tagged = nearest["nearest_tagged_primary_care_distance_m"]

nearest["nearest_primary_care_distance_m"] = pd.concat(
    [named, tagged],
    axis=1,
).min(axis=1)

distance_columns_m = [
    "nearest_feature_distance_m",
    "nearest_pharmacy_distance_m",
    "nearest_hospital_like_distance_m",
    "nearest_primary_care_distance_m",
]

for column in distance_columns_m:
    nearest[column.replace("_m", "_km")] = nearest[column] / 1000


# ============================================================
# 7. JOIN GEOGRAPHY, POPULATION AND DISTANCES
# ============================================================

print("\nCombining results...")

result = boundaries.merge(
    analysis,
    on="sector_code",
    how="left",
    validate="one_to_one",
)

result = result.merge(
    nearest,
    on="sector_code",
    how="left",
    validate="one_to_one",
)

if result["estimated_population"].isna().any():
    print("WARNING: Some sectors have no matched population estimate.")

if result["nearest_feature_distance_km"].isna().any():
    print("WARNING: Some sectors have no calculated nearest-feature distance.")


# ============================================================
# 8. CREATE INITIAL SCREENING FLAGS
# ============================================================

# These are transparent screening thresholds, not official clinical
# or government standards. Interpret results as candidates for review.
result["over_5km_straight_line"] = (
    result["nearest_feature_distance_km"] > 5
)

result["over_10km_straight_line"] = (
    result["nearest_feature_distance_km"] > 10
)

# Sort sectors by distance for easy inspection.
result = result.sort_values(
    "nearest_feature_distance_km",
    ascending=False,
    na_position="last",
)


# ============================================================
# 9. SAVE CSV
# ============================================================

# Do not export geometry as a text field in the CSV.
result.drop(columns="geometry").to_csv(
    OUTPUT_CSV,
    index=False,
    encoding="utf-8",
)


# ============================================================
# 10. BUILD INTERACTIVE MAP
# ============================================================

print("\nBuilding interactive map...")

# Rwanda approximate map centre.

m = folium.Map(
    location=[-1.94, 29.87],
    zoom_start=7,
    tiles=None,
    control_scale=True,
)


# Use a geographic copy for the web map.
result_wgs84 = result.to_crs("EPSG:4326")

def choose_color(distance):
    if pd.isna(distance):
        return "#808080"
    if distance > 10:
        return "#b2182b"
    if distance > 5:
        return "#ef8a62"
    return "#2166ac"


for _, row in result_wgs84.iterrows():
    distance = row.get("nearest_feature_distance_km")
    population = row.get("estimated_population")
    sector_code = row["sector_code"]

    district = row.get("district", "Unknown")
    sector_name = row.get("sector", "Unknown")

    distance_text = (
        f"{distance:.2f} km"
        if pd.notna(distance)
        else "Unavailable"
    )

    population_text = (
        f"{population:,.0f}"
        if pd.notna(population)
        else "Unavailable"
    )

    popup_html = f"""
    <b>Sector:</b> {sector_code}<br>
    <b>District:</b> {district}<br>
    <b>Sector name:</b> {sector_name}<br>
    <b>Estimated population:</b> {population_text}<br>
    <b>Nearest mapped feature:</b> {distance_text}<br>
    <i>Straight-line screening distance, not road travel distance.</i>
    """

    folium.GeoJson(
        row.geometry,
        style_function=lambda feature, color=choose_color(distance): {
            "fillColor": color,
            "color": "#444444",
            "weight": 0.5,
            "fillOpacity": 0.65,
        },
        tooltip=f"Sector {sector_code} — {distance_text}",
        popup=folium.Popup(popup_html, max_width=320),
    ).add_to(m)





# Build one merged province-boundary line layer.
# Unioning the lines removes duplicate shared borders.
province_dissolved = boundaries.dissolve(by="province")

province_edges = province_dissolved.geometry.boundary.union_all()

province_lines = gpd.GeoDataFrame(
    {"boundary_type": ["Province boundaries"]},
    geometry=[province_edges],
    crs=boundaries.crs,
).to_crs("EPSG:4326")

folium.GeoJson(
    province_lines,
    name="Province boundaries",
    style_function=lambda feature: {
        "color": "#202020",
        "weight": 2.5,
        "opacity": 1,
    },
    interactive=False,
).add_to(m)


# Legend: fixed inside the map, near the top-right corner.
legend_html = """
<div style="
position: fixed;
top: 80px;
right: 20px;
z-index: 9999;
background: white;
padding: 12px 14px;
border: 1px solid #777;
border-radius: 6px;
font-size: 13px;
line-height: 1.6;
box-shadow: 0 1px 5px rgba(0,0,0,0.25);
">
<b>Distance to nearest mapped feature</b><br>
<span style="color:#2166ac;">&#9632;</span> 5 km or less<br>
<span style="color:#ef8a62;">&#9632;</span> Over 5 to 10 km<br>
<span style="color:#b2182b;">&#9632;</span> Over 10 km<br>
<span style="color:#808080;">&#9632;</span> Unavailable<br>
<hr style="margin:6px 0;">
<span style="color:#202020;">━━</span> Province boundary
</div>
"""

m.get_root().html.add_child(folium.Element(legend_html))


# Map title and interpretation note.
title_html = """
<div style="
position: fixed;
top: 10px;
left: 50%;
transform: translateX(-50%);
z-index: 9999;
background: white;
padding: 10px 16px;
border: 1px solid #777;
border-radius: 6px;
box-shadow: 0 1px 5px rgba(0,0,0,0.2);
width: max-content;
max-width: 65%;
font-family: Arial, sans-serif;
text-align: center;
">
<div style="font-size:18px; font-weight:bold;">
HealthGap Rwanda
</div>
<div style="font-size:12px; margin-top:4px;">
Geographic access screening — straight-line distance to the nearest mapped health feature
</div>
</div>
"""

m.get_root().html.add_child(folium.Element(title_html))

# Fit the view to the full country boundary.
country_bounds = result_wgs84.total_bounds
m.fit_bounds([
    [country_bounds[1], country_bounds[0]],
    [country_bounds[3], country_bounds[2]],
])

# Save the interactive map.
m.save(OUTPUT_MAP)


# ============================================================
# 11. SUMMARY
# ============================================================

print("\n" + "=" * 60)
print("GEOGRAPHIC ACCESS SCREENING COMPLETE")
print("=" * 60)

print(f"Sectors analysed: {len(result):,}")
print(f"CSV saved: {OUTPUT_CSV}")
print(f"Map saved: {OUTPUT_MAP}")

print(
    "Sectors over 5 km straight-line distance: "
    f"{result['over_5km_straight_line'].sum():,}"
)

print(
    "Sectors over 10 km straight-line distance: "
    f"{result['over_10km_straight_line'].sum():,}"
)

print("\nTen sectors with the largest calculated distances:")
print(
    result[
        [
            "sector_code",
            "nearest_feature_distance_km",
            "estimated_population",
            "mapped_feature_count",
        ]
    ].head(10).to_string(index=False)
)

print("\nIMPORTANT:")
print("- Distances are from sector representative points.")
print("- Distances are straight-line, not road-network travel distances.")
print("- Mapped features may be incomplete, duplicated, or non-operational.")
print("- The 5 km and 10 km thresholds are exploratory, not official standards.")
print("- Population estimates require confirmation of NISR weighting guidance.")
