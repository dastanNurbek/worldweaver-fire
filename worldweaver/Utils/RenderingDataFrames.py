"""
   Schema of what the dataframes need to have so that Renderers are able to work.
   Dataframes outputed by Drivers have to follow these schemas.
"""
from dataclasses import dataclass

import geopandas as g
import pandas as p
import numpy as np

import shapely
from shapely import area, difference, intersects, contains, intersection

from worldweaver.Utils.Logging import logger
from worldweaver.Utils.Utils import safe_overlay, OverlayType


class RenderingDataFrame:
    geometry = "geometry"  # shapely geometry

    @staticmethod
    def is_valid(gdf: g.GeoDataFrame, log_messages: list[str]) -> bool:

        is_valid = True

        if RenderingDataFrame.geometry not in gdf.columns:
            log_messages.append(f"Missing column: {RenderingDataFrame.geometry}")
            is_valid = False
        else:
            if not gdf.empty:
                for entry in gdf[RenderingDataFrame.geometry]:
                    if not isinstance(entry, shapely.geometry.base.BaseGeometry):
                        log_messages.append(
                            f"Invalid geometry (should be shapely BaseGeometry): {entry}"
                        )
                        is_valid = False

        return is_valid

    @staticmethod
    def validate(dataframe: g.GeoDataFrame, dataframe_name: str):

        is_valid = True

        logs = []
        if not RenderingDataFrame.is_valid(dataframe, logs):
            is_valid = False
            logger.error(
                f"Invalid {dataframe_name}. Columns: {dataframe.columns}. Dataframe: {dataframe}"
            )
            for log in logs:
                logger.error(log)

        return is_valid


class RenderingBuildingDataFrame:

    geometry = "geometry"  # shapely Polygon or MultiPolygon
    height = "height"  # p.Float64Dtype
    number_floors = "Nb_floors"  # p.Int8Dtype
    change_status = "Change_Status"  # p.Int8Dtype

    @staticmethod
    def is_valid(gdf: g.GeoDataFrame, log_messages: list[str]) -> bool:

        is_valid = True

        if RenderingBuildingDataFrame.geometry not in gdf.columns:
            log_messages.append(
                f"Missing column: {RenderingBuildingDataFrame.geometry}"
            )
            is_valid = False
        else:
            if not gdf.empty:
                for entry in gdf[RenderingBuildingDataFrame.geometry]:
                    if not (
                        type(entry) == shapely.geometry.Polygon
                        or type(entry) == shapely.geometry.MultiPolygon
                    ):
                        log_messages.append(
                            f"Invalid geometry (should be shapely Polygon or MultiPolygon): {entry}"
                        )
                        is_valid = False

        if RenderingBuildingDataFrame.number_floors not in gdf.columns:
            log_messages.append(
                f"Missing column: {RenderingBuildingDataFrame.number_floors}"
            )
            is_valid = False
        else:
            if not gdf.empty:
                if (
                    not gdf[RenderingBuildingDataFrame.number_floors].dtype
                    == p.Int8Dtype()
                ):
                    log_messages.append(
                        f"Invalid number_floors type (should be pandas Int8Dtype): {gdf[RenderingBuildingDataFrame.number_floors].dtype}"
                    )
                    is_valid = False

        if RenderingBuildingDataFrame.height not in gdf.columns:
            log_messages.append(f"Missing column: {RenderingBuildingDataFrame.height}")
            is_valid = False
        else:
            if not gdf.empty:
                if not gdf[RenderingBuildingDataFrame.height].dtype == p.Float64Dtype():
                    log_messages.append(
                        f"Invalid height type (should be pandas Float64Dtype): {gdf[RenderingBuildingDataFrame.height].dtype}"
                    )
                    is_valid = False

        if RenderingBuildingDataFrame.change_status not in gdf.columns:
            log_messages.append(
                f"Missing column: {RenderingBuildingDataFrame.change_status}"
            )
            is_valid = False
        # TODO: find validation schema
        # else:
        #     if not gdf.empty:
        #         if (
        #             not gdf[RenderingBuildingDataFrame.change_status].dtype
        #             == p.Int8Dtype()
        #         ):
        #             log_messages.append(
        #                 f"Invalid change_status type (should be pandas Int8Dtype): {gdf[RenderingBuildingDataFrame.change_status].dtype}"
        #             )
        #             is_valid = False

        return is_valid

    @staticmethod
    def validate(dataframe: g.GeoDataFrame, dataframe_name: str):

        is_valid = True

        logs = []
        if not RenderingBuildingDataFrame.is_valid(dataframe, logs):
            is_valid = False
            logger.error(
                f"Invalid {dataframe_name}. Columns: {dataframe.columns}. Dataframe: {dataframe}"
            )
            for log in logs:
                logger.error(log)

        return is_valid


