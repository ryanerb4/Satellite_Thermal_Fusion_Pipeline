# Satellite_Thermal_Fusion_Pipeline
PhD research tool for near‑real‑time fusion of thermal land/water surface temperature (LST) from free satellite sources: **NASA ECOSTRESS**, **USGS Landsat 8/9 Collection 2 Level‑2**, and (optional) **ESA Sentinel‑3 SLSTR**

# Satellite‑Fusion Imaging Pipeline

*Near‑real‑time fusion of ECOSTRESS, Landsat 8/9, and Sentinel‑3 SLSTR thermal imagery—sub‑daily Land/Water Surface Temperature (LWST) maps at 30 m, using only free/open data.*

---

## Why this repo exists
Single missions trade off **resolution × latency**. By fusing the complementary revisit cycles of three sensors we reduce the expected gap between usable LST observations:

* **Landsat‑only:** ~8 days  
* **ECOSTRESS‑only:** ~4 days  
* **Sentinel‑3‑only:** ~1 day  
* **Fusion (all three):** **< 1 day** (~17 h median)

---

## Quick‑start

1. **Create the environment**

```bash
conda env create -f environment.yml
conda activate sat-fusion
```

2. **Run a minimal job**

```bash
python satellite_fusion_pipeline.py   --aoi "POLYGON ((-112 40, -111 40, -111 41, -112 41, -112 40))"   --start 2025-05-25 --end 2025-05-30   --out utah_lake_LWST.tif
```

3. **Custom scaling & pansharpen**

```bash
python satellite_fusion_pipeline.py   --config myrun.yml \
  --target-resolution 30 \
  --ecostress-resample cubic \
  --pansharpen
```

Outputs appear as GeoTIFF (`.tif`), NetCDF (`.nc`), and a JSON metadata side‑car.

---

## Sensor cheat‑sheet

| Mission | Pixel (thermal) | Delivered grid | Revisit time | Free L2 latency |
|---------|-----------------|----------------|--------------|-----------------|
| **ECOSTRESS** | 38 × 68 m (~70 m) | *70 m → 30 m* (upscaled) | ~4 days* | < 6 h after downlink |
| **Landsat 8/9** | 100 m (TIRS) | 100 m → *30 m* (pansharpen) | 8 days | < 24 h (Collection‑2 L2) |
| **Sentinel‑3 SLSTR** | 1 km | 1 km → *30 m* (SR model) | 0.9 days | < 6 h |

\*ECOSTRESS revisit varies with ISS orbit; 4 days is median at mid‑latitudes.

---

## How it works

1. **Discovery:** Queries NASA CMR, USGS STAC, and Copernicus Hub for the freshest L2‐LST scenes intersecting your AOI.
2. **Streaming I/O:** Reads COG tiles lazily—no full downloads.
3. **Scaling:**  
   * Up‑scales ECOSTRESS to 30 m (area‑weighted or cubic).  
   * Optionally pansharpens Landsat TIRS to 15 m.  
   * Down‑scales SLSTR with a super‑resolution CNN (if `--sr-model` given).
4. **Fusion:** ESTARFM‑style weighted average (or simple mean) blends per‑pixel LWST.
5. **Output:** Writes GeoTIFF+NetCDF plus JSON metadata for provenance.

---

## Citations

* ECOSTRESS L2‐LST Product Guide, NASA JPL, 2024.  
* Landsat Collection 2 L2 ST Product Guide, USGS, 2023.  
* Sentinel‑3 SLSTR LST Product Notice, ESA, 2024.  
* Allen et al., 2021. “Multi‑sensor fusion of ECOSTRESS and Landsat LST.” *Remote Sensing of Environment*.

---

*Created for PhD research on low‑latency thermal monitoring of inland waters.*
