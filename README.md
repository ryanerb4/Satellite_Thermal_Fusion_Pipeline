# Satellite‑Fusion Imaging Pipeline

*Near‑real‑time fusion of ECOSTRESS, Landsat 8/9, Sentinel‑3 SLSTR **and MODIS Terra/Aqua** LST — delivering sub‑daily Land/Water Surface Temperature (LWST) at **30 m** for small lakes such as Mirror Lake, Rockport, and Jordanelle (Utah).*

---

## ✨ Updates
- **MODIS integrated** (`MOD11A1`, `MYD11A1` C6 1 km LST) with optional super‑resolution down‑scaling to 30 m.
- Pipeline prioritises high‑resolution sensors (ECOSTRESS, Landsat) and uses SLSTR & MODIS to fill temporal gaps, ensuring robust time‑series for small water bodies that cannot rely solely on coarse products.

---

## ⚡ Quick‑start

```bash
pip install -r requirements.txt

python satellite_fusion_pipeline.py \
  --aoi "POINT (-111.152 40.684)" \  # Jordanelle center
  --start 2025-06-01 --end 2025-06-07 \
  --target-resolution 30 \
  --pansharpen --sr-model sr_unet_v2 \
  --out jordanelle_LWST_20250601_07.tif
```

---

## Sensor cheat‑sheet

| Mission | Native thermal pixel | Delivered grid (this pipeline) | Typical revisit | Free L2 latency |
|---------|---------------------|--------------------------------|-----------------|-----------------|
| **ECOSTRESS** | 38 × 68 m (~70 m) | 70 m → 30 m | ~4 d | < 6 h |
| **Landsat 8/9** | 100 m | 100 m → 30 m (15 m pan‑sharpen) | 8 d | < 24 h |
| **Sentinel‑3 SLSTR** | 1 km | 1 km → 30 m (SR) | 0.9 d | < 6 h |
| **MODIS Terra/Aqua** | 1 km | 1 km → 30 m (SR) | 0.5 d (4 passes) | < 6 h |

**Latency boost:** ECOSTRESS+Landsat+SLSTR+MODIS reduces median gap **8 d → ~12 h** at mid‑latitudes.

---

## How it works
1. **STAC discovery** of all four sensors for AOI & date range.  
2. **Cloud screening** with QA masks, `--max-cloud` threshold.  
3. **Scaling**  
   * ECOSTRESS up‑scaled to 30 m (area‑weighted/cubic).  
   * Landsat optional 15 m pan‑sharpen.  
   * SLSTR & MODIS down‑scaled to 30 m via `--sr-model`.  
4. **Fusion** (ESTARFM/mean) with weight favouring finest‑resolution scene when multiple sensors overlap.  
5. **Output** GeoTIFF+NetCDF+JSON.

---

## Suitability for small lakes
Mirror Lake (~0.5 km across) and similar reservoirs fall below MODIS/SLSTR native pixel size. The pipeline therefore:

* Uses **ECOSTRESS & Landsat** as primary spatial sources (70 m and 30 m).  
* **Down‑scaled SLSTR/MODIS** provide temporal continuity; their coarse pixels are averaged over the lake extent and blended with higher‑resolution data to maintain consistency without introducing artefacts.

---

## Requirements
See `requirements.txt`.

GPU strongly recommended for super‑resolution.

---

*PhD tool for low‑latency thermal monitoring of inland waters.*
