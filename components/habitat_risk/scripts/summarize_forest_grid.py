"""Threshold-free mapped-area evidence on the provisional grid (not training labels)."""
from pathlib import Path
from contextlib import ExitStack
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask, geometry_window
from shapely.geometry import box, mapping
from pyproj import Geod

ROOT = Path(__file__).resolve().parents[1]

def main():
    cfg = json.loads((ROOT / 'configs/study.json').read_text())
    grid_id = f"lka_laea_{int(cfg['grid_size_m'])}m"
    grid = gpd.read_file(ROOT / f'data/interim/spatial/{grid_id}_grid.geojson').to_crs(4326)
    geod = Geod(ellps='WGS84')
    row_areas = {}
    rows, histograms = [], []
    with ExitStack() as stack:
        tiles = []
        for tile in ['10N_070E', '10N_080E']:
            sources = {b: stack.enter_context(rasterio.open(ROOT / f'data/raw/forest/Hansen_GFC-2024-v1.12_{b}_{tile}.tif'))
                       for b in ['treecover2000', 'lossyear', 'datamask']}
            assert len({(s.transform, s.crs, s.shape) for s in sources.values()}) == 1
            tiles.append(sources)
        for index, cell in grid.iterrows():
            totals = np.zeros(3, dtype=float)
            histogram = np.zeros(101 * 25, dtype=float)
            pixels = 0
            for sources in tiles:
                src = sources['datamask']
                geom = cell.geometry.intersection(box(*src.bounds))
                if geom.is_empty or geom.area == 0:
                    continue
                window = geometry_window(src, [mapping(geom)])
                values = {b: s.read(1, window=window) for b, s in sources.items()}
                included = geometry_mask([mapping(geom)], out_shape=values['datamask'].shape,
                                         transform=src.window_transform(window), invert=True, all_touched=False)
                mask, canopy, loss = (values[b] for b in ['datamask', 'treecover2000', 'lossyear'])
                assert np.isin(mask[included], [0, 1, 2]).all()
                assert (canopy[included] <= 100).all() and (loss[included] <= 24).all()
                areas = []
                for r in range(int(window.row_off), int(window.row_off + window.height)):
                    if r not in row_areas:
                        top = src.transform.f + r * src.transform.e
                        bottom = top + src.transform.e
                        dx = src.transform.a
                        area, _ = geod.polygon_area_perimeter([0, dx, dx, 0], [top, top, bottom, bottom])
                        row_areas[r] = abs(area)
                    areas.append(row_areas[r])
                weights = np.broadcast_to(np.array(areas)[:, None], included.shape)
                pixels += int(included.sum())
                totals += np.bincount(mask[included], weights=weights[included], minlength=3)
                land = included & (mask == 1)
                code = canopy[land].astype(np.int32) * 25 + loss[land]
                histogram += np.bincount(code, weights=weights[land], minlength=101 * 25)
            assert np.isclose(histogram.sum(), totals[1])
            total = totals.sum()
            rows.append({'cell_id': cell.cell_id, 'sampled_pixels': pixels,
                         'sampled_area_m2': total, 'no_data_area_m2': totals[0],
                         'mapped_land_area_m2': totals[1], 'persistent_water_area_m2': totals[2],
                         'observed_area_fraction_of_sampled_footprint': (totals[1]+totals[2])/total if total else np.nan,
                         'mean_canopy_percent_on_mapped_land': float((histogram.reshape(101,25).sum(axis=1)*np.arange(101)).sum()/totals[1]) if totals[1] else np.nan,
                         'status': 'no_pixel_centres' if not pixels else 'no_mapped_land' if not totals[1] else 'evidence_available'})
            for code in np.flatnonzero(histogram):
                histograms.append({'cell_id': cell.cell_id, 'canopy_percent': int(code//25),
                                   'loss_year_code': int(code%25), 'mapped_land_area_m2': histogram[code]})
            if (index+1) % 500 == 0:
                print(f'Summarized {index+1}/{len(grid)} cells', flush=True)
    out = ROOT / 'data/interim/spatial'
    pd.DataFrame(rows).to_csv(out / f'{grid_id}_forest_evidence.csv', index=False)
    pd.DataFrame(histograms).to_csv(out / f'{grid_id}_canopy_loss_histogram.csv', index=False)
    report = {'grid_cells': len(rows), 'histogram_rows': len(histograms),
              'source_release': 'Hansen GFC 2024 v1.12',
              'status_counts': pd.DataFrame(rows).status.value_counts().to_dict(),
              'method': 'Native pixel centres inside clipped country cells; WGS84 geodesic pixel areas; no boundary pixel fractional weighting.',
              'limitations': ['Mapped areas, not unbiased statistical area estimates.',
                             'Small coastal cells may contain no pixel centres.',
                             'Observed fraction includes water and is not a final modelling eligibility rule.',
                             'No baseline canopy threshold selected; no target labels generated.',
                             'Loss code zero means no mapped loss through 2024, not missing data.',
                             'Grid remains provisional; historical release revisions mean hindcast interpretation.']}
    (ROOT / 'reports/audits/forest_grid_evidence.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return report

if __name__ == '__main__':
    main()
