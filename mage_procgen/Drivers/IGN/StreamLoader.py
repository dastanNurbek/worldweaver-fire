import os
import io
import math
import requests

import geopandas as g
import pandas as p
import numpy as np

from owslib.wms import WebMapService
from owslib.wfs import WebFeatureService

from PIL import Image

from mage_procgen.Drivers.IGN.Loader import Loader
from mage_procgen.Drivers.IGN.Utils import GeoData
from mage_procgen.Drivers.IGN.Utils import WFS_FR
from mage_procgen.Drivers.IGN.DataFrames import (
    BuildingDataFrame,
    RoadDataFrame,
    ZoneInterestDataFrame,
    WaterDataFrame,
    DefaultDataFrame,
    SportDataFrame,
    LandUseDataFrame,
    PlotDataFrame,
)

from mage_procgen.Parser.ShapeFileParser import ShapeFileParser
from mage_procgen.Parser.WFSParser import WFSParser

from mage_procgen.Utils.Logging import logger
from mage_procgen.Utils.Utils import GeoWindow, CRS_fr, CRS_degrees
from mage_procgen.Utils.Utils import TerrainData
from mage_procgen.Utils.RenderingDataFrames import (
    RenderingBuildingDataFrame,
)
import mage_procgen.Utils.DataFiles as df


