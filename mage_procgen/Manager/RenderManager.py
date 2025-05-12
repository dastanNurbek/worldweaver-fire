import math

from bpy import data as D

import geopandas as g

from shapely.geometry import MultiPolygon, LineString, MultiLineString

from mage_procgen.Renderer import (
    BuildingRenderer,
    BoxBuildingRenderer,
    BuildingFootprintRenderer,
    ForestRenderer,
    PrettyRoadRenderer,
    WaterRenderer,
    TerrainRenderer,
    FloodRenderer,
    ZoneRenderer,
    LineZoneRenderer,
)

from mage_procgen.Utils.Config import Config
from mage_procgen.Utils.Logging import logger
from mage_procgen.Utils.Utils import PolygonList, TerrainData
from mage_procgen.Utils.Utils import RenderingData, GeoWindow, safe_overlay, OverlayType
from mage_procgen.Utils.RenderingDataFrames import RenderingBuildingDataFrame
from mage_procgen.Utils.Rendering import (
    configure_render,
    rendering_collection_name,
    terrain_collection_name,
    buildings_collection_name,
    additionals_collection_name,
    persp_camera_name,
    ortho_camera_name,
)


class RenderManager:
    def __init__(
        self,
        terrain_data: list[TerrainData],
        rendering_data: RenderingData,
        geowindow: GeoWindow,
        crs: int,
        config: Config,
    ):
        self.terrain_data = terrain_data
        self.rendering_data = rendering_data
        self.window = geowindow
        self.crs = crs
        self.config = config
        self.current_zone = None
        configure_render(self.window.center_deg)
        self.terrain_renderer = TerrainRenderer.TerrainRenderer(
            config.base_folder,
            self.config.terrain_resolution,
            terrain_data[0].resolution,
            self.config.use_sat_img,
        )
        self.building_renderer = BuildingRenderer.BuildingRenderer(
            self.terrain_data, self.config.building_render_config
        )
        self.houses_renderer = BoxBuildingRenderer.BoxBuildingRenderer(
            self.terrain_data, self.config.house_render_config
        )
        self.malls_renderer = BuildingRenderer.MallRenderer(
            self.terrain_data, self.config.mall_render_config
        )
        self.churches_renderer = BuildingRenderer.ChurchRenderer(
            self.terrain_data, self.config.church_render_config
        )
        self.factories_renderer = BuildingRenderer.FactoryRenderer(
            self.terrain_data, self.config.factory_render_config
        )
        self.flowing_water_renderer = WaterRenderer.FlowingWaterRenderer(
            self.terrain_data, self.config.water_render_config
        )
        self.ocean_renderer = WaterRenderer.OceanRenderer(
            self.terrain_data, self.config.water_render_config
        )
        self.flood_renderer = FloodRenderer.FloodRenderer(
            self.config.flood_render_config
        )
        self.forests_renderer = ForestRenderer.ForestRenderer(
            self.terrain_data, self.config.forest_render_config
        )
        self.road_renderer = PrettyRoadRenderer.PrettyRoadRenderer(
            self.terrain_data,
            self.config.road_render_config,
            self.config.car_render_config,
        )
        self.still_water_renderer = WaterRenderer.StillWaterRenderer(
            self.terrain_data, self.config.water_render_config
        )
        self.building_footprint_renderer = (
            BuildingFootprintRenderer.BuildingFootprintRenderer(self.terrain_data)
        )
        self.wheatfields_renderer = ZoneRenderer.WheatFieldRenderer(self.terrain_data)
        self.cornfields_renderer = ZoneRenderer.CornFieldRenderer(self.terrain_data)
        self.grass_renderer = ZoneRenderer.GrassRenderer(self.terrain_data)
        self.developed_renderer = ZoneRenderer.DevelopedRenderer(self.terrain_data)
        self.tartan_renderer = ZoneRenderer.TartanRenderer(self.terrain_data)
        self.compacted_renderer = ZoneRenderer.CompactedRenderer(self.terrain_data)
        self.asphalt_renderer = ZoneRenderer.AsphaltRenderer(self.terrain_data)
        self.sand_renderer = ZoneRenderer.SandRenderer(self.terrain_data)
        self.path_renderer = LineZoneRenderer.PathRenderer(self.terrain_data)

    def draw_terrain(self):
        # Rendering objects that are ground level or interact with terrain
        logger.info("Rendering terrain and its dependencies")
        self.terrain_renderer.render(
            self.terrain_data,
            self.window,
            terrain_collection_name,
        )
        logger.info("Terrain rendered")

        # Drawing water
        logger.info("Rendering flowing water")
        self.flowing_water_renderer.render(
            self.rendering_data.flowing_water,
            self.rendering_data.ocean,
            self.window.center,
            rendering_collection_name,
        )

        oceans_geom = self.__extract_geom(self.rendering_data.ocean.geometry)
        self.ocean_renderer.render(
            oceans_geom, self.window.center, rendering_collection_name
        )

        still_water = self.__extract_geom(self.rendering_data.still_water.geometry)
        self.still_water_renderer.render(
            still_water, self.window.center, rendering_collection_name
        )

        # Drawing roads and buildind footprints to modify terrain
        self.road_renderer.render(
            self.rendering_data.roads,
            self.window,
            rendering_collection_name,
        )

        buildings_zone = safe_overlay(
            self.rendering_data.buildings.default_buildings,
            self.window.dataframe,
            OverlayType.INTERSECTION,
        )
        buildings = self.__extract_geom(buildings_zone.geometry)

        houses_zone = safe_overlay(
            self.rendering_data.buildings.houses,
            self.window.dataframe,
            OverlayType.INTERSECTION,
        )
        houses = self.__extract_geom(houses_zone.geometry)

        churches_zone = safe_overlay(
            self.rendering_data.buildings.churches,
            self.window.dataframe,
            OverlayType.INTERSECTION,
        )
        churches = self.__extract_geom(churches_zone.geometry)

        factories_zone = safe_overlay(
            self.rendering_data.buildings.factories,
            self.window.dataframe,
            OverlayType.INTERSECTION,
        )
        factories = self.__extract_geom(factories_zone.geometry)

        malls_zone = safe_overlay(
            self.rendering_data.buildings.malls,
            self.window.dataframe,
            OverlayType.INTERSECTION,
        )
        malls = self.__extract_geom(malls_zone.geometry)

        buildings.extend(houses)
        buildings.extend(churches)
        buildings.extend(factories)
        buildings.extend(malls)
        self.building_footprint_renderer.render(
            buildings, self.window.center, additionals_collection_name
        )

        # Drawing zones to texture terrain
        wheatfields = self.__extract_geom(
            self.rendering_data.zones.wheatfields.geometry
        )
        self.wheatfields_renderer.render(
            wheatfields, self.window.center, additionals_collection_name
        )

        cornfields = self.__extract_geom(self.rendering_data.zones.cornfields.geometry)
        self.cornfields_renderer.render(
            cornfields, self.window.center, additionals_collection_name
        )

        grass = self.__extract_geom(self.rendering_data.zones.grass.geometry)
        self.grass_renderer.render(
            grass, self.window.center, additionals_collection_name
        )

        developed = self.__extract_geom(self.rendering_data.zones.developed.geometry)
        self.developed_renderer.render(
            developed, self.window.center, additionals_collection_name
        )

        tartan = self.__extract_geom(self.rendering_data.zones.tartan.geometry)
        self.tartan_renderer.render(
            tartan, self.window.center, additionals_collection_name
        )

        compacted = self.__extract_geom(self.rendering_data.zones.compacted.geometry)
        self.compacted_renderer.render(
            compacted, self.window.center, additionals_collection_name
        )

        asphalt = self.__extract_geom(self.rendering_data.zones.asphalt.geometry)
        self.asphalt_renderer.render(
            asphalt, self.window.center, additionals_collection_name
        )

        sands = self.__extract_geom(self.rendering_data.zones.sand.geometry)
        self.sand_renderer.render(
            sands, self.window.center, additionals_collection_name
        )

        self.path_renderer.render(
            self.rendering_data.zones.paths,
            self.window,
            additionals_collection_name,
        )

        # Once everything is rendered, it can be plugged into the terrain's geometrynodes
        self.terrain_renderer._TerrainRenderer__config_geometry_node(
            road_object=self.road_renderer.get_mesh_obj(),
            water_object=self.flowing_water_renderer.get_mesh_obj(),
            still_water_object=self.still_water_renderer.get_mesh_obj(),
            ocean_object=self.ocean_renderer.get_mesh_obj(),
            building_object=self.building_footprint_renderer.get_mesh_obj(),
        )

        if not self.config.use_sat_img:
            self.terrain_renderer._TerrainRenderer__config_tagging_node(
                wheatfields_object=self.wheatfields_renderer.get_mesh_obj(),
                cornields_object=self.cornfields_renderer.get_mesh_obj(),
                grass_object=self.grass_renderer.get_mesh_obj(),
                developed_object=self.developed_renderer.get_mesh_obj(),
                tartan_object=self.tartan_renderer.get_mesh_obj(),
                compacted_object=self.compacted_renderer.get_mesh_obj(),
                asphalt_object=self.asphalt_renderer.get_mesh_obj(),
                sand_object=self.sand_renderer.get_mesh_obj(),
                roads_object=self.road_renderer.get_mesh_obj(),
                path_object=self.path_renderer.get_mesh_obj(),
            )

        logger.info("Objects that interact with flood rendered")

    def draw_flood(self, flood_data):
        self.flood_renderer.render(flood_data, rendering_collection_name)

    def draw_decor(self, restrict_to_camera, use_camera_presp=False):

        zone_window = self.window

        if restrict_to_camera:

            # To draw more than the actual view
            vector_multiplier = 1.2

            # Calculating an area that is roughly vector_multiplier times bigger than the field of view of the camera
            # So that we only draw objects that are inside this area
            if use_camera_presp:
                camera = D.objects[persp_camera_name]
                origin = camera.location

                # camera Z should be by far the highest so this rule of thumb should hold
                max_distance = 2 * origin[2]

                vector_coord = math.tan(camera.data.angle / 2)

                vector_ul = (
                    -vector_multiplier * vector_coord,
                    -vector_multiplier * vector_coord,
                    -1,
                )
                vector_ur = (
                    vector_multiplier * vector_coord,
                    -vector_multiplier * vector_coord,
                    -1,
                )
                vector_ll = (
                    -vector_multiplier * vector_coord,
                    vector_multiplier * vector_coord,
                    -1,
                )
                vector_lr = (
                    vector_multiplier * vector_coord,
                    vector_multiplier * vector_coord,
                    -1,
                )

                zone_delimiters = (
                    self.__corner_coord(vector_ul, max_distance, origin),
                    self.__corner_coord(vector_ur, max_distance, origin),
                    self.__corner_coord(vector_ll, max_distance, origin),
                    self.__corner_coord(vector_lr, max_distance, origin),
                )

                try:
                    zone_x_min = (
                        min([c[0][0] for c in zone_delimiters]) + self.window.center[0]
                    )
                    zone_x_max = (
                        max([c[0][0] for c in zone_delimiters]) + self.window.center[0]
                    )
                    zone_y_min = (
                        min([c[0][1] for c in zone_delimiters]) + self.window.center[1]
                    )
                    zone_y_max = (
                        max([c[0][1] for c in zone_delimiters]) + self.window.center[1]
                    )

                    zone_window = GeoWindow.from_square(
                        x_min=zone_x_min,
                        x_max=zone_x_max,
                        y_min=zone_y_min,
                        y_max=zone_y_max,
                        from_crs=self.crs,
                        to_crs=self.crs,
                    )

                except:
                    raise ValueError(
                        "Zone to beautify is outside of the boundaries of the scene"
                    )
            else:
                camera = D.objects[ortho_camera_name]
                origin = camera.location
                window_size = camera.data.ortho_scale

                zone_x_min = (
                    origin[0]
                    - (window_size / 2) * vector_multiplier
                    + self.window.center[0]
                )
                zone_x_max = (
                    origin[0]
                    + (window_size / 2) * vector_multiplier
                    + self.window.center[0]
                )
                zone_y_min = (
                    origin[1]
                    - (window_size / 2) * vector_multiplier
                    + self.window.center[1]
                )
                zone_y_max = (
                    origin[1]
                    + (window_size / 2) * vector_multiplier
                    + self.window.center[1]
                )

                zone_window = GeoWindow.from_square(
                    x_min=zone_x_min,
                    x_max=zone_x_max,
                    y_min=zone_y_min,
                    y_max=zone_y_max,
                    from_crs=self.crs,
                    to_crs=self.crs,
                )

        buildings_zone = safe_overlay(
            self.rendering_data.buildings.default_buildings,
            zone_window.dataframe,
            OverlayType.INTERSECTION,
        )
        buildings = self.__extract_buildings_data(buildings_zone)
        self.building_renderer.render(
            buildings, self.window.center, buildings_collection_name
        )

        houses_zone = safe_overlay(
            self.rendering_data.buildings.houses,
            zone_window.dataframe,
            OverlayType.INTERSECTION,
        )
        houses = self.__extract_houses_data(houses_zone)
        self.houses_renderer.render(
            houses, self.window.center, buildings_collection_name
        )

        churches_zone = safe_overlay(
            self.rendering_data.buildings.churches,
            zone_window.dataframe,
            OverlayType.INTERSECTION,
        )
        churches = self.__extract_buildings_data(churches_zone)
        self.churches_renderer.render(
            churches, self.window.center, buildings_collection_name
        )

        factories_zone = safe_overlay(
            self.rendering_data.buildings.factories,
            zone_window.dataframe,
            OverlayType.INTERSECTION,
        )
        factories = self.__extract_buildings_data(factories_zone)
        self.factories_renderer.render(
            factories, self.window.center, buildings_collection_name
        )

        malls_zone = safe_overlay(
            self.rendering_data.buildings.malls,
            zone_window.dataframe,
            OverlayType.INTERSECTION,
        )
        malls = self.__extract_buildings_data(malls_zone)
        self.malls_renderer.render(malls, self.window.center, buildings_collection_name)

        forests_zone = safe_overlay(
            self.rendering_data.forests, zone_window.dataframe, OverlayType.INTERSECTION
        )
        forests = self.__extract_geom(forests_zone.geometry)
        self.forests_renderer.render(
            forests, self.window.center, rendering_collection_name
        )
        self.forests_renderer._ForestRenderer__config_geometry_node(
            self.road_renderer.get_mesh_obj(),
            self.building_footprint_renderer.get_mesh_obj(),
            self.terrain_renderer.get_mesh_obj(),
            D.objects[ortho_camera_name].location[2] * 2,
        )

        return zone_window

    def clean_zone(self):

        self.building_renderer.clear_object()

        self.houses_renderer.clear_object()

        self.churches_renderer.clear_object()

        self.malls_renderer.clear_object()

        self.factories_renderer.clear_object()

        self.forests_renderer.clear_object()

    def change_terrain_visibility(self, is_terrain_visible):

        terrain_collection = D.collections[terrain_collection_name].objects
        for terrain in terrain_collection:
            terrain.hide_viewport = not is_terrain_visible
            terrain.hide_render = not is_terrain_visible

    def change_non_sources_visibility(self, is_visible):
        """
        Hides objects that need to be displayed before flood because they interact with terrain, but need to be hidden
        during source computation
        """

        # Decor of terrain needs to be hidden during source computation
        self.terrain_renderer.change_decor_visibility(is_visible)

        for road_object in self.road_renderer.get_meshes_objs():
            road_object.hide_viewport = not is_visible
            road_object.hide_render = not is_visible

        still_water_obj = self.still_water_renderer.get_mesh_obj()
        still_water_obj.hide_viewport = not is_visible
        still_water_obj.hide_render = not is_visible

    def __corner_coord(self, ray_direction, max_distance, origin):

        terrain_collection = D.collections[terrain_collection_name].objects

        coord = None

        terrain_hit = None

        for terrain in terrain_collection:
            ray_result = terrain.ray_cast(origin, ray_direction, distance=max_distance)

            if ray_result[0]:
                coord = ray_result[1]
                terrain_hit = terrain.name

        return coord, terrain_hit

    def __extract_geom(self, geometry_list: g.GeoSeries) -> PolygonList:
        to_return = []
        for x in geometry_list:
            # If it's a multipolygon, it has multiple polygons inside of it that we need to separate for later
            if type(x) == MultiPolygon:
                for y in x.geoms:
                    to_return.append(y)
            else:
                to_return.append(x)

        return to_return

    def __extract_buildings_data(self, buildings: g.GeoDataFrame) -> PolygonList:
        to_return = []

        data = [
            (x[0], x[1])
            for x in buildings[
                [
                    RenderingBuildingDataFrame.number_floors,
                    RenderingBuildingDataFrame.geometry,
                ]
            ]
            .to_numpy()
            .tolist()
        ]
        for x in data:
            # If it's a multipolygon, it has multiple polygons inside of it that we need to separate for later
            if type(x[1]) == MultiPolygon:
                for y in x[1].geoms:
                    to_return.append((x[0], y))
            else:
                to_return.append(x)

        return to_return

    def __extract_houses_data(self, buildings: g.GeoDataFrame) -> PolygonList:
        to_return = []

        data = [
            (x[0], x[1])
            for x in buildings[
                [RenderingBuildingDataFrame.height, RenderingBuildingDataFrame.geometry]
            ]
            .to_numpy()
            .tolist()
        ]
        for x in data:
            # If it's a multipolygon, it has multiple polygons inside of it that we need to separate for later
            if type(x[1]) == MultiPolygon:
                for y in x[1].geoms:
                    to_return.append((x[0], y))
            else:
                to_return.append(x)

        return to_return
