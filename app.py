
from pathlib import Path

import pandas as pd
import geopandas as gpd
import folium
import streamlit as st
import streamlit.components.v1 as components


# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
DATA_DIR = ROOT / "data"

ANALYSIS_FILE = OUTPUT_DIR / "geographic_access_analysis.csv"
BOUNDARY_FILE = DATA_DIR / "boundaries" / "rwanda_sectors_2022.geojson"

st.set_page_config(
    page_title="HealthGap Rwanda",
    page_icon="🏥",
    layout="wide",
)

st.title("HealthGap Rwanda")
st.subheader("Geographic Healthcare Access Screening")

st.write(
    "Explore potential geographic access gaps using sector boundaries, "
    "population estimates, and mapped healthcare features. This is a "
    "preliminary planning tool, not proof of unmet healthcare need."
)


# ============================================================
# 2. LOAD DATA
# ============================================================

@st.cache_data
def load_analysis(path, modified_time):
    return pd.read_csv(path, dtype={"sector_code": str})


@st.cache_data
def load_boundaries(path, modified_time):
    return gpd.read_file(path)


if not ANALYSIS_FILE.exists():
    st.error(f"Analysis file not found: {ANALYSIS_FILE}")
    st.stop()

if not BOUNDARY_FILE.exists():
    st.error(f"Boundary file not found: {BOUNDARY_FILE}")
    st.stop()

data = load_analysis(
    str(ANALYSIS_FILE),
    ANALYSIS_FILE.stat().st_mtime,
)

boundaries = load_boundaries(
    str(BOUNDARY_FILE),
    BOUNDARY_FILE.stat().st_mtime,
)

for column in ["province", "district", "sector"]:
    if column in data.columns:
        data[column] = data[column].fillna("").astype(str).str.strip()

if "sector_code" not in data.columns:
    st.error("The analysis CSV does not contain sector_code.")
    st.stop()

data["sector_code"] = (
    data["sector_code"]
    .astype(str)
    .str.replace(r"\.0$", "", regex=True)
    .str.zfill(4)
)

# Ensure distance and population columns are numeric.
for column in [
    "nearest_feature_distance_km",
    "estimated_population",
    "mapped_feature_count",
    "nearest_pharmacy_distance_km",
    "nearest_hospital_like_distance_km",
    "nearest_primary_care_distance_km",
]:
    if column in data.columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

# Standardize the province label for display.
data["province"] = data["province"].replace({
    "Estern Province": "Eastern Province"
})

# Geographic screening priority score (0–100).
# Distance: 60%; population: 40%.
# Missing distances remain unscored.
valid_distance = data["nearest_feature_distance_km"].notna()
valid_population = data["estimated_population"].notna()

distance_max = data.loc[
    valid_distance, "nearest_feature_distance_km"
].max()

population_min = data.loc[
    valid_population, "estimated_population"
].min()

population_max = data.loc[
    valid_population, "estimated_population"
].max()

data["priority_score"] = float("nan")

if distance_max > 0 and population_max > population_min:
    distance_score = (
        data.loc[valid_distance, "nearest_feature_distance_km"]
        / distance_max * 100
    )

    population_score = (
        (data.loc[valid_distance, "estimated_population"] - population_min)
        / (population_max - population_min) * 100
    )

    score_rows = data.index[valid_distance & valid_population]

    data.loc[score_rows, "priority_score"] = (
        0.60 * distance_score.loc[score_rows]
        + 0.40 * population_score.loc[score_rows]
    )

# Provisional, project-defined screening categories.
data["priority_band"] = "Not scored"

scored = data["priority_score"].notna()

data.loc[
    scored & (data["priority_score"] >= 70),
    "priority_band"
] = "Higher priority"

data.loc[
    scored
    & (data["priority_score"] >= 40)
    & (data["priority_score"] < 70),
    "priority_band"
] = "Moderate priority"

data.loc[
    scored & (data["priority_score"] < 40),
    "priority_band"
] = "Lower priority"

