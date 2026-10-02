"""Download monthly means; credentials stay in the standard local CDS configuration."""
from pathlib import Path
import os,json,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[1]
def main():
    if not (Path.home()/'.cdsapirc').exists() and not os.environ.get('CDSAPI_KEY'):
        raise SystemExit('CDS access not configured. Follow docs/guides/weather_access_setup.md; never paste the token into chat.')
    import cdsapi
    client=cdsapi.Client()
    folder=ROOT/'data/raw/weather/era5_land_monthly';folder.mkdir(parents=True,exist_ok=True)
    request={'product_type':['monthly_averaged_reanalysis'],'variable':['2m_temperature','total_precipitation'],'year':[str(y) for y in range(2010,2024)],'month':[f'{m:02}' for m in range(1,13)],'time':['00:00'],'area':[10.2,79.2,5.6,82.2],'data_format':'netcdf','download_format':'unarchived'}
    (ROOT/'data/metadata/era5_weather_request.json').write_text(json.dumps(request,indent=2)+'\n')
    path=folder/'era5_land_monthly_2010_2023.nc'
    if not path.exists():
        temp=path.with_suffix('.nc.part');client.retrieve('reanalysis-era5-land-monthly-means',request,str(temp));temp.replace(path)
    if zipfile.is_zipfile(path):
        raise SystemExit('Provider returned ZIP despite NetCDF request. Inspect archive and record per-variable files before processing; no automatic format assumption.')
    import xarray as xr
    with xr.open_dataset(path) as ds:assert {'t2m','tp'}.issubset(ds.data_vars),f'Unexpected variables: {list(ds.data_vars)}'
    manifest={'dataset':'reanalysis-era5-land-monthly-means','request':request,'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_url':'https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means','status':'downloaded_and_variables_checked'}
    (ROOT/'data/metadata/weather_download_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Weather file downloaded and variable names checked.')
if __name__=='__main__':main()
