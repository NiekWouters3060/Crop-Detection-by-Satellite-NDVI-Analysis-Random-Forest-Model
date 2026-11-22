import rasterio
import numpy as np
import re
import csv
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
#dit bestand creëert de afbeelding en tijdreeks

# ============================================================
# FUNCTIE 1: datum uit bestandsnaam halen
# ============================================================
def haal_datum_uit_bestandsnaam(pad):
    """
    Haalt de datum (YYYY-MM-DD) uit bestandsnamen zoals:
    'veld1_2026-07-28_Sentinel-2_L2A_B04_(Raw).tif'
    """
    naam = Path(pad).name
    match = re.search(r"(\d{4}-\d{2}-\d{2})", naam)
    if match:
        return match.group(1)
    return None


# ============================================================
# FUNCTIE 2: NDVI-statistieken + array berekenen voor één datum
# ============================================================
def bereken_ndvi_statistieken(red_path, nir_path):
    with rasterio.open(red_path) as red_src:
        red = red_src.read(1).astype("float32")
    with rasterio.open(nir_path) as nir_src:
        nir = nir_src.read(1).astype("float32")

    nodata_mask = (red == 0) | (nir == 0) | (red == 65535) | (nir == 65535)

    red_refl = red / 10000.0
    nir_refl = nir / 10000.0

    np.seterr(divide="ignore", invalid="ignore")
    ndvi = (nir_refl - red_refl) / (nir_refl + red_refl)
    ndvi = np.clip(ndvi, -1, 1)

    nodata_mask = nodata_mask | ~np.isfinite(ndvi)
    ndvi_masked = np.ma.masked_where(nodata_mask, ndvi)

    return {
        "gemiddelde": float(np.ma.mean(ndvi_masked)) if ndvi_masked.count() > 0 else float("nan"),
        "min": float(np.ma.min(ndvi_masked)) if ndvi_masked.count() > 0 else float("nan"),
        "max": float(np.ma.max(ndvi_masked)) if ndvi_masked.count() > 0 else float("nan"),
        "nodata_pixels": int(nodata_mask.sum()),
        "totaal_pixels": int(red.size),
        "ndvi_array": ndvi_masked,
    }


# ============================================================
# FUNCTIE 3: bestanden per datum koppelen (B04 <-> B08), optioneel gefilterd op jaar
# ============================================================
def koppel_banden_per_datum(map_pad, jaar_filter=None):
    map_pad = Path(map_pad)
    gekoppeld = {}
    for bestand in map_pad.glob("*.tif*"):  # vangt zowel .tif als .tiff
        datum = haal_datum_uit_bestandsnaam(bestand)
        if datum is None:
            continue
        if jaar_filter and not datum.startswith(str(jaar_filter)):
            continue
        if datum not in gekoppeld:
            gekoppeld[datum] = {}
        if "_B04_" in bestand.name:
            gekoppeld[datum]["red"] = bestand
        elif "_B08_" in bestand.name:
            gekoppeld[datum]["nir"] = bestand

    volledig = {
        datum: paden
        for datum, paden in gekoppeld.items()
        if "red" in paden and "nir" in paden
    }
    return volledig


# ============================================================
# FUNCTIE 4: alle NDVI-kaarten samen weergeven in een grid
# ============================================================
def toon_alle_ndvi_kaarten(datums, ndvi_arrays, veldnaam, jaar, map_output):
    cmap = LinearSegmentedColormap.from_list(
        "ndvi_health", ["red", "orange", "yellow", "yellowgreen", "green"]
    )
    cmap.set_bad(color="lightgray")

    n = len(datums)
    kolommen = 3
    rijen = int(np.ceil(n / kolommen))

    fig, axes = plt.subplots(rijen, kolommen, figsize=(5 * kolommen, 5 * rijen))
    axes = np.array(axes).reshape(-1)

    for i, (datum, ndvi_array) in enumerate(zip(datums, ndvi_arrays)):
        im = axes[i].imshow(ndvi_array, cmap=cmap, vmin=-0.2, vmax=0.8)
        axes[i].set_title(datum)
        axes[i].axis("off")

    for j in range(i + 1, len(axes)):
        axes[j].axis("off")

    fig.colorbar(im, ax=axes.tolist(), label="NDVI", shrink=0.6)
    fig.suptitle(f"NDVI {veldnaam} — {jaar}", fontsize=14)

    afbeelding_pad = Path(map_output) / f"ndvi_kaarten_{veldnaam}_{jaar}.png"
    plt.savefig(afbeelding_pad, dpi=200, bbox_inches="tight")
    print(f"Afbeelding weggeschreven naar {afbeelding_pad}")
    plt.show()


# ============================================================
# HOOFDSCRIPT
# ============================================================
def main():
    tif_basis_map = Path(r"C:\Users\niekw\OneDrive\Bureaublad\AgroBase\RAW-DATA-TIF-FILES")
    map_output = Path(r"C:\Users\niekw\OneDrive\Bureaublad\AgroBase\NDVI-TIJDREEKS-VELDEN")
    map_output.mkdir(parents=True, exist_ok=True)

    veldnaam = input("Voor welk veld? (bv. 'veld1'): ").strip()
    map_met_bestanden = tif_basis_map / veldnaam

    if not map_met_bestanden.exists():
        print(f"Map niet gevonden: {map_met_bestanden}")
        beschikbaar = [p.name for p in tif_basis_map.iterdir() if p.is_dir()]
        print(f"Beschikbare velden: {beschikbaar}")
        return

    jaar = input("Voor welk jaar? (bv. 2026): ").strip()

    gekoppelde_bestanden = koppel_banden_per_datum(map_met_bestanden, jaar_filter=jaar)

    if not gekoppelde_bestanden:
        print(f"Geen gekoppelde B04/B08-bestanden gevonden voor {veldnaam} in {jaar}.")
        return

    standaard_naam = f"tijdreeks-{veldnaam}-{jaar}.csv"
    bestandsnaam = input(f"Bestandsnaam voor csv [Enter voor '{standaard_naam}']: ").strip()
    if not bestandsnaam:
        bestandsnaam = standaard_naam

    output_csv = map_output / bestandsnaam

    resultaten = []
    datums = []
    ndvi_arrays = []

    for datum in sorted(gekoppelde_bestanden.keys()):
        paden = gekoppelde_bestanden[datum]
        print(f"Verwerken: {datum}...")
        stats = bereken_ndvi_statistieken(paden["red"], paden["nir"])

        resultaten.append({
            "datum": datum,
            "gemiddelde_ndvi": round(stats["gemiddelde"], 4),
            "min_ndvi": round(stats["min"], 4),
            "max_ndvi": round(stats["max"], 4),
        })

        datums.append(datum)
        ndvi_arrays.append(stats["ndvi_array"])

    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["datum", "gemiddelde_ndvi", "min_ndvi", "max_ndvi"])
        writer.writeheader()
        writer.writerows(resultaten)

    print(f"\nKlaar! {len(resultaten)} datums weggeschreven naar {output_csv}")

    toon_alle_ndvi_kaarten(datums, ndvi_arrays, veldnaam, jaar, map_output)


if __name__ == "__main__":
    main()
