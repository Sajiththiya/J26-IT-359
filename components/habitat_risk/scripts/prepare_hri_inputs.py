"""Visible, resumable preparation of HRI inputs; no HRI scores or model fitting.

Run from the repository root:
  python3 components/habitat_risk/scripts/prepare_hri_inputs.py --stage download
  python3 components/habitat_risk/scripts/prepare_hri_inputs.py --stage forest
  python3 components/habitat_risk/scripts/prepare_hri_inputs.py --stage population
  python3 components/habitat_risk/scripts/prepare_hri_inputs.py --stage master
Each numbered section is mirrored in 05_hri_input_preparation.ipynb.
"""

# %% 1. Imports and explicit research choices
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime, timezone
import argparse
import hashlib
import json
import subprocess
import time

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from shapely import box
from rasterio.features import geometry_mask, geometry_window
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.transform import from_origin
from rasterio.windows import Window
from scipy import ndimage
from scipy.spatial import cKDTree

ROOT = next(p for base in [Path.cwd(), *Path.cwd().parents]
            for p in [base, base / 'components/habitat_risk']
            if (p / 'configs/study.json').exists())
CFG = json.loads((ROOT / 'configs/study.json').read_text())
GRID = ROOT / 'data/interim/spatial/lka_laea_5000m_grid.geojson'
OUT = ROOT / 'data/processed/hri/pre_hri_v1'
RAW = ROOT / 'data/raw/human_pressure/worldpop_global1_1km'
YEARS = list(range(2010, 2024))
POP_YEARS = list(range(2010, 2021))
THRESHOLD = 30  # >=30%; analyst working choice, not supervisor approval
MIN_COVERAGE = 0.95
PIXEL_M = 30
HALO_M = 1000
KEY = ['cell_id', 'reference_year']
WORLDPOP = 'https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, default=str) + '\n')


def load_grid():
    g = gpd.read_file(GRID).to_crs(CFG['projected_crs'])
    assert g.cell_id.is_unique and g.geometry.is_valid.all()
    return g


# %% 2. Download official annual population rasters with checksums
def download_population():
    """Country-level UN-adjusted official 1km counts, same product each year.

    Downloads use temporary .part files and fail visibly on network errors.
    Provider historical estimates are retrospective, not real-time records.
    """
    RAW.mkdir(parents=True, exist_ok=True)
    entries = []
    for year in POP_YEARS:
        filename = f'lka_ppp_{year}_1km_Aggregated_UNadj.tif'
        url = f'{WORLDPOP}/{year}/LKA/{filename}'
        target = RAW / filename
        if not target.exists():
            partial = target.with_suffix('.tif.part')
            print(f'Downloading {year}: {url}', flush=True)
            subprocess.run(['curl', '--fail', '--location', '--retry', '2',
                            '--connect-timeout', '30', '--max-time', '300',
                            '--silent', '--show-error', '--output', str(partial), url], check=True)
            with rasterio.open(partial) as ds:
                assert ds.count == 1 and ds.crs is not None
                assert ds.bounds.left < 82 and ds.bounds.right > 79
            partial.rename(target)
        with rasterio.open(target) as ds:
            info = {'crs': str(ds.crs), 'shape': ds.shape, 'nodata': ds.nodata,
                    'resolution_degrees': ds.res}
        entries.append({'year': year, 'url': url, 'path': str(target.relative_to(ROOT)),
                        'bytes': target.stat().st_size, 'sha256': digest(target), **info})
        print(f'Population {year} verified: {target.stat().st_size / 1e6:.1f} MB', flush=True)
        save_json(RAW / 'download_manifest.json', {
            'product': 'WorldPop Global1 2000–2020, unconstrained UN-adjusted official 1km aggregation',
            'source': 'https://hub.worldpop.org/Global1_2000-2020',
            'licence': 'CC BY 4.0; attribute WorldPop / University of Southampton',
            'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
            'units': 'estimated persons per native pixel', 'files': entries,
            'limitation': 'Modelled census disaggregation, not directly observed pressure. '
                          'No comparable Global1 rasters after 2020; no interpolation or backfill.'})


