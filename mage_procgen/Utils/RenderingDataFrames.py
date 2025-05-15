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

from mage_procgen.Utils.Logging import logger
from mage_procgen.Utils.Utils import safe_overlay, OverlayType


class RenderingDataFrame:
    geometry = "geometry"  # shapely geometry

    @staticmethod
    def is_valid(gdf: g.GeoDataFrame) -> bool:
        if RenderingDataFrame.geometry not in gdf.columns:
            logger.error("Missing column: geometry")
            return False

        if not gdf.empty:
            for entry in gdf[RenderingDataFrame.geometry]:
                if not isinstance(entry, shapely.geometry.base.BaseGeometry):
                    logger.error("Invalid geometry:", entry)
                    return False

        return True

    @staticmethod
    def validate(gdf: g.GeoDataFrame):
        if not RenderingDataFrame.is_valid(gdf):
            raise ValueError("Invalid RenderingDataFrame:", gdf)


class RenderingBuildingDataFrame:

    geometry = "geometry"  # shapely Polygon or MultiPolygon
    height = "height"  # p.Float64Dtype
    number_floors = "Nb_floors"  # p.Int8Dtype

    @staticmethod
    def is_valid(gdf: g.GeoDataFrame) -> bool:
        if RenderingBuildingDataFrame.geometry not in gdf.columns:
            logger.error("Missing column: geometry")
            return False

        if not gdf.empty:
            for entry in gdf[RenderingBuildingDataFrame.geometry]:
                if not (
                    type(entry) == shapely.geometry.Polygon
                    or type(entry) == shapely.geometry.MultiPolygon
                ):
                    logger.error("Invalid geometry:", entry)
                    return False

        if RenderingBuildingDataFrame.number_floors not in gdf.columns:
            logger.error("Missing column: number_floors")
            return False

        if not gdf.empty:
            if not gdf[RenderingBuildingDataFrame.number_floors].dtype == p.Int8Dtype():
                logger.error(
                    "Invalid number_floors type:",
                    gdf[RenderingBuildingDataFrame.number_floors].dtype,
                )
                return False

        if RenderingBuildingDataFrame.height not in gdf.columns:
            logger.error("Missing column: height")
            return False

        if not gdf.empty:
            if not gdf[RenderingBuildingDataFrame.height].dtype == p.Float64Dtype():
                logger.error(
                    "Invalid height type:", gdf[RenderingBuildingDataFrame.height].dtype
                )
                return False

        return True

    @staticmethod
    def validate(gdf: g.GeoDataFrame):
        if not RenderingBuildingDataFrame.is_valid(gdf):
            raise ValueError("Invalid RenderingBuildingDataFrame:", gdf)


class RenderingRoadDataFrame:

    geometry = "geometry"  # shapely MultiLineString or LineString
    number_lanes = "Nb_lanes"  # np.uint8
    has_sidewalks = "has_sidewalks"  # bool
    has_guardrails = "has_guardrails"  # bool
    is_bridge = "is_bridge"  # bool
    is_tunnel = "is_tunnel"  # bool

    @staticmethod
    def is_valid(gdf: g.GeoDataFrame) -> bool:

        if RenderingRoadDataFrame.geometry not in gdf.columns:
            logger.error("Missing column: geometry")
            return False

        if not gdf.empty:
            for entry in gdf[RenderingRoadDataFrame.geometry]:
                if not (
                    type(entry) == shapely.geometry.LineString
                    or type(entry) == shapely.geometry.MultiLineString
                ):
                    logger.error("Invalid geometry:", entry)
                    return False

        if RenderingRoadDataFrame.number_lanes not in gdf.columns:
            logger.error("Missing column: number_lanes")
            return False

        if not gdf.empty:
            if not gdf[RenderingRoadDataFrame.number_lanes].dtype.type == np.uint8:
                logger.error(
                    "Invalid number_lanes type:",
                    gdf[RenderingRoadDataFrame.number_lanes].dtype,
                )
                return False

        if RenderingRoadDataFrame.has_sidewalks not in gdf.columns:
            logger.error("Missing column: has_sidewalks")
            return False

        if not gdf.empty:
            if not gdf[RenderingRoadDataFrame.has_sidewalks].dtype == bool:
                logger.error(
                    "Invalid has_sidewalks type:",
                    gdf[RenderingRoadDataFrame.has_sidewalks].dtype,
                )
                return False

        if RenderingRoadDataFrame.has_guardrails not in gdf.columns:
            logger.error("Missing column: has_guardrails")
            return False

        if not gdf.empty:
            if not gdf[RenderingRoadDataFrame.has_guardrails].dtype == bool:
                logger.error(
                    "Invalid has_guardrails type:",
                    gdf[RenderingRoadDataFrame.has_guardrails].dtype,
                )
                return False

        if RenderingRoadDataFrame.is_bridge not in gdf.columns:
            logger.error("Missing column: is_bridge")
            return False

        if not gdf.empty:
            if not gdf[RenderingRoadDataFrame.is_bridge].dtype == bool:
                logger.error(
                    "Invalid is_bridge type:",
                    gdf[RenderingRoadDataFrame.is_bridge].dtype,
                )
                return False

        if RenderingRoadDataFrame.is_tunnel not in gdf.columns:
            logger.error("Missing column: is_tunnel")
            return False

        if not gdf.empty:
            if not gdf[RenderingRoadDataFrame.is_tunnel].dtype == bool:
                logger.error(
                    "Invalid is_tunnel type:",
                    gdf[RenderingRoadDataFrame.is_tunnel].dtype,
                )
                return False

        return True

    @staticmethod
    def validate(gdf: g.GeoDataFrame):
        if not RenderingRoadDataFrame.is_valid(gdf):
            raise ValueError("Invalid RenderingRoadDataFrame:", gdf)


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
        RenderingDataFrame.validate(self.forests)
        RenderingBuildingDataFrame.validate(self.buildings.churches)
        RenderingBuildingDataFrame.validate(self.buildings.malls)
        RenderingBuildingDataFrame.validate(self.buildings.factories)
        RenderingBuildingDataFrame.validate(self.buildings.houses)
        RenderingBuildingDataFrame.validate(self.buildings.default_buildings)
        RenderingRoadDataFrame.validate(self.roads)
        RenderingDataFrame.validate(self.still_water)
        RenderingDataFrame.validate(self.flowing_water)
        RenderingDataFrame.validate(self.ocean)
        RenderingDataFrame.validate(self.zones.wheatfields)
        RenderingDataFrame.validate(self.zones.cornfields)
        RenderingDataFrame.validate(self.zones.grass)
        RenderingDataFrame.validate(self.zones.developed)
        RenderingDataFrame.validate(self.zones.tartan)
        RenderingDataFrame.validate(self.zones.compacted)
        RenderingDataFrame.validate(self.zones.asphalt)
        RenderingDataFrame.validate(self.zones.sand)
        RenderingDataFrame.validate(self.zones.paths)
