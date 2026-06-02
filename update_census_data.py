"""
WFD CRA — Automated Census Data Updater
========================================
Pulls fresh ACS 5-Year data from the Census API, cleans it,
runs a spatial join against fire district boundaries, and writes
all output CSVs to data/clean/.

Runs via GitHub Actions every October 15th.

Tables pulled:
  B17001 — Poverty status (tract level)
  B27001 — Health insurance coverage (tract level)
  B01001 — Age 65+ (tract level)
  B16004 — Language spoken at home (tract level)
  B01003 — Total population (tract level)
  B03002 — Race and ethnicity (tract level)

Output files:
  data/clean/westminster_poverty.csv
  data/clean/westminster_insurance.csv
  data/clean/westminster_age_65plus.csv
  data/clean/westminster_language.csv
  data/clean/westminster_population.csv
  data/clean/westminster_race.csv
  data/clean/westminster_demographics_by_district.csv  ← spatial join output

GitHub repo: https://github.com/smaddux303/wfd-cra
"""

import requests
import pandas as pd
import json
import os
import sys
import urllib.request
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────
CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "")
ACS_YEAR       = datetime.now().year - 2
BASE_URL       = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"
STATE          = "08"
ADAMS_CO       = "001"
JEFFERSON_CO   = "059"
OUT_DIR        = "data/clean"
DISTRICTS_FILE = "FireResponseAreas.json"

print(f"WFD CRA — Census Data Updater")
print(f"ACS Year: {ACS_YEAR} 5-Year Estimates")
print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 55)

# ── Install spatial libraries if needed ───────────────────────
import subprocess
subprocess.run([sys.executable, "-m", "pip", "install",
                "geopandas", "pyproj", "shapely", "--quiet"], check=True)

import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from pyproj import Transformer