if "sector_code" not in boundaries.columns:
    if "sector_id" in boundaries.columns:
        boundaries["sector_code"] = (
            pd.to_numeric(boundaries["sector_id"], errors="coerce")
            .astype("Int64")
            .astype("string")
            .str.zfill(4)
        )
    else:
        st.error("The boundary file has no sector_code or sector_id column.")
        st.stop()

boundaries["sector_code"] = (
    boundaries["sector_code"].astype("string").str.zfill(4)
)

# Keep valid sector records and repair invalid geometries.
boundaries = boundaries.dropna(
    subset=["sector_code", "geometry"]
).copy()

boundaries = boundaries[
    boundaries.geometry.notna() & ~boundaries.geometry.is_empty
].copy()

invalid_count = int((~boundaries.geometry.is_valid).sum())

if invalid_count:
    boundaries["geometry"] = boundaries.geometry.make_valid()

boundaries = boundaries[
    boundaries.geometry.notna() & ~boundaries.geometry.is_empty
].copy()

# Dissolve multiple records into one boundary per sector.
# Keep province and district names from the boundary source.
boundaries = boundaries.dissolve(
    by="sector_code",
    as_index=False,
    aggfunc="first",
)

# Join analysis values onto geographic boundaries.
geo = boundaries.merge(
    data,
    on="sector_code",
    how="left",
    suffixes=("_boundary", ""),
)

# Prefer names from the analysis data, falling back to boundary names.
for name in ["province", "district", "sector"]:
    boundary_name = f"{name}_boundary"

    if boundary_name in geo.columns and name in geo.columns:
        geo[name] = geo[name].replace("", pd.NA).fillna(
            geo[boundary_name]
        )
    elif boundary_name in geo.columns:
        geo[name] = geo[boundary_name]


# ============================================================
# 3. FILTERS
# ============================================================

st.sidebar.header("Explore sectors")

province_options = sorted(
    p for p in geo["province"].dropna().astype(str).unique() if p
)

selected_province = st.sidebar.selectbox(
    "Province",
    ["All provinces"] + province_options,
    key="province_selector",
)


if selected_province == "All provinces":
    province_geo = geo.copy()
else:
    province_geo = geo[
        geo["province"].astype(str) == selected_province
    ].copy()


district_options = sorted(
    d for d in province_geo["district"].dropna().astype(str).unique() if d
)

selected_district = st.sidebar.selectbox(
    "District",
    ["All districts"] + district_options,
    key="district_selector",
)

if selected_district == "All districts":
    filtered_geo = province_geo.copy()
else:
    filtered_geo = province_geo[
        province_geo["district"].astype(str) == selected_district
    ].copy()

minimum_distance = st.sidebar.slider(
    "Minimum distance to nearest mapped feature (km)",
    min_value=0.0,
    max_value=20.0,
    value=0.0,
    step=0.5,
    key="distance_selector",
)

filtered_geo = filtered_geo[
    filtered_geo["nearest_feature_distance_km"].isna()
    | (
        filtered_geo["nearest_feature_distance_km"]
        >= minimum_distance
    )
].copy()

st.sidebar.caption(f"{len(filtered_geo):,} sectors match your filters.")

if st.sidebar.button("Reset all filters"):
    st.session_state["province_selector"] = "All provinces"
    st.session_state["district_selector"] = "All districts"
    st.session_state["distance_selector"] = 0.0
    st.rerun()


# ============================================================
# 4. SUMMARY INDICATORS
# ============================================================

st.markdown("## Screening Overview")

distance = filtered_geo["nearest_feature_distance_km"]

col1, col2, col3, col4 = st.columns(4)

col1.metric("Sectors in selection", f"{len(filtered_geo):,}")
col2.metric("Over 5 km", f"{int((distance > 5).sum()):,}")
col3.metric("Over 10 km", f"{int((distance > 10).sum()):,}")
col4.metric("Distance unavailable", f"{int(distance.isna().sum()):,}")

# Priority-band counts for the current filtered selection.
bands = filtered_geo["priority_band"].fillna("Not scored")

