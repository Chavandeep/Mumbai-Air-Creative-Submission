# Data audit

Generated from `data/processed/data_inventory.json` (written by `scripts/build_processed.py`).

## Competition files

| File | Rows | Coverage | Notes |
|---|---|---|---|
| Train.csv | 48,400 | 2025-02-19 03:00:00 to 2026-11-10 09:00:00 IST, 4 stations | hourly, hour-ending; no nulls; no duplicate station-hours; 19 hours flagged above 1,000 µg/m³; 7,328 hours from 3 readings |
| Stations.csv | 4 | – | coordinates used unchanged |
| History_Mumbai_2024 | 216,472 | calendar 2024, 29 series | all series matched to coordinates in XKDR_All_Stations.csv; all inside BMC limits |
| History_Mumbai_2018_2020 | 87,717 | 2018-04 to 2020-07, 10 stations | 83,192 hours with both PM2.5 and PM10 |
| Legacy_Observations_2020_2022 | 12,452 | 2 stations | irregular samples, not hourly - inventoried, not used |
| Other_Mumbai_Stations_2025_2026 | 9,125 | 14 stations, mostly Oct 2026 | no coordinates or cross-source mapping supplied - inventoried, not mapped |
| Test.csv, SampleSubmission.csv, starter notebook | – | – | forecasting task files; not needed by this product |

Completeness (share of hours present between first and last timestamp): Borivali East - IITM 81%, Byculla - BMC 77%, Malad West - IITM 82%, Shivaji Nagar - BMC 80%.

## Geospatial layers

| Layer | Records | Used | Geometry | Null geom | Invalid (repaired) | Duplicates | Outside BMC |
|---|---|---|---|---|---|---|---|
| bmc_wards | 24 |  | Polygon | 0 | 0 | 0 |  |
| bmc_prabhags | 227 |  | Polygon | 0 | 1 | 0 |  |
| bmc_buildings | 341841 | 299810 | MultiPolygon, Polygon | 0 | 103 | 36276 | 78 |
| bmc_streets | 56804 |  | LineString, MultiLineString | 7 | 3 | 7 |  |
| bmc_railway_lines | 1829 |  | LineString, MultiLineString | 0 | 5 | 19 |  |
| opencity_suburban_lines | 106 |  |  |  |  |  |  |
| bmc_waterbodies | 31 |  | MultiPolygon, Polygon | 0 | 0 | 0 |  |
| opencity_suburban_stations | 106 | 53 |  |  |  | 0 | 53 |
| opencity_best | 6267 | 5583 |  |  |  | 20 | 684 |
| opencity_parks | 991 | 987 |  |  |  | 39 | 3 |
| bmc_civic_dispensary | 166 | 164 |  |  |  |  |  |
| bmc_civic_funeral_site | 191 | 189 |  |  |  |  |  |
| bmc_civic_hbt_clinic | 205 | 205 |  |  |  |  |  |
| bmc_civic_health_post | 216 | 215 |  |  |  |  |  |
| bmc_civic_hospital_dental | 1 | 1 |  |  |  |  |  |
| bmc_civic_hospital_main | 4 | 4 |  |  |  |  |  |
| bmc_civic_hospital_peripheral | 8 | 8 |  |  |  |  |  |
| bmc_civic_hospital_special | 5 | 5 |  |  |  |  |  |
| bmc_civic_maternity_home | 30 | 30 |  |  |  |  |  |
| bmc_civic_parking_off_street | 49 | 49 |  |  |  |  |  |
| bmc_civic_polyclinic | 33 | 33 |  |  |  |  |  |
| bmc_civic_public_toilet | 8412 | 8304 |  |  |  |  |  |
| bmc_civic_school_aided | 404 | 400 |  |  |  |  |  |
| bmc_civic_school_bmc | 1134 | 1123 |  |  |  |  |  |
| bmc_civic_school_unaided | 709 | 704 |  |  |  |  |  |
| bmc_dp_existing_amenities | 8195 |  | MultiPolygon, Polygon | 0 | 72 | 3 |  |
| bmc_dp_reservations | 5902 |  | MultiPolygon, Polygon | 0 | 75 | 0 |  |

Buildings: 2,984 demolished and 36,276 duplicate footprints removed; storeys parsed for 283,324, unknown for 19,257.
Streets: 5,040.3 km in total; carriageway width recorded for 1,751.9 km (18,788 segments).
Prabhag population total: 12,442,373 (equals the 2011 Census figure for Greater Mumbai).

All BMC layers were fetched from ArcGIS FeatureServer endpoints in native CRS EPSG:32643, 4326 or 3857 and requested in EPSG:4326; analysis is done in EPSG:32643 (metres). Personal-name, contact and staff columns present on some layers were never requested.

## Analyses the data supports

- Temporal patterns at four stations (hourly, weekly, monthly, seasonal, anomalies).
- Cross-sectional comparison of 25-29 stations for 2024 against derived surroundings.
- Ward-level urban form, access and amenity indicators.
- Measured PM2.5 : PM10 ratio for 2018-2020.

## Analyses it does not support

- Ward-level or street-level PM2.5.
- Source apportionment from the measurements.
- Any effect of traffic, construction activity or meteorology (not in the permitted data used).
- Ambient PM2.5 response to an intervention.
