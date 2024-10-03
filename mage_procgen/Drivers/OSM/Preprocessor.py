import math

import geopandas as g
import pandas as p
from mage_procgen.Utils.Utils import RenderingData, GeoWindow
from mage_procgen.Utils.Config import Config
from mage_procgen.Drivers.OSM.Utils import OSM_CH
from mage_procgen.Utils.RenderingDataFrames import (
    RenderingRoadDataFrame,
    RenderingBuildingDataFrame,
)


class Preprocessor:
    _window_threshold = 1e-2
    _minimal_size = 20
    _building_inter_threshold = 1

    @staticmethod
    def process(
        geo_dataframe: g.geodataframe, geowindow: GeoWindow, config: Config, crs: int
    ) -> RenderingData:

        print("Processing OSM data")

        points = geo_dataframe[geo_dataframe.geom_type == OSM_CH.point]
        multi_polys = geo_dataframe[geo_dataframe.geom_type == OSM_CH.multi_polygon]
        polys = geo_dataframe[geo_dataframe.geom_type == OSM_CH.polygon]
        all_polys = p.concat([polys, multi_polys])

        # Buildings
        churches_ind = []
        factories_ind = []
        malls_ind = []
        houses_ind = []
        buildings_ind = []
        buildings_height = {}
        buildings_levels = {}
        for ind in all_polys[OSM_CH.tags].index:
            if OSM_CH.building_tag in geo_dataframe[OSM_CH.tags][ind]:

                building_tag = geo_dataframe[OSM_CH.tags][ind][OSM_CH.building_tag]
                if building_tag in OSM_CH.churches_types:
                    churches_ind.append(ind)
                elif building_tag in OSM_CH.factories_types:
                    factories_ind.append(ind)
                elif building_tag in OSM_CH.malls_types:
                    malls_ind.append(ind)
                elif building_tag in OSM_CH.houses_types:
                    houses_ind.append(ind)
                else:
                    buildings_ind.append(ind)

                buildings_height[ind] = math.nan
                buildings_levels[ind] = math.nan
                if OSM_CH.height in geo_dataframe[OSM_CH.tags][ind]:
                    height = geo_dataframe[OSM_CH.tags][ind][OSM_CH.height]
                    if height.isdigit():
                        buildings_height[ind] = float(height)
                if OSM_CH.levels in geo_dataframe[OSM_CH.tags][ind]:
                    levels = geo_dataframe[OSM_CH.tags][ind][OSM_CH.levels]
                    if levels.isdigit():
                        buildings_levels[ind] = int(levels)

        all_buildings_ind = []
        all_buildings_ind.extend(churches_ind)
        all_buildings_ind.extend(factories_ind)
        all_buildings_ind.extend(malls_ind)
        all_buildings_ind.extend(houses_ind)
        all_buildings_ind.extend(buildings_ind)
        all_buildings = geo_dataframe.query("index in @all_buildings_ind")
        buildings_height_s = p.Series(buildings_height)
        buildings_levels_s = p.Series(buildings_levels)
        all_buildings = all_buildings.assign(
            height=buildings_height_s, Nb_floors=buildings_levels_s
        )

        all_building_data_dict = {
            RenderingBuildingDataFrame.height: all_buildings[
                RenderingBuildingDataFrame.height
            ],
            RenderingBuildingDataFrame.number_floors: all_buildings[
                RenderingBuildingDataFrame.number_floors
            ],
            RenderingBuildingDataFrame.geometry: all_buildings[
                RenderingBuildingDataFrame.geometry
            ],
        }
        all_building_data = g.GeoDataFrame(all_building_data_dict)

        churches = all_building_data.query("index in @churches_ind")
        factories = all_building_data.query("index in @factories_ind")
        malls = all_building_data.query("index in @malls_ind")
        houses = all_building_data.query("index in @houses_ind")
        buildings = all_building_data.query("index in @buildings_ind")

        # Landmasses
        masses_indexes = []
        for ind in geo_dataframe[OSM_CH.tags].index:
            if geo_dataframe[OSM_CH.tags][ind] is not None:
                if OSM_CH.landuse in geo_dataframe[OSM_CH.tags][ind]:
                    masses_indexes.append(ind)

        masses = geo_dataframe.query("index in @masses_indexes")

        # Forests
        selected_forest_tags = ["forest"]
        forests_iOSM_CH = []
        for ind in masses[OSM_CH.tags].index:
            if masses[OSM_CH.tags][ind][OSM_CH.landuse] in selected_forest_tags:
                forests_iOSM_CH.append(ind)

        forests = masses.query("index in @forests_iOSM_CH")

        # Residential
        selected_residential_tags = ["residential"]
        residential_ids = []
        for ind in masses[OSM_CH.tags].index:
            if masses[OSM_CH.tags][ind][OSM_CH.landuse] in selected_residential_tags:
                residential_ids.append(ind)

        residentials = masses.query("index in @residential_ids")

        # Interest zones
        selected_interest_tags = ["commercial", "industrial"]

        interest_ids = []
        for ind in masses[OSM_CH.tags].index:
            if masses[OSM_CH.tags][ind][OSM_CH.landuse] in selected_interest_tags:
                interest_ids.append(ind)

        interest_zones = masses.query("index in @interest_ids")

        # Roads
        lines = geo_dataframe[geo_dataframe.geom_type == OSM_CH.line_string]
        multi_lines = geo_dataframe[geo_dataframe.geom_type == OSM_CH.multi_line_string]
        all_lines = p.concat([lines, multi_lines])

        highway_ids = []
        for line_ind in all_lines.index:
            if all_lines[OSM_CH.tags][line_ind] is not None:
                for key in all_lines[OSM_CH.tags][line_ind].keys():
                    if OSM_CH.highway_tag in key:
                        highway_ids.append(line_ind)

        highways = all_lines[all_lines.index.isin(highway_ids)]

        road_has_sidewalk = []
        road_has_guardrails = []
        road_number_lanes = []
        road_position_rel_to_ground = []
        road_geometry = []

        for road_index in highways.index:
            road_geom = highways.geometry[road_index]
            road_tags = highways[OSM_CH.tags][road_index]
            road_lane_nbr = 1
            if OSM_CH.lanes in road_tags.keys():
                if road_tags[OSM_CH.lanes].isdigit():
                    road_lane_nbr = int(road_tags[OSM_CH.lanes])

            speed = 0
            # max_speed can in theory have units, but it SHOULD only be kmh in CH, so no unit need
            # will need better processing if we need to take other units into account
            if OSM_CH.max_speed in road_tags.keys():
                if road_tags[OSM_CH.max_speed].isdigit():
                    speed = int(road_tags[OSM_CH.max_speed])

            has_sidewalk = False
            has_guardrails = False
            if OSM_CH.sidewalk in road_tags.keys():
                if road_tags[OSM_CH.sidewalk] in OSM_CH.has_sidewalk_list:
                    has_sidewalk = True

            if not has_sidewalk:
                if speed > 90 or road_lane_nbr >= 5:
                    has_guardrails = True

            pos_rel_to_ground = "0"
            if OSM_CH.bridge in road_tags.keys():
                pos_rel_to_ground = "1"
            elif OSM_CH.tunnel in road_tags.keys():
                pos_rel_to_ground = "-1"

            road_has_sidewalk.append(has_sidewalk)
            road_has_guardrails.append(has_guardrails)
            road_number_lanes.append(road_lane_nbr)
            road_position_rel_to_ground.append(pos_rel_to_ground)
            road_geometry.append(road_geom)

        road_data_dict = {
            RenderingRoadDataFrame.number_lanes: road_number_lanes,
            RenderingRoadDataFrame.position_rel_to_ground: road_position_rel_to_ground,
            RenderingRoadDataFrame.has_sidewalks: road_has_sidewalk,
            RenderingRoadDataFrame.has_guardrails: road_has_guardrails,
            RenderingRoadDataFrame.geometry: road_geometry,
        }
        road_data = g.GeoDataFrame(road_data_dict)

        # Water
        water_tags = [OSM_CH.water]
        water_ids = []
        for ind in geo_dataframe[OSM_CH.tags].index:
            if geo_dataframe[OSM_CH.tags][ind] is not None:
                if OSM_CH.landuse in geo_dataframe[OSM_CH.tags][ind]:
                    if geo_dataframe[OSM_CH.tags][ind][OSM_CH.landuse] in water_tags:
                        if ind not in water_ids:
                            water_ids.append(ind)
                if OSM_CH.natural in geo_dataframe[OSM_CH.tags][ind]:
                    if geo_dataframe[OSM_CH.tags][ind][OSM_CH.natural] in water_tags:
                        if ind not in water_ids:
                            water_ids.append(ind)

        waters = geo_dataframe.query("index in @water_ids")

        flowing_water_tags = ["rapids", "river", "stream", "canal", "ditch"]
        still_water_tags = ["lagoon", "lake", "oxbow", "basin", "pond", "reservoir"]
        still_water_ban_list = ["fountain"]
        flowing_water_ids = []
        still_water_ids = []

        for ind in waters[OSM_CH.tags].index:
            if OSM_CH.water in waters[OSM_CH.tags][ind]:
                if waters[OSM_CH.tags][ind][OSM_CH.water] in flowing_water_tags:
                    if ind not in flowing_water_ids:
                        flowing_water_ids.append(ind)
            if OSM_CH.water in waters[OSM_CH.tags][ind]:
                if waters[OSM_CH.tags][ind][OSM_CH.water] in still_water_tags:
                    if ind not in flowing_water_ids:
                        if OSM_CH.amenity in waters[OSM_CH.tags][ind]:
                            if (
                                waters[OSM_CH.tags][ind][OSM_CH.amenity]
                                in still_water_ban_list
                            ):
                                still_water_ids.append(ind)
                        else:
                            still_water_ids.append(ind)

        still_water = waters.query("index in @still_water_ids")
        flowing_water = waters.query("index in @flowing_water_ids")

        # Lanes deprecated
        roads_lanes = None
        # No oceans in Switzerland
        new_oceans = None

        forests = forests.overlay(
            geowindow.dataframe, how="intersection", keep_geom_type=True
        )
        churches = churches.overlay(
            geowindow.dataframe, how="intersection", keep_geom_type=True
        )
        malls = malls.overlay(
            geowindow.dataframe, how="intersection", keep_geom_type=True
        )
        factories = factories.overlay(
            geowindow.dataframe, how="intersection", keep_geom_type=True
        )
        houses = houses.overlay(
            geowindow.dataframe, how="intersection", keep_geom_type=True
        )
        buildings = buildings.overlay(
            geowindow.dataframe, how="intersection", keep_geom_type=True
        )
        still_water = still_water.overlay(
            geowindow.dataframe, how="intersection", keep_geom_type=True
        )
        flowing_water = flowing_water.overlay(
            geowindow.dataframe, how="intersection", keep_geom_type=True
        )

        rendering_data = RenderingData(
            forests=forests,
            churches=churches,
            malls=malls,
            factories=factories,
            houses=houses,
            default_buildings=buildings,
            roads=road_data,
            lanes=roads_lanes,
            still_water=still_water,
            flowing_water=flowing_water,
            ocean=new_oceans,
        )

        return rendering_data