st.markdown("### Geographic Screening Priorities")

priority_cols = st.columns(4)

priority_cols[0].metric(
    "Higher priority",
    f"{(bands == 'Higher priority').sum():,}"
)

priority_cols[1].metric(
    "Moderate priority",
    f"{(bands == 'Moderate priority').sum():,}"
)

priority_cols[2].metric(
    "Lower priority",
    f"{(bands == 'Lower priority').sum():,}"
)

priority_cols[3].metric(
    "Not scored",
    f"{(bands == 'Not scored').sum():,}"
)

st.caption(
    "The 5 km and 10 km thresholds are exploratory, not official standards. "
    "Distances are straight-line measurements from sector representative "
    "points, not road travel distances."
)


# ============================================================
# 5. BUILD FILTERED INTERACTIVE MAP
# ============================================================

st.markdown("## Geographic Screening Map")


def distance_color(value):
    if pd.isna(value):
        return "#808080"
    if value > 10:
        return "#b2182b"
    if value > 5:
        return "#ef8a62"
    return "#2166ac"


if filtered_geo.empty:
    st.warning("No sectors match the current filters.")
else:
    # Reproject to latitude/longitude for Folium.
    map_geo = filtered_geo.to_crs("EPSG:4326")

    # Centre the map on the selected geography.
    centre = map_geo.geometry.union_all().centroid
    map_centre = [centre.y, centre.x]

    m = folium.Map(
    location=[-1.94, 29.87],
    zoom_start=8,
    tiles="OpenStreetMap"
)

    # Draw sectors with thin boundaries.
    for _, row in map_geo.iterrows():
        dist = row.get("nearest_feature_distance_km")
        population = row.get("estimated_population")
        feature_count = row.get("mapped_feature_count")

        priority_score = row.get("priority_score")
        priority_band = row.get("priority_band", "Not scored")

        sector_code = row.get("sector_code", "Unknown")
        district = row.get("district", "Unknown")
        sector_name = row.get("sector", "Unknown")
        province = row.get("province", "Unknown")

        dist_text = (
            f"{dist:.2f} km" if pd.notna(dist) else "Unavailable"
        )
        population_text = (
            f"{population:,.0f}"
            if pd.notna(population)
            else "Unavailable"
        )
        feature_text = (
            f"{feature_count:,.0f}"
            if pd.notna(feature_count)
            else "Unavailable"
        )

        priority_band_text = (
            str(priority_band)
            if pd.notna(priority_band)
            else "Not scored"
        )

        priority_score_text = (
            f"{priority_score:.1f} / 100"
            if pd.notna(priority_score)
            else "Not scored"
        )

        popup_html = f"""
        <div style="font-size:13px; min-width:220px;">
          <b>Province:</b> {province}<br>
          <b>District:</b> {district}<br>
          <b>Sector:</b> {sector_name} ({sector_code})<br>
          <b>Estimated population:</b> {population_text}<br>
          <b>Mapped features in sector:</b> {feature_text}<br>
          <b>Screening priority:</b> {priority_band_text}<br>
          <b>Priority score:</b> {priority_score_text}<br>
          <b>Nearest mapped feature:</b> {dist_text}<br>
          <i>Approximate straight-line distance, not road travel distance.</i>
        </div>
        """

        folium.GeoJson(
            row.geometry,
            style_function=lambda feature, color=distance_color(dist): {
                "fillColor": color,
                "color": "#64748b",
                "weight": 0.70,
                "fillOpacity": 0.68,
            },
            tooltip=f"{district} — {sector_name} — {dist_text}",
            popup=folium.Popup(popup_html, max_width=350),
        ).add_to(m)


    # Draw province boundaries with a distinct color and thin lines.
    province_boundaries = map_geo.dissolve(
        by="province",
        as_index=False,
    )

    for _, province_row in province_boundaries.iterrows():
        folium.GeoJson(
            province_row.geometry,
            style_function=lambda feature: {
                "fillOpacity": 0,
                "color": "#7c3aed",
                "weight": 1.0,
                "opacity": 0.9,
            },
            tooltip=str(province_row["province"]),
            interactive=False,
        ).add_to(m)


    legend_html = """
    <div style="
        position: fixed;
        bottom: 25px;
        left: 25px;
        z-index: 9999;
        background: white;
        color: #222;
        padding: 12px;
        border: 1px solid #888;
        border-radius: 5px;
        font-size: 13px;">
      <b>Distance to nearest mapped feature</b><br>
      <span style="color:#2166ac;">&#9632;</span> 5 km or less<br>
      <span style="color:#ef8a62;">&#9632;</span> Over 5 to 10 km<br>
      <span style="color:#b2182b;">&#9632;</span> Over 10 km<br>
      <span style="color:#808080;">&#9632;</span> Unavailable<br>
      <hr style="margin:6px 0;">
      <span style="color:#7c3aed;">━━</span> Province boundary
    </div>
    """

    m.get_root().html.add_child(folium.Element(legend_html))

    components.html(
        m.get_root().render(),
        height=680,
        scrolling=False,
    )

    st.caption(
        "The map follows the selected province, district, and distance "
        "filter. Thin grey-blue lines show sector boundaries; thin purple "
        "lines show province boundaries."
    )


