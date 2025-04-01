import math
import warnings
from random import random

import geopandas as g
import pandas as p

from mage_procgen.Drivers.OSM.Utils import OSM

from mage_procgen.Utils.Logging import logger
from mage_procgen.Utils.Utils import (
    RenderingData,
    GeoWindow,
    BuildingRenderingData,
    safe_overlay,
    OverlayType,
    ZonesRenderingData,
)
from mage_procgen.Utils.RenderingDataFrames import (
    RenderingRoadDataFrame,
    RenderingBuildingDataFrame,
)


class OSMPreprocessor:
    @staticmethod
    def process(
        geo_dataframe: g.geodataframe,
        oceans_data: g.geodataframe,
        geowindow: GeoWindow,
    ) -> RenderingData:

        logger.info("Processing OSM data")

        multi_polys = geo_dataframe[geo_dataframe.geom_type == OSM.multi_polygon]
        polys = geo_dataframe[geo_dataframe.geom_type == OSM.polygon]
        all_polys = p.concat([polys, multi_polys])

        # Buildings
        churches_ind = []
        factories_ind = []
        malls_ind = []
        houses_ind = []
        buildings_ind = []
        buildings_height = {}
        buildings_levels = {}
        for ind in all_polys[OSM.tags].index:
            if OSM.building_tag in geo_dataframe[OSM.tags][ind]:

                building_tag = geo_dataframe[OSM.tags][ind][OSM.building_tag]
                if building_tag in OSM.churches_types:
                    churches_ind.append(ind)
                elif building_tag in OSM.factories_types:
                    factories_ind.append(ind)
                elif building_tag in OSM.malls_types:
                    malls_ind.append(ind)
                elif building_tag in OSM.houses_types:
                    houses_ind.append(ind)
                else:
                    buildings_ind.append(ind)

                buildings_height[ind] = math.nan
                buildings_levels[ind] = math.nan
                if OSM.height in geo_dataframe[OSM.tags][ind]:
                    height = geo_dataframe[OSM.tags][ind][OSM.height]
                    if height.isdigit():
                        buildings_height[ind] = float(height)
                if OSM.levels in geo_dataframe[OSM.tags][ind]:
                    levels = geo_dataframe[OSM.tags][ind][OSM.levels]
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
        landused_ids = []
        for ind in all_polys[OSM.tags].index:
            if all_polys[OSM.tags][ind] is not None:
                if OSM.landuse in all_polys[OSM.tags][ind]:
                    landused_ids.append(ind)

        landused = all_polys.query("index in @landused_ids")

        surfaces_ids = []
        for ind in all_polys[OSM.tags].index:
            if all_polys[OSM.tags][ind] is not None:
                if OSM.surface in all_polys[OSM.tags][ind]:
                    surfaces_ids.append(ind)

        surfaces = all_polys.query("index in @surfaces_ids")

        nature_ids = []
        for ind in all_polys[OSM.tags].index:
            if all_polys[OSM.tags][ind] is not None:
                if OSM.natural in all_polys[OSM.tags][ind]:
                    nature_ids.append(ind)

        natures = all_polys.query("index in @nature_ids")

        # Forests
        selected_forest_tags = [OSM.usage_forests_tags]
        forests_ids = []
        for ind in landused[OSM.tags].index:
            if landused[OSM.tags][ind][OSM.landuse] in selected_forest_tags:
                forests_ids.append(ind)

        forests = landused.query("index in @forests_ids")

        # Residential
        selected_residential_tags = [OSM.usage_residential_tags]
        residential_ids = []
        for ind in landused[OSM.tags].index:
            if landused[OSM.tags][ind][OSM.landuse] in selected_residential_tags:
                residential_ids.append(ind)

        residentials = landused.query("index in @residential_ids")

        # Interest zones
        selected_interest_tags = [OSM.usage_commercial_tags, OSM.usage_commercial_tags]

        interest_ids = []
        for ind in landused[OSM.tags].index:
            if landused[OSM.tags][ind][OSM.landuse] in selected_interest_tags:
                interest_ids.append(ind)

        interest_zones = landused.query("index in @interest_ids")

        # Fields
        selected_field_tags = OSM.field_landuses

        field_ids = []
        for ind in landused[OSM.tags].index:
            if landused[OSM.tags][ind][OSM.landuse] in selected_field_tags:
                field_ids.append(ind)

        fields = landused.query("index in @field_ids")
        wheatfields_ids = []
        cornfields_ids = []
        wheat_interval = [0, 0.5]
        corn_interval = [0.5, 1]
        for ind in fields[OSM.tags].index:
            if OSM.field_crop in fields[OSM.tags][ind]:
                if fields[OSM.tags][ind][OSM.field_crop] == OSM.wheat_crop:
                    wheatfields_ids.append(ind)
                elif fields[OSM.tags][ind][OSM.field_crop] == OSM.corn_crop:
                    cornfields_ids.append(ind)
                else:
                    random_nbr = random()
                    if wheat_interval[0] <= random_nbr <= wheat_interval[1]:
                        wheatfields_ids.append(ind)
                    elif corn_interval[0] <= random_nbr <= corn_interval[1]:
                        cornfields_ids.append(ind)
            else:
                random_nbr = random()
                if wheat_interval[0] <= random_nbr <= wheat_interval[1]:
                    wheatfields_ids.append(ind)
                elif corn_interval[0] <= random_nbr <= corn_interval[1]:
                    cornfields_ids.append(ind)

        wheatfields = fields.query("index in @wheatfields_ids")
        cornfields = fields.query("index in @cornfields_ids")

        # Grass
        selected_grass_tags = OSM.grass_landuses.copy()
        selected_grass_tags.extend(OSM.leisure_landuses)

        grass_ids = []
        for ind in landused[OSM.tags].index:
            if landused[OSM.tags][ind][OSM.landuse] in selected_grass_tags:
                grass_ids.append(ind)

        grass = landused.query("index in @grass_ids")

        grass_surface_ids = []
        for ind in surfaces[OSM.tags].index:
            if surfaces[OSM.tags][ind][OSM.surface] == OSM.grass_surface:
                grass_surface_ids.append(ind)

        grass_surface = surfaces.query("index in @grass_surface_ids")
        grass = safe_overlay(grass, grass_surface, OverlayType.UNION)

        # Developed
        selected_developed_tags = OSM.developed_landuses

        developed_ids = []
        for ind in landused[OSM.tags].index:
            if landused[OSM.tags][ind][OSM.landuse] in selected_developed_tags:
                developed_ids.append(ind)

        developed = landused.query("index in @developed_ids")

        tartan_ids = []
        compacted_ids = []
        asphalt_ids = []
        sand_ids = []
        for ind in surfaces[OSM.tags].index:
            if surfaces[OSM.tags][ind][OSM.surface] == OSM.tartan_surface:
                tartan_ids.append(ind)
            elif surfaces[OSM.tags][ind][OSM.surface] == OSM.compacted_surface:
                compacted_ids.append(ind)
            elif surfaces[OSM.tags][ind][OSM.surface] in OSM.asphalt_surface:
                if OSM.highway_tag not in surfaces[OSM.tags][ind]:
                    asphalt_ids.append(ind)
            elif surfaces[OSM.tags][ind][OSM.surface] in OSM.sand_surface:
                sand_ids.append(ind)

        tartan = surfaces.query("index in @tartan_ids")
        compacted = surfaces.query("index in @compacted_ids")
        asphalt = surfaces.query("index in @asphalt_ids")
        sands = surfaces.query("index in @sand_ids")
        leisure_tartan_ids = []
        for ind in all_polys[OSM.tags].index:
            if OSM.leisure in all_polys[OSM.tags][ind]:
                if all_polys[OSM.tags][ind][OSM.leisure] == OSM.playground:
                    leisure_tartan_ids.append(ind)
        leisure_tartan = all_polys.query("index in @leisure_tartan_ids")

        # TODO: find out why a warning is thrown here
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=FutureWarning)
            tartan = safe_overlay(tartan, leisure_tartan, OverlayType.UNION)
        beaches_ids = []
        sand_natures_ids = []
        for ind in natures[OSM.tags].index:
            if all_polys[OSM.tags][ind][OSM.natural] == OSM.beach:
                beaches_ids.append(ind)
            if all_polys[OSM.tags][ind][OSM.natural] == OSM.sand_surface:
                sand_natures_ids.append(ind)
        beaches = natures.query("index in @beaches_ids")
        sand_natures = natures.query("index in @sand_natures_ids")
        sands = safe_overlay(sands, beaches, OverlayType.UNION)
        sands = safe_overlay(sands, sand_natures, OverlayType.UNION)
        # Roads
        lines = geo_dataframe[geo_dataframe.geom_type == OSM.line_string]
        multi_lines = geo_dataframe[geo_dataframe.geom_type == OSM.multi_line_string]
        all_lines = p.concat([lines, multi_lines], ignore_index=True)
        highway_ids = []
        paths_ids = []
        for line_ind in all_lines.index:
            if all_lines[OSM.tags][line_ind] is not None:
                if OSM.highway_tag in all_lines[OSM.tags][line_ind]:
                    if all_lines[OSM.tags][line_ind][OSM.highway_tag] in OSM.path_tags:
                        paths_ids.append(line_ind)
                    else:
                        highway_ids.append(line_ind)

        highways = all_lines.query("index in @highway_ids")
        paths = all_lines.query("index in @paths_ids")

        road_has_sidewalk = []
        road_has_guardrails = []
        road_number_lanes = []
        road_position_rel_to_ground = []
        road_geometry = []

        for road_index in highways.index:
            road_geom = highways.geometry[road_index]
            road_tags = highways[OSM.tags][road_index]
            road_lane_nbr = 1
            if OSM.lanes in road_tags.keys():
                if road_tags[OSM.lanes].isdigit():
                    road_lane_nbr = int(road_tags[OSM.lanes])

            speed = 0
            # max_speed can either be without units (in kmh) or with unit indicated:
            # cf https://wiki.openstreetmap.org/wiki/Key:maxspeed
            # some values are not parsed and ignored
            if OSM.max_speed in road_tags.keys():
                if road_tags[OSM.max_speed].isdigit():
                    speed = int(road_tags[OSM.max_speed])
                else:
                    try:
                        speed_value = float(road_tags[OSM.max_speed].split()[0])
                        speed_unit = road_tags[OSM.max_speed].split()[1]
                        if speed_unit == OSM.mph_key:
                            speed = speed_value * OSM.mph_mult
                        elif speed_unit == OSM.knot_key:
                            speed = speed_value * OSM.knot_mult
                        elif speed_unit in OSM.kmh_keys:
                            speed = speed_value
                    except ValueError:
                        pass

            has_sidewalk = False
            has_guardrails = False
            if OSM.sidewalk in road_tags.keys():
                if road_tags[OSM.sidewalk] in OSM.has_sidewalk_list:
                    has_sidewalk = True

            if not has_sidewalk:
                if speed > 90 or road_lane_nbr >= 5:
                    has_guardrails = True

            pos_rel_to_ground = "0"
            if OSM.bridge in road_tags.keys():
                pos_rel_to_ground = "1"
            elif OSM.tunnel in road_tags.keys():
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
        water_tags = [OSM.water]
        water_ids = []
        for ind in geo_dataframe[OSM.tags].index:
            if geo_dataframe[OSM.tags][ind] is not None:
                if OSM.landuse in geo_dataframe[OSM.tags][ind]:
                    if geo_dataframe[OSM.tags][ind][OSM.landuse] in water_tags:
                        if ind not in water_ids:
                            water_ids.append(ind)
                if OSM.natural in geo_dataframe[OSM.tags][ind]:
                    if geo_dataframe[OSM.tags][ind][OSM.natural] in water_tags:
                        if ind not in water_ids:
                            water_ids.append(ind)

        waters = geo_dataframe.query("index in @water_ids")

        # Tagging is not great on waters, so we consider any body of water "flowing" unless there is a tag that explicits it
        # Also, we filter for things like fountains that should not be displayed.
        still_water_tags = ["lagoon", "lake", "oxbow", "basin", "pond", "reservoir"]
        still_water_ban_list = ["fountain"]
        still_water_ids = []
        still_water_banned_ids = []

        for ind in waters[OSM.tags].index:
            if OSM.water in waters[OSM.tags][ind]:
                if waters[OSM.tags][ind][OSM.water] in still_water_tags:
                    if OSM.amenity in waters[OSM.tags][ind]:
                        if waters[OSM.tags][ind][OSM.amenity] in still_water_ban_list:
                            still_water_banned_ids.append(ind)
                        else:
                            still_water_ids.append(ind)
                    else:
                        still_water_ids.append(ind)
            else:
                if OSM.amenity in waters[OSM.tags][ind]:
                    if waters[OSM.tags][ind][OSM.amenity] in still_water_ban_list:
                        still_water_banned_ids.append(ind)

        non_flowing_water_ids = still_water_ids.copy()
        non_flowing_water_ids.extend(still_water_banned_ids)
        still_water = waters.query("index in @still_water_ids")
        flowing_water = waters.query("index not in @non_flowing_water_ids")
        still_water = safe_overlay(still_water, oceans_data, OverlayType.DIFFERENCE)
        flowing_water = safe_overlay(flowing_water, oceans_data, OverlayType.DIFFERENCE)

        forests = safe_overlay(forests, waters, OverlayType.DIFFERENCE)

        forests = safe_overlay(forests, geowindow.dataframe, OverlayType.INTERSECTION)
        churches = safe_overlay(churches, geowindow.dataframe, OverlayType.INTERSECTION)
        malls = safe_overlay(malls, geowindow.dataframe, OverlayType.INTERSECTION)
        houses = safe_overlay(houses, geowindow.dataframe, OverlayType.INTERSECTION)
        buildings = safe_overlay(
            buildings, geowindow.dataframe, OverlayType.INTERSECTION
        )
        still_water = safe_overlay(
            still_water, geowindow.dataframe, OverlayType.INTERSECTION
        )
        flowing_water = safe_overlay(
            flowing_water, geowindow.dataframe, OverlayType.INTERSECTION
        )
        new_oceans = safe_overlay(
            oceans_data, geowindow.dataframe, OverlayType.INTERSECTION
        )
        wheatfields = safe_overlay(
            wheatfields, geowindow.dataframe, OverlayType.INTERSECTION
        )
        cornfields = safe_overlay(
            cornfields, geowindow.dataframe, OverlayType.INTERSECTION
        )
        grass = safe_overlay(grass, geowindow.dataframe, OverlayType.INTERSECTION)
        developed = safe_overlay(
            developed, geowindow.dataframe, OverlayType.INTERSECTION
        )
        tartan = safe_overlay(tartan, geowindow.dataframe, OverlayType.INTERSECTION)
        compacted = safe_overlay(
            compacted, geowindow.dataframe, OverlayType.INTERSECTION
        )
        asphalt = safe_overlay(asphalt, geowindow.dataframe, OverlayType.INTERSECTION)
        sands = safe_overlay(sands, geowindow.dataframe, OverlayType.INTERSECTION)

        buildings_data = BuildingRenderingData(
            churches=churches,
            malls=malls,
            factories=factories,
            houses=houses,
            default_buildings=buildings,
        )

        zones_data = ZonesRenderingData(
            wheatfields=wheatfields,
            cornfields=cornfields,
            grass=grass,
            developed=developed,
            tartan=tartan,
            compacted=compacted,
            asphalt=asphalt,
            sand=sands,
            paths=paths,
        )

        rendering_data = RenderingData(
            forests=forests,
            buildings=buildings_data,
            roads=road_data,
            still_water=still_water,
            flowing_water=flowing_water,
            ocean=new_oceans,
            zones=zones_data,
        )

        return rendering_data
