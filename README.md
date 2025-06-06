# Satellite‑Fusion Imaging Pipeline

*Near‑real‑time fusion of ECOSTRESS, Landsat 8/9, and Sentinel‑3 SLSTR thermal imagery — sub‑daily Land/Water Surface Temperature (LWST) maps at **30 m** resolution using only open data.*

---

## ✨ What’s new
- **Cloud masking & scene filtering**  
  `--cloud-mask` (default *on*) applies QA bitmasks; `--max-cloud` discards scenes whose cloud coverage inside the AOI exceeds a threshold (default **20 %**).
- **Selectable target resolution**  
  `--target-resolution` (30 m default) up‑scales ECOSTRESS, optionally pan‑sharpens Landsat to 15 m, and down‑scales Sentinel‑3 via a super‑resolution model.
- **Fully cloud‑native** (COGs streamed via STAC; no bulk downloads).

---

## ⚡ Quick‑start

```bash
# 1) Install deps
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt   # or:  conda env create -f environment.yml

# 2) Minimal run over Utah Lake
python satellite_fusion_pipeline.py   --aoi "POLYGON ((-112 40, -111 40, -111 41, -112 41, -112 40))"   --start 2025-05-25 --end 2025-05-30   --out utah_lake_LWST.tif
```

Advanced example with custom options:

```bash
python satellite_fusion_pipeline.py   --config myrun.yml              \
  --target-resolution 30          \
  --ecostress-resample cubic      \
  --pansharpen                    \
  --cloud-mask --max-cloud 10
```

Outputs include GeoTIFF (`.tif`), NetCDF (`.nc`), and a JSON metadata side‑car.

---

## 🛠️ Command‑line options

| Flag | Default | Description |
|------|---------|-------------|
| `--aoi` | *required* | AOI polygon (WKT string or GeoJSON/GeoPackage path). |
| `--start` / `--end` | *required* | Date range (YYYY‑MM‑DD). |
| `--out` | *required* | Output file path (`.tif` or `.nc`). |
| `--target-resolution` | **30** | Target cell size in metres (30 m or 70 m). |
| `--ecostress-resample` | `area` | Upscale kernel for ECOSTRESS (`area` or `cubic`). |
| `--pansharpen` | *off* | Apply 15 m Brovey pansharpen on Landsat. |
| `--sr-model` | *none* | Sentinel‑3 super‑resolution model ID. |
| `--cloud-mask` | *on* | Apply QA‑bit cloud masks. |
| `--max-cloud` | **20** | Scene rejection threshold (% cloudy pixels). |
| `--config` | *none* | YAML file overriding any options above. |

---

## 🔬 Sensor cheat‑sheet

| Mission | Native thermal pixel | Delivered grid (this pipeline) | Typical revisit | Free L2 latency |
|---------|---------------------|--------------------------------|-----------------|-----------------|
| **ECOSTRESS** | 38 × 68 m (~70 m) | *70 m → 30 m* (up‑scaled) | ~4 days (ISS orbit) | < 6 h |
| **Landsat 8/9** | 100 m (TIRS) | 100 m → *30 m* (band resample) / *15 m* (pan‑sharpen) | 8 days | < 24 h |
| **Sentinel‑3 SLSTR** | 1 km | 1 km → *30 m* (SR model) | 0.9 days | < 6 h |

> **Latency win:** Fusing all three sensors reduces the median gap between usable LWST observations from **8 days → < 1 day (~17 h).**

---

## ⚙️ How the pipeline works

1. **Discovery** – Queries NASA CMR, USGS STAC, and Copernicus Hub for the freshest L2‑LST scenes intersecting the AOI.  
2. **Streaming I/O** – Reads COGs lazily with `rioxarray`; no full downloads.  
3. **Cloud screening** – Masks QA bits and discards scenes above `--max-cloud`.  
4. **Scaling**  
   * ECOSTRESS → 30 m (area‑weighted or cubic).  
   * Landsat pansharpen to 15 m when `--pansharpen`.  
   * SLSTR super‑resolved if `--sr-model` specified.  
5. **Fusion** – ESTARFM‑style weighted average (or fallback mean) blends per‑pixel LWST.  
6. **Output** – Writes Cloud‑Optimized GeoTIFF + NetCDF + JSON metadata.

---

## 📦 Requirements

See **requirements.txt** for exact pinned versions.

Core libraries: `rioxarray`, `xarray`, `rasterio`, `dask`, `pystac-client`, `numpy`, `pyproj`, `shapely`, `torch` (optional, for super‑resolution).

GPU acceleration is recommended for large AOIs or CNN super‑resolution.

---

## 📑 Citations

- **ECOSTRESS** L2‑LST Product Guide, NASA JPL, 2024.  
- **Landsat** Collection‑2 L2 Surface Temperature Product Guide, USGS, 2023.  
- **Sentinel‑3 SLSTR** LST Product Notice v1.0, ESA, 2024.  
- Allen et al., 2021. “Multi‑sensor fusion of ECOSTRESS and Landsat LST.” *Remote Sensing of Environment*.

---

*Created as part of PhD research on low‑latency thermal monitoring of inland waters.*
