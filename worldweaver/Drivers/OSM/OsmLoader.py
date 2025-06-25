import os
import io
import json
import math
from io import StringIO
from contextlib import redirect_stderr

import geopandas as g
import pandas as p
import numpy as np

from PIL import Image

import overpass

from owslib.wms import WebMapService

from worldweaver.Drivers.OSM.Utils import OSM, WFS

from worldweaver.Parser.ShapeFileParser import ShapeFileParser

from worldweaver.Utils.Logging import logger
from worldweaver.Utils.Utils import GeoWindow, CRS_wgs84_m, CRS_degrees, TerrainData

import worldweaver.Utils.DataFiles as df


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

        # TODO: Replace overpass query with Nominatim query
        api = overpass.API()

        query = OSM.get_town_request(town_name)

        response = api.get(query)

        input_folder = os.path.join(self.project_folder, df.input_data_folder)

        if not os.path.isdir(input_folder):
            os.makedirs(input_folder, exist_ok=True)

        response_str = json.dumps(response, indent=2)

        town = g.read_file(response_str).to_crs(self.internal_crs).query("index==0")

        if town.empty:
            raise ValueError(
                f"Query of town with identifier {town_name} returned nothing. Identifier should be a valid Nominatim query.\nYou can check it on https://nominatim.openstreetmap.org/ui/search.html"
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

        redirected_stderr = StringIO()

        # Redirecting stderr because overpass sometimes shows very long error messages that are benign, so we log them in debug.
        with redirect_stderr(redirected_stderr):
            response = api.get(map_query)

        if len(redirected_stderr.getvalue()) > 0:
            logger.info(
                "Overpass MapQuery: Some objects were not able to be loaded. See debug log for more info."
            )
            logger.debug(redirected_stderr.getvalue())

        geo_df = g.GeoDataFrame.from_features(
            response["features"], crs=CRS_degrees
        ).to_crs(self.internal_crs)

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

        # Have to check for feature count because setting crs on a geodataframe without geometry raises an error
        if len(additional_response["features"]) > 0:
            additional_geo_df = g.GeoDataFrame.from_features(
                additional_response["features"], crs=CRS_degrees
            ).to_crs(self.internal_crs)
        else:
            additional_geo_df = g.GeoDataFrame(
                columns=geo_df.columns, geometry=OSM.geometry, crs=geo_df.crs
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

        if len(additional_response2["features"]) > 0:
            additional_geo_df2 = g.GeoDataFrame.from_features(
                additional_response2["features"], crs=CRS_degrees
            ).to_crs(self.internal_crs)
        else:
            additional_geo_df2 = g.GeoDataFrame(
                columns=geo_df.columns, geometry=OSM.geometry, crs=geo_df.crs
            )

        geo_df = p.concat(
            [geo_df, additional_geo_df, additional_geo_df2], ignore_index=True
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

        # Requesting terrain at a 1m resolution
        terrain_resolution = 1
        # Need to impose a limit on the size of slabs of terrain requested because of the webservices limits,
        # so we fix a kind of arbitrary 1km limit
        terrain_max_slab_size = 1000
        # Arbitrary value
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
