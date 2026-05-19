from math import floor, ceil, sqrt

import numpy as np
import shapely
from shapely.ops import unary_union

from rasterio.features import rasterize as rio_rasterize
from rasterio.transform import from_bounds

from scipy.sparse.csgraph import dijkstra
from scipy.sparse import bsr_array

import geopandas as g

from worldweaver.Utils.Logging import logger
from worldweaver.Utils.Utils import GeoWindow


class FireProcessor:

    @staticmethod
    def burn(
        geo_window: GeoWindow,
        forests: g.GeoDataFrame,
        wheatfields: g.GeoDataFrame,
        cornfields: g.GeoDataFrame,
        grass: g.GeoDataFrame,
        paths: g.GeoDataFrame,
        ignition_points: list[tuple[float, float]],
        fire_cell_size: float,
        fire_threshold: float,
        seed: int | None = None,
    ):
        logger.info("Initialising fire spread")

        rng = np.random.default_rng(seed if seed is not None else 0)
        bounds = geo_window.bounds
        lower_left = (ceil(bounds[0]), ceil(bounds[1]))
        upper_right = (floor(bounds[2]), floor(bounds[3]))

        n_cols = int((upper_right[0] - lower_left[0]) / fire_cell_size)
        n_rows = int((upper_right[1] - lower_left[1]) / fire_cell_size)

        # --- Rasterize flammable zones into a boolean grid ---
        logger.info("Rasterizing flammable zones")

        flammable_geoms = []
        for gdf in [forests, wheatfields, cornfields, grass]:
            if not gdf.empty:
                flammable_geoms.extend(gdf.geometry.tolist())

        # Transform mapping grid pixels to geographic coordinates:
        # row 0 is the northernmost strip, column 0 is the westernmost strip.
        transform = from_bounds(
            west=lower_left[0], south=lower_left[1],
            east=upper_right[0], north=upper_right[1],
            width=n_cols, height=n_rows,
        )

        flammable_map = np.zeros((n_rows, n_cols), dtype=bool)
        if flammable_geoms:
            flammable_map = rio_rasterize(
                [(geom, 1) for geom in flammable_geoms],
                out_shape=(n_rows, n_cols),
                transform=transform,
                fill=0,
                dtype=np.uint8,
            ).astype(bool)

        if not paths.empty:
            path_polys = paths.geometry.buffer(fire_cell_size).tolist()
            path_mask = rio_rasterize(
                [(geom, 1) for geom in path_polys],
                out_shape=(n_rows, n_cols),
                transform=transform,
                fill=0,
                dtype=np.uint8,
            ).astype(bool)
            blocked_path = path_mask & (rng.random(size=(n_rows, n_cols)) >= 0.5)
            flammable_map &= ~blocked_path

        # --- Map ignition points to grid indices ---
        ignition_indices = []

        if not ignition_points:
            flammable_cells = np.argwhere(flammable_map)
            if len(flammable_cells) == 0:
                logger.warning("No flammable cells in scene — cannot start fire")
                return (np.zeros((n_rows, n_cols), dtype=bool), lower_left, upper_right, fire_cell_size)
            
            candidate_cells = flammable_cells
            if not forests.empty:
                forest_union = unary_union(forests.geometry.tolist())
                fc_x = lower_left[0] + (flammable_cells[:, 1] + 0.5) * fire_cell_size
                fc_y = upper_right[1] - (flammable_cells[:, 0] + 0.5) * fire_cell_size
                in_forest = shapely.within(shapely.points(fc_x, fc_y), forest_union)
                if in_forest.any():
                    candidate_cells = flammable_cells[in_forest]

            row, col = candidate_cells[rng.integers(len(candidate_cells))]
            ignition_indices = [int(row * n_cols + col)]
            logger.info(f"Random ignition at grid cell ({row}, {col})")
        else:
            for ix, iy in ignition_points:
                col = int((ix - lower_left[0]) / fire_cell_size)
                row = int((upper_right[1] - iy) / fire_cell_size)
                col = max(0, min(n_cols - 1, col))
                row = max(0, min(n_rows - 1, row))
                if not flammable_map[row][col]:
                    logger.warning(f"Ignition point ({ix}, {iy}) is not in a flammable zone")
                ignition_indices.append(row * n_cols + col)

        # --- Build sparse directed graph ---
        # Edge cost: 1 (cardinal) or sqrt(2) (diagonal) for flammable->flammable, near-infinite otherwise
        logger.info("Building fire spread graph")

        coord_modifiers = [
            (-1, -1, True),  (-1, 0, False), (-1, 1, True),
            (0,  -1, False),                  (0,  1, False),
            (1,  -1, True),  (1,  0, False),  (1,  1, True),
        ]

        noise_map = rng.uniform(0.8, 1.2, size=(n_rows, n_cols))

        all_rows, all_cols, all_data = [], [], []

        for dr, dc, is_diagonal in coord_modifiers:
            r0, r1 = max(0, -dr), n_rows - max(0, dr)
            c0, c1 = max(0, -dc), n_cols - max(0, dc)
            src_r, src_c = np.mgrid[r0:r1, c0:c1]
            dst_flam = flammable_map[r0 + dr : r1 + dr, c0 + dc : c1 + dc]
            noise_slice = noise_map[r0 + dr : r1 + dr, c0 + dc : c1 + dc]
            base_cost = np.where(dst_flam, sqrt(2) if is_diagonal else 1.0, 1e9)
            all_rows.append((src_r * n_cols + src_c).ravel())
            all_cols.append(((src_r + dr) * n_cols + (src_c + dc)).ravel())
            all_data.append((base_cost * noise_slice).ravel())

        fire_graph = bsr_array(
            (np.concatenate(all_data), (np.concatenate(all_rows), np.concatenate(all_cols))),
            shape=(n_rows * n_cols, n_rows * n_cols),
        )

        # --- Dijkstra from all ignition points simultaneously ---
        logger.info("Running Dijkstra fire spread")
        fire_distances = dijkstra(fire_graph, indices=ignition_indices, min_only=True)

        is_burnt = (fire_distances <= fire_threshold).reshape(n_rows, n_cols)
        is_burnt &= flammable_map

        logger.info("Fire spread complete")
        return (is_burnt, lower_left, upper_right, fire_cell_size)

    @staticmethod
    def _spread_cost(src_flammable: bool, dst_flammable: bool, is_diagonal: bool) -> float:
        if not dst_flammable:
            return 1e9
        return sqrt(2) if is_diagonal else 1.0
