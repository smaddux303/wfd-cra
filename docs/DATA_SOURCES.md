# Data Sources

All data used in the Westminster Fire Department CRA is documented here.
Every file in `/data/clean/` has a corresponding entry below.

---

## Census Data (ACS 5-Year Estimates, 2019–2023)

All Census data is pulled automatically via the Census API each October
using the GitHub Actions workflow in `.github/workflows/update_census_data.yml`.

### Poverty Rate — `westminster_poverty.csv`
- **Table:** B17001 — Poverty Status in the Past 12 Months by Sex by Age
- **Derived column:** Poverty_Rate = (B17001_002E / B17001_001E) × 100
- **Geography:** Census tracts — Adams County (08001) + Jefferson County (08059)
- **URL:** https://data.census.gov/table/ACSDT5Y2023.B17001

### Health Insurance — `westminster_insurance.csv`
- **Table:** B27001 — Health Insurance Coverage Status by Sex by Age
- **Derived column:** Uninsured_Rate = (total uninsured / total pop) × 100
- **Geography:** Westminster city (place code 83835)
- **URL:** https://data.census.gov/table/ACSDT5Y2023.B27001

### Population Age 65+ — `westminster_age_65plus.csv`
- **Table:** B01001 — Sex by Age
- **Derived column:** Pct_65plus = (pop 65+ / total pop) × 100
- **Geography:** Westminster city (place code 83835)
- **URL:** https://data.census.gov/table/ACSDT5Y2023.B01001

### Population Density — `westminster_population_density.csv`
- **Table:** B01003 — Total Population
- **Geography:** Census tracts — Adams County + Jefferson County
- **URL:** https://data.census.gov/table/ACSDT5Y2023.B01003

### Language Other Than English — `westminster_language.csv`
- **Table:** B16004 — Age by Language Spoken at Home
- **Derived column:** Pct_Non_English = (non-English speakers / total pop) × 100
- **Geography:** Census tracts — Adams County + Jefferson County
- **URL:** https://data.census.gov/table/ACSDT5Y2023.B16004

### Race and Ethnicity — `westminster_race.csv`
- **Table:** B03002 — Hispanic or Latino Origin by Race
- **Derived columns:** Pct_Hispanic, Pct_White_NonHispanic, Pct_Black, Pct_Asian
- **Geography:** Census tracts — Adams County + Jefferson County
- **URL:** https://data.census.gov/table/ACSDT5Y2023.B03002

---

## Population Growth — `westminster_population_growth.csv`
- **Source:** U.S. Census Decennial Census
- **Years:** 1990, 2000, 2010, 2020 + ACS 2023 estimate
- **Note:** Static file — updated manually each decennial census cycle
- **URL:** https://data.census.gov

---

## Infrastructure Data

### Hospitals and Medical Facilities — `westminster_hospitals.csv`
- **Source:** Colorado CDPHE + OpenStreetMap
- **Contents:** Facility name, address, latitude, longitude, type
- **Note:** Hand-maintained — verify annually

### Transportation — pulled automatically via GitHub Actions
- **Railroad lines:** U.S. Census TIGER/Line shapefiles (converted to GeoJSON)
- **Primary roads:** U.S. Census TIGER/Line shapefiles (converted to GeoJSON)
- **Source:** https://www2.census.gov/geo/tiger/

---

## Internal WFD Data

### Stations — `westminster_stations.csv`
- **Source:** Westminster Fire Department, Administrative Records
- **Contents:** Station number, address, lat/long, district, apparatus assigned
- **Note:** Update manually when station locations or apparatus changes

### Apparatus — `westminster_apparatus.csv`
- **Source:** Westminster Fire Department, Fleet Records
- **Contents:** Unit name, type, year, front-line vs reserve, station, min staffing
- **Note:** Update manually each accreditation cycle

### District Risk — `westminster_district_risk.csv`
- **Source:** Westminster Fire Department CRA/SOC Working Draft
- **Contents:** Risk level by discipline (EMS, Fire, Rescue, HazMat) per district
- **Note:** Update manually each accreditation cycle

---

## Automatic Update Schedule

| Dataset | Update trigger | Method |
|---------|---------------|--------|
| Poverty rate | October 15 annually | GitHub Actions → Census API |
| Uninsured rate | October 15 annually | GitHub Actions → Census API |
| Age 65+ | October 15 annually | GitHub Actions → Census API |
| Population density | October 15 annually | GitHub Actions → Census API |
| Language other than English | October 15 annually | GitHub Actions → Census API |
| Race/ethnicity | October 15 annually | GitHub Actions → Census API |
| Railroad/road GeoJSON | October 15 annually | GitHub Actions → TIGER/Line |
| Population growth | Manual — every 10 years | Hand-entered |
| Hospitals | Manual — annually | Hand-entered |
| Stations/apparatus | Manual — each cycle | Hand-entered |
| District risk ratings | Manual — each cycle | Hand-entered |
