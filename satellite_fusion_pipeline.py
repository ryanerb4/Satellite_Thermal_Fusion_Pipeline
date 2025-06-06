
#!/usr/bin/env python3
"""
satellite_fusion_pipeline.py

Near‑real‑time fusion of ECOSTRESS, Landsat 8/9, Sentinel‑3 SLSTR **and MODIS (Terra/Aqua)** thermal imagery.

Focus: Deliver sub‑daily Land/Water Surface Temperature (LWST) maps at 30 m resolution for
small inland water bodies such as Mirror Lake, Rockport Reservoir, and Jordanelle Reservoir.

───────────────────────────────────────────────────────────────────────────────
FEATURES
────────
• Cloud‑native ingestion (COGs streamed via STAC endpoints, no bulky downloads)
• Cloud masking and scene‑level cloud‑percentage filtering (`--cloud-mask`, `--max-cloud`)
• Selectable target resolution (`--target-resolution 30` or 70 m)
• ECOSTRESS upscale (area‑weighted or cubic); optional Landsat 15 m pansharpen
• Super‑resolution hook for down‑scaling SLSTR & MODIS to 30 m (`--sr-model`)
• Simple temporal fusion (mean composite) — replace with ESTARFM/STARFM if desired
• YAML config injection for batch runs
───────────────────────────────────────────────────────────────────────────────
DISCLAIMER
──────────
This is a reference scaffold. Discovery queries, pansharpen, and super‑resolution
functions are placeholders (marked TODO). Replace with production implementations
(e.g., PySTAC search, Brovey pansharpen with spectral bands, CNN model inference).
"""
from __future__ import annotations
import argparse, pathlib, json, yaml, datetime as dt
import numpy as np
import rioxarray as rxr
import xarray as xr
import dask.array as da
from rasterio.enums import Resampling
from shapely.geometry import shape
from shapely import wkt
from pystac_client import Client as StacClient
from tqdm import tqdm

###############################################################################
# CLI PARSER
###############################################################################
def _parse_args() -> argparse.Namespace:
    P = argparse.ArgumentParser(
        description="Fuse ECOSTRESS + Landsat + Sentinel‑3 + MODIS LST into 30 m maps"
    )
    P.add_argument("--aoi", required=True,
                   help="AOI polygon WKT, GeoJSON string, or file path")
    P.add_argument("--start", required=True, help="Start date YYYY‑MM‑DD")
    P.add_argument("--end", required=True, help="End date YYYY‑MM‑DD")
    P.add_argument("--out", required=True, help="Output path (.tif or .nc)")

    # Resolution and resample options
    P.add_argument("--target-resolution", type=int, default=30,
                   help="Target cell size in metres (30 or 70)")
    P.add_argument("--ecostress-resample", choices=["area", "cubic"],
                   default="area", help="Upscale kernel for ECOSTRESS")
    P.add_argument("--pansharpen", action="store_true",
                   help="Apply 15 m Brovey pansharpen on Landsat")
    P.add_argument("--sr-model",
                   help="ID/path for super‑resolution model (used for SLSTR/MODIS)")

    # Cloud handling
    P.add_argument("--cloud-mask", action="store_true", default=True,
                   help="Apply QA‑bit cloud masks (default on)")
    P.add_argument("--max-cloud", type=float, default=20.0,
                   help="Reject scenes with cloud % above threshold")

    # Config override
    P.add_argument("--config",
                   help="YAML file containing any CLI options (overrides earlier)")

    return P.parse_args()


###############################################################################
# GEOMETRY HELPER
###############################################################################
def _load_geom(aoi_spec: str):
    """Return Shapely geometry from WKT string, GeoJSON string, or vector file."""
    aoi_spec = aoi_spec.strip()
    if aoi_spec.startswith("{"):      # GeoJSON string
        return shape(json.loads(aoi_spec))
    p = pathlib.Path(aoi_spec)
    if p.exists():
        import fiona
        with fiona.open(p) as coll:
            return shape(next(iter(coll)))
    # Fallback to WKT
    return wkt.loads(aoi_spec)


