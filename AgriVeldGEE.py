import ee
import geemap
import json
import os
from pathlib import Path

ee.Authenticate()
ee.Initialize(project="agrobase1-test")

# --- Vaste paden ---
geojson_map = Path(r"C:\Users\niekw\OneDrive\Bureaublad\AgroBase\Geojson Velden")
tif_basis_map = Path(r"C:\Users\niekw\OneDrive\Bureaublad\AgroBase\RAW-DATA-TIF-FILES")

# --- Welk veld? ---
veldnaam = input("Voor welk veld? (bv. 'veld1'): ").strip()
geojson_pad = geojson_map / f"{veldnaam}.geojson"

if not geojson_pad.exists():
    print(f"Geojson niet gevonden: {geojson_pad}")
    beschikbaar = [p.stem for p in geojson_map.glob("*.geojson")]
    print(f"Beschikbare velden: {beschikbaar}")
    exit()

with open(geojson_pad) as f:
    geojson = json.load(f)
veld_geom = ee.Geometry(geojson["features"][0]["geometry"])

# --- Welk jaar? ---
jaar = int(input("Voor welk jaar? (bv. 2026): ").strip())

# --- Output map: submap per veld binnen de vaste RAW-DATA map ---
output_map = tif_basis_map / veldnaam
output_map.mkdir(parents=True, exist_ok=True)

for maand in range(1, 13):
    start = ee.Date.fromYMD(jaar, maand, 1)
    eind = start.advance(1, "month")
    collectie = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                 .filterBounds(veld_geom)
                 .filterDate(start, eind)
                 .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
                 .sort("CLOUDY_PIXEL_PERCENTAGE"))  # minst bewolkt eerst
    aantal = collectie.size().getInfo()
    if aantal == 0:
        print(f"Geen bruikbaar beeld voor {jaar}-{maand:02d} (te bewolkt of geen dekking)")
        continue
    beeld = collectie.first().clip(veld_geom)
    datum_str = ee.Date(beeld.get("system:time_start")).format("YYYY-MM-dd").getInfo()
    for band, naam in [("B4", "B04"), ("B8", "B08")]:
        bestand = output_map / f"{veldnaam}_{datum_str}_Sentinel-2_L2A_{naam}_(Raw).tif"
        geemap.ee_export_image(
            beeld.select(band),
            filename=str(bestand),
            scale=10,
            region=veld_geom,
            file_per_band=False
        )
        print(f"Gedownload: {bestand}")

print(f"\nKlaar — max. 12 maandbeelden gedownload naar {output_map}")