# %% 3. Read only raster windows intersecting each projected grid cell
def read_forest_context(geometry, sources, crs, pixel_m=PIXEL_M, halo_m=HALO_M):
    x0, y0, x1, y1 = geometry.buffer(halo_m).bounds
    x0, y1 = np.floor(x0 / pixel_m) * pixel_m, np.ceil(y1 / pixel_m) * pixel_m
    width, height = int(np.ceil((x1 - x0) / pixel_m)), int(np.ceil((y1 - y0) / pixel_m))
    affine = from_origin(x0, y1, pixel_m, pixel_m)
    bounds = (x0, y1 - height * pixel_m, x0 + width * pixel_m, y1)
    data = {band: np.full((height, width), 255, np.uint8)
            for band in ['treecover2000', 'lossyear', 'datamask']}
    for tile in sources:
        for band, src in tile.items():
            left, bottom, right, top = transform_bounds(crs, src.crs, *bounds, densify_pts=21)
            window = rasterio.windows.from_bounds(left, bottom, right, top, src.transform)
            # Expand outward to avoid losing boundary pixels through rounding.
            c0, r0 = np.floor(window.col_off) - 2, np.floor(window.row_off) - 2
            c1, r1 = np.ceil(window.col_off + window.width) + 2, np.ceil(window.row_off + window.height) + 2
            c0, r0, c1, r1 = max(0, c0), max(0, r0), min(src.width, c1), min(src.height, r1)
            if c1 <= c0 or r1 <= r0:
                continue
            window = Window(c0, r0, c1 - c0, r1 - r0)
            temp = np.full((height, width), 255, np.uint8)
            reproject(src.read(1, window=window), temp,
                      src_transform=src.window_transform(window), src_crs=src.crs,
                      dst_transform=affine, dst_crs=crs, dst_nodata=255,
                      resampling=Resampling.nearest)
            valid = temp != 255
            data[band][valid] = temp[valid]
    inside = geometry_mask([geometry], out_shape=(height, width), transform=affine, invert=True)
    return data, inside


# %% 4. Calculate explicit, local fragmentation metrics
def fragment_metrics(data, inside, year, threshold=THRESHOLD, pixel_m=PIXEL_M):
    observed = np.isin(data['datamask'], [1, 2])
    observed &= (data['treecover2000'] <= 100) & (data['lossyear'] <= 24)
    land = observed & (data['datamask'] == 1)
    forest = land & (data['treecover2000'] >= threshold)
    forest &= (data['lossyear'] == 0) | (data['lossyear'] > year - 2000)
    n_inside, n_land = int(inside.sum()), int((inside & land).sum())
    coverage = float((inside & observed).sum() / n_inside) if n_inside else np.nan
    names = ['cell_patch_count', 'mean_cell_patch_ha', 'largest_cell_patch_land_fraction',
             'largest_cell_patch_forest_fraction', 'edge_m_per_land_ha', 'mean_nearest_patch_centroid_m']
    out = dict.fromkeys(names, np.nan)
    out.update(mapped_observation_coverage=coverage, mapped_land_pixels=n_land,
               forest_pixels=int((inside & forest).sum()), no_forest=False,
               fragmentation_status='insufficient_coverage')
    if not n_land or not np.isfinite(coverage) or coverage < MIN_COVERAGE:
        return out
    labels, count = ndimage.label(forest, structure=ndimage.generate_binary_structure(2, 1))
    ids, sizes = np.unique(labels[inside & forest], return_counts=True)
    edges = 0
    for axis in [0, 1]:
        a = (slice(None, -1), slice(None)) if axis == 0 else (slice(None), slice(None, -1))
        b = (slice(1, None), slice(None)) if axis == 0 else (slice(None), slice(1, None))
        edges += int(((forest[a] != forest[b]) & land[a] & land[b] & inside[a] & inside[b]).sum())
    nearest = np.nan
    if len(ids) and count > 1:
        centres = np.asarray(ndimage.center_of_mass(forest, labels, np.arange(1, count + 1)))
        # k=2 excludes the queried patch itself; avoids a dense pairwise matrix.
        distances, _ = cKDTree(centres).query(centres[ids - 1], k=2)
        nearest = float(distances[:, 1].mean() * pixel_m)
    out.update(cell_patch_count=len(ids),
               mean_cell_patch_ha=float(sizes.mean() * pixel_m**2 / 10000) if len(ids) else np.nan,
               largest_cell_patch_land_fraction=float(sizes.max() / n_land) if len(ids) else 0.,
               largest_cell_patch_forest_fraction=float(sizes.max() / sizes.sum()) if len(ids) else np.nan,
               edge_m_per_land_ha=edges * pixel_m / (n_land * pixel_m**2 / 10000),
               mean_nearest_patch_centroid_m=nearest, no_forest=not len(ids),
               fragmentation_status='no_forest' if not len(ids) else 'coverage_pass')
    return out


