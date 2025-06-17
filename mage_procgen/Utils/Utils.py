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
    :param df1: The first dataframe
    :param df2: The second dataframe
    :param how: The mode of overlay
    :return: The resulting overlay
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


def get_class(tag: str, synonym_dict: dict, default_value: str) -> str:
    """
    Returns the class of an item based on its tag, or a default value if a class cannot be found.
    :param tag: The tag of the item
    :param synonym_dict: The dictionary whose keys are the possible classes, and values the possible tags
    :param default_value: The default value returned if a class cannot be found
    :return: The class of an item based on its tag, or a default value if a class cannot be found.
    """
    for key, value in synonym_dict.items():
        if tag in value:
            return key

    return default_value


def tag_water(water_geometry, water_types, default_name):
    """
    Matches the water geometry with a class by checking if the geometry intersects tha of a class
    :param water_geometry: The geometry of the water body we want the class of
    :param water_types: The dictionary whose keys are the possible classes, and values the geometry of the class
    :param default_name: The default value returned if a class cannot be found
    :return: The class of the water body based on its intersection with other bodies, or a default value if a class cannot be found.
    """
    for water_type, water_geometry in water_types.items():
        if not intersection(water_geometry, water_geometry).is_empty:
            return water_type

    return default_name


def reduce_columns(gdf: g.GeoDataFrame, list_cols: list[str]) -> g.GeoDataFrame:
    """
    Ensures the input dataframe has the exact columns in the list
    :param gdf: The dataframe
    :param list_cols: The list of columns the dataframe should have
    :return: The dataframe, with its columns reduced
    """
    gdf_e = ensure_columns_existence(gdf, list_cols)
    return gdf_e[list_cols]


def ensure_columns_existence(gdf, list_cols):
    """
    Ensures the input dataframe has the columns in the list
    :param gdf: The dataframe
    :param list_cols: The list of columns the dataframe should have
    :return: The dataframe, with its columns added
    """
    for col_name in list_cols:
        if col_name not in gdf.columns:
            # https://stackoverflow.com/questions/60115806/pd-na-vs-np-nan-for-pandas
            gdf[col_name] = np.nan
    return gdf


def safe_get_group(group_by, base_gdf, key):
    """
    Gets the group of the key, or a default dataframe if the key is not found
    :param group_by: The GroupBy containing the groups
    :param base_gdf: The base dataframe from which to construct the default dataframe if needs be
    :param key: The key of the group
    :return: The group of the key, or a default dataframe if the key is not found
    """
    # Needed because GroupBy.get_group() fails if key is missing
    if key in group_by.groups:
        return group_by.get_group(key)
    else:
        return g.GeoDataFrame(
            columns=base_gdf.columns, geometry="geometry", crs=base_gdf.crs
        )