class StreamLoader(Loader):
    def load(self, geo_window: GeoWindow) -> GeoData:

        bbox = geo_window.bounds

        # TODO: check if this one is necessary because the window should already be in lambert93
        if geo_window.crs != CRS_fr:
            logger.warn(f"IGN StreamLoader: Provided window was not in CRS {CRS_fr}")
        geo_window_lamb93 = geo_window.to_crs(CRS_fr)
        bbox_lamb93 = geo_window_lamb93.bounds

        geo_window_wgs84 = geo_window.to_crs(CRS_degrees)
        bbox_wgs84 = geo_window_wgs84.bounds

        # The box coordinates are the coordinates of the center pixels of the rasters,
        # which are (.5,.5) meters away from the envelope of the raster.
        # This bbox_lamb93_rounded holds the min and max coords of the envelope we need to query
        bbox_lamb93_rounded = (
            math.floor(bbox_lamb93[0]) - 0.5,
            math.floor(bbox_lamb93[1]) - 0.5,
            math.ceil(bbox_lamb93[2]) + 0.5,
            math.ceil(bbox_lamb93[3]) + 0.5,
        )

        # Requesting terrain at .5m because there are weird artifacts when you do it at 1m
        terrain_resolution = 0.5
        # Need to impose a limit on the size of slabs of terrain requested because of the webservices limits,
        # so we fix a kind of arbitrary 1km limit
        terrain_max_slab_size = 1000
        # Arbitrary value
        no_data = -9999
        logger.info("Loading data from stream")

        input_folder = os.path.join(self.project_folder, df.input_data_folder)

        if not os.path.isdir(input_folder):
            os.makedirs(input_folder, exist_ok=True)

        oceans_data = None
        terrain_data = []

        load_oceans = False

        wms = WebMapService(WFS_FR.wms_alti_url, version=WFS_FR.wms_alti_version)

        terrain_box_ll = (bbox_lamb93_rounded[0], bbox_lamb93_rounded[1])
        terrain_box_ur = (bbox_lamb93_rounded[2], bbox_lamb93_rounded[3])

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

                img_size = (
                    int((current_box_ur[0] - current_box_ll[0]) / terrain_resolution),
                    int((current_box_ur[1] - current_box_ll[1]) / terrain_resolution),
                )

                terrain_img = wms.getmap(
                    layers=[WFS_FR.rge_key_name],
                    styles=["normal"],
                    srs="EPSG:" + str(CRS_fr),
                    bbox=current_box,
                    size=img_size,
                    format="image/geotiff",
                )

                terrain_image = Image.open(io.BytesIO(terrain_img.read()))

                terrain_im_array = np.array(terrain_image)
                # Flipping terrain Y axis to ease up use.
                terrain_im_array = np.flip(terrain_im_array, axis=0)
                terrain_df = p.DataFrame(terrain_im_array)

                terrain_base_map = ""
                if self.use_sat_img:
                    try:
                        terrain_base_map = self.load_texture(current_box)
                    except Exception as e:
                        logger.exception(
                            "Couldn't load texture image of terrain slab.",
                            exc_info=e,
                        )

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
                        base_map_file=terrain_base_map,
                        data=terrain_df,
                    )
                )

                terrain_index += 1

        logger.info("Terrain done")

        wfs = WebFeatureService(url=WFS_FR.wfs_url, version=WFS_FR.wfs_version)

        building_data = WFSParser.load(
            wfs=wfs,
            key=WFS_FR.buildings_key_name,
            bbox=bbox_wgs84,
            to_crs=geo_window.crs,
            required_columns=BuildingDataFrame.WFS.get_columns(),
        )

        forest_data = WFSParser.load(
            wfs=wfs,
            key=WFS_FR.forests_key_name,
            bbox=bbox_wgs84,
            to_crs=geo_window.crs,
            required_columns=DefaultDataFrame.get_columns(),
        )

        road_data = WFSParser.load(
            wfs=wfs,
            key=WFS_FR.road_key_name,
            bbox=bbox_wgs84,
            to_crs=geo_window.crs,
            required_columns=RoadDataFrame.WFS.get_columns(),
        )

        water_data = WFSParser.load(
            wfs=wfs,
            key=WFS_FR.water_key_name,
            bbox=bbox_wgs84,
            to_crs=geo_window.crs,
            required_columns=WaterDataFrame.WFS.get_columns(),
        )

        residential_data = WFSParser.load(
            wfs=wfs,
            key=WFS_FR.residential_zone_key_name,
            bbox=bbox_wgs84,
            to_crs=geo_window.crs,
            required_columns=DefaultDataFrame.get_columns(),
        )

        interest_zone_data = WFSParser.load(
            wfs=wfs,
            key=WFS_FR.activity_zone_key_name,
            bbox=bbox_wgs84,
            to_crs=geo_window.crs,
            required_columns=ZoneInterestDataFrame.WFS.get_columns(),
        )

        departements_data = WFSParser.load(
            wfs=wfs,
            key=WFS_FR.departement_key_name,
            bbox=bbox_wgs84,
            to_crs=geo_window.crs,
            required_columns=DefaultDataFrame.get_columns(),
        )

        shore_data = WFSParser.load(
            wfs=wfs,
            key=WFS_FR.shore_key_name,
            bbox=bbox_wgs84,
            to_crs=geo_window.crs,
            required_columns=DefaultDataFrame.get_columns(),
        )

        sport_data = WFSParser.load(
            wfs=wfs,
            key=WFS_FR.sport_key_name,
            bbox=bbox_wgs84,
            to_crs=geo_window.crs,
            required_columns=SportDataFrame.WFS.get_columns(),
        )

        landuse_data = WFSParser.load(
            wfs=wfs,
            key=WFS_FR.landuse_key_name,
            bbox=bbox_wgs84,
            to_crs=geo_window.crs,
            required_columns=LandUseDataFrame.WFS.get_columns(),
        )

        plot_data = WFSParser.load(
            wfs=wfs,
            key=WFS_FR.plot_key_name,
            bbox=bbox_wgs84,
            to_crs=geo_window.crs,
            required_columns=PlotDataFrame.WFS.get_columns(),
        )

        logger.info("Features done")

        if len(shore_data) > 0:
            load_oceans = True

        if load_oceans:
            # Ocean file is in degrees so we have to convert the box back to this csr
            ocean_box = geo_window.dataframe.to_crs(CRS_degrees).geometry[0].bounds
            oceans_data = ShapeFileParser.load(
                os.path.join(self.base_folder, df.ocean_file),
                ocean_box,
                CRS_fr,
                force_2d=True,
            )
        else:
            oceans_data = g.GeoDataFrame(
                columns=["id", "geometry"], geometry="geometry"
            )

        # Treat the data to homogenise column names between different data sources
        building_data_dict = {
            BuildingDataFrame.ID: building_data[BuildingDataFrame.WFS.ID],
            BuildingDataFrame.nature: building_data[BuildingDataFrame.WFS.nature],
            BuildingDataFrame.usage_1: building_data[BuildingDataFrame.WFS.usage_1],
            BuildingDataFrame.usage_2: building_data[BuildingDataFrame.WFS.usage_2],
            BuildingDataFrame.number_housings: building_data[
                BuildingDataFrame.WFS.number_housings
            ],
            RenderingBuildingDataFrame.number_floors: building_data[
                BuildingDataFrame.WFS.number_floors
            ],
            RenderingBuildingDataFrame.height: building_data[
                BuildingDataFrame.WFS.height
            ],
            BuildingDataFrame.geometry: building_data[BuildingDataFrame.WFS.geometry],
        }
        building_data = g.GeoDataFrame(building_data_dict)

        road_data_dict = {
            RoadDataFrame.ID: road_data[RoadDataFrame.WFS.ID],
            RoadDataFrame.nature: road_data[RoadDataFrame.WFS.nature],
            RoadDataFrame.importance: road_data[RoadDataFrame.WFS.importance],
            RoadDataFrame.number_lanes: road_data[RoadDataFrame.WFS.number_lanes],
            RoadDataFrame.direction: road_data[RoadDataFrame.WFS.direction],
            RoadDataFrame.position_rel_to_ground: road_data[
                RoadDataFrame.WFS.position_rel_to_ground
            ],
            RoadDataFrame.width: road_data[RoadDataFrame.WFS.width],
            RoadDataFrame.urban: road_data[RoadDataFrame.WFS.urban],
            RoadDataFrame.geometry: road_data[RoadDataFrame.WFS.geometry],
        }
        road_data = g.GeoDataFrame(road_data_dict)

        interest_zone_data_dict = {
            ZoneInterestDataFrame.ID: interest_zone_data[ZoneInterestDataFrame.WFS.ID],
            ZoneInterestDataFrame.detail_nature: interest_zone_data[
                ZoneInterestDataFrame.WFS.detail_nature
            ],
            ZoneInterestDataFrame.geometry: interest_zone_data[
                ZoneInterestDataFrame.WFS.geometry
            ],
        }
        interest_zone_data = g.GeoDataFrame(interest_zone_data_dict)

        water_data_dict = {
            WaterDataFrame.ID: water_data[WaterDataFrame.WFS.ID],
            WaterDataFrame.nature: water_data[WaterDataFrame.WFS.nature],
            WaterDataFrame.geometry: water_data[WaterDataFrame.WFS.geometry],
        }
        water_data = g.GeoDataFrame(water_data_dict)

        sport_data_dict = {
            SportDataFrame.ID: sport_data[SportDataFrame.WFS.ID],
            SportDataFrame.nature: sport_data[SportDataFrame.WFS.nature],
            SportDataFrame.detail_nature: sport_data[SportDataFrame.WFS.detail_nature],
            SportDataFrame.geometry: sport_data[SportDataFrame.WFS.geometry],
        }
        sport_data = g.GeoDataFrame(sport_data_dict)

        landuse_data_dict = {
            LandUseDataFrame.ID: landuse_data[LandUseDataFrame.WFS.ID],
            LandUseDataFrame.nature: landuse_data[LandUseDataFrame.WFS.nature],
            LandUseDataFrame.geometry: landuse_data[LandUseDataFrame.WFS.geometry],
        }
        landuse_data = g.GeoDataFrame(landuse_data_dict)

        plot_data_dict = {
            PlotDataFrame.ID: plot_data[PlotDataFrame.WFS.ID],
            PlotDataFrame.culture: plot_data[PlotDataFrame.WFS.culture],
            PlotDataFrame.group: plot_data[PlotDataFrame.WFS.group],
            PlotDataFrame.geometry: plot_data[PlotDataFrame.WFS.geometry],
        }
        plot_data = g.GeoDataFrame(plot_data_dict)

        geo_data = GeoData(
            buildings=building_data,
            forests=forest_data,
            roads=road_data,
            water=water_data,
            ocean=oceans_data,
            residentials=residential_data,
            interest_zones=interest_zone_data,
            departements=departements_data,
            terrain=terrain_data,
            sport=sport_data,
            landuse=landuse_data,
            plots=plot_data,
        )

        return geo_data

    def load_town_shape(self, town_id: str) -> g.GeoDataFrame:

        town_name = town_id.split(" ")[:-1]
        departement_nbr = town_id.split(" ")[-1]

        town_request_parameters = {
            WFS_FR.town_request_name: town_name,
            WFS_FR.town_request_dpt: departement_nbr,
            WFS_FR.town_request_format: WFS_FR.town_request_geojson,
            WFS_FR.town_request_geometry: WFS_FR.town_request_contour,
        }

        town_request_response = requests.get(
            WFS_FR.town_request_url, params=town_request_parameters
        )

        town_data = town_request_response.content.decode("utf-8")

        town = g.read_file(town_data).to_crs(CRS_fr)

        if town.empty:
            raise ValueError(
                f"Query of town with identifier {town_id} returned nothing. Format should be '<name_of_town> <departement_number>'"
            )

        return town

    def load_texture(self, mesh_box: tuple[float, float, float, float]) -> str:

        bdortho_wms = WebMapService(WFS_FR.bdortho_url, version=WFS_FR.bdortho_version)

        bdortho_resolution = 0.2

        img_size = (
            int((mesh_box[2] - mesh_box[0]) / bdortho_resolution),
            int((mesh_box[3] - mesh_box[1]) / bdortho_resolution),
        )

        img = bdortho_wms.getmap(
            layers=[WFS_FR.bdortho_key_name],
            styles=["normal"],
            srs="EPSG:" + str(CRS_fr),
            bbox=mesh_box,
            size=img_size,
            format="image/geotiff",
        )

        texture_file_name = (
            f"Texture_"
            f"{int(mesh_box[0])}_"
            f"{int(mesh_box[1])}_"
            f"{int(mesh_box[2])}_"
            f"{int(mesh_box[3])}_.tif"
        )

        texture_folder = os.path.join(self.project_folder, df.texture_folder)

        if not os.path.isdir(texture_folder):
            os.makedirs(texture_folder, exist_ok=True)

        texture_full_path = os.path.join(texture_folder, texture_file_name)

        with open(texture_full_path, "wb") as out_file:
            out_file.write(img.read())

        return texture_full_path
