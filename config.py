"""Paths, palette, thresholds and source references shared across the app."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"

# ---- palette (restrained, editorial) ---------------------------------------------------------
INK, MUTED, RULE, PAPER, PANEL = "#1F2328", "#6B6F76", "#D9D4C7", "#F7F4EE", "#EFEBE2"
GREEN, AMBER, RED, BLUE = "#2F5D50", "#C98A1B", "#B23A2E", "#2A78D6"
# station identity colours - validated for colour-vision-deficiency separation on PAPER
STATION_COLORS = {
    "Borivali East - IITM": "#2A78D6",
    "Byculla - BMC": "#C26A12",
    "Malad West - IITM": "#8A4FB0",
    "Shivaji Nagar - BMC": "#12A37A",
}
SEQ = ["#F3EBD8", "#EBD3A0", "#DFAE5E", "#CC8433", "#B25A25", "#8E3520", "#651D1B"]  # light -> dark, one direction

# ---- PM2.5 reference levels (24-hour mean, ug/m3) ----------------------------------------------
NAAQS_24H, WHO_24H = 60.0, 15.0
NAAQS_ANNUAL, WHO_ANNUAL = 40.0, 5.0
# CPCB National AQI sub-index breakpoints for PM2.5 (24-hour mean)
AQI_BANDS = [(0, 30, "Good", "#4E8C6A"), (30, 60, "Satisfactory", "#9DB86B"), (60, 90, "Moderate", "#E3B23C"),
             (90, 120, "Poor", "#D9822B"), (120, 250, "Very poor", "#B23A2E"), (250, 1e9, "Severe", "#6E1F1A")]


def band(v):
    for lo, hi, name, col in AQI_BANDS:
        if lo <= v < hi:
            return name, col
    return "No data", "#9AA0A6"


# ---- sources ------------------------------------------------------------------------------------
CV = "https://doi.org/"
SOURCES = [
    # name, publisher, ClimateVerse DOI, access, last updated (as stated by source), licence, how the app uses it
    ("CPCB hourly PM2.5, four target stations (Train.csv)", "CPCB / CAAQMS via OpenAQ, prepared by Zindi", None, "Competition file", "10 Nov 2026", "CC BY-SA 4.0", "Every measured PM2.5 chart; station markers"),
    ("Mumbai PM2.5 history 2024 (29 series)", "CPCB / AirNow via XKDR archive (AdditionalHistory.zip)", None, "Competition file", "31 Dec 2024", "Source terms apply", "29-station spatial comparison with surroundings"),
    ("Mumbai station history 2018-2020 with PM10", "CPCB-derived (Rohan Rao dataset, AdditionalHistory.zip)", None, "Competition file", "1 Jul 2020", "Source terms apply", "Measured PM2.5 : PM10 ratio"),
    ("BMC SAC building footprints with floors, type and usage", "Brihanmumbai Municipal Corporation", "10.71646/NVQWMN", "ArcGIS FeatureServer, polygons, EPSG:32643", "18 Dec 2025", "No licence stated", "Urban morphology, 3D Mumbai, exposure weights"),
    ("BMC street network with carriageway width", "Brihanmumbai Municipal Corporation", "10.71646/HEV9L0", "ArcGIS FeatureServer, polylines, EPSG:4326", "12 Sep 2023", "No licence stated", "Road density, carriageway widths"),
    ("BMC base layers: railways, water bodies", "Brihanmumbai Municipal Corporation", "10.71646/O2DK71", "ArcGIS FeatureServer, EPSG:3857", "24 Jun 2023", "No licence stated", "Rail and water map layers"),
    ("BMC electoral ward (prabhag) boundaries with population", "Brihanmumbai Municipal Corporation", "10.71646/EREDWQ", "ArcGIS FeatureServer, polygons, EPSG:32643", "24 Sep 2024", "No licence stated", "Ward population (sums to the 2011 Census total)"),
    ("BMC administrative ward boundaries", "Brihanmumbai Municipal Corporation", "10.71646/2DGEEJ", "ArcGIS FeatureServer, polygons, EPSG:32643", "26 Nov 2025", "No licence stated", "The 24 wards used for every ward indicator"),
    ("BMC Development Plan 2034 Know Your Ward GIS", "Brihanmumbai Municipal Corporation", "10.71646/OBVAPI", "ArcGIS FeatureServer, 2 polygon layers", "30 Jun 2021", "No licence stated", "Existing designations vs planned reservations"),
    ("My BMC on Maps: civic facility layers", "Brihanmumbai Municipal Corporation", "10.71646/1XSUVR", "ArcGIS FeatureServer, 27 layers", "30 Jul 2026", "No licence stated", "Schools, health facilities, toilets per ward (locations only)"),
    ("BEST bus stops and depots map", "BMC via OpenCity", "10.71646/MEEUPH", "KML points", "27 Nov 2025", "Public domain (as stated)", "Bus-stop access"),
    ("BMC public parks, gardens, Miyawaki gardens and zoos", "BMC via OpenCity", "10.71646/8EKNG8", "KML points", "27 Nov 2025", "Public domain (as stated)", "Park access (points only - no park area)"),
    ("Mumbai Suburban Network 2025", "BMC via OpenCity", "10.71646/91DIJW", "KML lines + points", "27 Nov 2025", "Public domain (as stated)", "Suburban rail lines and stations"),
]
NOT_USED = [
    ("BMC Vacant Land Tax plots", "10.71646/JXZJF0", "Served as an attribute table without geometry, so it cannot be mapped or buffered."),
    ("BMC Ganeshotsav mandap locations / immersion sites", "10.71646/CXGIO3", "Event-specific; not relevant to year-round infrastructure analysis."),
    ("BMC disaster management resources and incidents", "10.71646/OAAZGG", "Last edited 2023 and contains staff contact fields; outside this product's scope."),
    ("Other Mumbai stations 2025-2026 / legacy 2020-2022 samples", None, "No coordinates or cross-source station mapping supplied; irregular sampling. Inventoried only."),
]
