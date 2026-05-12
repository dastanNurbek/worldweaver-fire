"""
Batch renderer for France locations.

Usage:
    blender --background --python render_france.py -- \
        --config ~/Data/worldweaver/test_config.json \
        --locations ~/Data/worldweaver/france_locations.csv

Locations CSV format (header required):
    name,x_min,y_min,x_max,y_max
    beauce,1.7877,48.1885,1.8223,48.2115
    ...

Box area is validated in CRS 2154 (Lambert-93), which is what worldweaver uses
internally.  Boxes outside [6.55, 7.00] km2 are skipped and logged.
Failed renders are logged and skipped; the batch continues.
Already-completed locations are skipped on re-run.
"""

import argparse
import csv
import json
import logging
import os
import sys
import tempfile
import traceback

import bpy  # noqa: F401 — must be imported first to enable mathutils etc.

from pyproj import Transformer
from worldweaver import main as mpm

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_AREA_KM2 = 6.55
MAX_AREA_KM2 = 7.00

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_transformer = Transformer.from_crs(4326, 2154, always_xy=True)

def projected_area_km2(x_min, y_min, x_max, y_max):
    """Area of the CRS-2154 bounding box — matches what worldweaver actually renders."""
    corners = [(x_min, y_min), (x_min, y_max), (x_max, y_min), (x_max, y_max)]
    xs, ys = zip(*[_transformer.transform(lon, lat) for lon, lat in corners])
    return (max(xs) - min(xs)) * (max(ys) - min(ys)) / 1e6


def load_locations(csv_path):
    locations = []
    errors = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # start=2 accounts for header row
            try:
                name = row["name"].strip()
                x_min, y_min = float(row["x_min"]), float(row["y_min"])
                x_max, y_max = float(row["x_max"]), float(row["y_max"])
                area = projected_area_km2(x_min, y_min, x_max, y_max)
                if area < MIN_AREA_KM2:
                    errors.append((i, name, f"projected area {area:.3f} km2 < {MIN_AREA_KM2}"))
                    continue
                if area > MAX_AREA_KM2:
                    errors.append((i, name, f"projected area {area:.3f} km2 > {MAX_AREA_KM2}"))
                    continue
                locations.append((name, x_min, y_min, x_max, y_max))
            except (KeyError, ValueError) as e:
                errors.append((i, row.get("name", "?"), str(e)))
    return locations, errors


def setup_batch_logger(log_path):
    logger = logging.getLogger("batch")
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(log_path)
    fh.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s"))
    logger.addHandler(fh)
    return logger


def log(logger, level, msg, *args):
    """Log to file and print to console (stdout may be closed by worldweaver)."""
    getattr(logger, level)(msg, *args)
    try:
        print(f"{level.upper():<8} {msg % args if args else msg}", flush=True)
    except Exception:
        pass


def already_rendered(base_folder, name):
    """True if a completion marker file exists for this location name."""
    return os.path.isfile(os.path.join(base_folder, "completed", name))


def mark_completed(base_folder, name):
    completed_dir = os.path.join(base_folder, "completed")
    os.makedirs(completed_dir, exist_ok=True)
    open(os.path.join(completed_dir, name), "w").close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Batch WorldWeaver renderer")
    parser.add_argument("--config",    required=True, help="Base worldweaver config JSON")
    parser.add_argument("--locations", required=True, help="CSV file with box coordinates")
    # When called via: blender --background --python script.py -- --config ...
    # everything after '--' belongs to the script.
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    args, _ = parser.parse_known_args(argv)
    return args


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    with open(args.config) as f:
        base_cfg = json.load(f)

    base_folder = base_cfg["base_folder"]
    os.makedirs(base_folder, exist_ok=True)

    logger = setup_batch_logger(os.path.join(base_folder, "batch_render.log"))

    locations, load_errors = load_locations(args.locations)

    for lineno, name, reason in load_errors:
        log(logger, "warning", "SKIP  row %d  (%s): %s", lineno, name, reason)

    log(logger, "info", "Loaded %d valid locations, %d skipped", len(locations), len(load_errors))

    tmp_dir = tempfile.mkdtemp(prefix="worldweaver_batch_")
    ok = skipped = failed = 0

    for name, x_min, y_min, x_max, y_max in locations:
        if already_rendered(base_folder, name):
            log(logger, "info", "SKIP  %s - already completed", name)
            skipped += 1
            continue

        cfg = json.loads(json.dumps(base_cfg))
        cfg["simulation_area"]["geo_window"] = {
            "x_min": x_min, "y_min": y_min,
            "x_max": x_max, "y_max": y_max,
            "crs_from": 4326,
        }

        tmp_cfg_path = os.path.join(tmp_dir, f"config_{name}.json")
        with open(tmp_cfg_path, "w") as f:
            json.dump(cfg, f, indent=2)

        area = projected_area_km2(x_min, y_min, x_max, y_max)
        log(logger, "info", "START %s  area=%.2f km2  window=[%.4f,%.4f,%.4f,%.4f]",
            name, area, x_min, y_min, x_max, y_max)

        try:
            mpm.main(tmp_cfg_path)
            mark_completed(base_folder, name)
            log(logger, "info", "DONE  %s", name)
            ok += 1
        except Exception:
            log(logger, "error", "FAIL  %s\n%s", name, traceback.format_exc())
            failed += 1

    log(logger, "info", "Batch complete - ok=%d  skipped=%d  failed=%d", ok, skipped, failed)


main()
