import geopandas as g
import pandas as p
import numpy as np

from shapely import union, Polygon
from shapely.geometry import mapping

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

from mage_procgen.Utils.Logging import logger
from mage_procgen.Utils.RenderingDataFrames import (
    RenderingRoadDataFrame,
    RenderingBuildingDataFrame,
    RenderingData,
    BuildingRenderingData,
    ZonesRenderingData,
)
from mage_procgen.Utils.Utils import (
    GeoWindow,
    safe_overlay,
    tag_water,
    get_class,
    safe_get_group,
    OverlayType,
)


class IGNPreprocessor:
    @staticmethod
    def process(geo_data: GeoData, geowindow: GeoWindow) -> RenderingData:

        logger.info("Preprocessing")
        # Windowing all dataframes because they contain objects that might have points outside the strict window
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

        industrial_and_commercial_zones = geo_data.interest_zones.query(
            f"{ZoneInterestDataFrame.detail_nature} in {IGN.industrial_commercial_tags}"
        )

        # TODO: faire un union_all des geometries plutot qu'une geoseries ? Aucune idée de ce qui est le plus idiomatique/efficace
        sidewalks_zone_list = list(geo_data.residentials.geometry)
        sidewalks_zone_list.extend(list(industrial_and_commercial_zones.geometry))
        sidewalks_zone = g.GeoSeries(sidewalks_zone_list)

        # Windowing the roads leads to errors because geometries are not the same type (Lines vs Polygons)
        # Related thread: https://github.com/geopandas/geopandas/issues/1724
        new_roads = geo_data.roads

        # Splitting roads into those with cars and those without (paths)
        new_roads[RoadDataFrame.type] = new_roads[RoadDataFrame.nature].map(
            lambda x: get_class(x, IGN.roads_synonyms, IGN.other)
        )
        road_groups = new_roads.groupby(RoadDataFrame.type)
        paths = safe_get_group(road_groups, new_roads, IGN.path)
        roads_with_cars = safe_get_group(road_groups, new_roads, IGN.with_car_tag)

        # Using roads attributes to define whether they have sidewalks or guardrails, and whether they are bridges or tunnels
        roads_tagged = roads_with_cars.apply(
            lambda x: IGNPreprocessor.tag_roads(
                x[RoadDataFrame.geometry],
                x[RoadDataFrame.importance],
                x[RoadDataFrame.number_lanes],
                x[RoadDataFrame.position_rel_to_ground],
                sidewalks_zone,
            ),
            axis=1,
            result_type="expand",
        )
        roads_tagged = roads_tagged.rename(
            columns={
                0: RenderingRoadDataFrame.has_sidewalks,
                1: RenderingRoadDataFrame.has_guardrails,
                2: RenderingRoadDataFrame.is_bridge,
                3: RenderingRoadDataFrame.is_tunnel,
                4: RenderingRoadDataFrame.number_lanes,
            }
        )
        # Fusing the data we calculated with the geometries
        roads_full = g.GeoDataFrame(
            roads_tagged, geometry=roads_with_cars.geometry, crs=geowindow.crs
        )
        roads_full[RenderingRoadDataFrame.has_sidewalks] = roads_full[
            RenderingRoadDataFrame.has_sidewalks
        ].astype(bool)
        roads_full[RenderingRoadDataFrame.has_guardrails] = roads_full[
            RenderingRoadDataFrame.has_guardrails
        ].astype(bool)
        roads_full[RenderingRoadDataFrame.is_bridge] = roads_full[
            RenderingRoadDataFrame.is_bridge
        ].astype(bool)
        roads_full[RenderingRoadDataFrame.is_tunnel] = roads_full[
            RenderingRoadDataFrame.is_tunnel
        ].astype(bool)
        roads_full[RenderingRoadDataFrame.number_lanes] = roads_full[
            RenderingRoadDataFrame.number_lanes
        ].astype(np.uint8)

        # Removing forests from water
        cleaned_forests = safe_overlay(new_forests, new_water, OverlayType.DIFFERENCE)

        # Casting building columns into appropriate types
        new_buildings[RenderingBuildingDataFrame.height] = new_buildings[
            RenderingBuildingDataFrame.height
        ].astype(p.Float64Dtype())
        new_buildings[RenderingBuildingDataFrame.number_floors] = new_buildings[
            RenderingBuildingDataFrame.number_floors
        ].astype(p.Int8Dtype())

        # Splitting buildings into the different categories
        new_buildings[BuildingDataFrame.type] = new_buildings[
            BuildingDataFrame.usage_1
        ].map(lambda x: get_class(x, IGN.building_class_synonyms, IGN.default_building))
        buildings_groups = new_buildings.groupby(BuildingDataFrame.type)

        churches = safe_get_group(buildings_groups, new_buildings, IGN.church)
        factories = safe_get_group(buildings_groups, new_buildings, IGN.factory)
        malls = safe_get_group(buildings_groups, new_buildings, IGN.mall)
        buildings = safe_get_group(
            buildings_groups, new_buildings, IGN.default_building
        )

        # House filtering is done differently (it depends on the number of housings in the building)
        houses = buildings.query(f"{BuildingDataFrame.number_housings} < 4")
        # Default buildings are those whose index are not in the houses dataframe
        default_buildings = buildings.loc[buildings.index.difference(houses.index)]

        # Landuse part:
        if not new_plots.empty:
            new_plots = safe_overlay(new_plots, new_buildings, OverlayType.DIFFERENCE)

            # Prairies should be grass and not plots
            prairie_tags = IGN.prairie_codes
            new_plots = new_plots.query(
                f"{PlotDataFrame.group} not in {IGN.prairie_codes}"
            )

            # Orchards should be added to forests
            orchards = new_plots.query(f"{PlotDataFrame.group} in {IGN.orchard_codes}")
            new_plots = new_plots.query(
                f"{PlotDataFrame.group} not in {IGN.orchard_codes}"
            )

            cleaned_forests = safe_overlay(cleaned_forests, orchards, OverlayType.UNION)

        sands = new_landuse.query(
            f"{LandUseDataFrame.nature} in {IGN.bdcarto_sand_values}"
        )

        new_sport[SportDataFrame.type] = new_sport[SportDataFrame.nature].map(
            lambda x: get_class(x, IGN.sport_surface_class_synonyms, IGN.other)
        )
        sports_groups = new_sport.groupby(SportDataFrame.type)
        tartan = safe_get_group(sports_groups, new_sport, IGN.tartan)
        grass = safe_get_group(sports_groups, new_sport, IGN.grass)
        asphalt = safe_get_group(sports_groups, new_sport, IGN.asphalt)

        # Treating water. We first want to split individual features into "still" and "flowing", then fuse each category,
        # Then fuse all water in the window into a single polygon, and split it into its different connex components
        # https://gis.stackexchange.com/questions/225368/understanding-difference-between-polygon-and-multipolygon-for-shapefiles-in-qgis
        # Then, each component is again tagged as "flowing", "still" or "ocean" depending on what it intersects.
        # This way a connex surface only has a single type

        # Splitting features into different types
        new_water[WaterDataFrame.type] = new_water[WaterDataFrame.nature].map(
            lambda x: get_class(x, IGN.water_types_synonnyms, IGN.still)
        )
        water_groups = new_water.groupby(WaterDataFrame.type)

        base_still_water = safe_get_group(water_groups, new_water, IGN.still)
        base_flowing_water = safe_get_group(water_groups, new_water, IGN.flowing)

        # Fusing geometries
        still_geometry = base_still_water.geometry.union_all()
        flowing_geometry = base_flowing_water.geometry.union_all()
        ocean_geometry = new_oceans.geometry.union_all()

        # TODO: supposedly from there it's the same as OSMPreprocessor for water. Should it be factorised ? if so, how ?
        all_water = union(still_geometry, flowing_geometry)
        all_water = union(all_water, ocean_geometry)

        # Splitting into the connex components
        if not all_water.is_empty:
            # mapping(all_water)["coordinates"] raises a KeyError if geometry is empty
            water_geometry = mapping(all_water)["coordinates"]
            # Have to distinguish if it's a multipolygon or a regular polygon
            if all_water.geom_type == IGN.multi_polygon:

                split_water = g.GeoDataFrame(
                    geometry=[Polygon(geom[0], geom[1:]) for geom in water_geometry],
                    crs=geowindow.crs,
                )
            else:
                split_water = g.GeoDataFrame(
                    geometry=[Polygon(water_geometry[0], water_geometry[1:])],
                    crs=geowindow.crs,
                )
        else:
            split_water = g.GeoDataFrame(geometry=[], crs=geowindow.crs)

        # Tagging the connex components water types
        water_types = {
            IGN.flowing: flowing_geometry,
            IGN.ocean: ocean_geometry,
            IGN.still: still_geometry,
        }
        split_water[WaterDataFrame.type] = split_water[WaterDataFrame.geometry].map(
            lambda x: tag_water(x, water_types, IGN.other)
        )
        split_water_groups = split_water.groupby(WaterDataFrame.type)

        # Now we are done
        still_water = safe_get_group(split_water_groups, split_water, IGN.still)
        flowing_water = safe_get_group(split_water_groups, split_water, IGN.flowing)
        ocean_water = safe_get_group(split_water_groups, split_water, IGN.ocean)

        buildings_data = BuildingRenderingData(
            churches=churches,
            malls=malls,
            factories=factories,
            houses=houses,
            default_buildings=default_buildings,
        )
        zones_data = ZonesRenderingData(
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
            roads=roads_full,
            still_water=still_water,
            flowing_water=flowing_water,
            ocean=ocean_water,
            zones=zones_data,
        )

        return rendering_data

    @staticmethod
    def tag_roads(
        geometry, importance, number_lanes, position_rel_to_ground, sidewalks_zone
    ):
        # Importance has to be filled
        road_importance = int(importance)
        # Lane number is sometimes empty
        road_lane_nbr = int(number_lanes) if not p.isnull(number_lanes) else 1

        # Sidewalks are only in urban areas
        can_have_sidewalk = any(sidewalks_zone.intersects(geometry))

        if can_have_sidewalk and (road_importance == 4 or road_importance == 5):
            has_sidewalk = True
            has_guardrails = False
        elif road_importance < 2 or road_lane_nbr >= 3:
            has_sidewalk = False
            has_guardrails = True
        else:
            has_sidewalk = False
            has_guardrails = False

        is_bridge = False
        is_tunnel = False
        if position_rel_to_ground.isdigit():
            road_pos_to_ground_value = int(position_rel_to_ground)
            is_bridge = road_pos_to_ground_value >= 1
            is_tunnel = road_pos_to_ground_value <= -1

        return [has_sidewalk, has_guardrails, is_bridge, is_tunnel, road_lane_nbr]