###############################################################################
# SCENE WRAPPER
###############################################################################
class Scene:
    """Thin wrapper for one satellite scene (LST + QA)."""
    def __init__(self, href: str, qa_href: str | None, sensor: str, aoi_geom):
        self.href      = href
        self.qa_href   = qa_href
        self.sensor    = sensor
        self.aoi_geom  = aoi_geom
        self._lst: xr.DataArray | None = None
        self._qa : xr.DataArray | None = None

    # Lazy loaders ------------------------------------------------------------
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
# DISCOVERY (PLACEHOLDERS)
###############################################################################
def _discover_scenes(cfg: dict, geom) -> list[Scene]:
    """
    Query appropriate STAC endpoints & return Scene objects.
    Replace this stub with production discovery using pystac_client.
    """
    # TODO: Use StacClient.open() with NASA CMR, USGS landsatlook, Copernicus, LP DAAC
    print("⚠  Discovery stub: returning empty scene list (implement me).")
    return []


###############################################################################
# CLOUD METRICS
###############################################################################
def _cloud_fraction(scene: Scene) -> float:
    """Compute % cloud inside entire raster (AOI window optional)."""
    qa = scene.qa()
    if qa is None:
        return 0.0
    cloud_mask = qa != 0  # placeholder: non‑zero = cloud
    return float(cloud_mask.mean().compute()) * 100.0


###############################################################################
# RESAMPLING / SR / PANSHARPEN
###############################################################################
def _resample_to_target(scene: Scene, cfg: dict) -> xr.DataArray:
    res = cfg["target_resolution"]

    # ECOSTRESS upscale to 30 m
    if scene.sensor == "ECOSTRESS" and res == 30:
        kernel = (Resampling.cubic
                  if cfg["ecostress_resample"] == "cubic"
                  else Resampling.average)
        return scene.lst().rio.reproject(
            dst_crs="EPSG:32612", resolution=res, resampling=kernel)

    # Landsat pansharpen stub
    if scene.sensor == "Landsat" and cfg.get("pansharpen"):
        # TODO: Implement Brovey or PCA pansharpen to 15 m
        pass

    # SLSTR / MODIS down‑scale via SR model
    if scene.sensor in {"SLSTR", "MODIS"} and res == 30 and cfg.get("sr_model"):
        # TODO: Load CNN model & infer; fallback to nearest‑neighbour reproject
        return scene.lst().rio.reproject(
            dst_crs="EPSG:32612", resolution=res, resampling=Resampling.nearest)

    # Default: return at native grid
    return scene.lst()


###############################################################################
# FUSION
###############################################################################
def _fuse(arrays: list[xr.DataArray]) -> xr.DataArray:
    """
    Simple mean composite across time dimension.
    Replace with STARFM/ESTARFM weight‑averaged fusion for production.
    """
    if not arrays:
        raise RuntimeError("No arrays provided for fusion.")
    return xr.concat(arrays, dim="time").mean(dim="time")


###############################################################################
# MAIN PIPELINE
###############################################################################
def run_pipeline(cfg: dict):
    aoi_geom = _load_geom(cfg["aoi"])
    scenes   = _discover_scenes(cfg, aoi_geom)

    valid_arrays: list[xr.DataArray] = []
    for sc in tqdm(scenes, desc="Scenes"):
        # Cloud filtering -----------------------------------------------------
        if cfg["cloud_mask"] and sc.qa() is not None:
            cf = _cloud_fraction(sc)
            if cf > cfg["max_cloud"]:
                continue
            # Apply pixel‑level mask (placeholder: QA==0 clear)
            lst_da = xr.where(sc.qa() == 0, sc.lst(), np.nan)
            sc._lst = lst_da  # override for resampling
        # Resample / SR / pansharp -------------------------------------------
        da_res = _resample_to_target(sc, cfg)
        valid_arrays.append(da_res)

    fused = _fuse(valid_arrays)
    out_path = pathlib.Path(cfg["out"]).expanduser().resolve()
    fused.rio.to_raster(out_path)
    print("✓ Fusion complete →", out_path)


###############################################################################
# CONFIG MERGE
###############################################################################
def _merge_cli_yaml(args: argparse.Namespace) -> dict:
    cfg = vars(args).copy()
    if args.config:
        with open(args.config) as f:
            cfg.update(yaml.safe_load(f) or {})
    cfg["target_resolution"] = int(cfg["target_resolution"])
    cfg["max_cloud"]         = float(cfg["max_cloud"])
    return cfg


###############################################################################
# ENTRY
###############################################################################
if __name__ == "__main__":
    cli_args = _parse_args()
    cfg      = _merge_cli_yaml(cli_args)
    run_pipeline(cfg)