# %% 5. National forest release and fragmentation with deterministic scale checks
def prepare_forest():
    OUT.mkdir(parents=True, exist_ok=True)
    grid = load_grid()
    forest = pd.read_csv(ROOT / 'data/processed/hri/wp5_v1/forest_threshold_scenarios.csv')
    primary = forest.loc[forest.canopy_threshold_percent.eq(THRESHOLD)].copy()
    assert len(primary) == len(grid) * len(YEARS) and not primary.duplicated(KEY).any()
    primary.to_csv(OUT / 'forest_cell_year.csv', index=False)
    rank = forest.pivot(index=KEY, columns='canopy_threshold_percent',
                        values='remaining_baseline_forest_proportion')
    rank.corr(method='spearman').to_csv(OUT / 'forest_threshold_rank_sensitivity.csv')
    forest.groupby(['canopy_threshold_percent', 'reference_year']).agg(
        annual_loss_ha=('annual_loss_ha', 'sum'),
        valid_cells=('annual_loss_ha', 'count'),
        mean_remaining_proportion=('remaining_baseline_forest_proportion', 'mean')).to_csv(
            OUT / 'forest_threshold_summary.csv')
    cache = OUT / 'fragmentation_checkpoints'
    cache.mkdir(exist_ok=True)
    # Six cells from each baseline-forest quintile; fixed seed and stored identities.
    candidates = primary.loc[primary.reference_year.eq(2020) & primary.baseline_forest_ha.gt(0)].copy()
    candidates['stratum'] = pd.qcut(candidates.baseline_forest_ha.rank(method='first'), 5, labels=False)
    sample = candidates.groupby('stratum', group_keys=False).sample(n=6, random_state=42)
    sample[['cell_id', 'stratum']].to_csv(OUT / 'fragmentation_sensitivity_sample.csv', index=False)
    sample_ids = set(sample.cell_id)
    results, sensitivity = [], []
    source_paths = []
    with ExitStack() as stack:
        sources = []
        for tile in ['10N_070E', '10N_080E']:
            paths = {b: ROOT / f'data/raw/forest/Hansen_GFC-2024-v1.12_{b}_{tile}.tif'
                     for b in ['treecover2000', 'lossyear', 'datamask']}
            source_paths.extend(paths.values())
            sources.append({b: stack.enter_context(rasterio.open(p)) for b, p in paths.items()})
        cache_signature = hashlib.sha256((digest(Path(__file__)) if '__file__' in globals() else
                                         'notebook-visible-code-v1').encode()).hexdigest()
        for i, cell in enumerate(grid.itertuples(), 1):
            checkpoint = cache / f'{cell.cell_id}.json'
            previous = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
            if previous.get('signature') == cache_signature:
                rows, extra = previous['rows'], previous['sensitivity']
            else:
                data, inside = read_forest_context(cell.geometry, sources, grid.crs)
                rows = [{'cell_id': cell.cell_id, 'reference_year': year,
                         'canopy_threshold_percent': THRESHOLD,
                         **fragment_metrics(data, inside, year)} for year in YEARS]
                extra = []
                if cell.cell_id in sample_ids:
                    for px, halo in [(30, 1000), (60, 1000), (30, 2000)]:
                        d, mask = (data, inside) if (px, halo) == (30, 1000) else read_forest_context(
                            cell.geometry, sources, grid.crs, px, halo)
                        for t in [10, 30, 50]:
                            extra.append({'cell_id': cell.cell_id, 'reference_year': 2020,
                                          'pixel_m': px, 'halo_m': halo, 'canopy_threshold_percent': t,
                                          **fragment_metrics(d, mask, 2020, t, px)})
                    # Alter future losses; year-t fragmentation must be identical.
                    altered = {k: v.copy() for k, v in data.items()}
                    altered['lossyear'][(altered['lossyear'] > 20) & (altered['lossyear'] <= 24)] = 0
                    pd.testing.assert_series_equal(pd.Series(fragment_metrics(data, inside, 2020)),
                                                   pd.Series(fragment_metrics(altered, inside, 2020)))
                save_json(checkpoint, {'signature': cache_signature, 'rows': rows, 'sensitivity': extra})
            results.extend(rows)
            sensitivity.extend(extra)
            if i % 100 == 0 or i == len(grid):
                print(f'National fragmentation: {i}/{len(grid)} cells', flush=True)
    frag = pd.DataFrame(results)
    assert len(frag) == len(primary) and not frag.duplicated(KEY).any()
    frag.to_csv(OUT / 'fragmentation_cell_year.csv', index=False)
    pd.DataFrame(sensitivity).to_csv(OUT / 'fragmentation_scale_sensitivity.csv', index=False)
    frag.select_dtypes('number').drop(columns=['reference_year', 'canopy_threshold_percent']).corr(
        method='spearman').to_csv(OUT / 'fragmentation_metric_correlations.csv')
    save_json(OUT / 'forest_fragmentation_audit.json', {
        'national_cells': len(grid), 'rows': len(frag), 'primary_threshold': THRESHOLD,
        'threshold_operator': '>=', 'threshold_status': 'analyst working choice; supervisor review pending',
        'reference': 'https://gfr.wri.org/annual-tree-cover-loss-data-explained',
        'rationale': '30% is a widely used reporting benchmark; not a Sri Lankan forest definition. '
                     '10%/50% national forest and sampled fragmentation sensitivity retained.',
        'pixel_m': PIXEL_M, 'halo_m': HALO_M, 'connectivity': '4-neighbour',
        'coverage': 'observed land AND persistent water / grid pixel centres; metrics use mapped land only',
        'status_counts': frag.fragmentation_status.value_counts().to_dict(),
        'future_loss_perturbation_tests': len(sample_ids),
        'scale_test': '30 stratified cells, 2020; 30m/60m; 1km/2km halo; thresholds 10/30/50',
        'limitations': ['30m resampling; no forest gains; includes plantations',
                       'Local patches with cell-clipped areas; patches can connect outside the halo',
                       'Centroid distance is NOT edge-to-edge connectivity or dispersal',
                       'Forest-free cells have zero edge density; zero is not evidence of low habitat risk'],
        'input_sha256': {str(p.relative_to(ROOT)): digest(p) for p in [GRID, *source_paths,
            ROOT / 'data/processed/hri/wp5_v1/forest_threshold_scenarios.csv']}})


