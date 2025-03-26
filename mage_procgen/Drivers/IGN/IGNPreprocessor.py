import math
from typing import Union

import geopandas as g
import pandas as p

from mage_procgen.Utils.Utils import (
    RenderingData,
    GeoWindow,
    CRS_fr,
    BuildingRenderingData,
    ZonesRenderingData,
    safe_overlay,
    OverlayType,
)
from mage_procgen.Utils.Logging import logger
from mage_procgen.Utils.Geometry import polygonise
from functools import reduce
from mage_procgen.Utils.Config import Config, window_type_town
from mage_procgen.Drivers.IGN.Utils import GeoData, IGN
from mage_procgen.Drivers.IGN.DataFrames import (
    BuildingDataFrame,
    RoadDataFrame,
    ZoneInterestDataFrame,
    WaterDataFrame,
    LandUseDataFrame,
    SportDataFrame,
    PlotDataFrame,
)
from mage_procgen.Utils.RenderingDataFrames import (
    RenderingRoadDataFrame,
    clean_zones,
)


class IGNPreprocessor:
    @staticmethod
    def process(
        geo_data: GeoData, geowindow: GeoWindow, config: Config, crs: int
    ) -> RenderingData:

        logger.info("Preprocessing")
        new_buildings = safe_overlay(
            geo_data.buildings, geowindow.dataframe, OverlayType.INTERSECTION
        )
        new_forests = safe_overlay(
            geo_data.forests, geowindow.dataframe, OverlayType.INTERSECTION
        )
        new_water = safe_overlay(
            geo_data.water, geowindow.dataframe, OverlayType.INTERSECTION
        )
        new_landuse = safe_overlay(
            geo_data.landuse, geowindow.dataframe, OverlayType.INTERSECTION
        )
        new_sport = safe_overlay(
            geo_data.sport, geowindow.dataframe, OverlayType.INTERSECTION
        )
        new_plots = safe_overlay(
            geo_data.plots, geowindow.dataframe, OverlayType.INTERSECTION
        )
        new_developed = safe_overlay(
            geo_data.residentials, geowindow.dataframe, OverlayType.INTERSECTION
        )

        new_oceans = safe_overlay(
            geo_data.ocean, geowindow.dataframe, OverlayType.INTERSECTION
        )

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
        paths = new_roads.query("{} in @non_car_natures".format(RoadDataFrame.nature))

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
        # TODO: check if polygonized roads are still in use somewhere.
        # Forests uses raycast on road object to not spawn trees on roads,
        # and we can window lines later during rendermanager.
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
                new_row[RoadDataFrame.geometry] = geometry

                for key, value in new_row.items():
                    if key not in roads_content.keys():
                        roads_content[key] = []
                    roads_content[key].append(value)

            or_row_index += 1
        roads_polygonised = g.GeoDataFrame(roads_content, crs=CRS_fr)

        # Now that roads are polygons, we can apply the window on them and remove them from the background
        roads_polygonised = safe_overlay(
            roads_polygonised, geowindow.dataframe, OverlayType.INTERSECTION
        )

        roads_polygonised_ids = roads_polygonised[RoadDataFrame.ID]
        roads_selected = roads_with_cars.query(
            "{} in @roads_polygonised_ids".format(RoadDataFrame.ID)
        )

        # Removing roads from forests so we don't have trees on the road
        new_forests = safe_overlay(
            new_forests, roads_polygonised, OverlayType.DIFFERENCE
        )

        # Forests can intersect buildings, which we don't want
        cleaned_forests = safe_overlay(
            new_forests, new_buildings, OverlayType.DIFFERENCE
        )

        # Removing water from forests
        cleaned_forests = safe_overlay(
            cleaned_forests, new_water, OverlayType.DIFFERENCE
        )

        # Splitting water between "still" and "flowing"
        flowing_water_tags = WaterDataFrame.flowing_water_tags
        flowing_water = new_water.query(
            "{} in @flowing_water_tags".format(WaterDataFrame.nature)
        )
        still_water = new_water.query(
            "{} not in @flowing_water_tags".format(WaterDataFrame.nature)
        )
        still_water = safe_overlay(still_water, new_oceans, OverlayType.DIFFERENCE)
        flowing_water = safe_overlay(flowing_water, new_oceans, OverlayType.DIFFERENCE)

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

        if not new_plots.empty:
            new_plots = safe_overlay(new_plots, new_buildings, OverlayType.DIFFERENCE)

            # Prairies should be grass and not plots
            prairie_tags = IGN.prairie_codes
            new_plots = new_plots.query(
                "{} not in @prairie_tags".format(PlotDataFrame.group)
            )

            # Orchards should be added to forests
            orchards_tags = IGN.orchard_codes
            orchards = new_plots.query(
                "{} in @orchards_tags".format(PlotDataFrame.group)
            )
            new_plots = new_plots.query(
                "{} not in @orchards_tags".format(PlotDataFrame.group)
            )

            cleaned_forests = safe_overlay(cleaned_forests, orchards, OverlayType.UNION)

        sand_tags = IGN.bdcarto_sand_values
        sands = new_landuse.query("{} in @sand_tags".format(LandUseDataFrame.nature))

        tartan_tags = IGN.tartan_values
        tartan = new_sport.query("{} in @tartan_tags".format(SportDataFrame.nature))

        grass_tags = IGN.grass_values
        grass = new_sport.query("{} in @grass_tags".format(SportDataFrame.nature))

        asphalt_tags = IGN.asphalt_values
        asphalt = new_sport.query("{} in @asphalt_tags".format(SportDataFrame.nature))

        buildings_data = BuildingRenderingData(
            churches=churches,
            malls=malls,
            factories=factories,
            houses=houses,
            default_buildings=default_buildings,
        )
        zones_data = clean_zones(
            wheatfields=new_plots,
            cornfields=g.GeoDataFrame(columns=["id", "geometry"], geometry="geometry"),
            grass=grass,
            developed=new_developed,
            tartan=tartan,
            compacted=g.GeoDataFrame(columns=["id", "geometry"], geometry="geometry"),
            asphalt=asphalt,
            sand=sands,
            paths=paths,
        )
        rendering_data = RenderingData(
            forests=cleaned_forests,
            buildings=buildings_data,
            roads=roads_selected,
            still_water=still_water,
            flowing_water=flowing_water,
            ocean=new_oceans,
            zones=zones_data,
        )

        return rendering_data