class RenderingRoadDataFrame:

    geometry = "geometry"  # shapely MultiLineString or LineString
    number_lanes = "Nb_lanes"  # np.uint8
    has_sidewalks = "has_sidewalks"  # bool
    has_guardrails = "has_guardrails"  # bool
    is_bridge = "is_bridge"  # bool
    is_tunnel = "is_tunnel"  # bool

    @staticmethod
    def is_valid(gdf: g.GeoDataFrame, log_messages: list[str]) -> bool:

        is_valid = True

        if RenderingRoadDataFrame.geometry not in gdf.columns:
            log_messages.append(f"Missing column: {RenderingRoadDataFrame.geometry}")
            is_valid = False
        else:
            if not gdf.empty:
                for entry in gdf[RenderingRoadDataFrame.geometry]:
                    if not (
                        type(entry) == shapely.geometry.LineString
                        or type(entry) == shapely.geometry.MultiLineString
                    ):
                        log_messages.append(
                            f"Invalid geometry (should be shapely LineString or MultiLineString): {entry}"
                        )
                        is_valid = False

        if RenderingRoadDataFrame.number_lanes not in gdf.columns:
            log_messages.append(
                f"Missing column: {RenderingRoadDataFrame.number_lanes}"
            )
            is_valid = False
        else:
            if not gdf.empty:
                if not gdf[RenderingRoadDataFrame.number_lanes].dtype.type == np.uint8:
                    log_messages.append(
                        f"Invalid number_lanes type (should be numpy uint8): {gdf[RenderingRoadDataFrame.number_lanes].dtype}"
                    )
                    is_valid = False

        if RenderingRoadDataFrame.has_sidewalks not in gdf.columns:
            log_messages.append(
                f"Missing column: {RenderingRoadDataFrame.has_sidewalks}"
            )
            is_valid = False
        else:
            if not gdf.empty:
                if not gdf[RenderingRoadDataFrame.has_sidewalks].dtype == bool:
                    log_messages.append(
                        f"Invalid has_sidewalks type (should be bool): {gdf[RenderingRoadDataFrame.has_sidewalks].dtype}"
                    )
                    is_valid = False

        if RenderingRoadDataFrame.has_guardrails not in gdf.columns:
            log_messages.append(
                f"Missing column: {RenderingRoadDataFrame.has_guardrails}"
            )
            return False
        else:
            if not gdf.empty:
                if not gdf[RenderingRoadDataFrame.has_guardrails].dtype == bool:
                    log_messages.append(
                        f"Invalid has_guardrails type (should be bool): {gdf[RenderingRoadDataFrame.has_guardrails].dtype}"
                    )
                    is_valid = False

        if RenderingRoadDataFrame.is_bridge not in gdf.columns:
            log_messages.append(f"Missing column: {RenderingRoadDataFrame.is_bridge}")
            is_valid = False
        else:
            if not gdf.empty:
                if not gdf[RenderingRoadDataFrame.is_bridge].dtype == bool:
                    log_messages.append(
                        f"Invalid is_bridge type (should be bool): {gdf[RenderingRoadDataFrame.is_bridge].dtype}"
                    )
                    is_valid = False

        if RenderingRoadDataFrame.is_tunnel not in gdf.columns:
            log_messages.append(f"Missing column: {RenderingRoadDataFrame.is_tunnel}")
            is_valid = False
        else:
            if not gdf.empty:
                if not gdf[RenderingRoadDataFrame.is_tunnel].dtype == bool:
                    log_messages.append(
                        f"Invalid is_tunnel type (should be bool): {gdf[RenderingRoadDataFrame.is_tunnel].dtype}"
                    )
                    is_valid = False

        return is_valid

    @staticmethod
    def validate(dataframe: g.GeoDataFrame, dataframe_name: str):

        is_valid = True

        logs = []
        if not RenderingRoadDataFrame.is_valid(dataframe, logs):
            is_valid = False
            logger.error(
                f"Invalid {dataframe_name}. Columns: {dataframe.columns}. Dataframe: {dataframe}"
            )
            for log in logs:
                logger.error(log)

        return is_valid


@dataclass
class BuildingRenderingData:
    churches: g.GeoDataFrame
    malls: g.GeoDataFrame
    factories: g.GeoDataFrame
    houses: g.GeoDataFrame
    default_buildings: g.GeoDataFrame


