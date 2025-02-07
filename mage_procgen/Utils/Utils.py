import geopandas as g
import pandas as p
from shapely.geometry import Polygon, LineString, mapping
from enum import Enum
from dataclasses import dataclass

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
            print("Window was modified to be a rectangle in the destination crs")
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
            self.bounds[0],
            self.bounds[2],
            self.bounds[1],
            self.bounds[3],
            self.crs,
            to_crs,
        )


@dataclass
class BuildingRenderingData:
    churches: g.GeoDataFrame
    malls: g.GeoDataFrame
    factories: g.GeoDataFrame
    houses: g.GeoDataFrame
    default_buildings: g.GeoDataFrame


@dataclass
class ZonesRenderingData:
    wheatfields: g.GeoDataFrame
    cornfields: g.GeoDataFrame
    grass: g.GeoDataFrame
    developed: g.GeoDataFrame
    tartan: g.GeoDataFrame
    compacted: g.GeoDataFrame
    asphalt: g.GeoDataFrame
    sand: g.GeoDataFrame
    paths: g.GeoDataFrame


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


TerrainDataList = list[TerrainData]
