# MUMBAI: THE AIR WE BUILD

**Understanding how the city we build shapes the air we breathe.**

An interactive urban-intelligence platform for the Google Mumbai Data Challenge 2026 (Most Creative Submission).
It puts 48,381 hours of measured CPCB PM2.5 back into the city that produced them: 299,810 building footprints with
storeys and use, 5,040 km of streets, every BEST stop, suburban station, mapped park and Development Plan 2034
reservation — and lets you test planning decisions on that real geometry.

It is deliberately **not** an AQI dashboard and **not** a pollution forecast.

## The eight pages

| Page | What it does |
|---|---|
| Overview | The record at a glance and the four kinds of number used (measured / derived / research estimate / hypothetical) |
| Explore the city | Layered map: stations coloured by measured PM2.5 for a chosen period, streets by carriageway width, rail, bus stops, parks, 500 m built-form grid, Development Plan polygons. Click a station for trend, daily and weekly rhythm, and surroundings at 250 m – 2 km |
| 3D Mumbai | Buildings extruded by BMC's recorded storeys around each monitor or across any ward; citywide built-form columns |
| Understand the pollution | Hour × month heatmaps, weekday test with bootstrap intervals, spike episodes, a space-vs-time variance split, a 25-station test of surroundings vs PM2.5 with radius sensitivity, two published emission inventories, the measured PM2.5 : PM10 ratio, and mechanism explainers |
| Urban equity | Compare any wards on parks, open space, bus and rail access, schools, clinics, toilets, built form and planned reservations; population-weighted Gini per amenity |
| Reimagine Mumbai | Emissions-by-source simulator on either inventory; build out reserved parks; greedy bus-stop placement; development-intensity arithmetic |
| What next? | Eight evidence-linked interventions and a top five ranked on criteria whose weights the user sets |
| Data & methods | Sources with ClimateVerse DOIs, quality report, data dictionary, method, limits, and an optional Gemini explainer |

## What the data actually says

- **Season beats place.** 63% of hour-to-hour PM2.5 variation is shared by all four stations in the same hour; only 6% is a persistent difference between stations.
- **Winter medians are 2.8–6.2× monsoon medians** at the same stations. Emissions set the supply; weather decides how much stays in the air.
- **No clear spatial association.** Across 25 archive stations, no measure of surroundings (building cover, floor area ratio, road density, bus stops, parks, open space) has a rank correlation with 2024 median PM2.5 stronger than |ρ| = 0.29 at any buffer radius, and every 90% interval includes zero. The app says so rather than inventing a pattern.
- **Shivaji Nagar has 157 spike hours**, against 86 at the next-highest station.
- **The two published inventories disagree, instructively**: road dust is 72% of total particulate load (NEERI–IIT Bombay) but 15% of PM2.5 emissions (SAFAR), where exhaust and waste burning lead.
- **Access is unequal**: homes within 500 m of a mapped park range from 46% (F/South) to 99% (R/North); within 1 km of a suburban station from 19% to 100%.

## Scientific guardrails

- Measured PM2.5 is never altered, interpolated or gap-filled. Only the organisers' flag for readings above 1,000 µg/m³ (19 hours, including values near 100,000) is excluded.
- No ward-level PM2.5 is shown anywhere: four live monitors cannot support it.
- The simulator reports **emitted mass by source**, never µg/m³. Its assumptions panel explains why an emission cut is not a concentration cut.
- PM10 appears in exactly one chart, labelled. Everything else measured is PM2.5.
- Correlation, spatial association and causation are kept apart in the text.
- Gemini, when enabled, receives only a deterministic fact sheet and is instructed not to add numbers or causal claims.

## Run it

```bash
pip install -r requirements.txt
```

```bash
streamlit run app.py
```

`data/processed/` (38 MB) is committed, so the app runs as cloned.

### Deploy on Streamlit Community Cloud (free)

1. Push this folder to a public GitHub repository.
2. At share.streamlit.io choose **New app**, select the repository, branch `main`, main file `app.py`.
3. Optional: under **Advanced settings → Secrets** add `GEMINI_API_KEY = "..."` (free key from Google AI Studio) to switch on the "Ask the data" tab. `GEMINI_MODEL` overrides the default model.

