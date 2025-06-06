
#!/usr/bin/env python3

"""
satellite_fusion_pipeline.py

Near‑real‑time fusion of ECOSTRESS, Landsat 8/9, Sentinel‑3 SLSTR **and MODIS (Terra/Aqua)** thermal imagery.

Designed to monitor small lakes (e.g., Mirror Lake, Rockport, Jordanelle) by prioritising
high‑resolution sensors (ECOSTRESS ~70 m, Landsat 30/15 m) while using down‑scaled
SLSTR and MODIS (1 km) to fill temporal gaps.

This is a skeletal reference implementation:
 - Scene discovery, pansharpen, and super‑resolution steps are placeholders.
 - Replace TODO sections with production logic (e.g., pySTARFM, CNN SR model).

"""
from __future__ import annotations
import argparse, pathlib, json, yaml, numpy as np
import rioxarray as rxr, xarray as xr, dask.array as da
from rasterio.enums import Resampling
from shapely.geometry import shape
from shapely import wkt
from pystac_client import Client as StacClient
from tqdm import tqdm
###############################################################################
def _parse_args():
    p = argparse.ArgumentParser(description="Fuse ECOSTRESS + Landsat + SLSTR + MODIS LST")
    p.add_argument("--aoi", required=True, help="AOI polygon WKT/GeoJSON/file")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--target-resolution", type=int, default=30)
    p.add_argument("--ecostress-resample", choices=["area","cubic"], default="area")
    p.add_argument("--pansharpen", action="store_true")
    p.add_argument("--sr-model", help="Super‑resolution model for SLSTR/MODIS")
    p.add_argument("--cloud-mask", action="store_true", default=True)
    p.add_argument("--max-cloud", type=float, default=20.0)
    p.add_argument("--config")
    return p.parse_args()
###############################################################################
def _load_geom(arg:str):
    if arg.strip().startswith("{"):
        return shape(json.loads(arg))
    p=pathlib.Path(arg)
    if p.exists():
        import fiona, itertools
        with fiona.open(p) as ds: return shape(next(iter(ds)))
    return wkt.loads(arg)
###############################################################################
class Scene:
    def __init__(self, href:str, qa_href:str|None, sensor:str, geom):
        self.href, self.qa_href, self.sensor, self.geom = href, qa_href, sensor, geom
        self._lst=self._qa=None
    def lst(self): 
        if self._lst is None: self._lst = rxr.open_rasterio(self.href, chunks={"band":1})
        return self._lst
    def qa(self):
        if not self.qa_href: return None
        if self._qa is None: self._qa = rxr.open_rasterio(self.qa_href, chunks={"band":1})
        return self._qa
###############################################################################
def _discover(cfg, geom):
    # TODO: implement STAC searches for ECOSTRESS, Landsat, SLSTR, MODIS
    return []
###############################################################################
def _cloud_frac(scene:Scene):
    qa = scene.qa()
    if qa is None: return 0.0
    return float((qa!=0).mean().compute())*100.0
###############################################################################
def _resample(scene:Scene, cfg):
    res = cfg["target_resolution"]
    if scene.sensor=="ECOSTRESS" and res==30:
        method = Resampling.cubic if cfg["ecostress_resample"]=="cubic" else Resampling.average
        return scene.lst().rio.reproject(dst_crs="EPSG:32612", resolution=res, resampling=method)
    if scene.sensor=="Landsat" and cfg.get("pansharpen"):
        # TODO pansharpen logic
        pass
    if scene.sensor in {"SLSTR","MODIS"} and res==30 and cfg.get("sr_model"):
        return scene.lst().rio.reproject(dst_crs="EPSG:32612", resolution=res,
                                         resampling=Resampling.nearest)
    return scene.lst()
###############################################################################
def _fuse(arrays):
    if not arrays: raise RuntimeError("No scenes after filtering")
    return xr.concat(arrays, dim="time").mean(dim="time")
###############################################################################
def run(cfg):
    geom=_load_geom(cfg["aoi"])
    scenes=_discover(cfg, geom)
    arrs=[]
    for sc in tqdm(scenes, desc="Scenes"):
        if cfg["cloud_mask"] and sc.qa() is not None and _cloud_frac(sc)>cfg["max_cloud"]:
            continue
        arrs.append(_resample(sc,cfg))
    fused=_fuse(arrs)
    dst=pathlib.Path(cfg["out"]).expanduser()
    fused.rio.to_raster(dst)
    print("✓ Fusion complete →",dst)
###############################################################################
def _merge(args):
    cfg=vars(args).copy()
    if args.config:
        with open(args.config) as f: cfg.update(yaml.safe_load(f) or {})
    cfg["target_resolution"]=int(cfg["target_resolution"])
    cfg["max_cloud"]=float(cfg["max_cloud"])
    return cfg
###############################################################################
if __name__=="__main__":
    args=_parse_args()
    run(_merge(args))
