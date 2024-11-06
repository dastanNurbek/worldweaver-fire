import math

import geopandas as g
import pandas as p
from mage_procgen.Utils.Utils import RenderingData, GeoWindow, CRS_fr
from mage_procgen.Utils.Geometry import polygonise
from functools import reduce
from mage_procgen.Utils.Config import Config, window_type_town
from mage_procgen.Drivers.IGN.Utils import GeoData
from mage_procgen.Drivers.IGN.DataFrames import (
    BuildingDataFrame,
    RoadDataFrame,
    ZoneInterestDataFrame,
    WaterDataFrame,
)
from mage_procgen.Utils.RenderingDataFrames import RenderingRoadDataFrame


class Preprocessor:
    _window_threshold = 1e-2
    _minimal_size = 20
    _building_inter_threshold = 1

    @staticmethod
    def process(
        geo_data: GeoData, geowindow: GeoWindow, config: Config, crs: int
    ) -> RenderingData:

        print("Processing")
        new_buildings = geo_data.buildings.overlay(
            geowindow.dataframe, how="intersection", keep_geom_type=True
        )
        new_forests = geo_data.forests.overlay(
            geowindow.dataframe, how="intersection", keep_geom_type=True
        )
        new_water = geo_data.water.overlay(
            geowindow.dataframe, how="intersection", keep_geom_type=True
        )

        new_oceans = None

        if geo_data.ocean is not None:
            new_oceans = geo_data.ocean.overlay(
                geowindow.dataframe, how="intersection", keep_geom_type=True
            )
            # if not new_oceans.empty:
            #     new_oceans = geowindow.dataframe.overlay(
            #         geo_data.departements, how="difference", keep_geom_type=True
            #     )

        industrial_commercial_tags = ZoneInterestDataFrame.industrial_commercial_tags
        industrial_and_commercial_zones = geo_data.interest_zones.query(
            "{} in @industrial_commercial_tags".format(
                ZoneInterestDataFrame.detail_nature
            )
        )

        sidewalks_zone_list = list(geo_data.residentials.geometry)
        sidewalks_zone_list.extend(list(industrial_and_commercial_zones.geometry))
        sidewalks_zone = g.GeoSeries(sidewalks_zone_list)

        # Windowing the roads before polygonising them leads to errors
        # Related thread: https://github.com/geopandas/geopandas/issues/1724
        new_roads = geo_data.roads

        # TODO For now just pass the lists of geom, tagging will be handled later

        non_car_natures = RoadDataFrame.non_car_natures
        roads_with_cars = new_roads.query(
            "{} not in @non_car_natures".format(RoadDataFrame.nature)
        )

        road_has_sidewalk = {}
        road_has_guardrails = {}

        for road_index in roads_with_cars.index:
            road_geom = roads_with_cars.geometry[road_index]
            road_importance = int(roads_with_cars[RoadDataFrame.importance][road_index])
            road_lane_nbr = (
                int(roads_with_cars[RoadDataFrame.number_lanes][road_index])
                if not math.isnan(
                    (roads_with_cars[RoadDataFrame.number_lanes][road_index])
                )
                else 1
            )

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
        roads_with_cars = roads_with_cars.assign(
            has_sidewalks=roads_sidewalks, has_guardrails=roads_guardrails
        )

        # Transform the Polylines into polygons to allow geometry operations with other dataframes
        roads_elements = [
            polygonise(
                x[0],
                x[1],
                x[2],
                x[3],
                config.window_type == window_type_town,
                geowindow,
            )
            for x in roads_with_cars[
                [
                    RoadDataFrame.geometry,
                    RenderingRoadDataFrame.width,
                    RoadDataFrame.number_lanes,
                    RoadDataFrame.direction,
                ]
            ]
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
                new_row[RoadDataFrame.geometry] = geometry

                for key, value in new_row.items():
                    if key not in roads_content.keys():
                        roads_content[key] = []
                    roads_content[key].append(value)

            or_row_index += 1

        roads_polygonised = g.GeoDataFrame(roads_content, crs=CRS_fr)

        roads_lanes = reduce(lambda x, y: x + y, [x[1] for x in roads_elements])

        # Now that roads are polygons, we can apply the window on them and remove them from the background
        roads_polygonised = roads_polygonised.overlay(
            geowindow.dataframe, how="intersection", keep_geom_type=True
        )

        roads_polygonised_ids = roads_polygonised[RoadDataFrame.ID]
        roads_selected = roads_with_cars.query(
            "{} in @roads_polygonised_ids".format(RoadDataFrame.ID)
        )

        # Removing roads from forests so we don't have trees on the road
        if not new_forests.empty:
            new_forests = new_forests.overlay(
                roads_polygonised, how="difference", keep_geom_type=True
            )

        # Forests can intersect buildings, which we don't want
        if not new_forests.empty:
            cleaned_forests = new_forests.overlay(
                new_buildings, how="difference", keep_geom_type=True
            )
        else:
            cleaned_forests = new_forests

        # Removing water from forests
        if not cleaned_forests.empty:
            cleaned_forests = cleaned_forests.overlay(
                new_water, how="difference", keep_geom_type=True
            )

        # Splitting water between "still" and "flowing"
        flowing_water_tags = WaterDataFrame.flowing_water_tags
        flowing_water = new_water.query(
            "{} in @flowing_water_tags".format(WaterDataFrame.nature)
        )
        still_water = new_water.query(
            "{} not in @flowing_water_tags".format(WaterDataFrame.nature)
        )

        churches_tags = BuildingDataFrame.churches_tags
        churches = new_buildings.query(
            "{} in @churches_tags".format(BuildingDataFrame.usage_1)
        )
        non_churches = new_buildings.query(
            "{} not in @churches_tags".format(BuildingDataFrame.usage_1)
        )
        malls_tags = BuildingDataFrame.malls_tags
        malls = non_churches.query(
            "{} in @malls_tags".format(BuildingDataFrame.usage_1)
        )
        non_malls = non_churches.query(
            "{} not in @malls_tags".format(BuildingDataFrame.usage_1)
        )
        factories_tags = BuildingDataFrame.factories_tags
        factories = non_malls.query(
            "{} in @factories_tags".format(BuildingDataFrame.usage_1)
        )
        non_factories = non_malls.query(
            "{} not in @factories_tags".format(BuildingDataFrame.usage_1)
        )
        houses = non_factories.query("{} < 4".format(BuildingDataFrame.number_housings))
        default_buildings = non_factories.query(
            "{} not in @houses.ID".format(BuildingDataFrame.ID)
        )

        rendering_data = RenderingData(
            forests=cleaned_forests,
            churches=churches,
            malls=malls,
            factories=factories,
            houses=houses,
            default_buildings=default_buildings,
            roads=roads_selected,
            lanes=roads_lanes,
            still_water=still_water,
            flowing_water=flowing_water,
            ocean=new_oceans,
            fields=g.GeoDataFrame(columns=["id", "geometry"], geometry="geometry"),
            grass=g.GeoDataFrame(columns=["id", "geometry"], geometry="geometry"),
            developed=g.GeoDataFrame(columns=["id", "geometry"], geometry="geometry"),
        )

        return rendering_data
