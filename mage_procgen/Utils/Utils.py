from enum import Enum
from dataclasses import dataclass

import geopandas as g
import pandas as p
import numpy as np

from shapely.geometry import Polygon, LineString, mapping
from shapely import area, difference, intersects, contains, intersection

from mage_procgen.Utils.Logging import logger

Point = tuple[float, float, float]
PolygonList = list[Polygon]
BuildingList = list[(float, Polygon)]
LineStringList = list[LineString]

CRS_degrees = 4326
CRS_fr = 2154
CRS_ch = 2056
CRS_wgs84_m = 3857


class GeoWindow:
    @classmethod
    def from_square(
        cls,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        from_crs: int,
        to_crs: int,
    ):
        window_s = g.GeoSeries(
            [
                Polygon(
                    [
                        (x_min, y_min),
                        (x_max, y_min),
                        (x_max, y_max),
                        (x_min, y_max),
                    ]
                )
            ]
        )
        return cls(window_s, from_crs, to_crs)

    def __init__(
        self,
        geometry: g.GeoSeries,
        from_crs: int,
        to_crs: int,
    ):
        self.dataframe = g.GeoDataFrame({"geometry": geometry, "df": [1]}, crs=from_crs)

        # Have to convert it like this, so you are guaranteed to get a rectangle in the end.
        if from_crs != to_crs:
            # TODO: refine this. Users should be warned when the base window is modified but this seems to happen more than it should
            logger.warn("Window was modified to be a rectangle in the destination crs")
            logger.warn(
                f"(window was given in crs:{from_crs} and needs to be in crs:{to_crs})"
            )
            to_crs_box = self.dataframe.to_crs(to_crs).geometry[0].bounds
            window_s = g.GeoSeries(
                [
                    Polygon(
                        [
                            (to_crs_box[0], to_crs_box[1]),
                            (to_crs_box[2], to_crs_box[1]),
                            (to_crs_box[2], to_crs_box[3]),
                            (to_crs_box[0], to_crs_box[3]),
                        ]
                    )
                ]
            )
            self.dataframe = g.GeoDataFrame(
                {"geometry": window_s, "df": [1]}, crs=to_crs
            )

        centroid = self.dataframe.geometry[0].centroid
        # Used to geometrically center all the objects in render
        self.center = (centroid.coords[0][0], centroid.coords[0][1], 0.0)

        centroid_deg = self.dataframe.to_crs(CRS_degrees).geometry[0].centroid
        # Used to configure the sun object in render
        self.center_deg = (centroid_deg.coords[0][0], centroid_deg.coords[0][1], 0.0)

        # Order is Xmin, Ymin, Xmax, Ymax
        self.bounds = self.dataframe.geometry[0].bounds

        self.crs = to_crs

    def to_crs(self, to_crs: int):
        return GeoWindow.from_square(
            x_min=self.bounds[0],
            x_max=self.bounds[2],
            y_min=self.bounds[1],
            y_max=self.bounds[3],
            from_crs=self.crs,
            to_crs=to_crs,
        )


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


@dataclass
class RenderingData:
    forests: g.GeoDataFrame
    buildings: BuildingRenderingData
    roads: g.GeoDataFrame
    still_water: g.GeoDataFrame
    flowing_water: g.GeoDataFrame
    ocean: g.GeoDataFrame
    zones: ZonesRenderingData


@dataclass
class TaggingData:
    tagging_background: PolygonList
    buildings: PolygonList
    roads: PolygonList
    water: PolygonList


@dataclass
class TerrainData:
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    resolution: float
    nbcol: int
    nbrow: int
    no_data: float
    base_map_file: str
    data: p.DataFrame


TerrainDataList = list[TerrainData]


class OverlayType(Enum):

    DIFFERENCE = 1
    UNION = 2
    INTERSECTION = 3


def safe_overlay(
    df1: g.GeoDataFrame, df2: g.GeoDataFrame, how: OverlayType
) -> g.GeoDataFrame:
    """
    Performs overlay operation on the dataframes, with safety checks to avoid errors.
    """
    match how:
        case OverlayType.DIFFERENCE:
            if df1 is None:
                return df1
            if df1.empty:
                return df1
            if df2 is None:
                return df1
            if df2.empty:
                return df1
            return df1.overlay(df2, how="difference", keep_geom_type=True)
        case OverlayType.UNION:
            if df1 is None:
                return df2
            if df1.empty:
                return df2
            if df2 is None:
                return df1
            if df2.empty:
                return df1
            return df1.overlay(df2, how="union", keep_geom_type=True)
        case OverlayType.INTERSECTION:
            if df1 is None:
                return df1
            if df1.empty:
                return df1
            if df2 is None:
                return df2
            if df2.empty:
                return df2
            return df1.overlay(df2, how="intersection", keep_geom_type=True)


def get_class(tag: str, synonym_dict: dict, default_value: str):
    for key, value in synonym_dict.items():
        if tag in value:
            return key

    return default_value


def tag_water(geometry, water_types, default_name):
    for water_type, water_geometry in water_types.items():
        if not intersection(geometry, water_geometry).is_empty:
            return water_type

    return default_name


def reduce_columns(gdf, list_cols):
    gdf_e = ensure_columns_existence(gdf, list_cols)
    return gdf_e[list_cols]


def ensure_columns_existence(gdf, list_cols):
    for col_name in list_cols:
        if col_name not in gdf.columns:
            # https://stackoverflow.com/questions/60115806/pd-na-vs-np-nan-for-pandas
            gdf[col_name] = np.nan
    return gdf


# TODO: pareil qu'à la fin de OSMPreprocessor, le nom des geometries c'est toujours le meme en pratique, du coup est-ce qu'on devrait faire que ce soit paramétrable ou pas ?
# Pour le moment on le laisse comme ça
def safe_get_group(group_by, base_gdf, key):
    # Needed because GroupBy.get_group() fails if key is missing
    if key in group_by.groups:
        return group_by.get_group(key)
    else:
        return g.GeoDataFrame(
            columns=base_gdf.columns, geometry="geometry", crs=base_gdf.crs
        )
