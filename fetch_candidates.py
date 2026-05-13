"""
fetch_candidates.py

Generates non-overlapping geo windows within metropolitan France that:
  - Are fully inside France land boundary
  - Contain no settlement land cover (CLC classes 1-2 by default)
  - Have a projected area (CRS 2154) in [6.55, 7.00] km² after round-trip
    through CRS 4326 (matching what worldweaver actually renders)

This script is fully independent of the rendering pipeline and can be run
without having performed any prior worldweaver render.  The France boundary
shapefile is extracted automatically from the archive bundled with worldweaver.

Required one-time download:
  CLC 2018 GeoTIFF — Copernicus Land Monitoring Service:
    https://land.copernicus.eu/pan-european/corine-land-cover/clc2018
    Recommended file: U2018_CLC2018_V2020_20u1.tif

Usage:
  python fetch_candidates.py \\
      --clc /path/to/U2018_CLC2018_V2020_20u1.tif \\
      --output ~/Data/worldweaver/france_locations.csv \\
      [--boundary /path/to/france.shp] \\
      [--extract-to /tmp/ww_shapefiles] \\
      [--count 1000] \\
      [--cell-size 2598] \\
      [--urban-codes 1,2]
"""

import argparse
import csv
import math
import os
import sys
import warnings

import geopandas as gpd
import numpy as np
import rasterio
import rasterio.mask
import rasterio.transform
from pyproj import Transformer
from shapely.geometry import box

warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_AREA_KM2 = 6.55
MAX_AREA_KM2 = 6.97  # kept below 7.00 to absorb ~0.03 km2 rounding error from 4-decimal CSV coordinates

_DEFAULT_BOUNDARY_SHP = os.path.expanduser(
    "~/Data/worldweaver/maps/ARRONDISSEMENT/ARRONDISSEMENT.shp"
)

# ---------------------------------------------------------------------------
# Area validation (same logic as render_france.py)
# ---------------------------------------------------------------------------

_to_2154 = Transformer.from_crs(4326, 2154, always_xy=True)
_to_4326 = Transformer.from_crs(2154, 4326, always_xy=True)


def projected_area_km2(x_min_4326, y_min_4326, x_max_4326, y_max_4326):
    corners = [
        (x_min_4326, y_min_4326), (x_min_4326, y_max_4326),
        (x_max_4326, y_min_4326), (x_max_4326, y_max_4326),
    ]
    xs, ys = zip(*[_to_2154.transform(lon, lat) for lon, lat in corners])
    return (max(xs) - min(xs)) * (max(ys) - min(ys)) / 1e6


def cell_to_4326(x_min, y_min, x_max, y_max):
    """Convert a CRS-2154 cell box to CRS-4326 coordinates."""
    corners_2154 = [(x_min, y_min), (x_min, y_max), (x_max, y_min), (x_max, y_max)]
    lons, lats = zip(*[_to_4326.transform(x, y) for x, y in corners_2154])
    return min(lons), min(lats), max(lons), max(lats)

# ---------------------------------------------------------------------------
# CLC helpers
# ---------------------------------------------------------------------------

def load_clc_mask(clc_path, france_bounds_3035, urban_codes):
    """
    Read the CLC raster clipped to France, return a boolean numpy array
    (True = urban/settlement) and the affine transform for pixel lookups.
    """
    with rasterio.open(clc_path) as src:
        # Transform France bounds from CRS 3035 if CLC is in EPSG:3035,
        # or handle any CRS by reprojecting bounds.
        clc_crs = src.crs
        to_clc = Transformer.from_crs("EPSG:3035", clc_crs, always_xy=True)

        x_min, y_min, x_max, y_max = france_bounds_3035
        corners = [(x_min, y_min), (x_min, y_max), (x_max, y_min), (x_max, y_max)]
        xs, ys = zip(*[to_clc.transform(x, y) for x, y in corners])
        win = rasterio.windows.from_bounds(
            min(xs), min(ys), max(xs), max(ys), transform=src.transform
        )
        win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))

        data = src.read(1, window=win)
        transform = src.window_transform(win)

    urban_mask = np.isin(data, list(urban_codes))
    return urban_mask, transform, clc_crs