### Rebuild the data from source

```bash
pip install -r requirements-build.txt
```

```bash
python scripts/fetch_bmc.py
```

```bash
python scripts/build_processed.py
```

```bash
python scripts/validate.py
```

See `data/raw/README.md` for where the competition and OpenCity files go. `notebooks/rebuild_in_colab.ipynb` runs the same pipeline in Google Colab.

## Project layout

```
app.py                     navigation and shell
config.py                  palette, thresholds, source register
modules/                   data_loader, air_quality_analysis, geospatial_analysis,
                           scenario_simulator, recommendations, facts, gemini_explainer
views/                     one file per page
visualizations/            charts (Plotly), maps (pydeck), ui (typography)
scripts/                   fetch_bmc, build_processed, validate
data/processed/            app-ready tables (committed)
docs/                      DATA_AUDIT.md, DEMO_SCRIPT.md
```

## Data sources

All data comes from the challenge's core dataset or from ClimateVerse's *Google Air Quality Forecasting Challenge* catalogue.

| Dataset | ClimateVerse DOI | Used for |
|---|---|---|
| CPCB hourly PM2.5, four stations (Train.csv, CC BY-SA 4.0) | – | All measured charts |
| Mumbai PM2.5 2024, 29 series (AdditionalHistory.zip) | – | Station-surroundings test |
| Station history 2018–2020 with PM10 (AdditionalHistory.zip) | – | PM2.5 : PM10 ratio |
| BMC SAC building footprints | 10.71646/NVQWMN | Morphology, 3D, exposure weights |
| BMC street network with carriageway width | 10.71646/HEV9L0 | Road density, widths |
| BMC base layers (rail, water) | 10.71646/O2DK71 | Map layers |
| BMC electoral ward boundaries with population | 10.71646/EREDWQ | Ward population |
| BMC administrative ward boundaries | 10.71646/2DGEEJ | The 24 wards |
| BMC Development Plan 2034 Know Your Ward | 10.71646/OBVAPI | Existing vs planned land |
| My BMC on Maps civic facilities | 10.71646/1XSUVR | Schools, health, toilets |
| BEST bus stops and depots (OpenCity) | 10.71646/MEEUPH | Bus access |
| BMC parks and gardens (OpenCity) | 10.71646/8EKNG8 | Park access |
| Mumbai Suburban Network 2025 (OpenCity) | 10.71646/91DIJW | Rail access |

Research estimates (labelled in the app): CSIR-NEERI & IIT Bombay (2020) Mumbai emission inventory for MPCB; SAFAR-IITM 2019–20 Mumbai PM2.5 inventory as reported by The Times of India (2021).

## Known limits and flagged ambiguities

- **Licences.** BMC ArcGIS layers state no licence. They are catalogued by ClimateVerse, which the rules permit; raw copies are not redistributed here, only derived tables. Confirm with the organisers if the entry is published beyond the competition.
- **External research figures.** The two emission inventories are published reports, not ClimateVerse datasets. They are used as cited context, not as modelling inputs for the leaderboard task.
- **Mixed dates.** Population is Census 2011; buildings 2025; streets 2023; Development Plan 2021.
- **Thin attributes.** Parks are points without area; bus stops have no routes; carriageway width is recorded for 35% of street length; storeys are missing for 6% of buildings.
- **Not used.** Vacant Land Tax plots (table without geometry), Ganeshotsav layers and disaster-management layers (out of scope), other-station 2025–26 data (no coordinates supplied).
- **Google tools.** Gemini is integrated but optional and off without a key. Google Earth Engine was not used because it needs authenticated project access; satellite vegetation and built-up layers would be the natural next addition. A Colab notebook reproduces the pipeline.
- **No atmospheric model.** Converting scenarios to concentrations needs gridded emissions, meteorology and a dispersion model that the permitted data cannot drive.
#   M u m b a i - A i r - C r e a t i v e - S u b m i s s i o n  
 