# ============================================================
# 6. SECTOR RESULTS TABLE
# ============================================================

st.markdown("## Sector-Level Results")

st.caption(
    "Priority bands are based on a project-defined score combining "
    "relative straight-line distance to the nearest mapped healthcare "
    "feature (60%) and estimated sector population (40%). "
    "They are intended for geographic screening, not as official "
    "healthcare standards or proof of unmet need. "
    "Mapped features may be incomplete or unverified."
)

preferred_columns = [
    "province",
    "district",
    "sector",
    "sector_code",
    "estimated_population",
    "mapped_feature_count",
    "nearest_feature_distance_km",
    "nearest_pharmacy_distance_km",
    "nearest_hospital_like_distance_km",
    "nearest_primary_care_distance_km",
    "priority_band",
    "priority_score",
]

display_columns = [
    column
    for column in preferred_columns
    if column in filtered_geo.columns
]

table = filtered_geo[display_columns].copy()


# Show highest geographic screening priorities first.
table = table.sort_values(
    "priority_score",
    ascending=False,
    na_position="last",
)


st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    "Download filtered sector results (CSV)",
    data=table.to_csv(index=False).encode("utf-8"),
    file_name="healthgap_filtered_sector_results.csv",
    mime="text/csv",
)


# ============================================================
# 7. METHODOLOGY AND LIMITATIONS
# ============================================================

with st.expander("Methodology and limitations"):
    st.markdown(
        """
        **Data sources**

        - Weighted sector-level population estimates derived from NISR's 2022
          Population and Housing Census public-use sample using Pop_weight.
          The public-use sample excludes residents counted in institutions;
          estimates should therefore be interpreted with this limitation in mind.
        - OpenStreetMap/HOT mapped healthcare features.
        - Administrative sector boundaries with province and district names.

        **Distance method**

        Distances were calculated from representative points inside sector
        polygons to the nearest mapped feature using a projected coordinate
        system. They are straight-line distances, not road-network distances
        or travel times.

        **Facility classification**

        Facility-type groups are provisional and rely on available map tags
        and names. They do not confirm the facility's operating status,
        staffing, capacity, quality, or actual clinical services.

        **Limitations**

        - Mapped features may be incomplete, duplicated, or non-operational.
        - Pharmacies, health posts, health centres, and hospitals provide
          different services and are not interchangeable.
        - A sector's representative point does not represent every resident.
        - Distance alone does not establish unmet healthcare need.
        - The 5 km and 10 km thresholds are exploratory, not official standards.
        - NISR population-weighting guidance should be confirmed before
          describing the population figures as official totals.
        """
    )


# ============================================================
# 8. FOOTER
# ============================================================

st.markdown("---")
st.caption(
    "HealthGap Rwanda | Geographic decision support for preliminary "
    "planning and further investigation. Not a clinical tool."
)
