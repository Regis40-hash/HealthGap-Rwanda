HealthGap Rwanda — Data Documentation

Sector boundaries

File used: boundaries/rwanda_sectors_2022.geojson

These boundaries provide the geographic units used to display and summarize results by sector. Sector identifiers are used to connect boundary features to the census-derived analysis.

source:https://moegis.environment.gov.rw/server/rest/services/Hosted/Administrative_boundaries/FeatureServer/1?

Census population estimates

The analysis uses Rwanda's 2022 Population and Housing Census public-use microdata from NISR.

Source: https://www.microdata.statistics.gov.rw/index.php/catalog/109

The source microdata is not included in this repository. Weighted sector-level estimates are precomputed in the analysis outputs using Pop_weight. The public-use sample excludes residents counted in institutions, and the resulting estimates have that limitation.

Mapped healthcare locations

Healthcare locations were derived from an OpenStreetMap/Humanitarian OpenStreetMap Team (HOT) snapshot dated 7 October 2026.

Source portals:

https://www.openstreetmap.org/

https://export.hotosm.org/

The project uses mapped locations as screening inputs, not as a verified register of operating facilities. Features may be incomplete, duplicated, outdated, or misclassified.

Processed outputs

outputs/sector_analysis.csv — sector-level population and related analysis.

outputs/geographic_access_analysis.csv — sector-level geographic access indicators and screening scores.

These outputs are intended for preliminary analysis. Straight-line distances and project-defined scores should not be interpreted as proof of unmet healthcare need.

Reproducibility

The repository contains Python scripts used to prepare and validate the analysis. To reproduce the complete pipeline, obtain the required source datasets from their authorized sources and follow the scripts' expected file paths and dependencies.

Check the source datasets' license and redistribution conditions before sharing copies.