# %% 6. Aggregate population counts without interpolating people
def prepare_population():
    OUT.mkdir(parents=True, exist_ok=True)
    grid = load_grid()
    grid = grid.reset_index(drop=True)
    grid['grid_code'] = np.arange(len(grid))
    areas = grid.geometry.area.to_numpy()
    # Exact intersection in the equal-area CRS. Uniform population within each
    # 1km pixel is an explicit boundary-allocation assumption, tested for 2010.
    with rasterio.open(RAW / 'lka_ppp_2010_1km_Aggregated_UNadj.tif') as ds:
        template_shape, template_transform, template_crs = ds.shape, ds.transform, ds.crs
        rr, cc = np.indices(ds.shape)
        left = ds.transform.c + cc.ravel() * ds.transform.a
        top = ds.transform.f + rr.ravel() * ds.transform.e
        polygons = box(left, top + ds.transform.e, left + ds.transform.a, top)
        pixels = gpd.GeoDataFrame({'pixel_index': np.arange(ds.height * ds.width)},
                                 geometry=polygons, crs=ds.crs).to_crs(grid.crs)
        pixels['pixel_area'] = pixels.geometry.area
    intersections = gpd.overlay(pixels, grid[['grid_code', 'geometry']], how='intersection', keep_geom_type=True)
    intersections['intersection_area'] = intersections.geometry.area
    intersections['population_fraction'] = intersections.intersection_area / intersections.pixel_area
    assert intersections.population_fraction.between(0, 1 + 1e-8).all()
    pix = intersections.pixel_index.to_numpy(dtype=int)
    cell_codes = intersections.grid_code.to_numpy(dtype=int)
    overlap_area = intersections.intersection_area.to_numpy()
    fractions = intersections.population_fraction.to_numpy()
    footprint = np.bincount(cell_codes, weights=overlap_area, minlength=len(grid)) / areas
    assert (footprint <= 1 + 1e-5).all()  # missing raster extent remains missing coverage
    intersections.drop(columns='geometry').to_csv(OUT / 'population_pixel_cell_weights.csv', index=False)
    records = []
    for year in POP_YEARS:
        path = RAW / f'lka_ppp_{year}_1km_Aggregated_UNadj.tif'
        with rasterio.open(path) as ds:
            assert (ds.shape, ds.transform, ds.crs) == (template_shape, template_transform, template_crs)
            values = ds.read(1, masked=True).ravel()
            valid = ~np.ma.getmaskarray(values)[pix] & np.isfinite(values.data[pix]) & (values.data[pix] >= 0)
            counts = np.bincount(cell_codes[valid], weights=values.data[pix[valid]] * fractions[valid], minlength=len(grid))
            coverage = np.bincount(cell_codes[valid], weights=overlap_area[valid], minlength=len(grid)) / areas
            coverage = np.clip(coverage, 0, 1)
            for i, cell in enumerate(grid.itertuples()):
                ok = coverage[i] >= MIN_COVERAGE
                records.append({'cell_id': cell.cell_id, 'reference_year': year,
                                'population_count': counts[i] if ok else np.nan,
                                'population_density_per_km2': counts[i] / (areas[i] / 1e6) if ok else np.nan,
                                'population_coverage': coverage[i], 'population_source_year': year,
                                'population_status': 'coverage_pass' if ok else 'insufficient_coverage'})
        print(f'Population zonal aggregation: {year}', flush=True)
    scaffold = pd.MultiIndex.from_product([grid.cell_id, YEARS], names=KEY).to_frame(index=False)
    population = scaffold.merge(pd.DataFrame(records), on=KEY, how='left', validate='one_to_one')
    population['population_status'] = population.population_status.fillna('source_year_unavailable')
    # No carry-forward: a 2020 estimate is never relabelled as a 2023 estimate.
    assert population.loc[population.reference_year.gt(2020), 'population_density_per_km2'].isna().all()
    population.to_csv(OUT / 'human_pressure_cell_year.csv', index=False)
    resolution_check = population_resolution_check(grid, population)
    save_json(OUT / 'population_audit.json', {
        'rows': len(population), 'duplicate_keys': int(population.duplicated(KEY).sum()),
        'source_years': POP_YEARS, 'unavailable_years': [2021, 2022, 2023],
        'aggregation': 'area-fraction allocation of official 1km pixel counts in equal-area CRS; divide by clipped cell km2',
        'coverage_rule': MIN_COVERAGE, 'nodata': 'missing, never zero population',
        'status_counts': population.population_status.value_counts().to_dict(),
        'temporal_interpretation': 'retrospective modelled exposure; real-time availability unverified',
        'resolution_check_2010': resolution_check,
        'limitations': 'Coastal masks differ; uniform-within-1km boundary allocation; modelled census allocation; '
                       'pressure proxy, not observed habitat degradation; no Global1 data after 2020',
        'input_manifest_sha256': digest(RAW / 'download_manifest.json')})


