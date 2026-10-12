"""Area-weight monthly ERA5-Land on grid polygons; fail closed on unknown units/product."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
from shapely.geometry import box
from scipy.sparse import csr_matrix
ROOT=Path(__file__).resolve().parents[1]

def annual_fields(ds):
    name='valid_time' if 'valid_time' in ds.coords else 'time'
    ds=ds.rename({name:'time'}) if name!='time' else ds
    ds=ds.sortby('time')
    dates=pd.DatetimeIndex(ds.time.values)
    assert dates.to_period('M').is_unique,'Duplicate months'
    assert set(ds.t2m.dims)=={'time','latitude','longitude'} and set(ds.tp.dims)=={'time','latitude','longitude'}
    assert ds.t2m.attrs.get('units')=='K','Expected Kelvin'
    assert ds.tp.attrs.get('units') in ['m','m of water equivalent per day','m/day'],'Unexpected precipitation units'
    for year in range(2010,2024):
        sub=ds.sel(time=ds.time.dt.year==year)
        assert set(sub.time.dt.month.values)==set(range(1,13)),f'Missing month {year}'
        days=sub.time.dt.days_in_month
        temperature=((sub.t2m-273.15)*days).sum('time',skipna=False)/days.sum()
        # The request/manifest must be monthly_averaged_reanalysis (moda), not hourly or monthly-by-hour.
        precipitation=(sub.tp*1000*days).sum('time',skipna=False)
        yield year,temperature.transpose('latitude','longitude').values,precipitation.transpose('latitude','longitude').values

def main():
    manifest_path=ROOT/'data/metadata/weather_download_manifest.json'
    if not manifest_path.exists():raise SystemExit('Verified weather download manifest missing; run download_era5_weather.py after CDS setup.')
    manifest=json.loads(manifest_path.read_text());path=ROOT/manifest['path']
    assert manifest['dataset']=='reanalysis-era5-land-monthly-means'
    assert manifest['request']['product_type']==['monthly_averaged_reanalysis']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest['sha256']
    cfg=json.loads((ROOT/'configs/study.json').read_text());grid_id=f"lka_laea_{cfg['grid_size_m']}m"
    grid=gpd.read_file(ROOT/f'data/interim/spatial/{grid_id}_grid.geojson').to_crs(cfg['projected_crs'])
    with xr.open_dataset(path) as source:
        ds=source.load()
    # Only documented singleton auxiliary coordinates may be squeezed; multi-version files require review.
    for dim in ['expver','number']:
        if dim in ds.dims:
            assert ds.sizes[dim]==1,f'Multiple {dim} values require explicit handling'
            ds=ds.squeeze(dim,drop=True)
    ds=ds.sortby('latitude').sortby('longitude')
    lat=ds.latitude.values;lon=ds.longitude.values
    assert np.allclose(np.diff(lat),.1) and np.allclose(np.diff(lon),.1),'Unexpected source grid spacing'
    shapes=[box(x-.05,y-.05,x+.05,y+.05) for y in lat for x in lon]
    native=gpd.GeoDataFrame({'native_index':range(len(shapes))},geometry=shapes,crs=4326).to_crs(grid.crs)
    ri=[];ci=[];weights=[]
    for i,geom in enumerate(grid.geometry):
        for j in native.sindex.query(geom,predicate='intersects'):
            area=geom.intersection(native.geometry.iloc[j]).area
            if area>0:ri.append(i);ci.append(j);weights.append(area)
    matrix=csr_matrix((weights,(ri,ci)),shape=(len(grid),len(native)))
    polygon_area=grid.geometry.area.to_numpy()
    assert np.allclose(np.asarray(matrix.sum(axis=1)).ravel(),polygon_area,rtol=1e-5,atol=1),'Weather extent misses country polygons'
    rows=[]
    for year,temp,rain in annual_fields(ds):
        values={}
        for name,array in [('annual_mean_temperature_c',temp),('annual_precipitation_mm',rain)]:
            v=array.ravel();valid=np.isfinite(v)
            if name=='annual_precipitation_mm':assert (v[valid]>=0).all(),'Negative precipitation: inspect source'
            covered=np.asarray(matrix@valid.astype(float)).ravel()
            fraction=covered/polygon_area
            totals=np.asarray(matrix@np.where(valid,v,0)).ravel()
            mean=np.divide(totals,covered,out=np.full(len(grid),np.nan),where=covered>0)
            mean[fraction<.95]=np.nan
            values[name]=mean;values[name+'_coverage']=fraction
        rows.append(pd.DataFrame({'cell_id':grid.cell_id,'reference_year':year,**values}))
    out=pd.concat(rows,ignore_index=True)
    out['weather_status']=np.where(out[['annual_mean_temperature_c','annual_precipitation_mm']].notna().all(axis=1),'coverage_pass','insufficient_source_coverage')
    assert not out.duplicated(['cell_id','reference_year']).any()
    out.to_csv(ROOT/f'data/interim/spatial/{grid_id}_weather_features.csv',index=False)
    pd.DataFrame({'cell_index':ri,'native_index':ci,'intersection_area_m2':weights}).to_csv(ROOT/'data/interim/spatial/weather_native_cell_weights.csv',index=False)
    report={'source':'ERA5-Land monthly averaged reanalysis','rows':len(out),'status_counts':out.weather_status.value_counts().to_dict(),'temperature':'Day-weighted annual mean, K minus 273.15','precipitation':'moda mean daily m times days in month times 1000, then annual sum','spatial_method':'Area-weighted source-cell overlap; >=95% finite full-year source coverage required','native_resolution':'0.1 degree distributed grid; no independent 5km weather detail','source_sha256':manifest['sha256'],'live_source_processed':True}
    (ROOT/'reports/audits/weather_features.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return report
if __name__=='__main__':main()