class ZonesRenderingData:
    def __init__(
        self,
        wheatfields: g.GeoDataFrame,
        cornfields: g.GeoDataFrame,
        grass: g.GeoDataFrame,
        developed: g.GeoDataFrame,
        tartan: g.GeoDataFrame,
        compacted: g.GeoDataFrame,
        asphalt: g.GeoDataFrame,
        sand: g.GeoDataFrame,
        paths: g.GeoDataFrame,
    ):
        list_zones = [
            wheatfields,
            cornfields,
            grass,
            developed,
            tartan,
            compacted,
            asphalt,
            sand,
        ]
        for zone_a_ind in range(len(list_zones)):
            zone_a = list_zones[zone_a_ind]
            for zone_b_ind in range(zone_a_ind + 1, len(list_zones)):
                if zone_a_ind == 0 and zone_b_ind == 1:
                    continue
                zone_b = list_zones[zone_b_ind]
                # If either zone in empty, no point in comparing anything
                if zone_a.empty or zone_b.empty:
                    continue
                zone_inter = safe_overlay(zone_a, zone_b, OverlayType.INTERSECTION)
                if not zone_inter.empty:
                    new_geom_a = []
                    for geom_a in zone_a.geometry:
                        new_geom_b = []
                        for geom_b in zone_b.geometry:
                            if intersects(geom_a, geom_b):
                                if contains(geom_a, geom_b):
                                    geom_a = difference(geom_a, geom_b)
                                elif contains(geom_b, geom_a):
                                    geom_b = difference(geom_b, geom_a)
                                elif area(geom_a) <= area(geom_b):
                                    geom_b = difference(geom_b, geom_a)
                                else:
                                    geom_a = difference(geom_a, geom_b)
                            new_geom_b.append(geom_b)
                        new_geom_a.append(geom_a)
                        zone_b = zone_b.set_geometry(new_geom_b)
                        list_zones[zone_b_ind] = zone_b
                    zone_a = zone_a.set_geometry(new_geom_a)
                    list_zones[zone_a_ind] = zone_a

        self.wheatfields = list_zones[0]
        self.cornfields = list_zones[1]
        self.grass = list_zones[2]
        self.developed = list_zones[3]
        self.tartan = list_zones[4]
        self.compacted = list_zones[5]
        self.asphalt = list_zones[6]
        self.sand = list_zones[7]
        self.paths = paths


class RenderingData:
    def __init__(
        self,
        forests: g.GeoDataFrame,
        buildings: BuildingRenderingData,
        roads: g.GeoDataFrame,
        still_water: g.GeoDataFrame,
        flowing_water: g.GeoDataFrame,
        ocean: g.GeoDataFrame,
        zones: ZonesRenderingData,
    ):

        self.forests = forests
        self.buildings = buildings
        self.roads = roads
        self.still_water = still_water
        self.flowing_water = flowing_water
        self.ocean = ocean
        self.zones = zones

        self.validate()

    def validate(self):

        is_valid = True

        is_valid &= RenderingDataFrame.validate(self.forests, "Forest")
        is_valid &= RenderingBuildingDataFrame.validate(
            self.buildings.churches, "Church"
        )
        is_valid &= RenderingBuildingDataFrame.validate(self.buildings.malls, "Mall")
        is_valid &= RenderingBuildingDataFrame.validate(
            self.buildings.factories, "Factory"
        )
        is_valid &= RenderingBuildingDataFrame.validate(self.buildings.houses, "House")
        is_valid &= RenderingBuildingDataFrame.validate(
            self.buildings.default_buildings,
            "Default Building",
        )
        is_valid &= RenderingRoadDataFrame.validate(self.roads, "Road")
        is_valid &= RenderingDataFrame.validate(self.still_water, "Still Water")
        is_valid &= RenderingDataFrame.validate(self.flowing_water, "Flowing Water")
        is_valid &= RenderingDataFrame.validate(self.ocean, "Ocean")
        is_valid &= RenderingDataFrame.validate(self.zones.wheatfields, "Wheat Field")
        is_valid &= RenderingDataFrame.validate(self.zones.cornfields, "Corn Field")
        is_valid &= RenderingDataFrame.validate(self.zones.grass, "Grass")
        is_valid &= RenderingDataFrame.validate(self.zones.developed, "Developed")
        is_valid &= RenderingDataFrame.validate(self.zones.tartan, "Tartan")
        is_valid &= RenderingDataFrame.validate(self.zones.compacted, "Compacted")
        is_valid &= RenderingDataFrame.validate(self.zones.asphalt, "Asphalt")
        is_valid &= RenderingDataFrame.validate(self.zones.sand, "Sand")
        is_valid &= RenderingDataFrame.validate(self.zones.paths, "Path")

        if not is_valid:
            raise ValueError("Invalid RenderingData")
