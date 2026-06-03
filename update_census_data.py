"""
WFD CRA — Automated Census Data Updater
========================================
Pulls fresh ACS 5-Year data from Census API for:
  - All tract-level tables (Westminster area)
  - Colorado state benchmarks
  - US national benchmarks
  - Census County Business Patterns (Westminster zip codes)
  - BLS LAUS unemployment rates

Runs via GitHub Actions every October 15th.
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
BLS_API_KEY    = os.environ.get("BLS_API_KEY", "")
ACS_YEAR       = datetime.now().year - 2
BASE_URL       = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"
STATE          = "08"
ADAMS_CO       = "001"
JEFFERSON_CO   = "059"
WM_PLACE       = "83835"
WM_ZIPS        = ["80020","80021","80023","80030","80031","80234"]
OUT_DIR        = "data/clean"
DISTRICTS_FILE = "FireResponseAreas.json"

print(f"WFD CRA — Census Data Updater")
print(f"ACS Year: {ACS_YEAR} 5-Year Estimates")
print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 60)

# ── Install spatial libraries ──────────────────────────────────
import subprocess
subprocess.run([sys.executable, "-m", "pip", "install",
                "geopandas", "pyproj", "shapely", "--quiet"], check=True)

import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from pyproj import Transformer
import numpy as np

# ── Helper functions ───────────────────────────────────────────
def census_get(get_vars, for_clause, in_clause=None, base=None):
    url = base or BASE_URL
    params = {"get": ",".join(["NAME"] + get_vars), "for": for_clause}
    if in_clause:
        params["in"] = in_clause
    if CENSUS_API_KEY:
        params["key"] = CENSUS_API_KEY
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data[1:], columns=data[0])
    for col in df.columns:
        if col not in ("NAME","state","county","tract","place","zip code tabulation area"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def get_tracts(get_vars):
    frames = []
    for county in [ADAMS_CO, JEFFERSON_CO]:
        df = census_get(get_vars, "tract:*", f"state:{STATE} county:{county}")
        df["county_fips"] = county
        frames.append(df)
    combined = pd.concat(frames, ignore_index=True)
    combined["GEO_ID"] = (STATE + combined["county_fips"] + combined["tract"].str.zfill(6))
    return combined

def get_place(get_vars):
    return census_get(get_vars, f"place:{WM_PLACE}", f"state:{STATE}")

def get_state(get_vars):
    return census_get(get_vars, f"state:{STATE}")

def get_us(get_vars):
    return census_get(get_vars, "us:1")

def pct(n, d):
    return round(float(n)/float(d)*100, 1) if d and d > 0 and not pd.isna(n) and not pd.isna(d) else None

def safe_int(x):
    try: return int(x) if not pd.isna(x) else 0
    except: return 0

def weighted_median(values, weights):
    valid = [(v, w) for v, w in zip(values, weights)
             if not pd.isna(v) and not pd.isna(w) and w > 0]
    if not valid: return None
    valid.sort(key=lambda x: x[0])
    total_w = sum(w for _, w in valid)
    cumsum = 0
    for v, w in valid:
        cumsum += w
        if cumsum >= total_w / 2:
            return round(v, 1)
    return None

def weighted_mean(values, weights):
    valid = [(v, w) for v, w in zip(values, weights)
             if not pd.isna(v) and not pd.isna(w) and w > 0]
    if not valid: return None
    total_w = sum(w for _, w in valid)
    return round(sum(v*w for v, w in valid) / total_w, 2)

# ── 1. POVERTY RATE ────────────────────────────────────────────
print("\n1/11  Poverty rate (B17001)...")
try:
    raw = get_tracts(["B17001_001E","B17001_002E"])
    raw["Total_Pop"]     = raw["B17001_001E"]
    raw["Below_Poverty"] = raw["B17001_002E"]
    raw["Poverty_Rate"]  = raw.apply(lambda r: pct(r["Below_Poverty"], r["Total_Pop"]), axis=1)
    raw[["GEO_ID","NAME","Total_Pop","Below_Poverty","Poverty_Rate"]].to_csv(
        f"{OUT_DIR}/westminster_poverty.csv", index=False)
    print(f"   ✓ {len(raw)} tracts → westminster_poverty.csv")
except Exception as e:
    print(f"   ✗ {e}"); sys.exit(1)

# ── 2. UNINSURED RATE ──────────────────────────────────────────
print("\n2/11  Uninsured rate (B27001)...")
try:
    um = [f"B27001_{str(i).zfill(3)}E" for i in [5,8,11,14,17,20,23,26,29]]
    uf = [f"B27001_{str(i).zfill(3)}E" for i in [33,36,39,42,45,48,51,54,57]]
    raw = get_tracts(["B27001_001E"] + um + uf)
    raw["Total_Pop"]       = raw["B27001_001E"]
    raw["Total_Uninsured"] = raw[um + uf].sum(axis=1)
    raw["Uninsured_Rate"]  = raw.apply(lambda r: pct(r["Total_Uninsured"], r["Total_Pop"]), axis=1)
    raw[["GEO_ID","NAME","Total_Pop","Total_Uninsured","Uninsured_Rate"]].to_csv(
        f"{OUT_DIR}/westminster_insurance.csv", index=False)
    print(f"   ✓ {len(raw)} tracts → westminster_insurance.csv")
except Exception as e:
    print(f"   ✗ {e}"); sys.exit(1)

# ── 3. AGE 65+ ─────────────────────────────────────────────────
print("\n3/11  Age 65+ (B01001)...")
try:
    m65 = [f"B01001_{str(i).zfill(3)}E" for i in range(20,26)]
    f65 = [f"B01001_{str(i).zfill(3)}E" for i in range(44,50)]
    raw = get_tracts(["B01001_001E"] + m65 + f65)
    raw["Total_Pop"]  = raw["B01001_001E"]
    raw["Pop_65plus"] = raw[m65 + f65].sum(axis=1)
    raw["Pct_65plus"] = raw.apply(lambda r: pct(r["Pop_65plus"], r["Total_Pop"]), axis=1)
    raw[["GEO_ID","NAME","Total_Pop","Pop_65plus","Pct_65plus"]].to_csv(
        f"{OUT_DIR}/westminster_age_65plus.csv", index=False)
    print(f"   ✓ {len(raw)} tracts → westminster_age_65plus.csv")
except Exception as e:
    print(f"   ✗ {e}"); sys.exit(1)

# ── 4. LEP ─────────────────────────────────────────────────────
print("\n4/11  Limited English Proficiency (B16004)...")
try:
    lep_vars = [f"B16004_{str(i).zfill(3)}E" for i in
                [4,5,11,12,18,19,25,26,32,33,39,40,46,47,53,54,60,61]]
    raw = get_tracts(["B16004_001E"] + lep_vars)
    raw["Total_Pop_5plus"] = raw["B16004_001E"]
    raw["LEP_Pop"]         = raw[lep_vars].sum(axis=1)
    raw["Pct_LEP"]         = raw.apply(lambda r: pct(r["LEP_Pop"], r["Total_Pop_5plus"]), axis=1)
    raw[["GEO_ID","NAME","Total_Pop_5plus","LEP_Pop","Pct_LEP"]].to_csv(
        f"{OUT_DIR}/westminster_language.csv", index=False)
    print(f"   ✓ {len(raw)} tracts → westminster_language.csv")
except Exception as e:
    print(f"   ✗ {e}"); sys.exit(1)

# ── 5. POPULATION ──────────────────────────────────────────────
print("\n5/11  Total population (B01003)...")
try:
    raw = get_tracts(["B01003_001E"])
    raw["Total_Pop"] = raw["B01003_001E"]
    raw[["GEO_ID","NAME","Total_Pop"]].to_csv(
        f"{OUT_DIR}/westminster_population.csv", index=False)
    print(f"   ✓ {len(raw)} tracts → westminster_population.csv")
except Exception as e:
    print(f"   ✗ {e}"); sys.exit(1)

# ── 6. RACE ────────────────────────────────────────────────────
print("\n6/11  Race and ethnicity (B03002)...")
try:
    raw = get_tracts(["B03002_001E","B03002_003E","B03002_004E","B03002_006E","B03002_012E"])
    raw["Total_Pop"]         = raw["B03002_001E"]
    raw["White_NonHispanic"] = raw["B03002_003E"]
    raw["Black_NonHispanic"] = raw["B03002_004E"]
    raw["Asian_NonHispanic"] = raw["B03002_006E"]
    raw["Hispanic"]          = raw["B03002_012E"]
    raw["Pct_Hispanic"]      = raw.apply(lambda r: pct(r["Hispanic"], r["Total_Pop"]), axis=1)
    raw[["GEO_ID","NAME","Total_Pop","White_NonHispanic","Black_NonHispanic",
         "Asian_NonHispanic","Hispanic","Pct_Hispanic"]].to_csv(
        f"{OUT_DIR}/westminster_race.csv", index=False)
    print(f"   ✓ {len(raw)} tracts → westminster_race.csv")
except Exception as e:
    print(f"   ✗ {e}"); sys.exit(1)

# ── 7. HOUSEHOLD SIZE ──────────────────────────────────────────
print("\n7/11  Household size (B25010)...")
try:
    raw = get_tracts(["B25010_001E"])
    raw["Avg_HH_Size"] = raw["B25010_001E"]
    raw[["GEO_ID","NAME","Avg_HH_Size"]].to_csv(
        f"{OUT_DIR}/westminster_household_size.csv", index=False)
    print(f"   ✓ {len(raw)} tracts → westminster_household_size.csv")
except Exception as e:
    print(f"   ✗ {e}"); sys.exit(1)

# ── 8. HOUSEHOLDS ──────────────────────────────────────────────
print("\n8/11  Number of households (B11001)...")
try:
    raw = get_tracts(["B11001_001E","B11001_002E","B11001_007E"])
    raw["Total_Households"]    = raw["B11001_001E"]
    raw["Family_Households"]   = raw["B11001_002E"]
    raw["Nonfamily_Households"]= raw["B11001_007E"]
    raw[["GEO_ID","NAME","Total_Households","Family_Households","Nonfamily_Households"]].to_csv(
        f"{OUT_DIR}/westminster_household_number.csv", index=False)
    print(f"   ✓ {len(raw)} tracts → westminster_household_number.csv")
except Exception as e:
    print(f"   ✗ {e}"); sys.exit(1)

# ── 9. MEDIAN AGE ──────────────────────────────────────────────
print("\n9/11  Median age (B01002)...")
try:
    raw = get_tracts(["B01002_001E","B01002_002E","B01002_003E"])
    raw["Median_Age"]        = raw["B01002_001E"]
    raw["Median_Age_Male"]   = raw["B01002_002E"]
    raw["Median_Age_Female"] = raw["B01002_003E"]
    raw[["GEO_ID","NAME","Median_Age","Median_Age_Male","Median_Age_Female"]].to_csv(
        f"{OUT_DIR}/westminster_median_age.csv", index=False)
    print(f"   ✓ {len(raw)} tracts → westminster_median_age.csv")
except Exception as e:
    print(f"   ✗ {e}"); sys.exit(1)

# ── 10. MEDIAN INCOME ──────────────────────────────────────────
print("\n10/11  Median household income (B19013)...")
try:
    raw = get_tracts(["B19013_001E"])
    raw["Median_HH_Income"] = raw["B19013_001E"]
    raw[["GEO_ID","NAME","Median_HH_Income"]].to_csv(
        f"{OUT_DIR}/westminster_median_income.csv", index=False)
    print(f"   ✓ {len(raw)} tracts → westminster_median_income.csv")
except Exception as e:
    print(f"   ✗ {e}"); sys.exit(1)

# ── 11. REMAINING TABLES ───────────────────────────────────────
print("\n11/11  Additional vulnerability tables...")

# Median home value (B25077)
try:
    raw = get_tracts(["B25077_001E"])
    raw["Median_Home_Value"] = raw["B25077_001E"]
    raw[["GEO_ID","NAME","Median_Home_Value"]].to_csv(
        f"{OUT_DIR}/westminster_median_home_value.csv", index=False)
    print(f"   ✓ Median home value → westminster_median_home_value.csv")
except Exception as e:
    print(f"   ✗ Home value: {e}")

# Insurance by type (B27010)
try:
    emp_vars = [f"B27010_{str(i).zfill(3)}E" for i in [4,17,28,40]]
    dp_vars  = [f"B27010_{str(i).zfill(3)}E" for i in [5,18,29,41]]
    mc_vars  = [f"B27010_{str(i).zfill(3)}E" for i in [6,19,30,42]]
    md_vars  = [f"B27010_{str(i).zfill(3)}E" for i in [7,20,31,43]]
    tr_vars  = [f"B27010_{str(i).zfill(3)}E" for i in [8,21,32,44]]
    va_vars  = [f"B27010_{str(i).zfill(3)}E" for i in [9,22,33,45]]
    un_vars  = [f"B27010_{str(i).zfill(3)}E" for i in [16,26,37,49]]
    all_ins  = ["B27010_001E"] + emp_vars+dp_vars+mc_vars+md_vars+tr_vars+va_vars+un_vars
    raw = get_tracts(all_ins)
    raw["Total_Pop"]          = raw["B27010_001E"]
    raw["Employer_Insurance"] = raw[emp_vars].sum(axis=1)
    raw["Direct_Purchase"]    = raw[dp_vars].sum(axis=1)
    raw["Medicare"]           = raw[mc_vars].sum(axis=1)
    raw["Medicaid"]           = raw[md_vars].sum(axis=1)
    raw["TRICARE"]            = raw[tr_vars].sum(axis=1)
    raw["VA"]                 = raw[va_vars].sum(axis=1)
    raw["Uninsured"]          = raw[un_vars].sum(axis=1)
    raw[["GEO_ID","NAME","Total_Pop","Employer_Insurance","Direct_Purchase",
         "Medicare","Medicaid","TRICARE","VA","Uninsured"]].to_csv(
        f"{OUT_DIR}/westminster_insurance_type.csv", index=False)
    print(f"   ✓ Insurance by type → westminster_insurance_type.csv")
except Exception as e:
    print(f"   ✗ Insurance type: {e}")

# Public assistance (B19057)
try:
    raw = get_tracts(["B19057_001E","B19057_002E"])
    raw["Total_Households"]    = raw["B19057_001E"]
    raw["Public_Assistance_HH"]= raw["B19057_002E"]
    raw[["GEO_ID","NAME","Total_Households","Public_Assistance_HH"]].to_csv(
        f"{OUT_DIR}/westminster_public_assistance.csv", index=False)
    print(f"   ✓ Public assistance → westminster_public_assistance.csv")
except Exception as e:
    print(f"   ✗ Public assistance: {e}")

# SNAP (B22010)
try:
    raw = get_tracts(["B22010_001E","B22010_002E"])
    raw["Total_Households"] = raw["B22010_001E"]
    raw["SNAP_Households"]  = raw["B22010_002E"]
    raw[["GEO_ID","NAME","Total_Households","SNAP_Households"]].to_csv(
        f"{OUT_DIR}/westminster_SNAP.csv", index=False)
    print(f"   ✓ SNAP → westminster_SNAP.csv")
except Exception as e:
    print(f"   ✗ SNAP: {e}")

# Disability (B18101)
try:
    dis_m = [f"B18101_{str(i).zfill(3)}E" for i in [4,7,10,13,16,19]]
    dis_f = [f"B18101_{str(i).zfill(3)}E" for i in [23,26,29,32,35,38]]
    raw = get_tracts(["B18101_001E"] + dis_m + dis_f)
    raw["Total_Pop"]    = raw["B18101_001E"]
    raw["Pop_Disabled"] = raw[dis_m + dis_f].sum(axis=1)
    raw[["GEO_ID","NAME","Total_Pop","Pop_Disabled"]].to_csv(
        f"{OUT_DIR}/westminster_disabled.csv", index=False)
    print(f"   ✓ Disability → westminster_disabled.csv")
except Exception as e:
    print(f"   ✗ Disability: {e}")

# No vehicle (B08201)
try:
    raw = get_tracts(["B08201_001E","B08201_002E"])
    raw["Total_Households"] = raw["B08201_001E"]
    raw["No_Vehicle_HH"]    = raw["B08201_002E"]
    raw[["GEO_ID","NAME","Total_Households","No_Vehicle_HH"]].to_csv(
        f"{OUT_DIR}/westminster_no_vehicle.csv", index=False)
    print(f"   ✓ No vehicle → westminster_no_vehicle.csv")
except Exception as e:
    print(f"   ✗ No vehicle: {e}")

# No internet (B28002)
try:
    raw = get_tracts(["B28002_001E","B28002_013E"])
    raw["Total_Households"] = raw["B28002_001E"]
    raw["No_Internet_HH"]   = raw["B28002_013E"]
    raw[["GEO_ID","NAME","Total_Households","No_Internet_HH"]].to_csv(
        f"{OUT_DIR}/westminster_no_internet.csv", index=False)
    print(f"   ✓ No internet → westminster_no_internet.csv")
except Exception as e:
    print(f"   ✗ No internet: {e}")

# ── BENCHMARKS ─────────────────────────────────────────────────
print("\n── Pulling Colorado & US benchmarks...")
try:
    benchmarks = {}

    # Helper to get place/state/us value
    def bmark(df, col, denom=None):
        val = pd.to_numeric(df[col].iloc[0], errors='coerce')
        if denom:
            d = pd.to_numeric(df[denom].iloc[0], errors='coerce')
            return pct(val, d)
        return val

    # Westminster city-level
    wm = get_place(["B01003_001E","B17001_001E","B17001_002E",
                    "B19013_001E","B01002_001E","B25077_001E",
                    "B11001_001E","B25010_001E"])
    wm_pop     = bmark(wm, "B01003_001E")
    wm_poverty = pct(bmark(wm,"B17001_002E"), bmark(wm,"B17001_001E"))
    wm_income  = bmark(wm, "B19013_001E")
    wm_age     = bmark(wm, "B01002_001E")
    wm_home    = bmark(wm, "B25077_001E")
    wm_hh      = bmark(wm, "B11001_001E")
    wm_hhsize  = bmark(wm, "B25010_001E")

    # Colorado state
    co = get_state(["B01003_001E","B17001_001E","B17001_002E",
                    "B19013_001E","B01002_001E","B25077_001E",
                    "B11001_001E","B25010_001E"])
    co_poverty = pct(bmark(co,"B17001_002E"), bmark(co,"B17001_001E"))
    co_income  = bmark(co, "B19013_001E")
    co_age     = bmark(co, "B01002_001E")
    co_home    = bmark(co, "B25077_001E")
    co_hhsize  = bmark(co, "B25010_001E")

    # US national
    us = get_us(["B01003_001E","B17001_001E","B17001_002E",
                 "B19013_001E","B01002_001E","B25077_001E",
                 "B11001_001E","B25010_001E"])
    us_poverty = pct(bmark(us,"B17001_002E"), bmark(us,"B17001_001E"))
    us_income  = bmark(us, "B19013_001E")
    us_age     = bmark(us, "B01002_001E")
    us_home    = bmark(us, "B25077_001E")
    us_hhsize  = bmark(us, "B25010_001E")

    benchmarks_df = pd.DataFrame([{
        "Geography":       "Westminster, CO",
        "ACS_Year":        ACS_YEAR,
        "Population":      wm_pop,
        "Total_Households":wm_hh,
        "Avg_HH_Size":     wm_hhsize,
        "Median_Age":      wm_age,
        "Median_HH_Income":wm_income,
        "Median_Home_Value":wm_home,
        "Poverty_Rate":    wm_poverty,
    },{
        "Geography":       "Colorado",
        "ACS_Year":        ACS_YEAR,
        "Avg_HH_Size":     co_hhsize,
        "Median_Age":      co_age,
        "Median_HH_Income":co_income,
        "Median_Home_Value":co_home,
        "Poverty_Rate":    co_poverty,
    },{
        "Geography":       "United States",
        "ACS_Year":        ACS_YEAR,
        "Avg_HH_Size":     us_hhsize,
        "Median_Age":      us_age,
        "Median_HH_Income":us_income,
        "Median_Home_Value":us_home,
        "Poverty_Rate":    us_poverty,
    }])
    benchmarks_df.to_csv(f"{OUT_DIR}/westminster_benchmarks.csv", index=False)
    print(f"   ✓ Benchmarks → westminster_benchmarks.csv")
    print(f"     Poverty: Westminster {wm_poverty}% · CO {co_poverty}% · US {us_poverty}%")
    print(f"     Income:  Westminster ${int(wm_income):,} · CO ${int(co_income):,} · US ${int(us_income):,}")
except Exception as e:
    print(f"   ✗ Benchmarks: {e}")

# ── BLS UNEMPLOYMENT ───────────────────────────────────────────
print("\n── Pulling BLS unemployment rates...")
try:
    bls_headers = {"Content-type": "application/json"}
    if BLS_API_KEY:
        bls_headers["Authorization"] = f"Bearer {BLS_API_KEY}"

    # Westminster LAUS, Colorado, US
    series = ["LAUCT081483500000003","LASST080000000000003","LNS14000000"]
    payload = json.dumps({
        "seriesid": series,
        "startyear": str(ACS_YEAR),
        "endyear":   str(ACS_YEAR),
        "annualaverage": True,
        "registrationkey": BLS_API_KEY
    })
    r = requests.post("https://api.bls.gov/publicAPI/v2/timeseries/data/",
                      data=payload, headers=bls_headers, timeout=30)
    r.raise_for_status()
    bls_data = r.json()

    unemp = {}
    geo_map = {
        "LAUCT081483500000003": "Westminster, CO",
        "LASST080000000000003": "Colorado",
        "LNS14000000":          "United States"
    }
    for series_data in bls_data.get("Results", {}).get("series", []):
        sid = series_data["seriesID"]
        for item in series_data.get("data", []):
            if item.get("period") == "M13":  # Annual average
                unemp[geo_map.get(sid, sid)] = float(item["value"])

    unemp_df = pd.DataFrame([
        {"Geography": k, "Unemployment_Rate": v, "Year": ACS_YEAR}
        for k, v in unemp.items()
    ])
    unemp_df.to_csv(f"{OUT_DIR}/westminster_unemployment.csv", index=False)
    print(f"   ✓ Unemployment → westminster_unemployment.csv")
    for k, v in unemp.items():
        print(f"     {k}: {v}%")
except Exception as e:
    print(f"   ✗ BLS unemployment (will retry next run): {e}")

# ── COUNTY BUSINESS PATTERNS ───────────────────────────────────
print("\n── Pulling business data (County Business Patterns)...")
try:
    cbp_year = ACS_YEAR
    cbp_url  = f"https://api.census.gov/data/{cbp_year}/cbp"
    businesses_total = 0
    employees_total  = 0

    for zipcode in WM_ZIPS:
        try:
            df = census_get(
                ["ESTAB","EMP"],
                f"zipcode:{zipcode}",
                base=cbp_url
            )
            businesses_total += safe_int(df["ESTAB"].sum())
            employees_total  += safe_int(df["EMP"].sum())
        except:
            pass

    biz_df = pd.DataFrame([{
        "Geography":    "Westminster, CO",
        "Year":         cbp_year,
        "Total_Businesses": businesses_total,
        "Total_Employees":  employees_total,
        "Source":       "Census County Business Patterns"
    }])
    biz_df.to_csv(f"{OUT_DIR}/westminster_businesses.csv", index=False)
    print(f"   ✓ Businesses: {businesses_total:,} establishments, {employees_total:,} employees")
    print(f"     → westminster_businesses.csv")
except Exception as e:
    print(f"   ✗ Business data: {e}")

# ── SPATIAL JOIN → DISTRICT DEMOGRAPHICS ──────────────────────
print("\n── Spatial join → district demographics...")
try:
    if not os.path.exists(DISTRICTS_FILE):
        raise FileNotFoundError(f"{DISTRICTS_FILE} not found")

    with open(DISTRICTS_FILE, 'r') as f:
        raw_json = json.load(f)

    transformer_esri = Transformer.from_crs("EPSG:6428", "EPSG:4326", always_xy=True)

    def transform_esri_geom(geom):
        result_rings = []
        for ring_set in [geom.get('rings',[]), geom.get('curveRings',[])]:
            for ring in ring_set:
                coords = []
                for pt in ring:
                    if isinstance(pt, list) and len(pt)==2 and isinstance(pt[0],(int,float)):
                        lon, lat = transformer_esri.transform(pt[0], pt[1])
                        coords.append([lon, lat])
                    elif isinstance(pt, dict):
                        for key in ['c','a','b']:
                            if key in pt and isinstance(pt[key], list):
                                endpoint = pt[key][-1] if isinstance(pt[key][-1], list) else pt[key]
                                if isinstance(endpoint, list) and len(endpoint)==2:
                                    lon, lat = transformer_esri.transform(endpoint[0], endpoint[1])
                                    coords.append([lon, lat])
                                    break
                if coords:
                    result_rings.append(coords)
        return result_rings

    district_rows = []
    for feat in raw_json.get('features', []):
        attrs    = feat.get('attributes', {})
        dist_num = attrs.get('DISTRICT')
        if dist_num not in [1,2,3,4,5,6]:
            continue
        rings = transform_esri_geom(feat['geometry'])
        polys = [Polygon(r) for r in rings if len(r)>=3]
        if not polys:
            continue
        geom = polys[0] if len(polys)==1 else MultiPolygon(polys)
        district_rows.append({'District': dist_num, 'geometry': geom})

    districts_gdf = gpd.GeoDataFrame(district_rows, crs='EPSG:4326')

    req = urllib.request.Request(
        "https://raw.githubusercontent.com/uscensusbureau/citysdk/master/v2/GeoJSON/500k/2020/08/tract.json",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        co_tracts = json.load(r)

    tracts_gdf = gpd.GeoDataFrame.from_features(co_tracts["features"], crs="EPSG:4326")
    tracts_gdf["GEO_ID"] = (tracts_gdf["STATEFP"]+tracts_gdf["COUNTYFP"]+tracts_gdf["TRACTCE"]).astype(str)
    tracts_gdf = tracts_gdf[tracts_gdf["COUNTYFP"].isin(["001","059"])]

    tracts_proj    = tracts_gdf.to_crs("EPSG:26913")
    districts_proj = districts_gdf.to_crs("EPSG:26913")
    tracts_proj["centroid"] = tracts_proj.geometry.centroid
    tracts_c = tracts_proj.set_geometry("centroid")

    joined = gpd.sjoin(tracts_c, districts_proj[["District","geometry"]],
                       how="left", predicate="within")
    joined = joined[["GEO_ID","District"]].dropna(subset=["District"]).copy()
    joined["District"] = joined["District"].astype(int)
    joined["GEO_ID"]   = joined["GEO_ID"].astype(str)

    def load_fix(path, cols):
        df = pd.read_csv(path)
        df["GEO_ID"] = df["GEO_ID"].astype(str).str.zfill(11)
        return df[["GEO_ID"] + [c for c in cols if c in df.columns]]

    tracts = joined.copy()
    for path, cols in [
        (f"{OUT_DIR}/westminster_poverty.csv",         ["Total_Pop","Below_Poverty"]),
        (f"{OUT_DIR}/westminster_insurance.csv",        ["Total_Uninsured"]),
        (f"{OUT_DIR}/westminster_age_65plus.csv",       ["Pop_65plus"]),
        (f"{OUT_DIR}/westminster_language.csv",         ["Total_Pop_5plus","LEP_Pop"]),
        (f"{OUT_DIR}/westminster_race.csv",             ["White_NonHispanic","Black_NonHispanic","Asian_NonHispanic","Hispanic"]),
        (f"{OUT_DIR}/westminster_household_size.csv",   ["Avg_HH_Size"]),
        (f"{OUT_DIR}/westminster_household_number.csv", ["Total_Households","Family_Households"]),
        (f"{OUT_DIR}/westminster_median_age.csv",       ["Median_Age"]),
        (f"{OUT_DIR}/westminster_median_income.csv",    ["Median_HH_Income"]),
        (f"{OUT_DIR}/westminster_median_home_value.csv",["Median_Home_Value"]),
        (f"{OUT_DIR}/westminster_insurance_type.csv",   ["Employer_Insurance","Direct_Purchase","Medicare","Medicaid","TRICARE","VA","Uninsured"]),
        (f"{OUT_DIR}/westminster_public_assistance.csv",["Public_Assistance_HH"]),
        (f"{OUT_DIR}/westminster_SNAP.csv",             ["SNAP_Households"]),
        (f"{OUT_DIR}/westminster_disabled.csv",         ["Pop_Disabled"]),
        (f"{OUT_DIR}/westminster_no_vehicle.csv",       ["No_Vehicle_HH"]),
        (f"{OUT_DIR}/westminster_no_internet.csv",      ["No_Internet_HH"]),
    ]:
        if os.path.exists(path):
            tracts = tracts.merge(load_fix(path, cols), on="GEO_ID", how="left")

    def district_summary(district_num, group):
        t   = safe_int(group["Total_Pop"].sum())
        hh  = safe_int(group["Total_Households"].sum()) if "Total_Households" in group else 0
        bp  = safe_int(group["Below_Poverty"].sum())
        ui  = safe_int(group["Total_Uninsured"].sum())
        s65 = safe_int(group["Pop_65plus"].sum())
        t5  = safe_int(group["Total_Pop_5plus"].sum())
        lep = safe_int(group["LEP_Pop"].sum())
        wh  = safe_int(group["White_NonHispanic"].sum())
        bl  = safe_int(group["Black_NonHispanic"].sum())
        asi = safe_int(group["Asian_NonHispanic"].sum())
        hi  = safe_int(group["Hispanic"].sum())
        fam = safe_int(group["Family_Households"].sum()) if "Family_Households" in group else 0
        emp = safe_int(group["Employer_Insurance"].sum()) if "Employer_Insurance" in group else 0
        dp  = safe_int(group["Direct_Purchase"].sum()) if "Direct_Purchase" in group else 0
        mc  = safe_int(group["Medicare"].sum()) if "Medicare" in group else 0
        md  = safe_int(group["Medicaid"].sum()) if "Medicaid" in group else 0
        tri = safe_int(group["TRICARE"].sum()) if "TRICARE" in group else 0
        va  = safe_int(group["VA"].sum()) if "VA" in group else 0
        un  = safe_int(group["Uninsured"].sum()) if "Uninsured" in group else 0
        pa  = safe_int(group["Public_Assistance_HH"].sum()) if "Public_Assistance_HH" in group else 0
        sn  = safe_int(group["SNAP_Households"].sum()) if "SNAP_Households" in group else 0
        dis = safe_int(group["Pop_Disabled"].sum()) if "Pop_Disabled" in group else 0
        nv  = safe_int(group["No_Vehicle_HH"].sum()) if "No_Vehicle_HH" in group else 0
        ni  = safe_int(group["No_Internet_HH"].sum()) if "No_Internet_HH" in group else 0
        ins_t = emp+dp+mc+md+tri+va+un

        pop_w = group["Total_Pop"].fillna(0).tolist()
        hh_w  = group["Total_Households"].fillna(0).tolist() if "Total_Households" in group else pop_w

        return pd.Series({
            "Station":              f"Station {district_num}",
            "Total_Pop":            t,
            "Total_Households":     hh,
            "Family_Households":    fam,
            "Pct_Family_HH":        pct(fam, hh),
            "Avg_HH_Size":          weighted_mean(group["Avg_HH_Size"].tolist(), hh_w) if "Avg_HH_Size" in group else None,
            "Median_Age":           weighted_median(group["Median_Age"].tolist(), pop_w) if "Median_Age" in group else None,
            "Median_HH_Income":     weighted_median(group["Median_HH_Income"].tolist(), hh_w) if "Median_HH_Income" in group else None,
            "Median_Home_Value":    weighted_median(group["Median_Home_Value"].tolist(), hh_w) if "Median_Home_Value" in group else None,
            "Below_Poverty":        bp, "Poverty_Rate":     pct(bp, t),
            "Total_Uninsured":      ui, "Uninsured_Rate":   pct(ui, t),
            "Pop_65plus":           s65,"Pct_65plus":        pct(s65, t),
            "Total_Pop_5plus":      t5, "LEP_Pop":           lep, "Pct_LEP": pct(lep, t5),
            "White_NonHispanic":    wh, "Pct_White_NonHisp": pct(wh, t),
            "Black_NonHispanic":    bl, "Pct_Black":          pct(bl, t),
            "Asian_NonHispanic":    asi,"Pct_Asian":          pct(asi, t),
            "Hispanic":             hi, "Pct_Hispanic":       pct(hi, t),
            "Employer_Insurance":   emp,"Pct_Employer":       pct(emp, ins_t),
            "Direct_Purchase":      dp, "Pct_Direct":         pct(dp, ins_t),
            "Medicare":             mc, "Pct_Medicare":       pct(mc, ins_t),
            "Medicaid":             md, "Pct_Medicaid":       pct(md, ins_t),
            "TRICARE":              tri,"Pct_TRICARE":        pct(tri, ins_t),
            "VA":                   va, "Pct_VA":             pct(va, ins_t),
            "Uninsured":            un, "Pct_Uninsured_Ins":  pct(un, ins_t),
            "Public_Assistance_HH": pa, "Pct_Public_Assistance": pct(pa, hh),
            "SNAP_Households":      sn, "Pct_SNAP":           pct(sn, hh),
            "Pop_Disabled":         dis,"Pct_Disabled":        pct(dis, t),
            "No_Vehicle_HH":        nv, "Pct_No_Vehicle":     pct(nv, hh),
            "No_Internet_HH":       ni, "Pct_No_Internet":    pct(ni, hh),
            "Tract_Count":          len(group)
        })

    summary = tracts.groupby("District").apply(
        lambda g: district_summary(g.name, g)).reset_index()
    summary = summary.sort_values("District")
    summary.to_csv(f"{OUT_DIR}/westminster_demographics_by_district.csv", index=False)

    print(f"   ✓ {len(summary)} districts → westminster_demographics_by_district.csv")
    for _, row in summary.iterrows():
        print(f"   District {int(row.District)} | Pop {int(row.Total_Pop):,} | "
              f"Poverty {row.Poverty_Rate}% | Income ${int(row.Median_HH_Income or 0):,} | "
              f"SNAP {row.Pct_SNAP}% | No Vehicle {row.Pct_No_Vehicle}%")

except Exception as e:
    print(f"   ✗ Spatial join failed: {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print(f"✓ All data updated — ACS {ACS_YEAR} 5-Year Estimates")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
print(f"  Repo: https://github.com/smaddux303/wfd-cra")
print("=" * 60)
