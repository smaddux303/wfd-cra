# CRA Update Guide
## How to keep the WFD CRA current between accreditation cycles

---

## What updates automatically (you do nothing)

Every October 15th, GitHub Actions runs the Census data script automatically.
It pulls fresh ACS 5-Year data, recalculates all rates, commits updated CSVs,
and your Datawrapper maps refresh on their own.

You will see a new commit in your repo from "Census Data Bot" confirming it ran.
If it fails for any reason, GitHub sends you an email notification.

You can also trigger it manually any time:
1. Go to github.com/smaddux303/wfd-cra
2. Click **Actions** tab
3. Click **Update Census Data** in the left sidebar
4. Click **Run workflow** → **Run workflow**

---

## What needs manual updating and when

### Every year

**Power BI reports**
- Open WFD CRA Power BI file
- Home → Refresh
- Republish to Power BI Service
- Verify embeds are showing current data in the live site

**Hospitals and medical facilities**
- Open `data/clean/westminster_hospitals.csv`
- Verify facility list is current — check for closures or new openings
- Edit on GitHub using the pencil icon → commit

**EMBED_CODES.md**
- If any Datawrapper or Power BI URL changed, update `docs/EMBED_CODES.md`
- Note the change in the Update Log at the bottom of that file

---

### Each accreditation cycle (every 5 years)

**Stations and apparatus**
1. Open `data/clean/westminster_stations.csv` on GitHub → pencil icon
2. Update for any new stations, address changes, or apparatus reassignments
3. Commit message: `Update stations — [cycle year]`

4. Open `data/clean/westminster_apparatus.csv` on GitHub → pencil icon
5. Update for fleet changes — new apparatus, retired units, status changes
6. Commit message: `Update apparatus fleet — [cycle year]`

**District risk ratings**
1. Open `data/clean/westminster_district_risk.csv` on GitHub → pencil icon
2. Review EMS, Fire, Rescue, HazMat risk levels for each district
3. Update based on current CRA/SOC working draft findings
4. Commit message: `Update district risk ratings — [cycle year]`

**Population growth**
1. Open `data/clean/westminster_population_growth.csv` on GitHub → pencil icon
2. Add the most recent ACS estimate row
3. Commit message: `Update population growth data — [year]`

**Narrative text in index.html**
1. Go to github.com/smaddux303/wfd-cra
2. Click index.html → pencil icon
3. Use Ctrl+F to find the section to update
4. Make edits
5. Commit message: `Update [section name] narrative — [cycle year]`

---

## How to update a Datawrapper map

Datawrapper maps that use the GitHub raw URL as their data source
update automatically when the CSV changes. You only need to
manually touch Datawrapper if you want to change the map's
visual design, title, color scale, or tooltips.

If you do republish a Datawrapper chart:
1. The embed URL stays the same — no changes needed in index.html
2. Just update the version number in the src URL if Datawrapper
   increments it (e.g. /1/ becomes /2/)
3. Note the change in docs/EMBED_CODES.md

---

## Annual update checklist

- [ ] GitHub Actions ran successfully in October (check Actions tab)
- [ ] Census data CSVs updated (check commit history)
- [ ] Datawrapper maps verified — hover a tract, confirm current data
- [ ] Power BI reports refreshed and republished
- [ ] Power BI embeds verified in live site
- [ ] westminster_hospitals.csv reviewed and updated if needed
- [ ] EMBED_CODES.md Update Log entry added
- [ ] README.md "Last Updated" date updated

## Accreditation cycle checklist (every 5 years)

- [ ] Annual checklist completed
- [ ] westminster_stations.csv updated
- [ ] westminster_apparatus.csv updated
- [ ] westminster_district_risk.csv updated
- [ ] westminster_population_growth.csv updated
- [ ] index.html narrative sections reviewed and updated
- [ ] New CRA/SOC working draft findings reflected in risk ratings
- [ ] Fire Chief endorsement quote updated if needed
- [ ] KPI cards in hero section verified (personnel count, stations, etc.)
- [ ] All embed heights verified — no scroll bars inside iframes
- [ ] Site tested on mobile
- [ ] Link to full PDF/Word CRA document updated in footer

---

## Getting help

If the GitHub Actions workflow fails:
- Click the **Actions** tab in your repo
- Click the failed run to see the error log
- Most common issue: Census API changed a variable name
  (fix: update the column reference in scripts/update_census_data.py)

If a Datawrapper map goes blank:
- Check that the raw GitHub CSV URL is still valid
- Open the URL in a browser — if it loads, Datawrapper should work
- In Datawrapper, go to the chart → Edit → Data → refresh the link

If the GitHub Pages site goes down:
- Go to repo Settings → Pages → verify it still shows main branch / root
- Check the Actions tab for any failed deployment
