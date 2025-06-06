
#!/usr/bin/env python3
"""satellite_fusion_pipeline.py

Near‑real‑time fusion of ECOSTRESS, Landsat 8/9 and Sentinel‑3 SLSTR thermal imagery.

Changes in this release
-----------------------
* **Cloud masking & filtering**
  - `--cloud-mask` (default true) applies QA‑bit cloud masks per mission.
  - `--max-cloud <pct>` drops scenes whose cloud coverage inside the AOI
    is greater than the threshold (default 20 %).
* **Target resolution switch** (30 m default) with ECOSTRESS upscale,
  optional Landsat pansharpen, and Sentinel‑3 down‑scale via SR model.

This script is designed for demonstrative purposes; replace the placeholder
functions (marked TODO) with production‑grade logic for STAC search,
quality bits, pansharpening, and super‑resolution.

"""

from __future__ import annotations
import argparse
import pathlib
import datetime as dt
import json
import yaml
import numpy as np
import rioxarray as rxr
import xarray as xr
import dask.array as da
from rasterio.enums import Resampling
from shapely.geometry import shape, box
from shapely import wkt
from rasterio.features import geometry_window
from pystac_client import Client as StacClient
from tqdm import tqdm

###############################################################################
# CLI PARSING
###############################################################################

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fuse ECOSTRESS, Landsat, Sentinel‑3 LST with cloud filtering."
    )
    p.add_argument("--aoi", required=True,
                   help="AOI polygon in WKT or path to GeoJSON/GeoPackage")
    p.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    p.add_argument("--end",   required=True, help="End date YYYY-MM-DD")
    p.add_argument("--out",   required=True, help="Output GeoTIFF or NetCDF path")

    # Resolution / resample
    p.add_argument("--target-resolution", type=int, default=30,
                   help="Target cell size in metres (30 or 70)")
    p.add_argument("--ecostress-resample", choices=["area", "cubic"], default="area")
    p.add_argument("--pansharpen", action="store_true",
                   help="Brovey pansharpen Landsat to 15 m before fusion")
    p.add_argument("--sr-model",
                   help="Sentinel‑3 super‑resolution model identifier to reach 30 m")

    # Cloud options
    p.add_argument("--cloud-mask", action="store_true", default=True,
                   help="Apply cloud masks (default on)")
    p.add_argument("--max-cloud", type=float, default=20.0,
                   help="Discard scenes with cloud > this percent inside AOI")

    p.add_argument("--config", help="YAML config file with any of the above keys")
    return p.parse_args()

###############################################################################
# BASIC HELPERS
###############################################################################

def _load_aoi(aoi_arg: str):
    """Return shapely geometry from WKT or small GeoJSON/GeoPackage file."""
    if aoi_arg.strip().startswith("{"):  # GeoJSON string
        return shape(json.loads(aoi_arg))
    p = pathlib.Path(aoi_arg)
    if p.exists():
        import fiona
        with fiona.open(p) as ds:
            return shape(next(iter(ds)))
    # fallback WKT
    return wkt.loads(aoi_arg)

###############################################################################
# SCENE CLASS
###############################################################################

class Scene:
    """A minimal wrapper for one satellite LST scene and its QA band."""
    def __init__(self, href: str, qa_href: str | None, sensor: str, aoi_geom):
        self.href = href
        self.qa_href = qa_href  # may be None if no cloud mask desired
        self.sensor = sensor
        self.aoi_geom = aoi_geom
        self._lst: xr.DataArray | None = None
        self._qa: xr.DataArray | None = None

    def lst(self) -> xr.DataArray:
        if self._lst is None:
            self._lst = rxr.open_rasterio(self.href, chunks={"band": 1})
        return self._lst

    def qa(self) -> xr.DataArray | None:
        if self.qa_href is None:
            return None
        if self._qa is None:
            self._qa = rxr.open_rasterio(self.qa_href, chunks={"band": 1})
        return self._qa

###############################################################################
# DISCOVERY (PLACEHOLDER)
###############################################################################

def _discover(cfg: dict, aoi_geom) -> list[Scene]:
    """Query STAC endpoints to build a list of Scene objects (stub)."""
    # TODO: implement real discovery. For demo, return empty to avoid errors.
    return []

###############################################################################
# CLOUD FRACTION
###############################################################################

def _cloud_fraction(scene: Scene, cfg: dict) -> float:
    qa = scene.qa()
    if qa is None:
        return 0.0
    # Placeholder: treat non‑zero as cloud
    mask = qa != 0
    # Clip to AOI bbox window for efficiency
    try:
        window = geometry_window(qa.rio._manager().datasets[0], [scene.aoi_geom])
        subset = mask[0, window.row_off:window.row_off+window.height,
                         window.col_off:window.col_off+window.width]
        frac = subset.mean().compute().item()
    except Exception:
        frac = mask.mean().compute().item()
    return frac * 100.0

###############################################################################
# RESAMPLING
###############################################################################

def _resample(scene: Scene, cfg: dict) -> xr.DataArray:
    target_res = cfg["target_resolution"]
    # ECOSTRESS upscale
    if scene.sensor == "ECOSTRESS" and target_res == 30:
        resampling = Resampling.cubic if cfg["ecostress_resample"] == "cubic" else Resampling.average
        return scene.lst().rio.reproject(
            dst_crs="EPSG:32612", resolution=target_res, resampling=resampling)
    # Landsat pansharpen stub
    if scene.sensor == "Landsat" and cfg.get("pansharpen"):
        # TODO: pansharpen logic
        pass
    # Sentinel‑3 down‑scale stub
    if scene.sensor == "SLSTR" and target_res == 30 and cfg.get("sr_model"):
        return scene.lst().rio.reproject(
            dst_crs="EPSG:32612", resolution=target_res, resampling=Resampling.nearest)
    return scene.lst()

###############################################################################
# FUSION
###############################################################################

def _fuse(arrays: list[xr.DataArray]) -> xr.DataArray:
    if not arrays:
        raise RuntimeError("No scenes available after cloud filtering!")
    stack = xr.concat(arrays, dim="time")
    return stack.mean(dim="time")

###############################################################################
# MAIN PIPELINE
###############################################################################

def run_pipeline(cfg: dict):
    aoi_geom = _load_aoi(cfg["aoi"])
    scenes = _discover(cfg, aoi_geom)

    good_arrays = []
    for sc in tqdm(scenes, desc="Scenes"):
        if cfg["cloud_mask"]:
            cf = _cloud_fraction(sc, cfg)
            if cf > cfg["max_cloud"]:
                continue
            lst_da = xr.where(sc.qa() == 0, sc.lst(), np.nan)
        else:
            lst_da = sc.lst()
        regrid = _resample(scene := sc, cfg)
        good_arrays.append(regrid)

    fused = _fuse(good_arrays)
    dst = pathlib.Path(cfg["out"]).expanduser().resolve()
    fused.rio.to_raster(dst)
    print(f"✓ Fusion complete → {dst}")

###############################################################################
# CONFIG
###############################################################################

def _merge_cli_yaml(args: argparse.Namespace) -> dict:
    cfg = vars(args).copy()
    if args.config:
        with open(args.config) as f:
            cfg.update(yaml.safe_load(f) or {})
    # Normalize types
    cfg["target_resolution"] = int(cfg["target_resolution"])
    cfg["max_cloud"] = float(cfg["max_cloud"])
    return cfg

###############################################################################
# RUN
###############################################################################

if __name__ == "__main__":
    args = _parse_args()
    config = _merge_cli_yaml(args)
    run_pipeline(config)
