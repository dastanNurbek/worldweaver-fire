import os

import overpass
import pandas as p
import geopandas as g
from PIL import Image
import numpy as np
import math

from mage_procgen.Utils.Utils import GeoWindow, CRS_wgs84_m, CRS_degrees
from mage_procgen.Utils.Utils import TerrainData

from mage_procgen.Parser.ShapeFileParser import ShapeFileParser

import mage_procgen.Utils.DataFiles as df

from mage_procgen.Drivers.OSM.Utils import OSM, WFS

import json

from owslib.wms import WebMapService


class OsmLoader:
    def __init__(self, base_folder: str, project_folder: str):
        self.base_folder = base_folder
        self.project_folder = project_folder
        self.internal_crs = CRS_wgs84_m

    def load(self, geo_window: GeoWindow):

        input_folder = os.path.join(self.project_folder, df.input_data_folder)
        if not os.path.isdir(input_folder):
            os.makedirs(input_folder, exist_ok=True)

        terrain_data = self.load_terrain_data(input_folder, geo_window)

        geo_df = self.load_osm_data(input_folder, geo_window)

        ocean_box = geo_window.dataframe.to_crs(CRS_degrees).geometry[0].bounds
        oceans_data = ShapeFileParser.load(
            os.path.join(self.base_folder, df.ocean_file),
            ocean_box,
            self.internal_crs,
            force_2d=True,
        )

        geo_data = (geo_df, oceans_data, terrain_data)

        return geo_data

    def load_town_shape(self, town_name: str):

        api = overpass.API()

        query = OSM.get_town_request_url(town_name)

        response = api.get(query)

        input_folder = os.path.join(self.project_folder, df.input_data_folder)

        if not os.path.isdir(input_folder):
            os.makedirs(input_folder, exist_ok=True)

        response_str = json.dumps(response, indent=2)

        with open(os.path.join(input_folder, town_name + ".json"), "w") as town_file:
            bytes_written = town_file.write(response_str)

        town = g.read_file(os.path.join(input_folder, town_name + ".json")).to_crs(
            self.internal_crs
        )

        return town

    def load_texture(self, mesh_box: tuple[float, float, float, float]) -> str:

        raise NotImplementedError("Method not implemented for osm data")

    def load_osm_data(self, input_folder, geo_window):
        geo_window_wgs84 = geo_window.to_crs(CRS_degrees)
        bbox_wgs84 = geo_window_wgs84.bounds

        api = overpass.API()
        # Order for MapQuery is south, west, north, east
        map_query = overpass.MapQuery(
            bbox_wgs84[1],
            bbox_wgs84[0],
            bbox_wgs84[3],
            bbox_wgs84[2],
        )

        response = api.get(map_query)

        response_str = json.dumps(response, indent=2)

        with open(os.path.join(input_folder, "data.geojson"), "w") as data_file:
            bytes_written = data_file.write(response_str)

        geo_df = g.read_file(os.path.join(input_folder, "data.geojson")).to_crs(
            self.internal_crs
        )

        return geo_df

    def load_terrain_data(self, input_folder, geo_window):

        print("Loading terrain from SRTM")

        bbox = geo_window.bounds

        # Need to round out the terrain box to the nearest km in order to fetch the correct slabs
        bbox_rounded = (
            math.floor(bbox[0]),
            math.floor(bbox[1]),
            math.ceil(bbox[2]),
            math.ceil(bbox[3]),
        )

        terrain_resolution = 1
        terrain_max_slab_size = 1000
        # TODO: check this value
        no_data = -9999

        wms = WebMapService(WFS.srtm_url, version=WFS.srtm_version)

        terrain_box_ll = (bbox_rounded[0], bbox_rounded[1])
        terrain_box_ur = (bbox_rounded[2], bbox_rounded[3])

        terrain_index = 0
        terrain_data = []

        for x_ll in np.arange(
            terrain_box_ll[0], terrain_box_ur[0], terrain_max_slab_size
        ):
            for y_ll in np.arange(
                terrain_box_ll[1], terrain_box_ur[1], terrain_max_slab_size
            ):
                current_box_ll = (x_ll, y_ll)

                x_ur = (
                    x_ll + terrain_max_slab_size
                    if (terrain_box_ur[0] - x_ll) > terrain_max_slab_size
                    else terrain_box_ur[0]
                )
                y_ur = (
                    y_ll + terrain_max_slab_size
                    if (terrain_box_ur[1] - y_ll) > terrain_max_slab_size
                    else terrain_box_ur[1]
                )

                current_box_ur = (x_ur, y_ur)

                # Request slab
                current_box = (
                    current_box_ll[0],
                    current_box_ll[1],
                    current_box_ur[0],
                    current_box_ur[1],
                )

                img_size = (
                    int((current_box_ur[0] - current_box_ll[0]) / terrain_resolution),
                    int((current_box_ur[1] - current_box_ll[1]) / terrain_resolution),
                )

                terrain_img = wms.getmap(
                    layers=[WFS.srtm_key_name],
                    styles=["normal"],
                    srs="EPSG:" + str(self.internal_crs),
                    bbox=current_box,
                    size=img_size,
                    format="image/geotiff",
                )
                terrain_file_name = "terrain" + str(terrain_index) + ".tif"
                with open(
                    os.path.join(input_folder, terrain_file_name), "wb"
                ) as terrain_file:
                    bytes_written = terrain_file.write(terrain_img.read())

                terrain_image = Image.open(
                    os.path.join(input_folder, terrain_file_name)
                )

                terrain_im_array = np.array(terrain_image)
                terrain_df = p.DataFrame(terrain_im_array)

                terrain_data.append(
                    TerrainData(
                        current_box[0],
                        current_box[1],
                        current_box[2],
                        current_box[3],
                        terrain_resolution,
                        terrain_df.shape[1],
                        terrain_df.shape[0],
                        no_data,
                        "",
                        terrain_df,
                    )
                )

                terrain_index += 1

        return terrain_data
