"""Read-only audit of supplied weather; no provider or unit assumptions."""
from pathlib import Path
import calendar,hashlib,json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/raw/weather/legacy/SriLanka_Weather_Dataset.csv'
def main():
    d=pd.read_csv(SOURCE);d['date']=pd.to_datetime(d.time,errors='coerce');d['year']=d.date.dt.year
    variables=['temperature_2m_mean','precipitation_sum','windspeed_10m_max']
    rows=[]
    for (city,year),g in d.dropna(subset=['date']).groupby(['city','year']):
        year=int(year);expected=366 if calendar.isleap(year) else 365
        r={'city':city,'year':year,'rows':len(g),'unique_days':g.date.dt.normalize().nunique(),'expected_days':expected,'duplicate_days':int(g.date.dt.normalize().duplicated().sum())}
        for v in variables:r[v+'_valid_days']=g.loc[pd.to_numeric(g[v],errors='coerce').notna(),'date'].dt.normalize().nunique()
        r['complete_candidate_year']=r['unique_days']==expected and r['duplicate_days']==0 and all(r[v+'_valid_days']==expected for v in variables)
        rows.append(r)
    out=pd.DataFrame(rows);out.to_csv(ROOT/'reports/tables/weather_source_year_coverage.csv',index=False)
    report={'source_path':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'rows':len(d),'cities':d.city.nunique(),'invalid_dates':int(d.date.isna().sum()),'date_min':str(d.date.min().date()),'date_max':str(d.date.max().date()),'complete_city_years':int(out.complete_candidate_year.sum()),'incomplete_city_years':int((~out.complete_candidate_year).sum()),'ready_to_join':False,'remaining':['Verify provider, product, units and time zone','Replace city-based nearest-location estimates with justified grid weather extraction','Obtain full reference-year 2023 if retaining target year 2024','Obtain independent terrain raster; weather-source elevation is unsuitable as local terrain']}
    (ROOT/'reports/audits/weather_source_coverage.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return report
if __name__=='__main__':main()
