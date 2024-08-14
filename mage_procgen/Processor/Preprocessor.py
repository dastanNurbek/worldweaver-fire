import math

import geopandas as g
import pandas as p
from mage_procgen.Utils.Utils import RenderingData, GeoWindow, CRS_fr
from mage_procgen.Utils.Geometry import polygonise
from shapely.geometry import MultiPolygon, Polygon, mapping
from functools import reduce
from mage_procgen.Utils.Config import Config, window_type_town
from mage_procgen.Loader.Loader import Loader


class Preprocessor:
    _window_threshold = 1e-2
    _minimal_size = 20
    _building_inter_threshold = 1

    def __init__(
        self, geo_data: g.GeoDataFrame, geowindow: GeoWindow, config: Config, crs: int
    ):
        self.geo_data = geo_data
        self.window = geowindow
        self.crs = crs
        self.config = config

    def process(self) -> RenderingData:

        print("Processing")
        new_buildings = self.geo_data.buildings.overlay(
            self.window.dataframe, how="intersection", keep_geom_type=True
        )
        new_forests = self.geo_data.forests.overlay(
            self.window.dataframe, how="intersection", keep_geom_type=True
        )
        new_water = self.geo_data.water.overlay(
            self.window.dataframe, how="intersection", keep_geom_type=True
        )

        new_oceans = None

        if self.geo_data.ocean is not None:
            new_oceans = self.geo_data.ocean.overlay(
                self.window.dataframe, how="intersection", keep_geom_type=True
            )
            if not new_oceans.empty:
                new_oceans = new_oceans.overlay(
                    self.geo_data.departements, how="difference", keep_geom_type=True
                )

        industrial_commercial_tags = ["Zone artisanale", "Zone commerciale", "Zone d'activités"]
        industrial_and_commercial_zones = self.geo_data.interest_zones.query("NAT_DETAIL in @industrial_commercial_tags")

        sidewalks_zone_list = list(self.geo_data.residentials.geometry)#(industrial_and_commercial_zones, how="union", keep_geom_type=True)
        sidewalks_zone_list.extend(list(industrial_and_commercial_zones.geometry))
        sidewalks_zone = g.GeoSeries(sidewalks_zone_list)

        # Windowing the roads before polygonising them leads to errors
        # Related thread: https://github.com/geopandas/geopandas/issues/1724
        new_roads = self.geo_data.roads

        # TODO For now just pass the lists of geom, tagging will be handled later

        non_car_natures = ["Chemin", "Escalier", "Sentier"]
        roads_with_cars = new_roads.query("NATURE not in @non_car_natures")

        road_has_sidewalk = {}
        road_has_guardrails = {}

        for road_index in roads_with_cars.index:
            road_geom = roads_with_cars.geometry[road_index]
            road_importance = int(roads_with_cars["IMPORTANCE"][road_index])
            road_lane_nbr = int(roads_with_cars["NB_VOIES"][road_index]) if not math.isnan((roads_with_cars["NB_VOIES"][road_index])) else 1

            can_have_sidewalk = any(sidewalks_zone.intersects(road_geom))

            if can_have_sidewalk and (road_importance == 4 or road_importance == 5):
                road_has_sidewalk[road_index] = True
                road_has_guardrails[road_index] = False
            elif road_importance < 2 or road_lane_nbr >= 3:
                road_has_sidewalk[road_index] = False
                road_has_guardrails[road_index] = True
            else:
                road_has_sidewalk[road_index] = False
                road_has_guardrails[road_index] = False


        roads_sidewalks = p.Series(road_has_sidewalk)
        roads_guardrails = p.Series(road_has_guardrails)
        roads_with_cars = roads_with_cars.assign(has_sidewalks=roads_sidewalks, has_guardrails=roads_guardrails)

        # Transform the Polylines into polygons to allow geometry operations with other dataframes
        roads_elements = [
            polygonise(
                x[0],
                x[1],
                x[2],
                x[3],
                self.config.window_type == window_type_town,
                self.window,
            )
            for x in roads_with_cars[["geometry", "LARGEUR", "NB_VOIES", "SENS"]]
            .to_numpy()
            .tolist()
        ]

        roads_content = {}
        or_row_index = 0

        for index, row in roads_with_cars.iterrows():
            for geometry in roads_elements[or_row_index][0]:
                new_row = row.to_dict()
                # Saving the original line in another field to allow use of generators that work on lines
                # new_row["line"] = new_row["geometry"]
                new_row["geometry"] = geometry

                for key, value in new_row.items():
                    if key not in roads_content.keys():
                        roads_content[key] = []
                    roads_content[key].append(value)

            or_row_index += 1

        roads_polygonised = g.GeoDataFrame(roads_content, crs=CRS_fr)

        roads_lanes = reduce(lambda x, y: x + y, [x[1] for x in roads_elements])

        # Now that roads are polygons, we can apply the window on them and remove them from the background
        roads_polygonised = roads_polygonised.overlay(
            self.window.dataframe, how="intersection", keep_geom_type=True
        )

        roads_selected = roads_with_cars.query("ID in @roads_polygonised.ID")

        # Removing roads from forests so we don't have trees on the road
        new_forests = new_forests.overlay(
            roads_polygonised, how="difference", keep_geom_type=True
        )

        # Forests can intersect buildings, which we don't want
        cleaned_forests = new_forests.overlay(
            new_buildings, how="difference", keep_geom_type=True
        )

        # Removing water from forests
        cleaned_forests = cleaned_forests.overlay(
            new_water, how="difference", keep_geom_type=True
        )

        # Splitting water between "still" and "flowing"
        # TODO: check this tag list/update it
        flowing_water_tags = ["Ecoulement naturel", "Ecoulement canalisé", "Canal"]
        flowing_water = new_water.query("NATURE in @flowing_water_tags")
        still_water = new_water.query("NATURE not in @flowing_water_tags")

        churches_tags = ["Religieux"]
        churches = new_buildings.query("USAGE1 in @churches_tags")
        non_churches = new_buildings.query("USAGE1 not in @churches_tags")
        malls_tags = ["Commercial et services"]
        malls = non_churches.query("USAGE1 in @malls_tags")
        non_malls = non_churches.query("USAGE1 not in @malls_tags")
        factories_tags = ["Industriel"]
        factories = non_malls.query("USAGE1 in @factories_tags")
        non_factories = non_malls.query("USAGE1 not in @factories_tags")
        houses = non_factories.query("NB_LOGTS < 4")
        default_buildings = non_factories.query("ID not in @houses.ID")

        rendering_data = RenderingData(
            cleaned_forests,
            churches,
            malls,
            factories,
            houses,
            default_buildings,
            roads_selected,
            roads_lanes,
            still_water,
            flowing_water,
            new_oceans,
        )

        return rendering_data
