"""Download BMC ArcGIS FeatureServer layers catalogued by ClimateVerse India.

Reproducible, anonymous, read-only. Only non-personal attribute fields are requested
(owner / applicant / councillor / staff name columns are never downloaded).
Output: newline-delimited GeoJSON features in data/raw/bmc/<key>.geojsonl (EPSG:4326).

Usage: python scripts/fetch_bmc.py [key ...]
"""
import json, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

BASE = "https://services8.arcgis.com/r6MmJtuWAzMawmJ8/arcgis/rest/services/"
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "bmc"

# key: (service, layer id, fields, ClimateVerse DOI)
LAYERS = {
    "buildings": ("SAC_Buildings", 0, "OBJECTID,WARD,NO_OF_FLOO,TYPE,USAGE,CONSTRUCTI,AGE_BUILD,SLUM_NON_SLUM,Shape__Area", "10.71646/NVQWMN"),
    "streets": ("Streets", 0, "OBJECTID,WARD_ID,CARRIAGE_W,NO_OF_LANE,NAME,DRV_STATUS,LKM", "10.71646/HEV9L0"),
    "railway_lines": ("BaseLayersgdb", 1, "OBJECTID,NAME,REMARKS,SUB_TYPE", "10.71646/O2DK71"),
    "waterbodies": ("BaseLayersgdb", 2, "OBJECTID,NAME_OF_LAKE,TYPE", "10.71646/O2DK71"),
    "prabhags": ("Prabhaag_Boundary", 0, "OBJECTID,POPULATION,WARD,PRABHAG_NO", "10.71646/EREDWQ"),
    "wards": ("Ward_Boundary12", 0, "OBJECTID,WARD,REMARK,ABBREVIATION", "10.71646/2DGEEJ"),
    "dp_reservations": ("DP_KYW", 0, "OBJECTID,WARD,RES_CODE,RES_MAINTYPE,DISCRIPTION,TYPE,RES_AREA", "10.71646/OBVAPI"),
    "dp_existing_amenities": ("DP_KYW", 1, "FID_HE_DES,WARD,NEW_DES_MAINTYPE,NEW_DES_CODE,DISCRIPTION,TYPE,AREA", "10.71646/OBVAPI"),
}
# My BMC on Maps civic facility layers (ClimateVerse doi:10.71646/1XSUVR). Geometry + OBJECTID only:
# the contact, staff and phone columns on these layers are deliberately not requested.
CIVIC = {"school_bmc": 0, "school_aided": 1, "school_unaided": 2, "hospital_main": 3, "hospital_special": 4,
         "hospital_peripheral": 5, "hospital_dental": 27, "polyclinic": 6, "dispensary": 8, "hbt_clinic": 9,
         "maternity_home": 11, "health_post": 12, "funeral_site": 14, "parking_off_street": 18, "public_toilet": 22}
for _k, _id in CIVIC.items():
    LAYERS[f"civic_{_k}"] = ("BMConMaps_Nov26gdb", _id, "OBJECTID", "10.71646/1XSUVR")
PAGE = 2000


def get(url, params, tries=5):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=120)
            r.raise_for_status()
            j = r.json()
            if "error" in j:
                raise RuntimeError(j["error"])
            return j
        except Exception as e:  # retry transient failures
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def fetch(key):
    service, lid, fields, _ = LAYERS[key]
    url = f"{BASE}{service}/FeatureServer/{lid}/query"
    oid = fields.split(",")[0]
    n = get(url, {"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
    offsets = list(range(0, n, PAGE))

    def page(off):
        j = get(url, {"where": "1=1", "outFields": fields, "outSR": 4326, "f": "geojson",
                      "orderByFields": oid, "resultOffset": off, "resultRecordCount": PAGE,
                      "geometryPrecision": 6})
        return j["features"]

    OUT.mkdir(parents=True, exist_ok=True)
    got = 0
    with ThreadPoolExecutor(6) as ex, open(OUT / f"{key}.geojsonl", "w") as f:
        for feats in ex.map(page, offsets):
            for ft in feats:
                f.write(json.dumps(ft, separators=(",", ":")) + "\n")
            got += len(feats)
    print(f"{key}: {got}/{n} features", flush=True)
    assert got == n, f"{key}: incomplete download"


if __name__ == "__main__":
    for k in sys.argv[1:] or LAYERS:
        fetch(k)
