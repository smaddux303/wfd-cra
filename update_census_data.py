"""
WFD CRA — Automated Census Data Updater
========================================
Pulls fresh ACS 5-Year data from the Census API and writes
cleaned CSVs to data/clean/. Runs via GitHub Actions each October.

Tables pulled:
  B17001 — Poverty status (tract level)
  B27001 — Health insurance coverage (city level)
  B01001 — Age by sex (city level)
  B01003 — Total population (tract level)
  B16004 — Language spoken at home (tract level)
  B03002 — Race and ethnicity (tract level)

Infrastructure:
  Census TIGER/Line — Railroad lines (GeoJSON)
  Census TIGER/Line — Primary roads (GeoJSON)

Geography:
  Westminster, CO (place code 83835)
  Census tracts in Adams County (08001) + Jefferson County (08059)

GitHub repo: https://github.com/smaddux303/wfd-cra
"""

import requests
import pandas as pd
import json
from datetime import datetime
import os
import sys

# ── Configuration ─────────────────────────────────────────────
CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "")
ACS_YEAR       = datetime.now().year - 2   # ACS 5-year lags ~2 years
BASE_URL       = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"
STATE          = "08"       # Colorado
ADAMS_CO       = "001"      # Adams County FIPS
JEFFERSON_CO   = "059"      # Jefferson County FIPS
PLACE          = "83835"    # Westminster city place code
OUT_DIR        = "data/clean"

print(f"WFD CRA — Census Data Updater")
print(f"ACS Year: {ACS_YEAR} 5-Year Estimates")
print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 55)