def population_resolution_check(grid, population):
    fine = ROOT / 'data/raw/human_pressure/worldpop_global1/lka_ppp_2010_UNadj.tif'
    if not fine.exists():
        return {'status': '100m reference raster not available'}
    rows = []
    with rasterio.open(fine) as ds:
        for cell in grid.to_crs(ds.crs).itertuples():
            window = geometry_window(ds, [cell.geometry], boundless=True)
            values = ds.read(1, window=window, boundless=True, masked=True)
            inside = geometry_mask([cell.geometry], out_shape=values.shape,
                                   transform=ds.window_transform(window), invert=True)
            valid = inside & ~np.ma.getmaskarray(values) & np.isfinite(values.data) & (values.data >= 0)
            coverage = valid.sum() / inside.sum() if inside.any() else 0
            rows.append({'cell_id': cell.cell_id, 'count_100m': float(values.data[valid].sum(dtype=np.float64))
                         if coverage >= MIN_COVERAGE else np.nan})
    compare = population.loc[population.reference_year.eq(2010), ['cell_id', 'population_count']].merge(
        pd.DataFrame(rows), on='cell_id', validate='one_to_one')
    compare['relative_difference'] = (compare.population_count - compare.count_100m) / compare.count_100m.replace(0, np.nan)
    compare.to_csv(OUT / 'population_resolution_sensitivity_2010.csv', index=False)
    paired = compare.dropna(subset=['population_count', 'count_100m'])
    return {'paired_cells': len(paired), 'spearman': paired[['population_count', 'count_100m']].corr(method='spearman').iloc[0, 1],
            'median_absolute_relative_difference': compare.relative_difference.abs().median(),
            'reference_sha256': digest(fine),
            'note': '1km area fractions versus 100m pixel-centre sums; both resolution and boundary allocation differ'}