def has_urban_pixels(urban_mask, transform, cell_x_min, cell_y_min, cell_x_max, cell_y_max, crs_cell, clc_crs):
    """Return True if any pixel in the cell window is urban."""
    to_clc = Transformer.from_crs(crs_cell, clc_crs, always_xy=True)
    corners = [
        (cell_x_min, cell_y_min), (cell_x_min, cell_y_max),
        (cell_x_max, cell_y_min), (cell_x_max, cell_y_max),
    ]
    xs, ys = zip(*[to_clc.transform(x, y) for x, y in corners])

    col_min, row_max = ~transform * (min(xs), min(ys))
    col_max, row_min = ~transform * (max(xs), max(ys))

    col_min = max(0, int(math.floor(col_min)))
    col_max = min(urban_mask.shape[1], int(math.ceil(col_max)))
    row_min = max(0, int(math.floor(row_min)))
    row_max = min(urban_mask.shape[0], int(math.ceil(row_max)))

    if row_min >= row_max or col_min >= col_max:
        return False

    return bool(urban_mask[row_min:row_max, col_min:col_max].any())

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Fetch candidate geo windows for WorldWeaver")
    parser.add_argument("--clc",      required=True,  help="CLC 2018 GeoTIFF path")
    parser.add_argument("--output",   required=True,  help="Output CSV path")
    parser.add_argument("--boundary", default=_DEFAULT_BOUNDARY_SHP,
                        help="France boundary shapefile (default: ~/Data/worldweaver/maps/ARRONDISSEMENT/ARRONDISSEMENT.shp)")
    parser.add_argument("--count",    type=int, default=None,
                        help="Stop after N valid windows (default: all)")
    parser.add_argument("--cell-size", type=int, default=2598,
                        help="Cell side length in metres in CRS 2154 (default: 2598 → 6.75 km²)")
    parser.add_argument("--urban-codes", default="1",
                        help="Comma-separated CLC raster values to exclude (default: 1 = continuous urban fabric only)")
    args, _ = parser.parse_known_args(sys.argv[1:])
    return args

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    urban_codes = set(int(c) for c in args.urban_codes.split(","))
    cell_size = args.cell_size

    # -- France boundary -------------------------------------------------------
    if not os.path.isfile(args.boundary):
        raise FileNotFoundError(
            f"France boundary shapefile not found: {args.boundary}\n"
            "Provide it with --boundary or run one worldweaver render first to extract it."
        )
    print("Loading France boundary...")
    gdf = gpd.read_file(args.boundary)
    france = gdf.dissolve().to_crs(2154)
    france_poly = france.geometry.iloc[0]
    x_min_fr, y_min_fr, x_max_fr, y_max_fr = france_poly.bounds

    # For CLC clipping we need France bounds in EPSG:3035
    to_3035 = Transformer.from_crs(2154, 3035, always_xy=True)
    corners_2154 = [
        (x_min_fr, y_min_fr), (x_min_fr, y_max_fr),
        (x_max_fr, y_min_fr), (x_max_fr, y_max_fr),
    ]
    xs_3035, ys_3035 = zip(*[to_3035.transform(x, y) for x, y in corners_2154])
    france_bounds_3035 = (min(xs_3035), min(ys_3035), max(xs_3035), max(ys_3035))

    # -- CLC settlement mask ---------------------------------------------------
    print(f"Loading CLC raster (urban codes: {sorted(urban_codes)})...")
    urban_mask, clc_transform, clc_crs = load_clc_mask(
        args.clc, france_bounds_3035, urban_codes
    )
    print(f"  CLC tile loaded: {urban_mask.shape[1]} x {urban_mask.shape[0]} px, "
          f"{urban_mask.sum():,} urban pixels")

    # -- Systematic grid in CRS 2154 -------------------------------------------
    xs = np.arange(x_min_fr, x_max_fr, cell_size)
    ys = np.arange(y_min_fr, y_max_fr, cell_size)
    total_cells = len(xs) * len(ys)
    print(f"Grid: {len(xs)} cols x {len(ys)} rows = {total_cells:,} cells")

    # Build GeoDataFrame of all cells and batch-filter by France containment.
    print("Filtering cells inside France...")
    cell_geoms = [
        box(x, y, x + cell_size, y + cell_size)
        for x in xs for y in ys
    ]
    cell_ids = [
        (xi, yi)
        for xi in range(len(xs))
        for yi in range(len(ys))
    ]
    cells_gdf = gpd.GeoDataFrame(
        {"xi": [c[0] for c in cell_ids], "yi": [c[1] for c in cell_ids]},
        geometry=cell_geoms,
        crs=2154,
    )
    inside = gpd.sjoin(cells_gdf, france[["geometry"]], predicate="within", how="inner")
    print(f"  {len(inside):,} cells inside France")

    # -- Per-cell filters ------------------------------------------------------
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    found = 0
    skipped_area = 0
    skipped_urban = 0

    with open(args.output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "x_min", "y_min", "x_max", "y_max"])

        for _, row in inside.iterrows():
            if args.count and found >= args.count:
                break

            xi, yi = int(row["xi"]), int(row["yi"])
            cx = xs[xi]
            cy = ys[yi]

            # Convert to 4326 for CSV and area validation
            x_min_4326, y_min_4326, x_max_4326, y_max_4326 = cell_to_4326(
                cx, cy, cx + cell_size, cy + cell_size
            )

            area = projected_area_km2(x_min_4326, y_min_4326, x_max_4326, y_max_4326)
            if not (MIN_AREA_KM2 <= area <= MAX_AREA_KM2):
                skipped_area += 1
                continue

            if has_urban_pixels(
                urban_mask, clc_transform,
                cx, cy, cx + cell_size, cy + cell_size,
                crs_cell=2154, clc_crs=clc_crs,
            ):
                skipped_urban += 1
                continue

            name = f"fr_{xi:04d}_{yi:04d}"
            writer.writerow([
                name,
                round(x_min_4326, 4), round(y_min_4326, 4),
                round(x_max_4326, 4), round(y_max_4326, 4),
            ])
            found += 1

            if found % 500 == 0:
                print(f"  {found:,} valid windows found...")

    print(f"\nDone.")
    print(f"  Valid windows : {found:,}")
    print(f"  Skipped (area): {skipped_area:,}")
    print(f"  Skipped (urban): {skipped_urban:,}")
    print(f"  Output: {args.output}")


main()