# ── Helper functions ───────────────────────────────────────────
def census_get(get_vars, for_clause, in_clause=None):
    params = {"get": ",".join(["NAME"] + get_vars), "for": for_clause}
    if in_clause:
        params["in"] = in_clause
    if CENSUS_API_KEY:
        params["key"] = CENSUS_API_KEY
    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data[1:], columns=data[0])
    for col in df.columns:
        if col not in ("NAME", "state", "county", "tract"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def get_tracts(get_vars):
    frames = []
    for county in [ADAMS_CO, JEFFERSON_CO]:
        df = census_get(
            get_vars=get_vars,
            for_clause="tract:*",
            in_clause=f"state:{STATE} county:{county}"
        )
        df["county_fips"] = county
        frames.append(df)
    combined = pd.concat(frames, ignore_index=True)
    combined["GEO_ID"] = (STATE
                          + combined["county_fips"]
                          + combined["tract"].str.zfill(6))
    combined["Tract_Name"] = combined["NAME"]
    return combined

def pct(n, d):
    return round(float(n) / float(d) * 100, 1) if d and d > 0 else None

# ── 1. POVERTY RATE ────────────────────────────────────────────
print("\n1/6  Poverty rate (B17001)...")
try:
    raw = get_tracts(["B17001_001E", "B17001_002E"])
    raw["Total_Pop"]     = raw["B17001_001E"]
    raw["Below_Poverty"] = raw["B17001_002E"]
    raw["Poverty_Rate"]  = raw.apply(
        lambda r: pct(r["Below_Poverty"], r["Total_Pop"]), axis=1)
    out = raw[["GEO_ID","Tract_Name","Total_Pop","Below_Poverty","Poverty_Rate"]]
    out.to_csv(f"{OUT_DIR}/westminster_poverty.csv", index=False)
    print(f"   ✓ {len(out)} tracts → westminster_poverty.csv")
except Exception as e:
    print(f"   ✗ Failed: {e}"); sys.exit(1)

# ── 2. UNINSURED RATE ──────────────────────────────────────────
print("\n2/6  Health insurance (B27001)...")
try:
    uninsured_male   = [f"B27001_{str(i).zfill(3)}E" for i in [5,8,11,14,17,20,23,26,29]]
    uninsured_female = [f"B27001_{str(i).zfill(3)}E" for i in [33,36,39,42,45,48,51,54,57]]
    all_cols = ["B27001_001E"] + uninsured_male + uninsured_female
    raw = get_tracts(all_cols)
    raw["Total_Pop"]       = raw["B27001_001E"]
    raw["Total_Uninsured"] = raw[uninsured_male + uninsured_female].sum(axis=1)
    raw["Uninsured_Rate"]  = raw.apply(
        lambda r: pct(r["Total_Uninsured"], r["Total_Pop"]), axis=1)
    out = raw[["GEO_ID","Tract_Name","Total_Pop","Total_Uninsured","Uninsured_Rate"]]
    out.to_csv(f"{OUT_DIR}/westminster_insurance.csv", index=False)
    print(f"   ✓ {len(out)} tracts → westminster_insurance.csv")
except Exception as e:
    print(f"   ✗ Failed: {e}"); sys.exit(1)

# ── 3. AGE 65+ ─────────────────────────────────────────────────
print("\n3/6  Age 65+ (B01001)...")
try:
    male_65   = [f"B01001_{str(i).zfill(3)}E" for i in range(20, 26)]
    female_65 = [f"B01001_{str(i).zfill(3)}E" for i in range(44, 50)]
    all_cols  = ["B01001_001E"] + male_65 + female_65
    raw = get_tracts(all_cols)
    raw["Total_Pop"]  = raw["B01001_001E"]
    raw["Pop_65plus"] = raw[male_65 + female_65].sum(axis=1)
    raw["Pct_65plus"] = raw.apply(
        lambda r: pct(r["Pop_65plus"], r["Total_Pop"]), axis=1)
    out = raw[["GEO_ID","Tract_Name","Total_Pop","Pop_65plus","Pct_65plus"]]
    out.to_csv(f"{OUT_DIR}/westminster_age_65plus.csv", index=False)
    print(f"   ✓ {len(out)} tracts → westminster_age_65plus.csv")
except Exception as e:
    print(f"   ✗ Failed: {e}"); sys.exit(1)

# ── 4. LANGUAGE ────────────────────────────────────────────────
print("\n4/6  Language spoken at home (B16004)...")
try:
    raw = get_tracts(["B16004_001E", "B16004_003E"])
    raw["Total_Pop_5plus"] = raw["B16004_001E"]
    raw["English_Only"]    = raw["B16004_003E"]
    raw["Non_English"]     = raw["Total_Pop_5plus"] - raw["English_Only"]
    raw["Pct_Non_English"] = raw.apply(
        lambda r: pct(r["Non_English"], r["Total_Pop_5plus"]), axis=1)
    out = raw[["GEO_ID","Tract_Name","Total_Pop_5plus",
               "English_Only","Non_English","Pct_Non_English"]]
    out.to_csv(f"{OUT_DIR}/westminster_language.csv", index=False)
    print(f"   ✓ {len(out)} tracts → westminster_language.csv")
except Exception as e:
    print(f"   ✗ Failed: {e}"); sys.exit(1)

# ── 5. POPULATION ──────────────────────────────────────────────
print("\n5/6  Total population (B01003)...")
try:
    raw = get_tracts(["B01003_001E"])
    raw["Total_Pop"] = raw["B01003_001E"]
    out = raw[["GEO_ID","Tract_Name","Total_Pop"]]
    out.to_csv(f"{OUT_DIR}/westminster_population.csv", index=False)
    print(f"   ✓ {len(out)} tracts → westminster_population.csv")
except Exception as e:
    print(f"   ✗ Failed: {e}"); sys.exit(1)

# ── 6. RACE AND ETHNICITY ──────────────────────────────────────
print("\n6/6  Race and ethnicity (B03002)...")
try:
    raw = get_tracts(["B03002_001E","B03002_003E",
                      "B03002_004E","B03002_006E","B03002_012E"])
    raw["Total_Pop"]          = raw["B03002_001E"]
    raw["White_NonHispanic"]  = raw["B03002_003E"]
    raw["Black_NonHispanic"]  = raw["B03002_004E"]
    raw["Asian_NonHispanic"]  = raw["B03002_006E"]
    raw["Hispanic"]           = raw["B03002_012E"]
    raw["Pct_White_NonHisp"]  = raw.apply(lambda r: pct(r["White_NonHispanic"], r["Total_Pop"]), axis=1)
    raw["Pct_Black"]          = raw.apply(lambda r: pct(r["Black_NonHispanic"],  r["Total_Pop"]), axis=1)
    raw["Pct_Asian"]          = raw.apply(lambda r: pct(r["Asian_NonHispanic"],  r["Total_Pop"]), axis=1)
    raw["Pct_Hispanic"]       = raw.apply(lambda r: pct(r["Hispanic"],           r["Total_Pop"]), axis=1)
    out = raw[["GEO_ID","Tract_Name","Total_Pop",
               "White_NonHispanic","Pct_White_NonHisp",
               "Black_NonHispanic","Pct_Black",
               "Asian_NonHispanic","Pct_Asian",
               "Hispanic","Pct_Hispanic"]]
    out.to_csv(f"{OUT_DIR}/westminster_race.csv", index=False)
    print(f"   ✓ {len(out)} tracts → westminster_race.csv")
except Exception as e:
    print(f"   ✗ Failed: {e}"); sys.exit(1)

# ── 7. SPATIAL JOIN → DEMOGRAPHICS BY DISTRICT ────────────────
print("\n7/7  Spatial join → demographics by district...")
try:
    # Load district boundaries
    if not os.path.exists(DISTRICTS_FILE):
        raise FileNotFoundError(f"{DISTRICTS_FILE} not found in repo root")

    districts_gdf = gpd.read_file(DISTRICTS_FILE)
    districts_gdf = districts_gdf.set_crs('EPSG:4326', allow_override=True)
    print(f"   Districts loaded: {len(districts_gdf)}")

    # Download Colorado tract boundaries from Census SDK
    print("   Downloading CO tract boundaries...")
    req = urllib.request.Request(
        "https://raw.githubusercontent.com/uscensusbureau/citysdk/master/v2/GeoJSON/500k/2020/08/tract.json",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        co_tracts = json.load(r)

    tracts_gdf = gpd.GeoDataFrame.from_features(co_tracts["features"], crs="EPSG:4326")
    tracts_gdf["GEO_ID"] = (tracts_gdf["STATEFP"]
                             + tracts_gdf["COUNTYFP"]
                             + tracts_gdf["TRACTCE"]).astype(str)
    tracts_gdf = tracts_gdf[tracts_gdf["COUNTYFP"].isin(["001","059"])]
    print(f"   CO tracts loaded: {len(tracts_gdf)}")

    # Reproject to UTM 13N for accurate centroid calculation
    tracts_proj    = tracts_gdf.to_crs("EPSG:26913")
    districts_proj = districts_gdf.to_crs("EPSG:26913")

    tracts_proj["centroid"] = tracts_proj.geometry.centroid
    tracts_c = tracts_proj.set_geometry("centroid")

    joined = gpd.sjoin(tracts_c, districts_proj[["District","geometry"]],
                       how="left", predicate="within")
    joined = joined[["GEO_ID","District"]].dropna(subset=["District"]).copy()
    joined["District"] = joined["District"].astype(int)
    joined["GEO_ID"]   = joined["GEO_ID"].astype(str)
    print(f"   Tracts matched to districts: {len(joined)}")

    # Load all tract CSVs and fix GEO_ID to 11-digit format
    def load_fix(path, cols):
        df = pd.read_csv(path)
        df["GEO_ID"] = df["GEO_ID"].astype(str).str.zfill(11)
        return df[cols]

    poverty  = load_fix(f"{OUT_DIR}/westminster_poverty.csv",
                        ["GEO_ID","Total_Pop","Below_Poverty"])
    insure   = load_fix(f"{OUT_DIR}/westminster_insurance.csv",
                        ["GEO_ID","Total_Uninsured"])
    age      = load_fix(f"{OUT_DIR}/westminster_age_65plus.csv",
                        ["GEO_ID","Pop_65plus"])
    language = load_fix(f"{OUT_DIR}/westminster_language.csv",
                        ["GEO_ID","Non_English"])
    race     = load_fix(f"{OUT_DIR}/westminster_race.csv",
                        ["GEO_ID","White_NonHispanic","Black_NonHispanic",
                         "Asian_NonHispanic","Hispanic"])

    tracts = joined.copy()
    tracts = tracts.merge(poverty,  on="GEO_ID", how="left")
    tracts = tracts.merge(insure,   on="GEO_ID", how="left")
    tracts = tracts.merge(age,      on="GEO_ID", how="left")
    tracts = tracts.merge(language, on="GEO_ID", how="left")
    tracts = tracts.merge(race,     on="GEO_ID", how="left")

    # Aggregate by district
    def district_summary(group):
        t  = group["Total_Pop"].sum()
        bp = group["Below_Poverty"].sum()
        ui = group["Total_Uninsured"].sum()
        s  = group["Pop_65plus"].sum()
        ne = group["Non_English"].sum()
        wh = group["White_NonHispanic"].sum()
        bl = group["Black_NonHispanic"].sum()
        as_ = group["Asian_NonHispanic"].sum()
        hi = group["Hispanic"].sum()
        return pd.Series({
            "Station":          f"Station {int(group['District'].iloc[0])}",
            "Total_Pop":        int(t),
            "Below_Poverty":    int(bp),
            "Poverty_Rate":     pct(bp, t),
            "Total_Uninsured":  int(ui),
            "Uninsured_Rate":   pct(ui, t),
            "Pop_65plus":       int(s),
            "Pct_65plus":       pct(s, t),
            "Non_English":      int(ne),
            "Pct_Non_English":  pct(ne, t),
            "White_NonHispanic":int(wh),
            "Pct_White_NonHisp":pct(wh, t),
            "Black_NonHispanic":int(bl),
            "Pct_Black":        pct(bl, t),
            "Asian_NonHispanic":int(as_),
            "Pct_Asian":        pct(as_, t),
            "Hispanic":         int(hi),
            "Pct_Hispanic":     pct(hi, t),
            "Tract_Count":      len(group)
        })

    summary = tracts.groupby("District").apply(district_summary).reset_index()
    summary = summary.sort_values("District")
    summary.to_csv(f"{OUT_DIR}/westminster_demographics_by_district.csv", index=False)

    print(f"   ✓ {len(summary)} districts → westminster_demographics_by_district.csv")
    print()
    print("   District summary:")
    for _, row in summary.iterrows():
        print(f"   District {int(row.District)} | Pop {int(row.Total_Pop):,} | "
              f"Poverty {row.Poverty_Rate}% | Uninsured {row.Uninsured_Rate}% | "
              f"65+ {row.Pct_65plus}% | Hispanic {row.Pct_Hispanic}%")

except Exception as e:
    print(f"   ✗ Spatial join failed: {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

# ── Done ───────────────────────────────────────────────────────
print()
print("=" * 55)
print(f"✓ All data updated — ACS {ACS_YEAR} 5-Year Estimates")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
print(f"  Repo: https://github.com/smaddux303/wfd-cra")
print("=" * 55)
