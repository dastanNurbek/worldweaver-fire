import os
import array

from math import floor, ceil, exp, pow

from mathutils import *

import numpy as np

import OpenEXR
import Imath

from PIL import Image

from scipy.sparse.csgraph import dijkstra
from scipy.sparse import bsr_array
from scipy.ndimage import gaussian_filter as gf

from tqdm import tqdm

from worldweaver.Utils.Geometry import center_point
from worldweaver.Utils.Logging import logger
from worldweaver.Utils.Utils import GeoWindow
from worldweaver.Utils.Rendering import (
    setup_compositing_height_map,
    setup_compositing_semantic_map,
    export_rendered_img,
    setup_img_ortho,
)
import worldweaver.Utils.DataFiles as df


class FloodProcessor:
    @staticmethod
    def generate_height_map(
        base_folder: str,
        geo_window: GeoWindow,
        flood_cell_size: float,
    ):
        bounds = geo_window.bounds
        center = geo_window.center

        # We will only flood on the geowindow, but we also need to round up the coords
        lower_left = (bounds[0], bounds[1], 0)
        upper_right = (bounds[2], bounds[3], 0)
        centered_ll = center_point(lower_left, center)
        centered_ur = center_point(upper_right, center)
        rounded_ll = (ceil(centered_ll[0]), ceil(centered_ll[1]), 0)
        rounded_ur = (floor(centered_ur[0]), floor(centered_ur[1]), 0)

        size_x = rounded_ur[0] - rounded_ll[0]
        size_y = rounded_ur[1] - rounded_ll[1]

        setup_compositing_height_map(base_folder)

        camera_z = setup_img_ortho(size_x, size_y, flood_cell_size, (0, 0))

        export_rendered_img(
            base_folder,
            os.path.join(base_folder, df.rendering, df.temp_folder),
            df.temp_rendering_file,
        )

    @staticmethod
    def generate_semantic_map(
        base_folder: str,
        geo_window: GeoWindow,
        flood_cell_size: float,
    ):
        bounds = geo_window.bounds
        center = geo_window.center

        # We will only flood on the geowindow, but we also need to round up the coords
        lower_left = (bounds[0], bounds[1], 0)
        upper_right = (bounds[2], bounds[3], 0)
        centered_ll = center_point(lower_left, center)
        centered_ur = center_point(upper_right, center)
        rounded_ll = (ceil(centered_ll[0]), ceil(centered_ll[1]), 0)
        rounded_ur = (floor(centered_ur[0]), floor(centered_ur[1]), 0)

        size_x = rounded_ur[0] - rounded_ll[0]
        size_y = rounded_ur[1] - rounded_ll[1]

        setup_compositing_semantic_map(base_folder)

        camera_z = setup_img_ortho(size_x, size_y, flood_cell_size, (0, 0))

        export_rendered_img(
            base_folder,
            os.path.join(base_folder, df.rendering, df.temp_folder),
            df.temp_rendering_file,
        )

    @staticmethod
    def flood(
        base_folder: str,
        geo_window: GeoWindow,
        max_flood_height: float,
        flood_threshold: float,
        flood_cell_size: float,
    ):
        logger.info("Initialising flood")

        bounds = geo_window.bounds
        center = geo_window.center

        # We will only flood on the geowindow, but we also need to round up the coords
        lower_left = (bounds[0], bounds[1], 0)
        upper_right = (bounds[2], bounds[3], 0)
        centered_ll = center_point(lower_left, center)
        centered_ur = center_point(upper_right, center)
        rounded_ll = (ceil(centered_ll[0]), ceil(centered_ll[1]), 0)
        rounded_ur = (floor(centered_ur[0]), floor(centered_ur[1]), 0)

        size_x = rounded_ur[0] - rounded_ll[0]
        size_y = rounded_ur[1] - rounded_ll[1]

        camera_z = setup_img_ortho(size_x, size_y, flood_cell_size, (0, 0))

        depth_map_file = OpenEXR.InputFile(
            os.path.join(
                base_folder,
                df.rendering,
                df.temp_folder,
                df.depth_map_file_full_name,
            )
        )

        # Compute the size
        depth_map_data_window = depth_map_file.header()["dataWindow"]
        depth_map_size = (
            depth_map_data_window.max.x - depth_map_data_window.min.x + 1,
            depth_map_data_window.max.y - depth_map_data_window.min.y + 1,
        )

        # Read the three color channels as 32-bit floats
        FLOAT = Imath.PixelType(Imath.PixelType.FLOAT)

        # In Blender 3.6, EXR file had 3 channels (RGB), and in 4.1, it has only one (V).
        channel_name = "V" if "V" in depth_map_file.header()["channels"].keys() else "R"

        depth_map = np.array(
            array.array("f", depth_map_file.channel(channel_name, FLOAT))
        ).reshape(depth_map_size[1], depth_map_size[0])

        height_map = camera_z - depth_map

        source_points_file = Image.open(
            os.path.join(
                base_folder,
                df.rendering,
                df.temp_folder,
                df.semantic_map_file_full_name,
            )
        )
        source_points = np.array(source_points_file.getdata()).reshape(height_map.shape)

        # Compute for each pixel the height of the flood, if applicable
        flood_state_rows = source_points.shape[0]
        flood_state_cols = source_points.shape[1]

        # To get the coordinates of a cell's neighbors
        coord_modifiers = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ]

        sources_index = []
        rows = []
        cols = []
        data = []

        for row in range(flood_state_rows):
            for column in range(flood_state_cols):
                point_distance_index = row * flood_state_cols + column

                # If a point is a source
                if source_points[row][column]:
                    sources_index.append(point_distance_index)

                for mod in coord_modifiers:
                    comp_row = row + mod[0]
                    comp_col = column + mod[1]

                    # If the neighbor is actually inside the grid (no out of bounds)
                    if (
                        0 <= comp_row < flood_state_rows
                        and 0 <= comp_col < flood_state_cols
                    ):
                        mod_index = comp_row * flood_state_cols + comp_col
                        rows.append(point_distance_index)
                        cols.append(mod_index)

                        # Compute the cell to cell distance
                        data.append(
                            FloodProcessor.distance_function(
                                height_map[row][column], height_map[comp_row][comp_col]
                            )
                        )

        a_rows = np.array(rows)
        a_cols = np.array(cols)
        a_data = np.array(data)

        flood_graph = bsr_array(
            (a_data, (a_rows, a_cols)),
            shape=(
                flood_state_rows * flood_state_cols,
                flood_state_rows * flood_state_cols,
            ),
        )

        flood_graph_distances, predecessors, sources = dijkstra(
            flood_graph,
            indices=sources_index,
            min_only=True,
            return_predecessors=True,
        )

        flood_result = np.zeros((flood_state_rows, flood_state_cols))
        flood_state = np.zeros((flood_state_rows, flood_state_cols))

        logger.info("Calculating flood")

        for row in tqdm(range(flood_state_rows)):
            for column in range(flood_state_cols):
                point_index = row * flood_state_cols + column

                # Retrieving the source point of the current point
                point_source = sources[point_index]
                source_row = point_source // flood_state_cols
                source_column = point_source % flood_state_cols
                source_elevation = height_map[source_row][source_column]

                (is_flooded, water_height) = FloodProcessor.flood_height(
                    max_flood_height,
                    flood_threshold,
                    flood_graph_distances[point_index],
                    height_map[row][column],
                    source_elevation,
                )

                flood_state[row][column] = is_flooded

                flood_result[row][column] = water_height

        flood_result = gf(flood_result, 5)

        return (
            height_map,
            flood_result,
            flood_state,
            rounded_ll,
            rounded_ur,
            flood_cell_size,
        )

    # TODO: take buildings into account somehow
    # TODO: generally, calibrate this
    @staticmethod
    def distance_function(point_a, point_b):
        return exp(point_b - point_a)

    @staticmethod
    def flood_height(
        max_flood_height,
        flood_threshold,
        distance_to_source,
        terrain_height,
        source_height,
    ):

        water_height = terrain_height
        is_flooded = 1

        if distance_to_source > flood_threshold:
            is_flooded = 0
            return (is_flooded, 0)

        # Water height if the cell was at the same height as the source
        flood_value = max_flood_height * pow(
            (distance_to_source - flood_threshold) / flood_threshold, 2
        )

        water_height = flood_value + source_height

        if water_height < terrain_height + 1e-1:
            is_flooded = 0

        return is_flooded, water_height
