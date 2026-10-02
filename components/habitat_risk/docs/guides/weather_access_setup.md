# One-time weather source access

Official ERA5-Land access returned HTTP 401 without authentication. No standard CDS config or CDSAPI_KEY was present at inspection. Terrain work does not require this account.

1. Sign in or register at https://cds.climate.copernicus.eu/.
2. Follow https://cds.climate.copernicus.eu/how-to-api to store your personal access token in `~/.cdsapirc` locally. Never put the token into chat, a notebook, or the project repository.
3. Open https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means?tab=download and accept the dataset's terms in your account. This is required by the provider.
4. From the project directory run `.venv/bin/python scripts/download_era5_weather.py`, or tell the assistant that local setup is complete.

The prepared request covers 2010–2023, every month, monthly-averaged reanalysis, 2m temperature and total precipitation, and a bounding box around Sri Lanka. It requests NetCDF. Provider-generated request syntax and returned metadata must be checked on first authenticated use; the live download has not yet been tested.

The selected monthly precipitation is a mean daily accumulation. Monthly total = value × 1000 × days in month. Temperature annual means are weighted by days in month. These rules apply to this particular monthly product, not all precipitation datasets. Documentation: https://confluence.ecmwf.int/spaces/CKB/pages/140385202/ERA5-Land+data+documentation .
