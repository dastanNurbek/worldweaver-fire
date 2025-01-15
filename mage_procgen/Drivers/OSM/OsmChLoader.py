import os

import geopandas as g
import pandas as p
from PIL import Image
import numpy as np
import math

from mage_procgen.Utils.Utils import GeoWindow, CRS_ch
from mage_procgen.Utils.Utils import TerrainData, TerrainDataList

from mage_procgen.Drivers.OSM.Utils import SwissAlti

from mage_procgen.Drivers.OSM.OsmLoader import OsmLoader

import requests
import overpass
import json

import mage_procgen.Utils.DataFiles as df

from mage_procgen.Drivers.OSM.Utils import OSM


class OsmChLoader(OsmLoader):
    def __init__(self, base_folder: str, project_folder: str):
        super().__init__(base_folder, project_folder)
        self.internal_crs = CRS_ch

    def load_town_shape(self, town_name: str):

        api = overpass.API()

        query = OSM.get_town_request_ch(town_name)

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

    def load_terrain_data(
        self, input_folder: str, geo_window: GeoWindow
    ) -> TerrainDataList:
        bbox_lv95 = geo_window.bounds

        # Need to round out the terrain box to the nearest km in order to fetch the correct slabs
        bbox_lv95_rounded = (
            math.floor(bbox_lv95[0] / 1000) * 1000,
            math.floor(bbox_lv95[1] / 1000) * 1000,
            math.ceil(bbox_lv95[2] / 1000) * 1000,
            math.ceil(bbox_lv95[3] / 1000) * 1000,
        )

        terrain_resolution = 0.5
        terrain_max_slab_size = 1000
        # TODO: check this value
        no_data = -9999
        print("Loading terrain data from swissalti")

        terrain_data = []

        terrain_box_ll = (bbox_lv95_rounded[0], bbox_lv95_rounded[1])
        terrain_box_ur = (bbox_lv95_rounded[2], bbox_lv95_rounded[3])

        terrain_index = 0

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

                terrain_img = requests.get(
                    SwissAlti.get_terrain_request_url(int(x_ll), int(y_ll))
                )
                terrain_file_name = "terrain" + str(terrain_index) + ".tif"
                with open(
                    os.path.join(input_folder, terrain_file_name), "wb"
                ) as terrain_file:
                    bytes_written = terrain_file.write(terrain_img.content)

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