def census_get(get_vars, for_clause, in_clause=None):
    """Hit the Census API and return a DataFrame."""
    params = {
        "get": ",".join(["NAME"] + get_vars),
        "for": for_clause,
    }
    if in_clause:
        params["in"] = in_clause
    if CENSUS_API_KEY:
        params["key"] = CENSUS_API_KEY

    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data[1:], columns=data[0])
    for col in df.columns:
        if col not in ("NAME", "state", "county", "tract", "place"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def build_geo_id(county, tract):
    """Build full GEO_ID from state, county, and tract components."""
    return f"1400000US{STATE}{county}{str(tract).zfill(6)}"

def get_tracts(get_vars):
    """Pull tract-level data for both Adams and Jefferson counties."""
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
    combined["GEO_ID"] = combined.apply(
        lambda r: build_geo_id(r["county_fips"], r["tract"]), axis=1
    )
    combined["Tract_Name"] = combined["NAME"]
    return combined

# ── 1. POVERTY RATE — tract level ─────────────────────────────
print("\n1/6  Poverty rate (B17001) by tract...")
try:
    poverty_raw = get_tracts(["B17001_001E", "B17001_002E"])
    poverty_raw["Total_Pop"]     = poverty_raw["B17001_001E"]
    poverty_raw["Below_Poverty"] = poverty_raw["B17001_002E"]
    poverty_raw["Poverty_Rate"]  = (
        poverty_raw["Below_Poverty"] / poverty_raw["Total_Pop"] * 100
    ).round(1)
    poverty_out = poverty_raw[
        ["GEO_ID", "Tract_Name", "Total_Pop", "Below_Poverty", "Poverty_Rate"]
    ].copy()
    poverty_out.to_csv(f"{OUT_DIR}/westminster_poverty.csv", index=False)
    print(f"   ✓ {len(poverty_out)} tracts → westminster_poverty.csv")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# ── 2. UNINSURED RATE — city level ────────────────────────────
print("\n2/6  Health insurance (B27001) citywide...")
try:
    uninsured_male_cols   = [f"B27001_{str(i).zfill(3)}E" for i in [5,8,11,14,17,20,23,26,29]]
    uninsured_female_cols = [f"B27001_{str(i).zfill(3)}E" for i in [33,36,39,42,45,48,51,54,57]]
    all_ins_cols = ["B27001_001E"] + uninsured_male_cols + uninsured_female_cols

    ins = census_get(
        get_vars=all_ins_cols,
        for_clause=f"place:{PLACE}",
        in_clause=f"state:{STATE}"
    )
    total_pop       = ins["B27001_001E"].iloc[0]
    total_uninsured = (
        ins[uninsured_male_cols].iloc[0].sum() +
        ins[uninsured_female_cols].iloc[0].sum()
    )
    uninsured_rate = round(total_uninsured / total_pop * 100, 1)

    ins_out = pd.DataFrame([{
        "Geography":        "Westminster, CO",
        "GEO_ID":          "16000US0883835",
        "Total_Pop":       int(total_pop),
        "Total_Uninsured": int(total_uninsured),
        "Uninsured_Rate":  uninsured_rate,
        "ACS_Year":        ACS_YEAR
    }])
    ins_out.to_csv(f"{OUT_DIR}/westminster_insurance.csv", index=False)
    print(f"   ✓ Uninsured rate: {uninsured_rate}% → westminster_insurance.csv")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# ── 3. AGE 65+ AND UNDER 18 — city level ──────────────────────
print("\n3/6  Age demographics (B01001) citywide...")
try:
    male_65plus    = [f"B01001_{str(i).zfill(3)}E" for i in range(20, 26)]
    female_65plus  = [f"B01001_{str(i).zfill(3)}E" for i in range(44, 50)]
    male_under18   = [f"B01001_{str(i).zfill(3)}E" for i in range(3, 7)]
    female_under18 = [f"B01001_{str(i).zfill(3)}E" for i in range(27, 31)]
    all_age_cols   = (["B01001_001E"] + male_65plus + female_65plus +
                      male_under18 + female_under18)

    age = census_get(
        get_vars=all_age_cols,
        for_clause=f"place:{PLACE}",
        in_clause=f"state:{STATE}"
    )
    total_pop_age = age["B01001_001E"].iloc[0]
    pop_65plus    = age[male_65plus + female_65plus].iloc[0].sum()
    pop_under18   = age[male_under18 + female_under18].iloc[0].sum()

    age_out = pd.DataFrame([{
        "Geography":   "Westminster, CO",
        "GEO_ID":     "16000US0883835",
        "Total_Pop":  int(total_pop_age),
        "Pop_65plus": int(pop_65plus),
        "Pct_65plus": round(pop_65plus / total_pop_age * 100, 1),
        "Pop_Under18": int(pop_under18),
        "Pct_Under18": round(pop_under18 / total_pop_age * 100, 1),
        "ACS_Year":   ACS_YEAR
    }])
    age_out.to_csv(f"{OUT_DIR}/westminster_age_65plus.csv", index=False)
    print(f"   ✓ 65+: {age_out.Pct_65plus.iloc[0]}% · Under 18: {age_out.Pct_Under18.iloc[0]}% → westminster_age_65plus.csv")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# ── 4. POPULATION DENSITY — tract level ───────────────────────
print("\n4/6  Population density (B01003) by tract...")
try:
    pop_raw = get_tracts(["B01003_001E"])
    pop_raw["Total_Pop"] = pop_raw["B01003_001E"]
    pop_out = pop_raw[["GEO_ID", "Tract_Name", "Total_Pop"]].copy()
    pop_out.to_csv(f"{OUT_DIR}/westminster_population_density.csv", index=False)
    print(f"   ✓ {len(pop_out)} tracts → westminster_population_density.csv")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# ── 5. LANGUAGE OTHER THAN ENGLISH — tract level ──────────────
print("\n5/6  Language spoken at home (B16004) by tract...")
try:
    # B16004_001E = total pop 5+
    # B16004_003E = speak only English
    # Non-English = total - English only
    lang_raw = get_tracts(["B16004_001E", "B16004_003E"])
    lang_raw["Total_Pop_5plus"]  = lang_raw["B16004_001E"]
    lang_raw["English_Only"]     = lang_raw["B16004_003E"]
    lang_raw["Non_English"]      = (
        lang_raw["Total_Pop_5plus"] - lang_raw["English_Only"]
    )
    lang_raw["Pct_Non_English"]  = (
        lang_raw["Non_English"] / lang_raw["Total_Pop_5plus"] * 100
    ).round(1)
    lang_out = lang_raw[[
        "GEO_ID", "Tract_Name", "Total_Pop_5plus",
        "English_Only", "Non_English", "Pct_Non_English"
    ]].copy()
    lang_out.to_csv(f"{OUT_DIR}/westminster_language.csv", index=False)
    print(f"   ✓ {len(lang_out)} tracts → westminster_language.csv")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# ── 6. RACE AND ETHNICITY — tract level ───────────────────────
print("\n6/6  Race and ethnicity (B03002) by tract...")
try:
    # B03002_001E = total
    # B03002_003E = White alone non-Hispanic
    # B03002_004E = Black alone non-Hispanic
    # B03002_006E = Asian alone non-Hispanic
    # B03002_012E = Hispanic or Latino (any race)
    race_raw = get_tracts([
        "B03002_001E", "B03002_003E",
        "B03002_004E", "B03002_006E", "B03002_012E"
    ])
    race_raw["Total_Pop"]          = race_raw["B03002_001E"]
    race_raw["White_NonHispanic"]  = race_raw["B03002_003E"]
    race_raw["Black"]              = race_raw["B03002_004E"]
    race_raw["Asian"]              = race_raw["B03002_006E"]
    race_raw["Hispanic"]           = race_raw["B03002_012E"]
    race_raw["Pct_White_NonHisp"]  = (race_raw["White_NonHispanic"] / race_raw["Total_Pop"] * 100).round(1)
    race_raw["Pct_Black"]          = (race_raw["Black"]    / race_raw["Total_Pop"] * 100).round(1)
    race_raw["Pct_Asian"]          = (race_raw["Asian"]    / race_raw["Total_Pop"] * 100).round(1)
    race_raw["Pct_Hispanic"]       = (race_raw["Hispanic"] / race_raw["Total_Pop"] * 100).round(1)

    race_out = race_raw[[
        "GEO_ID", "Tract_Name", "Total_Pop",
        "White_NonHispanic", "Pct_White_NonHisp",
        "Black", "Pct_Black",
        "Asian", "Pct_Asian",
        "Hispanic", "Pct_Hispanic"
    ]].copy()
    race_out.to_csv(f"{OUT_DIR}/westminster_race.csv", index=False)
    print(f"   ✓ {len(race_out)} tracts → westminster_race.csv")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# ── Summary ───────────────────────────────────────────────────
print()
print("=" * 55)
print(f"✓ All Census data updated successfully")
print(f"  ACS {ACS_YEAR} 5-Year Estimates")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
print(f"  Datawrapper maps will refresh automatically")
print(f"  GitHub Pages site: https://smaddux303.github.io/wfd-cra")
print("=" * 55)