# %% 7. Build a new version of the master with transparent admission flags
def build_master():
    OUT.mkdir(parents=True, exist_ok=True)
    old = ROOT / 'data/processed/hri/wp6_v1/master_cell_year_dataset.csv'
    master = pd.read_csv(old)
    assert len(master) == 40166 and not master.duplicated(KEY).any()
    source_paths = [old, GRID, ROOT / 'scripts/prepare_hri_inputs.py',
                    RAW / 'download_manifest.json', OUT / 'forest_fragmentation_audit.json',
                    OUT / 'population_audit.json']
    for prefix, name in [('forest', 'forest_cell_year'), ('fragmentation', 'fragmentation_cell_year'),
                         ('pressure', 'human_pressure_cell_year')]:
        path = OUT / f'{name}.csv'
        frame = pd.read_csv(path)
        assert len(frame) == len(master) and not frame.duplicated(KEY).any()
        assert set(map(tuple, frame[KEY].to_numpy())) == set(map(tuple, master[KEY].to_numpy()))
        frame = frame.rename(columns={c: prefix + '__' + c for c in frame if c not in KEY})
        master = master.merge(frame, on=KEY, how='left', validate='one_to_one')
        source_paths.append(path)
    master['forest_core_data_available'] = master[
        ['forest__remaining_baseline_forest_proportion', 'forest__previous_3yr_loss_fraction_of_baseline',
         'fragmentation__edge_m_per_land_ha']].notna().all(axis=1)
    master['pressure_extension_data_available'] = master.forest_core_data_available & master[
        'pressure__population_density_per_km2'].notna()
    # Availability is not ecological validity, a score, or approval to train.
    master.to_csv(OUT / 'master_cell_year_raw.csv', index=False)
    issues = []
    for col in master.select_dtypes(include='number'):
        s = master[col]
        bad = s.notna() & ~np.isfinite(s)
        if ('fraction' in col or 'proportion' in col or col.endswith('_coverage')) and '__qa_' not in col:
            bad |= s.notna() & ~s.between(-1e-8, 1 + 1e-8)
        if col.startswith(('forest__', 'fragmentation__', 'pressure__')):
            bad |= s.notna() & s.lt(0)
        if bad.any():
            issues.append({'feature': col, 'invalid_values': int(bad.sum())})
    assert not issues, issues
    assert master.reference_year.between(2010, 2023).all()
    assert (master.pressure__population_source_year.dropna() <=
            master.loc[master.pressure__population_source_year.notna(), 'reference_year']).all()
    master.to_csv(OUT / 'master_cell_year_dataset.csv', index=False)
    missing = master.isna().sum().rename('missing_rows').to_frame()
    missing['total_rows'] = len(master)
    missing['missing_fraction'] = missing.missing_rows / len(master)
    missing.rename_axis('feature').to_csv(OUT / 'master_missing_data_report.csv')
    master.groupby('reference_year').agg(
        total_cells=('cell_id', 'size'),
        forest_core_available_cells=('forest_core_data_available', 'sum'),
        pressure_extension_available_cells=('pressure_extension_data_available', 'sum')).to_csv(
            OUT / 'coverage_by_year.csv')
    forest_features = ['forest__remaining_baseline_forest_proportion',
                       'forest__previous_3yr_loss_fraction_of_baseline',
                       'forest__cumulative_prior_loss_fraction_of_baseline']
    candidates = forest_features + ['fragmentation__edge_m_per_land_ha',
                  'fragmentation__largest_cell_patch_land_fraction',
                  'fragmentation__largest_cell_patch_forest_fraction',
                  'pressure__population_density_per_km2']
    data = master[candidates]
    corr = data.corr(method='spearman')
    corr.to_csv(OUT / 'candidate_spearman.csv')
    data.notna().astype(int).T.dot(data.notna().astype(int)).to_csv(OUT / 'correlation_sample_counts.csv')
    redundancy = [{'feature_a': a, 'feature_b': b, 'spearman_r': float(corr.loc[a, b])}
                  for i, a in enumerate(candidates) for b in candidates[i + 1:]
                  if pd.notna(corr.loc[a, b]) and abs(corr.loc[a, b]) >= .8]
    pd.DataFrame(redundancy, columns=['feature_a', 'feature_b', 'spearman_r']).to_csv(
        OUT / 'redundant_metric_review.csv', index=False)
    # VIF is descriptive, complete-case, includes an intercept, never selects using test outcomes.
    complete = data.dropna()
    if len(complete) > 10000:
        complete = complete.sample(10000, random_state=42)
    varying = complete.loc[:, complete.std().gt(0)]
    z = (varying - varying.mean()) / varying.std()
    vif = []
    for c in z:
        y = z[c].to_numpy()
        x = np.column_stack([np.ones(len(z)), z.drop(columns=c).to_numpy()])
        residual = y - x @ np.linalg.lstsq(x, y, rcond=None)[0]
        unexplained = float(residual @ residual / (y @ y))
        vif.append({'feature': c, 'vif': 1 / unexplained if unexplained > 1e-12 else np.inf,
                    'sample_rows': len(z)})
    pd.DataFrame(vif).to_csv(OUT / 'candidate_vif.csv', index=False)
    plot_features(data, corr)
    create_dictionary(master, candidates)
    summarize_scale_sensitivity()
    report = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'prepared_inputs_with_explicit_scope_and_coverage_limits',
              'rows': len(master), 'unique_cells': master.cell_id.nunique(), 'duplicate_keys': 0,
              'years': YEARS, 'primary_key': KEY, 'analysis_crs': CFG['projected_crs'],
              'forest_core_available_rows': int(master.forest_core_data_available.sum()),
              'pressure_extension_available_rows': int(master.pressure_extension_data_available.sum()),
              'invalid_value_checks': issues, 'primary_canopy_threshold': THRESHOLD,
              'threshold_status': 'documented analyst working choice; supervisor review pending',
              'hri_score_calculated': False, 'model_trained': False,
              'missing_policy': 'preserve NaN; no zero-filling, carry-forward or adaptive weight renormalization',
              'temporal_policy': 'end-of-year historical assessment; no forest events after t; '
                                 'population source-year <= t; retrospective products may use revised covariates',
              'remaining_decisions': ['HRI ecological scope and indicator transforms',
                  'Weights and missingness eligibility; class thresholds; independent validation',
                  'Human-pressure scope after 2020; 5km ecological-scale sensitivity remains unresolved'],
              'deferred': {'vegetation': 'No harmonised QA-filtered 2010–2023 vegetation series admitted; '
                           'forest-condition core has no claim to measure greenness decline.',
                           'conservation': 'Designation belongs to protection/priority context; '
                           'no licensed historical boundary series admitted.',
                           'climate_risk': 'Climate and terrain retained as context; absolute anomalies '
                           'are not automatically ecologically adverse.'},
              'input_sha256': {str(p.relative_to(ROOT)): digest(p) for p in source_paths}}
    save_json(OUT / 'master_dataset_audit.json', report)
    print(json.dumps({k: report[k] for k in ['status', 'rows', 'duplicate_keys',
                      'forest_core_available_rows', 'pressure_extension_available_rows']}, indent=2))


