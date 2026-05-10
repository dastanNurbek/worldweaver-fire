import random

import geopandas as g
import pandas as p
import numpy as np

from shapely import union, Polygon
from shapely.geometry import mapping

from worldweaver.Drivers.OSM.Utils import OSM

from worldweaver.Utils.Logging import logger
from worldweaver.Utils.RenderingDataFrames import (
    RenderingRoadDataFrame,
    RenderingBuildingDataFrame,
    RenderingData,
    BuildingRenderingData,
    ZonesRenderingData,
)
from worldweaver.Utils.Utils import (
    GeoWindow,
    safe_overlay,
    reduce_columns,
    ensure_columns_existence,
    tag_water,
    get_class,
    safe_get_group,
    OverlayType,
)


class OSMPreprocessor:
    @staticmethod
    def process(
        geo_dataframe: g.geodataframe,
        oceans_data: g.geodataframe,
        geowindow: GeoWindow,
    ) -> RenderingData:
        logger.info("Processing OSM data")
        # Avoids the "SettingWithCopyWarning: A value is trying to be set on a copy of a slice from a DataFrame"warning,
        # which would be triggered a lot here.
        # https://stackoverflow.com/a/20627316
        p.options.mode.chained_assignment = None

        # Ensure columns always exist even when the dataframe was built from empty fallbacks
        if OSM.tags not in geo_dataframe.columns:
            geo_dataframe[OSM.tags] = [{}] * len(geo_dataframe)
        if OSM.id not in geo_dataframe.columns:
            geo_dataframe[OSM.id] = range(len(geo_dataframe))
        # Fill no values with empty JSON dicts to avoid errors when parsing
        geo_dataframe[OSM.tags] = geo_dataframe[OSM.tags].apply(
            lambda x: {} if p.isnull(x) else x
        )
        # Flatten the nested JSON dicts into a proper DataFrame
        normalized_tags = p.json_normalize(geo_dataframe[OSM.tags])
        # Join the DataFrames to keep the geometry
        geo_dataframe = geo_dataframe[[OSM.id, OSM.geometry]].join(
            normalized_tags, validate="one_to_one"
        )

        multi_polys = geo_dataframe[geo_dataframe.geom_type == OSM.multi_polygon]
        polys = geo_dataframe[geo_dataframe.geom_type == OSM.polygon]
        all_polys = p.concat([polys, multi_polys])

        # Buildings
        # We have to make sure that a certain column exist in order to use it for filtering, and it only exists if at least one feature in the scene has this tag
        all_polys = ensure_columns_existence(all_polys, [OSM.building_tag])
        buildings = all_polys[all_polys[OSM.building_tag].notnull()]

        # Trimming columns (base geodataframe has hundreds of columns)
        buildings = reduce_columns(
            buildings,
            [
                OSM.id,
                OSM.geometry,
                OSM.building_tag,
                OSM.height,
                OSM.levels,
                RenderingBuildingDataFrame.change_status,
            ],
        )
        buildings[OSM.height] = buildings[OSM.height].astype(p.Float64Dtype())
        # Found one case where levels was a float, meaning it cannt go from str to int directly, it needs to be cast as float before.
        buildings[OSM.levels] = buildings[OSM.levels].astype(p.Float64Dtype())
        buildings[OSM.levels] = buildings[OSM.levels].astype(p.Int8Dtype())

        # Splitting buildigns into the different categories
        buildings[OSM.building_class] = buildings[OSM.building_tag].map(
            lambda x: get_class(x, OSM.building_class_synonyms, OSM.default_building)
        )
        # Transforming column names to fit what renderers need
        buildings = buildings.rename(
            columns={
                OSM.geometry: RenderingBuildingDataFrame.geometry,
                OSM.height: RenderingBuildingDataFrame.height,
                OSM.levels: RenderingBuildingDataFrame.number_floors,
            }
        )
        buildings_groups = buildings.groupby(OSM.building_class)

        churches = safe_get_group(buildings_groups, buildings, OSM.church)
        factories = safe_get_group(buildings_groups, buildings, OSM.factory)
        malls = safe_get_group(buildings_groups, buildings, OSM.mall)
        houses = safe_get_group(buildings_groups, buildings, OSM.house)
        buildings = safe_get_group(buildings_groups, buildings, OSM.default_building)

        # Landmasses
        all_polys = ensure_columns_existence(
            all_polys, [OSM.landuse, OSM.surface, OSM.leisure, OSM.natural, OSM.water]
        )
        # All those landuse elements will be split into different categories that fit our purpose
        landused = all_polys[all_polys[OSM.landuse].notnull()]
        surfaces = all_polys[all_polys[OSM.surface].notnull()]
        leisures = all_polys[all_polys[OSM.leisure].notnull()]
        natures = all_polys[all_polys[OSM.natural].notnull()]
        waters = all_polys[all_polys[OSM.water].notnull()]

        landused[OSM.landuse_class] = landused[OSM.landuse].map(
            lambda x: get_class(x, OSM.landuse_class_synonyms, OSM.other)
        )
        landuse_groups = landused.groupby(OSM.landuse_class)

        surfaces[OSM.surface_class] = surfaces[OSM.surface].map(
            lambda x: get_class(x, OSM.surface_class_synonyms, OSM.other)
        )
        surface_groups = surfaces.groupby(OSM.surface_class)

        leisures[OSM.leisure_class] = leisures[OSM.leisure].map(
            lambda x: get_class(x, OSM.leisure_class_synonyms, OSM.other)
        )
        leisure_groups = leisures.groupby(OSM.leisure_class)

        natures[OSM.nature_class] = natures[OSM.natural].map(
            lambda x: get_class(x, OSM.nature_class_synonyms, OSM.other)
        )
        nature_groups = natures.groupby(OSM.nature_class)

        forests = safe_get_group(landuse_groups, landused, OSM.usage_forests_tags)

        fields = safe_get_group(landuse_groups, landused, OSM.field)
        fields = reduce_columns(fields, [OSM.id, OSM.geometry, OSM.field_crop])

        # Since crops are not well tagged, we randomly split the non-tagged into the available categories
        fields_crops_choices = list(OSM.crop_class_synonyms.keys())
        fields[OSM.crop_class] = fields[OSM.field_crop].map(
            lambda x: get_class(
                x, OSM.crop_class_synonyms, random.choice(fields_crops_choices)
            )
        )
        field_groups = fields.groupby(OSM.crop_class)
        wheat_fields = safe_get_group(field_groups, fields, OSM.wheat_crop)
        corn_fields = safe_get_group(field_groups, fields, OSM.corn_crop)

        # Grass
        selected_grass_tags = OSM.grass_landuses.copy()
        selected_grass_tags.extend(OSM.leisure_landuses)

        grass = safe_get_group(landuse_groups, landused, OSM.grass)
        leisures = safe_get_group(landuse_groups, landused, OSM.leisure)
        # We want to display leisure elements in grass
        grass = p.concat([grass, leisures])

        grass_surface = safe_get_group(surface_groups, surfaces, OSM.grass)
        # Grass can be tagged in landuse or surface, we want both
        grass = safe_overlay(grass, grass_surface, OverlayType.UNION)

        developed = safe_get_group(landuse_groups, landused, OSM.developed)

        asphalt = safe_get_group(surface_groups, surfaces, OSM.asphalt_surface)
        tartan = safe_get_group(surface_groups, surfaces, OSM.tartan_surface)
        compacted = safe_get_group(surface_groups, surfaces, OSM.compacted_surface)
        sands = safe_get_group(surface_groups, surfaces, OSM.sand_surface)

        leisure_tartan = safe_get_group(leisure_groups, leisures, OSM.playground)
        # Tartan can be either a surface or a specific leisure
        tartan = safe_overlay(tartan, leisure_tartan, OverlayType.UNION)

        beaches = safe_get_group(nature_groups, natures, OSM.beach)
        sand_natures = safe_get_group(nature_groups, natures, OSM.sand_surface)

        # Sands can also be tagged in multiple ways
        sands = safe_overlay(sands, beaches, OverlayType.UNION)
        sands = safe_overlay(sands, sand_natures, OverlayType.UNION)

        # Roads
        lines = geo_dataframe[geo_dataframe.geom_type == OSM.line_string]
        multi_lines = geo_dataframe[geo_dataframe.geom_type == OSM.multi_line_string]
        all_lines = p.concat([lines, multi_lines], ignore_index=True)

        all_lines = ensure_columns_existence(all_lines, [OSM.highway_tag])

        roads = all_lines[all_lines[OSM.highway_tag].notnull()]
        roads[OSM.road_class] = roads[OSM.highway_tag].map(
            lambda x: get_class(x, OSM.roads_synonyms, OSM.highway_tag)
        )
        road_groups = roads.groupby(OSM.road_class)

        paths = safe_get_group(road_groups, roads, OSM.path)
        highways_data = safe_get_group(road_groups, roads, OSM.highway_tag)

        highways_data = ensure_columns_existence(
            highways_data,
            [
                OSM.max_speed,
                OSM.sidewalk,
                OSM.lanes,
                OSM.bridge,
                OSM.tunnel,
            ],
        )
        highways_tagged = highways_data.apply(
            lambda x: OSMPreprocessor.tag_roads(
                x[OSM.max_speed],
                x[OSM.sidewalk],
                x[OSM.lanes],
                x[OSM.bridge],
                x[OSM.tunnel],
            ),
            axis=1,
            result_type="expand",
        )
        highways_tagged = highways_tagged.rename(
            columns={
                0: RenderingRoadDataFrame.has_sidewalks,
                1: RenderingRoadDataFrame.has_guardrails,
                2: RenderingRoadDataFrame.is_bridge,
                3: RenderingRoadDataFrame.is_tunnel,
                4: RenderingRoadDataFrame.number_lanes,
            }
        )
        highways = g.GeoDataFrame(
            highways_tagged, geometry=highways_data.geometry, crs=geowindow.crs
        )
        # When highways_data is empty, apply produces no columns — ensure they exist with correct types
        for col, dtype, default in [
            (RenderingRoadDataFrame.has_sidewalks, bool, False),
            (RenderingRoadDataFrame.has_guardrails, bool, False),
            (RenderingRoadDataFrame.is_bridge, bool, False),
            (RenderingRoadDataFrame.is_tunnel, bool, False),
        ]:
            if col in highways.columns:
                highways[col] = highways[col].astype(bool)
            else:
                highways[col] = p.Series(default, index=highways.index, dtype=bool)
        col = RenderingRoadDataFrame.number_lanes
        if col in highways.columns:
            highways[col] = highways[col].astype(np.uint8)
        else:
            highways[col] = p.Series(1, index=highways.index, dtype=np.uint8)

        # Water.
        # Algorithm is the same as in IGNPreprocessor.
        waters[OSM.water_class] = waters[OSM.water].map(
            lambda x: get_class(x, OSM.waters_synonyms, OSM.flowing)
        )
        water_groups = waters.groupby(OSM.water_class)

        base_still_water = safe_get_group(water_groups, waters, OSM.still)
        base_flowing_water = safe_get_group(water_groups, waters, OSM.flowing)

        still_geometry = base_still_water.geometry.union_all()
        flowing_geometry = base_flowing_water.geometry.union_all()

        ocean_geometry = oceans_data.geometry.union_all()

        all_water = union(still_geometry, flowing_geometry)
        all_water = union(all_water, ocean_geometry)

        if not all_water.is_empty:
            # mapping(all_water)["coordinates"] raises a KeyError if geometry is empty
            water_geometry = mapping(all_water)["coordinates"]
            # Have to distinguish if it's a multipolygon or a regular polygon
            if all_water.geom_type == OSM.multi_polygon:

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

        water_types = {
            OSM.flowing: flowing_geometry,
            OSM.ocean: ocean_geometry,
            OSM.still: still_geometry,
        }
        split_water[OSM.water_class] = split_water[OSM.geometry].map(
            lambda x: tag_water(x, water_types, OSM.other)
        )
        split_water_groups = split_water.groupby(OSM.water_class)

        still_water = safe_get_group(split_water_groups, split_water, OSM.still)
        flowing_water = safe_get_group(split_water_groups, split_water, OSM.flowing)
        ocean_water = safe_get_group(split_water_groups, split_water, OSM.ocean)

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
        ocean_water = safe_overlay(
            ocean_water, geowindow.dataframe, OverlayType.INTERSECTION
        )
        wheatfields = safe_overlay(
            wheat_fields, geowindow.dataframe, OverlayType.INTERSECTION
        )
        cornfields = safe_overlay(
            corn_fields, geowindow.dataframe, OverlayType.INTERSECTION
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
        # TODO: trim dataframes
        # TODO: pour que ce soit vrai faut forcément que OSM.geometry soit egal a RenderingDataFrame.geometry ...
        # Est-ce qu'on dit que c'est le cas parce que c'est une convention respectée ? et du coup pas de pb a utiliser OSM.geometry ici ?
        # Sinon faut trim le dataframe pour laisser que la geometrie PUIS changer le nom de la col de OSM.geometry en RenderingDataFrame.geometry (et les deux seront a priori toujours egaux)
        zones_data = ZonesRenderingData(
            wheatfields=reduce_columns(wheatfields, [OSM.geometry]),
            cornfields=reduce_columns(cornfields, [OSM.geometry]),
            grass=reduce_columns(grass, [OSM.geometry]),
            developed=reduce_columns(developed, [OSM.geometry]),
            tartan=reduce_columns(tartan, [OSM.geometry]),
            compacted=reduce_columns(compacted, [OSM.geometry]),
            asphalt=reduce_columns(asphalt, [OSM.geometry]),
            sand=reduce_columns(sands, [OSM.geometry]),
            paths=reduce_columns(paths, [OSM.geometry]),
        )

        # TODO: water lines are currently empty due to the fact that we cannot use OSM queries.
        # If a fix is found on overpass systematically returning a 403,
        # water lines should be correctly extracted from data and passed there.
        rendering_data = RenderingData(
            forests=reduce_columns(forests, [OSM.geometry]),
            buildings=buildings_data,
            roads=highways,
            still_water=still_water,
            flowing_water=flowing_water,
            flowing_water_line=g.GeoDataFrame(
                columns=["cleabs", "geometry"], geometry="geometry", crs=geowindow.crs
            ),
            ocean=ocean_water,
            zones=zones_data,
        )

        return rendering_data

    @staticmethod
    def tag_roads(max_speed, sidewalk_tag, road_lane_tag, bridge_tag, tunnel_tag):
        road_lane_nbr = 1
        if not p.isnull(road_lane_tag):
            road_lane_nbr = int(road_lane_tag)

        # Speed is not always filled, and sometimes it also has a unit attached to it.
        # In case it doesn't fit the formats we filter for, we just ignore its value and treat it as if it wasn't filled
        speed = 0
        if not p.isnull(max_speed):
            if max_speed.isdigit():
                speed = int(max_speed)
            else:
                try:
                    speed_value = float(max_speed.split()[0])
                    speed_unit = max_speed.split()[1]
                    if speed_unit == OSM.mph_key:
                        speed = speed_value * OSM.mph_mult
                    elif speed_unit == OSM.knot_key:
                        speed = speed_value * OSM.knot_mult
                    elif speed_unit in OSM.kmh_keys:
                        speed = speed_value
                except ValueError:
                    pass

        has_sidewalk = sidewalk_tag in OSM.has_sidewalk_list
        has_guardrails = False
        if not has_sidewalk:
            if speed > 90 or road_lane_nbr >= 5:
                has_guardrails = True

        is_bridge = not p.isnull(bridge_tag)
        is_tunnel = not p.isnull(tunnel_tag)
        return [has_sidewalk, has_guardrails, is_bridge, is_tunnel, road_lane_nbr]
