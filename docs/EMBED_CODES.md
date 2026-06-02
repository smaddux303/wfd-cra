markdown# Embed Codes & URLs

Update this file whenever a Datawrapper chart or Power BI report
is republished. This is your master reference for all embedded content.

---

## GitHub Repository

- **Repo:** https://github.com/smaddux303/wfd-cra
- **Live site:** https://smaddux303.github.io/wfd-cra

---

## GitHub Raw Data URLs
*Paste these into Datawrapper under "Link external dataset"*
https://raw.githubusercontent.com/smaddux303/wfd-cra/main/data/clean/westminster_poverty.csv
https://raw.githubusercontent.com/smaddux303/wfd-cra/main/data/clean/westminster_insurance.csv
https://raw.githubusercontent.com/smaddux303/wfd-cra/main/data/clean/westminster_age_65plus.csv
https://raw.githubusercontent.com/smaddux303/wfd-cra/main/data/clean/westminster_population_density.csv
https://raw.githubusercontent.com/smaddux303/wfd-cra/main/data/clean/westminster_language.csv
https://raw.githubusercontent.com/smaddux303/wfd-cra/main/data/clean/westminster_race.csv
https://raw.githubusercontent.com/smaddux303/wfd-cra/main/data/clean/westminster_stations.csv
https://raw.githubusercontent.com/smaddux303/wfd-cra/main/data/clean/westminster_hospitals.csv
https://raw.githubusercontent.com/smaddux303/wfd-cra/main/data/clean/westminster_district_risk.csv
https://raw.githubusercontent.com/smaddux303/wfd-cra/main/data/clean/westminster_population_growth.csv

---

## Datawrapper Maps
*Update the URL column after publishing each map*

| Map | Datawrapper URL | Section | Embed height |
|-----|----------------|---------|-------------|
| Poverty rate choropleth |https://datawrapper.dwcdn.net/vJliz/1/ | Demographics | 600px |
| Uninsured rate choropleth | https://datawrapper.dwcdn.net/Q9OYv/1/| Demographics | 600px |
| Population 65+ choropleth | https://datawrapper.dwcdn.net/3k2ot/1/ | Demographics | 600px |
| Limited English Proficiency | https://datawrapper.dwcdn.net/UXK5S/1/ | Demographics | 600px |
| Population density choropleth | https://datawrapper.dwcdn.net/PCeH5/1/ | Community | 600px |
| Hispanic choropleth | https://datawrapper.dwcdn.net/aRmWT/1/) | Demographics | 600px |
| Station locations map | https://datawrapper.dwcdn.net/XXXXX/1/ | Community | 480px |
| Medical facilities map | https://datawrapper.dwcdn.net/XXXXX/1/ | Community | 480px |
| Transportation map | https://datawrapper.dwcdn.net/XXXXX/1/ | Community | 480px |
| Population growth chart | https://datawrapper.dwcdn.net/h2myN/1/ | Community | 380px |

---

## Power BI Reports
*Update after publishing each report page to Power BI Service*

| Report | Embed URL | Section | Embed height |
|--------|-----------|---------|-------------|
| At-a-glance KPIs | https://app.powerbigov.us/view?r=XXXXX | Opening | 220px |
| Vulnerability dashboard | https://app.powerbigov.us/view?r=XXXXX | Demographics | 560px |
| Risk score matrix | https://app.powerbigov.us/view?r=XXXXX | Risk assessment | 500px |
| District profiles | https://app.powerbigov.us/view?r=XXXXX | Districts | 520px |
| Incident volume & workload | https://app.powerbigov.us/view?r=XXXXX | Districts | 500px |

---

## How to swap a placeholder for a real embed in index.html

1. Go to github.com/smaddux303/wfd-cra
2. Click index.html → pencil icon to edit
3. Use Ctrl+F to find the placeholder comment for that section
4. Delete the placeholder div
5. Paste the iframe code below (fill in your URL and height):

### Datawrapper iframe:
```html
<iframe
  title="[Descriptive map title]"
  aria-label="Map"
  src="https://datawrapper.dwcdn.net/XXXXX/1/"
  width="100%"
  height="500"
  frameborder="0"
  scrolling="no"
  style="border:none; width:100%; min-width:100%!important;">
</iframe>
```

### Power BI iframe:
```html
<iframe
  title="[Descriptive report title]"
  src="https://app.powerbigov.us/view?r=XXXXX"
  width="100%"
  height="560"
  frameborder="0"
  allowfullscreen="true">
</iframe>
```

---

## Update Log

| Date | What changed | Who |
|------|-------------|-----|
| 2025 | Initial setup | WFD |
