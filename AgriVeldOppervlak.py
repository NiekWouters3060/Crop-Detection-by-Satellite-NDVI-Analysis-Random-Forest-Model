import re
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt
import fiona
from pathlib import Path


def dms_naar_decimaal(dms_str):
    """
    Zet een DMS-coördinaat zoals 50°52'07.1"N 4°37'26.3"E om naar (lat, lon) in decimale graden.
    Werkt met het formaat: graden° minuten' seconden" richting (N/S/E/W)
    """
    patroon = r"(\d+)°(\d+)'([\d.]+)\"?([NSEW])"
    matches = re.findall(patroon, dms_str)
    if len(matches) != 2:
        raise ValueError(f"Kon geen 2 coördinaten (lat + lon) vinden in: '{dms_str}'")
    resultaat = {}
    for graden, minuten, seconden, richting in matches:
        waarde = float(graden) + float(minuten) / 60 + float(seconden) / 3600
        if richting in ("S", "W"):
            waarde = -waarde
        if richting in ("N", "S"):
            resultaat["lat"] = waarde
        else:
            resultaat["lon"] = waarde
    return resultaat["lat"], resultaat["lon"]


# --- Vaste paden ---
gpkg_pad = Path(r"C:\Users\niekw\OneDrive\Documenten\agpa_2026_2026-06-02_public.gpkg")
geojson_map = Path(r"C:\Users\niekw\OneDrive\Bureaublad\AgroBase\Geojson Velden")
geojson_map.mkdir(parents=True, exist_ok=True)

if not gpkg_pad.exists():
    print(f"Perceelbestand niet gevonden op: {gpkg_pad}")
    exit()

# --- Input ---
veldnaam = input("Naam van het veld: ").strip()
coordinaat_input = input("Coördinaten in het veld: ").strip()

lat, lon = dms_naar_decimaal(coordinaat_input)
print(f"Decimale coördinaten: lat={lat:.6f}, lon={lon:.6f}")

# --- Percelenbestand inladen ---
lagen = fiona.listlayers(str(gpkg_pad))
percelen = gpd.read_file(str(gpkg_pad), layer=lagen[0])

# --- Naar WGS84 (lat/lon) zetten om het punt te kunnen gebruiken ---
percelen_wgs84 = percelen.to_crs(epsg=4326)

# --- Punt maken (let op: shapely wil (lon, lat)) ---
mijn_locatie = Point(lon, lat)

# --- Perceel zoeken dat dit punt bevat ---
mijn_veld = percelen_wgs84[percelen_wgs84.contains(mijn_locatie)]
print(f"Aantal gevonden percelen: {len(mijn_veld)}")
print(mijn_veld)

# --- Visueel checken ---
fig, ax = plt.subplots(figsize=(8, 8))
mijn_veld.plot(ax=ax, edgecolor="red", facecolor="lightgreen", linewidth=2)
ax.plot(lon, lat, "b*", markersize=20, label="Mijn punt")
ax.legend()
plt.title(f"Gevonden veld rond opgegeven coördinaat ({veldnaam})")
plt.show()

# --- Wegschrijven als GeoJSON in de vaste veld-map ---
if len(mijn_veld) > 0:
    output_pad = geojson_map / f"{veldnaam}.geojson"
    mijn_veld.to_file(output_pad, driver="GeoJSON")
    print(f"Weggeschreven naar {output_pad}")
else:
    print("Geen perceel gevonden op dit punt — check of je coördinaten kloppen of of dit punt buiten alle percelen valt.")
