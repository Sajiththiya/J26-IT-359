"""SRTM 90m terrain summaries on country-clipped cells; no invented void values."""
from pathlib import Path
from contextlib import ExitStack
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.merge import merge
from rasterio.warp import reproject,Resampling
from rasterio.transform import from_origin
from rasterio.features import rasterize
ROOT=Path(__file__).resolve().parents[1]
def main():
    cfg=json.loads((ROOT/'configs/study.json').read_text());grid_id=f"lka_laea_{cfg['grid_size_m']}m"
    grid=gpd.read_file(ROOT/f'data/interim/spatial/{grid_id}_grid.geojson').to_crs(cfg['projected_crs'])
    geographic=grid.to_crs(4326);left,bottom,right,top=geographic.total_bounds
    with ExitStack() as stack:
        sources=[stack.enter_context(rasterio.open(ROOT/f'data/raw/terrain/srtm_{tile}.tif')) for tile in ['52_11','53_11']]
        assert all(s.crs.to_epsg()==4326 for s in sources)
        mosaic,source_transform=merge(sources,bounds=(left-.02,bottom-.02,right+.02,top+.02),nodata=-32768,dtype='float32')
        source_crs=sources[0].crs
    x0,y0,x1,y1=grid.total_bounds;res=90
    x0=np.floor((x0-270)/res)*res;y1=np.ceil((y1+270)/res)*res
    width=int(np.ceil((x1+270-x0)/res));height=int(np.ceil((y1-y0+270)/res))
    transform=from_origin(x0,y1,res,res)
    elevation=np.full((height,width),np.nan,dtype='float32')
    reproject(mosaic[0],elevation,src_transform=source_transform,src_crs=source_crs,src_nodata=-32768,dst_transform=transform,dst_crs=cfg['projected_crs'],dst_nodata=np.nan,resampling=Resampling.bilinear)
    del mosaic
    dy,dx=np.gradient(elevation,res,res)
    slope=np.degrees(np.arctan(np.hypot(dx,dy)))
    # Require the centre and all four gradient neighbours to be valid.
    valid=np.isfinite(elevation)
    neighbours=valid&np.roll(valid,1,0)&np.roll(valid,-1,0)&np.roll(valid,1,1)&np.roll(valid,-1,1)
    neighbours[[0,-1],:]=False;neighbours[:,[0,-1]]=False
    slope[~neighbours]=np.nan
    labels=rasterize(((g,i+1) for i,g in enumerate(grid.geometry)),out_shape=elevation.shape,transform=transform,fill=0,dtype='int32')
    n=len(grid)+1
    total=np.bincount(labels.ravel(),minlength=n)
    def stats(values):
        mask=(labels>0)&np.isfinite(values)
        codes=labels[mask];v=values[mask].astype('float64')
        count=np.bincount(codes,minlength=n)
        sums=np.bincount(codes,weights=v,minlength=n);sq=np.bincount(codes,weights=v*v,minlength=n)
        mean=np.divide(sums,count,out=np.full(n,np.nan),where=count>0)
        var=np.divide(sq,count,out=np.full(n,np.nan),where=count>0)-mean**2
        return count,mean,np.sqrt(np.maximum(var,0))
    count,mean,sd=stats(elevation);slope_count,slope_mean,_=stats(slope)
    output=pd.DataFrame({'cell_id':grid.cell_id,'terrain_sampled_pixels':total[1:],'terrain_valid_pixels':count[1:],'terrain_valid_fraction':np.divide(count[1:],total[1:],out=np.full(len(grid),np.nan),where=total[1:]>0),'slope_valid_fraction':np.divide(slope_count[1:],total[1:],out=np.full(len(grid),np.nan),where=total[1:]>0),'mean_elevation_m':mean[1:],'elevation_sd_m':sd[1:],'mean_slope_degrees':slope_mean[1:]})
    output['terrain_status']=np.select([output.terrain_sampled_pixels.eq(0),output.terrain_valid_fraction.lt(.95)|output.slope_valid_fraction.lt(.95)],['no_pixel_centres','below_working_95pct_coverage'],default='coverage_pass')
    assert output.cell_id.is_unique and output.mean_slope_degrees.dropna().between(0,90).all()
    assert output.elevation_sd_m.dropna().ge(0).all()
    out=ROOT/'data/interim/spatial';output.to_csv(out/f'{grid_id}_terrain_features.csv',index=False)
    path=out/f'{grid_id}_terrain_90m.tif'
    with rasterio.open(path,'w',driver='GTiff',width=width,height=height,count=2,dtype='float32',crs=cfg['projected_crs'],transform=transform,nodata=np.nan,compress='deflate') as dst:
        dst.write(elevation,1);dst.write(slope.astype('float32'),2);dst.set_band_description(1,'elevation_m');dst.set_band_description(2,'slope_degrees')
    report={'source':'CGIAR-CSI SRTM v4.1 90m','cell_count':len(output),'status_counts':output.terrain_status.value_counts().to_dict(),'elevation_mean_range_m':[float(output.mean_elevation_m.min()),float(output.mean_elevation_m.max())],'method':'Bilinear projection to 90m local LAEA, central finite-difference slope, pixel-centre zonal mean/population SD. Four valid neighbours required for slope.','limitations':['SRTM surface heights may include vegetation/buildings; not guaranteed bare earth','Void-filled product; interpolation mask not acquired','90m terrain smooths finer slopes; 5km grid provisional','95% coverage criterion is a working choice, not ecological standard','Boundary pixels use centre assignment, not fractional clipping'],'source_epoch':'SRTM mission 2000; product processing may use auxiliary DEMs'}
    (ROOT/'reports/audits/terrain_features.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return report
if __name__=='__main__':main()