# %% 8. Feature-level provenance and diagnostic plots
def create_dictionary(master, candidates):
    existing = pd.read_csv(ROOT / 'data/processed/hri/wp6_v1/master_feature_dictionary.csv')
    existing.to_csv(OUT / 'inherited_feature_dictionary.csv', index=False)
    inherited = existing.set_index('feature').to_dict('index')
    rows = []
    for col in master:
        if col in KEY:
            source, unit, role = str(GRID.relative_to(ROOT)), 'identifier/year', 'key'
        elif col.startswith('forest__'):
            source, role = 'forest_cell_year.csv; Hansen GFC 2024 v1.12', 'diagnostic/context'
            unit = ('ha' if col.endswith('_ha') else 'percent' if 'percent' in col else
                    'years' if 'years_since' in col else 'fraction' if 'fraction' in col or 'proportion' in col or 'coverage' in col else 'flag/status/ratio')
        elif col.startswith('fragmentation__'):
            source, role = 'fragmentation_cell_year.csv; Hansen GFC 2024 v1.12', 'diagnostic/context'
            unit = ('metres/ha' if 'edge_m_' in col else 'metres' if col.endswith('_m') else
                    'ha' if col.endswith('_ha') else 'fraction' if 'fraction' in col or 'coverage' in col else
                    'percent' if 'threshold_percent' in col else 'count/flag/status')
        elif col.startswith('pressure__'):
            source, role = 'human_pressure_cell_year.csv; WorldPop Global1 UN-adjusted', 'diagnostic/context'
            unit = ('persons/km2' if 'density' in col else 'persons' if col.endswith('_count') else
                    'fraction' if col.endswith('_coverage') else 'year' if col.endswith('_year') else 'count/status')
        elif col.startswith(('climate__', 'terrain__')):
            source, unit, role = 'inherited_feature_dictionary.csv (original WP6 definition)', 'see inherited dictionary', 'context/QA'
        else:
            source, unit, role = 'prepare_hri_inputs.py: build_master', 'boolean', 'data availability only'
        direction = 'no generic risk direction'
        if col in candidates:
            role = 'candidate; not selected or weighted'
            direction = ('lower generally adverse for forest-associated habitat; ecological baseline required'
                         if 'proportion' in col or 'largest' in col else
                         'higher candidate pressure; conditional interpretation and correlation review required')
        formula = 'see source feature and visible preparation function'
        temporal = 'end-of-year t; source revisions retrospective'
        if col.startswith(('climate__', 'terrain__')) and col in inherited:
            original = inherited[col]
            source, unit = original['source_table'], original['unit']
            formula, temporal = original['formula'], original['temporal_window']
        elif col.startswith('forest__'):
            feature = col.split('__', 1)[1]
            if feature == 'remaining_baseline_forest_proportion':
                formula = '(baseline forest area - loss 2001 through t) / mapped valid land area'
            elif feature == 'baseline_forest_ha':
                formula, temporal = 'sum mapped land area with treecover2000 >=30 / 10000', 'year 2000 baseline'
            elif feature == 'baseline_canopy_percent':
                formula, temporal = 'area-weighted mean treecover2000 on mapped land', 'year 2000 baseline'
            elif 'loss_fraction_of_baseline' in feature:
                formula = 'corresponding loss hectares / baseline_forest_ha; undefined for zero baseline'
            elif feature == 'years_since_previous_loss':
                formula = 't - last year with mapped loss before t; NaN when no previous loss or no coverage'
            if 'previous_' in feature and 'yr' in feature:
                temporal = 'years t-N through t-1; N is the number in the feature name'
            elif 'cumulative_prior' in feature:
                temporal = '2001 through t-1'
            elif feature.startswith('annual_loss'):
                temporal = 'calendar year t'
        elif col.startswith('fragmentation__'):
            formula = 'fragment_metrics: 30m four-neighbour patches in a 1km halo; cell-clipped areas'
        elif col.startswith('pressure__'):
            formula = 'sum(persons per 1km pixel × area fraction in cell); density divides by clipped cell km2'
            temporal = 'matching reference year 2010–2020; missing 2021–2023'
        rows.append({'feature': col, 'source_table': source, 'unit': unit, 'role': role,
                     'formula': formula,
                     'risk_direction': direction, 'row_unit': 'cell × reference_year',
                     'transformation': 'none; raw physical units', 'weight': 'not assigned',
                     'missing_treatment': 'NaN retained; availability flags do not imply ecological eligibility',
                     'temporal_interpretation': temporal})
    pd.DataFrame(rows).to_csv(OUT / 'master_feature_dictionary.csv', index=False)


