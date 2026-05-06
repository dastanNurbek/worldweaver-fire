from math import floor, ceil, sqrt

import numpy as np
import shapely
from shapely.ops import unary_union

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

        flammable_map = np.zeros((n_rows, n_cols), dtype=bool)

        if flammable_geoms:
            flammable_union = unary_union(flammable_geoms)

            # Cell centers: rows go top-to-bottom (y decreasing), cols left-to-right (x increasing)
            col_centers = lower_left[0] + (np.arange(n_cols) + 0.5) * fire_cell_size
            row_centers = upper_right[1] - (np.arange(n_rows) + 0.5) * fire_cell_size
            xx, yy = np.meshgrid(col_centers, row_centers)

            points_array = shapely.points(xx.ravel(), yy.ravel())
            flammable_map = shapely.within(points_array, flammable_union).reshape(n_rows, n_cols)

        # --- Map ignition points to grid indices ---
        ignition_indices = []

        if not ignition_points:
            flammable_cells = np.argwhere(flammable_map)
            if len(flammable_cells) == 0:
                logger.warning("No flammable cells in scene — cannot start fire")
                return (np.zeros((n_rows, n_cols), dtype=bool), lower_left, upper_right, fire_cell_size)
            row, col = flammable_cells[rng.integers(len(flammable_cells))]
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

        rows_list, cols_list, data_list = [], [], []

        for row in range(n_rows):
            for col in range(n_cols):
                src_idx = row * n_cols + col
                for dr, dc, is_diagonal in coord_modifiers:
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < n_rows and 0 <= nc < n_cols:
                        dst_idx = nr * n_cols + nc
                        cost = FireProcessor._spread_cost(
                            flammable_map[row][col],
                            flammable_map[nr][nc],
                            is_diagonal,
                        ) * noise_map[nr][nc]
                        rows_list.append(src_idx)
                        cols_list.append(dst_idx)
                        data_list.append(cost)

        fire_graph = bsr_array(
            (np.array(data_list), (np.array(rows_list), np.array(cols_list))),
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
