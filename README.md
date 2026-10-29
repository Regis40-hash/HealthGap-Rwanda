HealthGap Rwanda

Geospatial Screening for Potential Healthcare Access Gaps

Overview

HealthGap Rwanda is an interactive geospatial dashboard designed to support preliminary exploration of potential geographic gaps in healthcare access across Rwanda.

It combines administrative sector boundaries, weighted sector-level population estimates derived from Rwanda's 2022 Population and Housing Census public-use sample, and mapped healthcare locations. The dashboard helps users identify sectors that may warrant further investigation.

Important: HealthGap Rwanda is a preliminary screening tool. Its distance estimates and priority scores do not prove that a community lacks healthcare services or that a particular facility is accessible, operational, or adequately staffed.

Problem

Geographic distance, population distribution, and the location of mapped healthcare facilities are useful starting points for healthcare planning. Bringing these datasets together can help identify locations where further assessment may be worthwhile.

HealthGap Rwanda provides a visual and interactive way to explore these relationships at sector level.

Features

Interactive map of Rwanda's sectors.

Geographic screening based on the distance from a sector representative point to the nearest mapped healthcare feature.

Sector-level population estimates and mapped-feature counts.

Filters for province and district.

Exploratory priority scores combining normalized distance and population.

A sortable sector results table.

CSV export for further analysis.

Methodology and limitations information within the application.

Data sources

Population data

The project uses Rwanda's 2022 Population and Housing Census public-use microdata provided by the National Institute of Statistics of Rwanda (NISR).

Source: https://www.microdata.statistics.gov.rw/index.php/catalog/109

The analysis uses Pop_weight to calculate weighted sector-level population estimates. The public-use sample represents private households and excludes residents counted in institutions, so these estimates should not be interpreted as exact official sector population totals.

Administrative boundaries

The project uses Rwanda sector boundary data for geographic mapping and joins census-derived estimates to sector identifiers.

The processed boundary file used by the application is:

data/boundaries/rwanda_sectors_2022.geojson

See the data documentation for the source and processing details of the boundary file.

Healthcare locations

The project uses mapped healthcare features from an OpenStreetMap/Humanitarian OpenStreetMap Team (HOT) data snapshot dated 7 October 2026.

Source portals:

OpenStreetMap: https://www.openstreetmap.org/

HOT Export Tool: https://export.hotosm.org/

Mapped features may be incomplete, duplicated, incorrectly classified, or no longer operational. A missing mapped feature does not establish that a sector has no healthcare facility.

Methodology

Prepare sector-level population estimates using the NISR public-use census sample and its population weights.

Join sector estimates to the administrative boundary dataset using sector identifiers.

Calculate straight-line distances from sector representative points to the nearest mapped healthcare feature.

Summarize mapped healthcare features and geographic access indicators by sector.

Calculate an exploratory priority score using normalized distance (60%) and normalized population (40%).

The distance and population weights are project-defined choices for exploratory screening, not validated clinical or government planning standards. The distance calculations do not account for road networks, terrain, travel time, facility capacity, service availability, or quality of care.

How to use the dashboard

Open the deployed application.

Explore the national sector map.

Use the province and district filters to narrow the area of interest.

Review sector distances, mapped-feature counts, population estimates, and priority scores.

Select or inspect sectors on the map to view their details.

Sort the sector results table and download the displayed analysis as a CSV.

Read the methodology and limitations before drawing conclusions.

Run locally

Requirements: Python and the packages listed in requirements.txt.

Clone this repository.

Create and activate a Python virtual environment.

Install dependencies:

pip install -r requirements.txt

Run the application:

streamlit run app.py

Ensure the required analysis CSV and boundary GeoJSON are present at the paths expected by app.py.

Repository structure

app.py — Streamlit dashboard.

requirements.txt — Python dependencies.

build_sector_analysis.py — sector-level analysis preparation.

build_access_analysis.py — geographic access analysis.

validate_priority_scores.py — priority-score validation.

outputs/ — processed analysis CSV files.

data/boundaries/ — sector boundary data.

data/README.md — additional data-source and processing documentation.

Limitations and responsible interpretation

Straight-line distance is not road travel distance or travel time.

Sector representative points may not reflect where residents actually live.

Mapped healthcare locations may be incomplete, duplicated, misclassified, or outdated.

A mapped location does not confirm that a facility is operational or offers a particular service.

Population estimates are derived from a public-use sample that excludes institutional residents.

The priority score uses project-defined weights and is not a validated measure of unmet healthcare need.

Results should be checked through local consultation, facility verification, and more detailed transport and service-capacity analysis.

Potential next steps

Future work could incorporate verified facility registers, road-network travel times, facility capacity and service information, and consultation with local health authorities and communities.

AI-use disclosure

AI assistance was used during project development and documentation. The project team is responsible for reviewing, testing, and validating the submitted code, analysis, and claims, in accordance with the hackathon rules.

Project status

HealthGap Rwanda is a prototype for preliminary geospatial screening and further investigation. It is not a diagnostic tool and does not establish that healthcare needs are unmet.