def summarize_scale_sensitivity():
    frame = pd.read_csv(OUT / 'fragmentation_scale_sensitivity.csv')
    metrics = ['cell_patch_count', 'mean_cell_patch_ha', 'largest_cell_patch_land_fraction',
               'largest_cell_patch_forest_fraction', 'edge_m_per_land_ha', 'mean_nearest_patch_centroid_m']
    base = frame.query('pixel_m == 30 and halo_m == 1000 and canopy_threshold_percent == 30').set_index('cell_id')
    rows = []
    for (px, halo, threshold), group in frame.groupby(['pixel_m', 'halo_m', 'canopy_threshold_percent']):
        comparison = group.set_index('cell_id')
        for col in metrics:
            paired = pd.concat([base[col].rename('baseline'), comparison[col].rename('comparison')], axis=1).dropna()
            rows.append({'feature': col, 'pixel_m': px, 'halo_m': halo, 'threshold_percent': threshold,
                         'paired_cells': len(paired), 'spearman_r': paired.baseline.corr(paired.comparison, method='spearman'),
                         'median_absolute_change': (paired.comparison - paired.baseline).abs().median()})
    pd.DataFrame(rows).to_csv(OUT / 'fragmentation_scale_sensitivity_summary.csv', index=False)


def plot_features(data, corr):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder = OUT / 'figures'
    folder.mkdir(exist_ok=True)
    for col in data:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(data[col].dropna(), bins=50)
        ax.set(xlabel=col, ylabel='Cell-years', title='Raw candidate distribution (not risk scores)')
        fig.tight_layout()
        fig.savefig(folder / f'{col}.png', dpi=130)
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(corr, vmin=-1, vmax=1, cmap='coolwarm')
    labels = [c.split('__')[1] for c in corr]
    ax.set_xticks(range(len(labels)), labels, rotation=90)
    ax.set_yticks(range(len(labels)), labels)
    fig.colorbar(im, ax=ax, label='Pairwise Spearman correlation')
    fig.tight_layout()
    fig.savefig(folder / 'candidate_correlations.png', dpi=130)
    plt.close(fig)


# %% 9. Foreground entry point: choose one stage, inspect its outputs, then continue
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['download', 'forest', 'population', 'master'], required=True)
    args = parser.parse_args()
    {'download': download_population, 'forest': prepare_forest,
     'population': prepare_population, 'master': build_master}[args.stage]()
