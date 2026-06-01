Westminster Fire Department — Community Risk Assessment
### Interactive CRA · 2024–2028 Accreditation Cycle

This repository hosts the data, code, and documentation for the Westminster Fire Department's interactive Community Risk Assessment, built for the 2024–2028 CFAI accreditation cycle.

The CRA is published as a GitHub Pages website at:
**[https://smaddux303.github.io/wfd-cra](https://smaddux303.github.io/wfd-cra)**

---

## Repository Structure
wfd-cra/
├── index.html                        ← Main CRA webpage
├── assets/css/style.css              ← Westminster brand styles
├── data/
│   ├── raw/                          ← Original Census downloads
│   └── clean/                        ← Datawrapper-ready CSVs
├── maps/                             ← GeoJSON boundary files
├── scripts/
│   └── update_census_data.py         ← Automated data updater
├── docs/
│   ├── DATA_SOURCES.md
│   ├── UPDATE_GUIDE.md
│   └── EMBED_CODES.md
└── .github/workflows/
└── update_census_data.yml        ← GitHub Actions automation

## Data Sources

| File | Source | Table | Last Updated |
|------|--------|-------|-------------|
| westminster_poverty.csv | U.S. Census ACS 5-Year | B17001 | 2023 |
| westminster_insurance.csv | U.S. Census ACS 5-Year | B27001 | 2023 |
| westminster_age_65plus.csv | U.S. Census ACS 5-Year | B01001 | 2023 |
| westminster_population_density.csv | U.S. Census ACS 5-Year | B01003 | 2023 |
| westminster_stations.csv | Westminster Fire Dept. | Internal | 2024 |
| westminster_apparatus.csv | Westminster Fire Dept. | Internal | 2024 |


