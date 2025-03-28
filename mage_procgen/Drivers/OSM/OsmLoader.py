import os
import io
import json
import math

import geopandas as g
import pandas as p
import numpy as np

from PIL import Image

import overpass

from owslib.wms import WebMapService

from mage_procgen.Drivers.OSM.Utils import OSM, WFS

from mage_procgen.Parser.ShapeFileParser import ShapeFileParser

from mage_procgen.Utils.Logging import logger
from mage_procgen.Utils.Utils import GeoWindow, CRS_wgs84_m, CRS_degrees, TerrainData

import mage_procgen.Utils.DataFiles as df


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

        query = OSM.get_town_request(town_name)

        response = api.get(query)

        input_folder = os.path.join(self.project_folder, df.input_data_folder)

        if not os.path.isdir(input_folder):
            os.makedirs(input_folder, exist_ok=True)

        response_str = json.dumps(response, indent=2)

        town = g.read_file(response_str).to_crs(self.internal_crs).query("index==0")

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

        geo_df = g.read_file(response_str).to_crs(self.internal_crs)

        # Due to defaults in osm2geojson, some polygons, which are inners of multipolygons but still objects of their own,
        # are not returned by a simple mapquery. To get around this, we query them separately
        # https://github.com/mvexel/overpass-api-python-wrapper/issues/163
        # https://github.com/aspectumapp/osm2geojson/issues/46
        additional_request = OSM.get_additional_request_inners(bbox_wgs84)

        additional_response = api.get(additional_request)

        # For some reason there seem to be duplicated features in the response
        filtered_features = []
        for feature in additional_response["features"]:
            if feature not in filtered_features:
                filtered_features.append(feature)
        additional_response["features"] = filtered_features
        additional_response_str = json.dumps(additional_response, indent=2)

        additional_geo_df = g.read_file(additional_response_str).to_crs(
            self.internal_crs
        )

        # We are still missing some pieces, namely objects that include the window and contain landuse information
        additional_request2 = OSM.get_additional_request_landuses(bbox_wgs84)

        additional_response2 = api.get(additional_request2)

        # For some reason there seem to be duplicated features in the response
        filtered_features_query = []
        for feature in additional_response2["features"]:
            if feature not in filtered_features_query:
                filtered_features_query.append(feature)
        additional_response2["features"] = filtered_features_query
        additional_response_str2 = json.dumps(additional_response2, indent=2)

        additional_geo_df2 = g.read_file(additional_response_str2).to_crs(
            self.internal_crs
        )

        geo_df = g.GeoDataFrame(
            p.concat([geo_df, additional_geo_df, additional_geo_df2], ignore_index=True)
        )

        return geo_df

    def load_terrain_data(self, input_folder, geo_window):

        logger.info("Loading terrain from SRTM")

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

                terrain_image = Image.open(io.BytesIO(terrain_img.read()))

                terrain_im_array = np.array(terrain_image)
                # Flipping terrain Y axis to ease up use.
                terrain_im_array = np.flip(terrain_im_array, axis=0)
                terrain_df = p.DataFrame(terrain_im_array)

                terrain_data.append(
                    TerrainData(
                        x_min=current_box[0],
                        y_min=current_box[1],
                        x_max=current_box[2],
                        y_max=current_box[3],
                        resolution=terrain_resolution,
                        nbcol=terrain_df.shape[1],
                        nbrow=terrain_df.shape[0],
                        no_data=no_data,
                        base_map_file="",
                        data=terrain_df,
                    )
                )

                terrain_index += 1

        return terrain_data
